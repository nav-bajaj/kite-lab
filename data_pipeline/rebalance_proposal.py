"""Membership-only rebalance proposal.

Translate a model rebalance into the simple, base-agnostic actions a
subscriber actually takes. See ``tasks/rebalance_page/PLAN.md`` for the product
decisions this encodes:

- **SELL (exit fully)** — a name in the current model book but not in the
  post-rebalance target. Universal: "sell your entire position", no math.
- **BUY (new entry)** — a name entering the target; carries the model's target
  *weight*. Optional rupee sizing is derived from a supplied capital base.
- **HOLD** — a name in both books. We deliberately do *not* surface weight
  drift on continuing holdings as an action (momentum lets winners run; forcing
  per-cycle weight trades is costly and differs per subscriber).

The model speaks in **weights + membership**, never raw share counts — a model
share count is meaningless across subscribers with different rupee bases. Rupee
amounts and share counts are only ever *indicative*, derived from a caller-
supplied capital base (the subscriber's own, client-side, or the model's, for
the admin artifact).

Pure module: no pandas / DB / network, so it is cheap to unit-test.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Mapping, Optional


@dataclass(frozen=True)
class ProposedOrder:
    symbol: str
    side: str                          # "BUY" | "SELL"
    target_weight: float               # post-rebalance model weight (0..1); 0.0 for exits
    est_notional: Optional[float] = None
    est_shares: Optional[int] = None

    def to_row(self) -> dict:
        return {
            "symbol": self.symbol,
            "side": self.side,
            "target_weight": round(self.target_weight, 6),
            "est_notional": (round(self.est_notional, 2)
                             if self.est_notional is not None else ""),
            "est_shares": self.est_shares if self.est_shares is not None else "",
        }


@dataclass(frozen=True)
class RebalanceProposal:
    sells: list = field(default_factory=list)   # full exits
    buys: list = field(default_factory=list)    # new entries
    holds: list = field(default_factory=list)   # continuing symbols (no action)
    capital: Optional[float] = None

    @property
    def has_actions(self) -> bool:
        return bool(self.sells or self.buys)

    def to_rows(self) -> list:
        """Flat rows for ``proposed_orders_<date>.csv`` — sells first, then buys."""
        return [o.to_row() for o in (*self.sells, *self.buys)]

    def to_dict(self) -> dict:
        return {
            "sells": [o.symbol for o in self.sells],
            "buys": [
                {
                    "symbol": o.symbol,
                    "target_weight": round(o.target_weight, 6),
                    "est_notional": o.est_notional,
                    "est_shares": o.est_shares,
                }
                for o in self.buys
            ],
            "holds": list(self.holds),
            "sell_count": len(self.sells),
            "buy_count": len(self.buys),
            "hold_count": len(self.holds),
            "capital": self.capital,
        }


def build_proposal(
    current_symbols: Iterable[str],
    target_weights: Mapping[str, float],
    prices: Optional[Mapping[str, float]] = None,
    capital: Optional[float] = None,
) -> RebalanceProposal:
    """Build a membership-only proposal from the model's current vs target book.

    Args:
        current_symbols: symbols currently held in the model.
        target_weights: post-rebalance model book, ``symbol -> weight`` as a
            fraction in [0, 1] (e.g. ``contribution_pct`` from the holdings
            CSV). Names not present are treated as weight 0 (exited / not held).
        prices: optional ``symbol -> last price`` for share sizing.
        capital: optional rupee base for sizing BUYs. When given,
            ``est_notional = weight * capital`` and, if a positive price is
            known, ``est_shares = round(est_notional / price)``.

    Returns:
        RebalanceProposal with sells / buys / holds, each sorted by symbol.
    """
    current = set(current_symbols)
    target = {s for s, w in target_weights.items() if w and w > 0}
    prices = prices or {}

    sells = [
        ProposedOrder(symbol=s, side="SELL", target_weight=0.0)
        for s in sorted(current - target)
    ]

    buys = []
    for s in sorted(target - current):
        weight = float(target_weights[s])
        est_notional = None
        est_shares = None
        if capital is not None:
            est_notional = weight * capital
            price = prices.get(s)
            if price and price > 0:
                est_shares = int(round(est_notional / price))
        buys.append(ProposedOrder(
            symbol=s,
            side="BUY",
            target_weight=weight,
            est_notional=est_notional,
            est_shares=est_shares,
        ))

    holds = sorted(current & target)

    return RebalanceProposal(sells=sells, buys=buys, holds=holds, capital=capital)


def select_target_membership(
    ranked: list,
    current_symbols: Iterable[str],
    *,
    top_n: int,
    exit_buffer: int,
    is_entry: bool,
    is_bear: bool = False,
    bear_skips_entries: bool = True,
):
    """Mirror the engine's rank + exit-buffer membership rule for one rebalance.

    Reproduces the dominant entry/exit logic in ``scripts/_clean_engine.run_strategy``:
    a held name survives while it stays inside the top ``top_n + exit_buffer``
    by score (the buffer is hysteresis); names that fall outside are exited; on
    an entry rebalance, the highest-ranked names not already held fill the book
    back up to ``top_n``. On an exit-only (off-week) check, no new names enter.

    Known limitation (validated on staging via the reconciliation test): this
    does NOT model ad-hoc per-position exits — the 20%-from-peak trailing stop
    (``atr_min_floor``) or DMA/Donchian exits — which can also sell a name
    mid-cycle. Those surface as extra engine SELLs the rank rule misses.

    Args:
        ranked: symbols by descending score, length ``top_n + exit_buffer``
            (i.e. the engine's ``signals[date]`` list).
        current_symbols: symbols currently held.
        is_entry: True for a biweekly entry rebalance, False for an off-week
            exit-only check.
        is_bear / bear_skips_entries: in a bear regime with entry-skip on
            (om25_v3 / combo_defensive), no new names are added.

    Returns:
        (target_symbols, entries, exits, retained) — all lists, sorted where
        order is not significant; ``entries`` preserves rank order.
    """
    keep_zone = set(ranked[:top_n + exit_buffer])
    target_top = ranked[:top_n]
    # Preserve order, drop dupes.
    current = list(dict.fromkeys(current_symbols))

    retained = [s for s in current if s in keep_zone]
    exits = [s for s in current if s not in keep_zone]

    entries: list = []
    if is_entry and not (is_bear and bear_skips_entries):
        slots = max(0, top_n - len(retained))
        held = set(current)
        for s in target_top:
            if len(entries) >= slots:
                break
            if s not in held:
                entries.append(s)

    target_symbols = retained + entries
    return target_symbols, entries, exits, retained


def propose_next_rebalance(
    ranked: list,
    current_symbols: Iterable[str],
    *,
    top_n: int,
    exit_buffer: int,
    is_entry: bool,
    is_bear: bool = False,
    bear_skips_entries: bool = True,
    prices: Optional[Mapping[str, float]] = None,
    capital: Optional[float] = None,
    entry_weight: Optional[float] = None,
) -> RebalanceProposal:
    """Engine-faithful membership target → membership-only proposal.

    Computes the post-rebalance target via ``select_target_membership`` and
    feeds it to ``build_proposal``, so exits respect the exit-buffer hysteresis
    (not a naive top-N set diff). New entries are sized at ``entry_weight``
    (default equal weight ``1/top_n``).
    """
    target_symbols, _entries, _exits, _retained = select_target_membership(
        ranked, current_symbols,
        top_n=top_n, exit_buffer=exit_buffer, is_entry=is_entry,
        is_bear=is_bear, bear_skips_entries=bear_skips_entries,
    )
    weight = entry_weight if entry_weight is not None else (1.0 / top_n if top_n else 0.0)
    target_weights = {s: weight for s in target_symbols}
    return build_proposal(current_symbols, target_weights, prices=prices, capital=capital)
