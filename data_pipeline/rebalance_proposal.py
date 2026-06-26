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

