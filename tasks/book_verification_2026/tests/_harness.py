"""Shared machinery for the book behaviour suite (TESTS_BOOKS.md).

Three things live here:

* `BookRun`   — the runner's output for one book, loaded from disk.
* `StoreCtx`  — an independent re-assembly of the inputs `scripts/rebuilt_books.build_and_run`
                feeds to the engine (score, regime, weights, membership, sector map, calendar).
* `Replay`    — a per-rebalance re-derivation of what the engine should have done. State at each
                action day is taken from the runner's own trades and equity, so every rebalance is
                judged against the engine's true prior state and one bad month cannot cascade.

The re-assembly deliberately repeats `build_and_run`'s wiring rather than calling it: the point of
the suite is to check that wiring, and a shared helper would hide a drift in it. `test_books_*`
asserts the two agree where they must (A-05, A-06, A-09, F-01).
"""
from __future__ import annotations

import json
import math
import sys
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
for _p in (ROOT, ROOT / "scripts"):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from data_pipeline.loaders import load_price_panels, load_benchmark  # noqa: E402
from data_pipeline.master_store import MASTER as _MASTER  # noqa: E402
from data_pipeline.strategies.blend import make_blend_score  # noqa: E402
from data_pipeline.strategies.calendar import monthly_on_or_after  # noqa: E402
from data_pipeline.strategies.capture import make_capture_score  # noqa: E402
from data_pipeline.strategies.momentum import make_momentum_score  # noqa: E402
from data_pipeline.strategies.regime import roc_regime  # noqa: E402
from data_pipeline.strategies.sectors import load_sector_map  # noqa: E402
from data_pipeline.strategies.sizing import make_inverse_vol_weights, truncate_in_bear  # noqa: E402
from scripts.rebuilt_books import LOCKED  # noqa: E402
from scripts.universe_membership import load_membership, members_asof, resolve_universe  # noqa: E402

BOOKS = ("mm_v1", "om25_v4")
START = "2010-01-01"
MASTER = Path(_MASTER)

# §23 decision line, runner convention, stop_reentry_block=1.
REFERENCE = {"mm_v1": (0.235, -0.263), "om25_v4": (0.226, -0.283)}


# ---------------------------------------------------------------------------
# runner output
# ---------------------------------------------------------------------------
@dataclass
class BookRun:
    book: str
    path: Path
    trades: pd.DataFrame
    exits: pd.DataFrame
    equity: pd.DataFrame
    signals: pd.DataFrame
    metrics: dict

    @property
    def dashboard(self) -> Path:
        return self.path / "backtests" / "baseline"

    @property
    def action_dates(self) -> list[pd.Timestamp]:
        return sorted(self.trades["date"].unique())

    @property
    def buys(self) -> pd.DataFrame:
        return self.trades[self.trades.side == "BUY"]

    @property
    def sells(self) -> pd.DataFrame:
        return self.trades[self.trades.side == "SELL"]


def load_run(book: str, path: Path) -> BookRun:
    return BookRun(
        book=book,
        path=path,
        trades=pd.read_csv(path / f"{book}_trades.csv", parse_dates=["date"]),
        exits=pd.read_csv(path / f"{book}_exits.csv", parse_dates=["entry_date", "exit_date"]),
        equity=pd.read_csv(path / f"{book}_equity.csv", parse_dates=["date"]),
        signals=pd.read_csv(path / f"{book}_signals.csv", parse_dates=["date"]),
        metrics=json.loads((path / "metrics.json").read_text()),
    )


# ---------------------------------------------------------------------------
# store context
# ---------------------------------------------------------------------------
@dataclass
class Panels:
    close: pd.DataFrame
    trade: pd.DataFrame

    @property
    def calendar(self) -> pd.DatetimeIndex:
        return self.close.index


def load_panels(master: Path = MASTER) -> Panels:
    close, trade = load_price_panels(master / "panels/pr")
    return Panels(close=close, trade=trade)


@dataclass
class StoreCtx:
    book: str
    cfg: dict
    panels: Panels
    returns: pd.DataFrame
    regime: pd.Series
    raw_score: object                 # score before the bear truncation
    score: object                     # what the engine receives
    size_weights: object
    membership: pd.DataFrame
    candidate_fn: object
    sector_of: dict
    entries: pd.DatetimeIndex
    benchmark: pd.Series

    @property
    def depth(self) -> int:
        return self.cfg["top_n"] + self.cfg["exit_buffer"]

    def is_bull(self, signal_date) -> bool:
        return bool(self.regime.get(signal_date, True))

    def top_n_at(self, signal_date) -> int:
        return self.cfg["top_n"] if self.is_bull(signal_date) else self.cfg["bear_n"]

    def members_at(self, signal_date) -> set:
        return members_asof(self.membership, signal_date)

    def engine_ranking(self, signal_date) -> list[str]:
        """The ranked list run_strategy precomputes: nlargest(depth) then the remainder descending.

        nlargest and sort_values break ties differently, and the 45/46 boundary decides the keep
        set, so the tie convention has to match the engine's (see the comment at
        scripts/_clean_engine.py:268-277).
        """
        sc = self.score(signal_date)
        if sc is None or sc.empty:
            return []
        head = sc.nlargest(self.depth)
        tail = sc.drop(head.index).sort_values(ascending=False)
        return list(head.index) + list(tail.index)

    def score_window(self, signal_date) -> pd.DataFrame:
        """The momentum leg's window: `lookback` sessions ending `skip` sessions before the signal."""
        i = self.returns.index.get_loc(signal_date)
        lb, sk = self.cfg["lookback"], self.cfg["skip"]
        return self.returns.iloc[i - lb - sk + 1: i - sk + 1]

    def capture_window(self, signal_date) -> pd.DataFrame:
        """The capture leg's window: `lookback` sessions ending at the signal date."""
        i = self.returns.index.get_loc(signal_date)
        return self.returns.iloc[i - self.cfg["lookback"] + 1: i + 1]


def build_ctx(book: str, panels: Panels, start: str = START, master: Path = MASTER) -> StoreCtx:
    cfg = dict(LOCKED[book])
    cal = panels.calendar
    universe, _membership_fn, candidate_fn = resolve_universe(
        master / f"membership/{cfg['universe']}.csv", master / f"membership/{cfg['universe']}.csv")
    cols = [s for s in panels.close.columns if s in universe]
    returns = panels.close[cols].pct_change()
    regime = (roc_regime(master / f"benchmarks/{cfg['regime_index']}.csv", cfg["roc_n"], cfg["confirm"], cal)
              .reindex(cal).ffill().fillna(True).astype(bool))
    mom = make_momentum_score(returns, kind="voladj", lookback=cfg["lookback"], min_obs=cfg["min_obs"],
                              skip=cfg["skip"], candidate_fn=candidate_fn)
    if cfg["score"] == "voladj":
        raw = mom
    else:
        cr = make_capture_score(returns, None, w_uc_bull=0.0, w_cr_bull=1.0, return_filter=True,
                                lookback=cfg["lookback"], min_obs=cfg["min_obs"], candidate_fn=candidate_fn)
        raw = make_blend_score(mom, cr, cfg["mix_w"])
    monthly = monthly_on_or_after(cal, cfg["rebalance_day"])
    entries = monthly[(monthly >= pd.Timestamp(start)) & (monthly <= cal[-1])]
    return StoreCtx(
        book=book, cfg=cfg, panels=panels, returns=returns, regime=regime, raw_score=raw,
        score=truncate_in_bear(raw, regime, cfg["bear_n"] + cfg["bear_buffer"]),
        size_weights=make_inverse_vol_weights(returns, cfg["iv_window"], cfg["max_weight"]),
        membership=load_membership(master / f"membership/{cfg['universe']}.csv"),
        candidate_fn=candidate_fn, sector_of=load_sector_map(), entries=entries,
        benchmark=load_benchmark(master / f"benchmarks/{cfg['regime_index']}_bench.csv").reindex(cal).ffill(),
    )


# ---------------------------------------------------------------------------
# replay
# ---------------------------------------------------------------------------
@dataclass
class Rebalance:
    signal_date: pd.Timestamp
    exec_date: pd.Timestamp
    is_bull: bool
    held_at_open: set                       # before this day's exits
    held_pre_entry: set                     # after this day's exits
    cash_pre_entry: float
    book_value: float                       # the engine's pv2 for this rebalance
    actual_stops: set
    actual_rank_exits: set
    actual_buys: dict                       # symbol -> shares
    expected_stops_engine: set
    expected_stops_literal: set             # peak includes the entry-session close
    expected_stops_signal_only: set         # peak excludes the execution-day close
    expected_rank_exits: set
    expected_entrants: list
    expected_shares: dict
    entry_pool: set
    target_weights: dict
    vol63: dict
    sector_counts_after: dict


@dataclass
class Replay:
    ctx: StoreCtx
    run: BookRun
    rebalances: list = field(default_factory=list)
    equity_error: float = 0.0
    holdings_mismatch_days: int = 0
    partial_sells: int = 0
    held_topups: int = 0
    breach_days_without_trade: int = 0
    same_day_both_sides: int = 0
    final_holdings: dict = field(default_factory=dict)

    def signal_of(self, exec_date) -> pd.Timestamp:
        return self._sigmap[exec_date]

    # -- construction --------------------------------------------------
    def run_all(self) -> "Replay":
        self._build_signal_map()
        self._daily_pass()
        self._rebalance_pass()
        return self

    def _build_signal_map(self):
        cal = self.ctx.panels.calendar
        self._sigmap = {}
        for sd in self.ctx.entries:
            i = cal.get_loc(sd)
            if i + 1 < len(cal):
                self._sigmap[cal[i + 1]] = sd

    def _daily_pass(self):
        """Bookkeeping invariants that need every session: D-06, C-05, D-07, D-08."""
        close = self.ctx.panels.close
        eq = self.run.equity.set_index("date")
        bydate = {d: g for d, g in self.run.trades.groupby("date")}
        shares: dict = {}
        cash = float(self.ctx.cfg["initial_capital"])
        last: dict = {}
        peak: dict = {}
        worst = 0.0
        for dt in eq.index:
            row = close.loc[dt]
            for s in shares:
                p = row.get(s, np.nan)
                if not pd.isna(p):
                    last[s] = p
            for s in list(shares):
                p = row.get(s, np.nan)
                if not pd.isna(p):
                    peak[s] = max(peak.get(s, p), p)
            invested = sum(sh * (row.get(s) if not pd.isna(row.get(s, np.nan)) else last.get(s, 0))
                           for s, sh in shares.items())
            e = eq.loc[dt]
            worst = max(worst, abs(cash + invested - float(e.pv)))
            if len(shares) != int(e.holdings):
                self.holdings_mismatch_days += 1
            if dt not in bydate:
                # C-05: a live breach on a non-action day must not produce a trade
                if any(peak.get(s, 0) > 0 and not pd.isna(row.get(s, np.nan)) and row[s] / peak[s] - 1 < -0.20
                       for s in shares):
                    self.breach_days_without_trade += 1
                continue
            g = bydate[dt]
            held_at_open = set(shares)
            for _, r in g[g.side == "SELL"].iterrows():
                if shares.get(r.symbol, 0) != r.shares:
                    self.partial_sells += 1
                shares[r.symbol] = shares.get(r.symbol, 0) - r.shares
                if shares[r.symbol] <= 0:
                    shares.pop(r.symbol, None)
                    peak.pop(r.symbol, None)
                cash += r.shares * r.price * (1 - self.ctx.cfg["slippage"])
            for sym in g[g.side == "BUY"].symbol.unique():
                if sym in held_at_open and sym in shares:
                    self.held_topups += 1
            for _, r in g[g.side == "BUY"].iterrows():
                first = r.symbol not in shares
                shares[r.symbol] = shares.get(r.symbol, 0) + r.shares
                cash -= r.shares * r.price * (1 + self.ctx.cfg["slippage"])
                if first:
                    peak[r.symbol] = r.price
            sides = g.groupby("symbol").side.nunique()
            self.same_day_both_sides += int((sides > 1).sum())
        self.equity_error = worst
        self.final_holdings = {k: int(v) for k, v in shares.items()}

    def _peak_tracks(self):
        """Three peak conventions, keyed by execution date (C-03, C-04, G-05).

        engine        max(entry trade price, closes from the session after entry through today)
        literal       the same, with the entry session's own close folded in
        signal_only   the engine convention minus the execution-day close
        """
        close = self.ctx.panels.close
        cal = self.ctx.panels.calendar
        bydate = {d: g for d, g in self.run.trades.groupby("date")}
        first = min(bydate)
        out = {k: {} for k in ("engine", "literal", "signal_only")}
        shares: dict = {}
        pk = {k: {} for k in out}
        for dt in cal[cal >= first]:
            row = close.loc[dt]
            held_at_open = set(shares)
            for kind in ("engine", "literal"):
                for s in held_at_open:
                    p = row.get(s, np.nan)
                    if not pd.isna(p) and s in pk[kind]:
                        pk[kind][s] = max(pk[kind][s], p)
            if dt in bydate:
                for kind in out:
                    out[kind][dt] = {s: pk[kind][s] for s in held_at_open if s in pk[kind]}
                g = bydate[dt]
                for _, r in g[g.side == "SELL"].iterrows():
                    shares[r.symbol] = shares.get(r.symbol, 0) - r.shares
                    if shares[r.symbol] <= 0:
                        shares.pop(r.symbol, None)
                        for kind in out:
                            pk[kind].pop(r.symbol, None)
                for _, r in g[g.side == "BUY"].iterrows():
                    new = r.symbol not in shares
                    shares[r.symbol] = shares.get(r.symbol, 0) + r.shares
                    if new:
                        for kind in out:
                            pk[kind][r.symbol] = r.price
                        p = row.get(r.symbol, np.nan)
                        if not pd.isna(p):
                            pk["literal"][r.symbol] = max(pk["literal"][r.symbol], p)
            for s in list(shares):
                if s not in held_at_open:
                    continue
                p = row.get(s, np.nan)
                if not pd.isna(p) and s in pk["signal_only"]:
                    pk["signal_only"][s] = max(pk["signal_only"][s], p)
        return out

    def _rebalance_pass(self):
        ctx, run = self.ctx, self.run
        cfg = ctx.cfg
        close, trade = ctx.panels.close, ctx.panels.trade
        eq = run.equity.set_index("date")
        bydate = {d: g for d, g in run.trades.groupby("date")}
        peaks = self._peak_tracks()
        ivol_std = ctx.returns.rolling(cfg["iv_window"], min_periods=int(cfg["iv_window"] * 0.8)).std()
        slip = cfg["slippage"]
        exec_dates = sorted(bydate)
        shares: dict = {}
        stopped_on: dict = {}
        for dt in exec_dates:
            g = bydate[dt]
            sd = self._sigmap[dt]
            row = close.loc[dt]
            srow = close.loc[sd]
            cash = float(eq.loc[dt, "cash"])
            held_at_open = set(shares)

            exp_stops = {}
            for kind, track in peaks.items():
                snap = track.get(dt, {})
                exp_stops[kind] = {s for s, p in snap.items()
                                   if s in held_at_open and p > 0
                                   and not pd.isna(srow.get(s, np.nan)) and srow[s] / p - 1 < -cfg["trailing_stop"]}

            actual_stops = set(g[(g.side == "SELL") & (g.reason == "atr_stop")].symbol)
            actual_rank = set(g[(g.side == "SELL") & (g.reason == "rank")].symbol)

            ranked_all = ctx.engine_ranking(sd)
            members = ctx.members_at(sd)
            ranked = [s for s in ranked_all if s in members or s in held_at_open]
            keep = set(ranked[:ctx.depth])
            exp_rank = {s for s in held_at_open if s not in keep} - actual_stops

            for _, r in g[g.side == "SELL"].iterrows():
                if r.reason == "atr_stop":
                    stopped_on[r.symbol] = dt
                shares[r.symbol] = shares.get(r.symbol, 0) - r.shares
                if shares[r.symbol] <= 0:
                    shares.pop(r.symbol, None)
                cash += r.shares * r.price * (1 - slip)
            held_pre_entry = set(shares)

            tn = ctx.top_n_at(sd)
            pool = [s for s in ranked[:tn + cfg["exit_buffer"]] if s not in shares]
            blocked = {s for s in pool if s in stopped_on
                       and sum(1 for d in exec_dates if stopped_on[s] < d <= dt) < cfg["stop_reentry_block"]}
            cand = [s for s in pool if s not in blocked]
            counts: dict = {}
            for h in shares:
                k = ctx.sector_of.get(h)
                counts[k] = counts.get(k, 0) + 1
            kept = []
            for s in cand:
                k = ctx.sector_of.get(s)
                if k is not None and counts.get(k, 0) >= cfg["sector_cap"]:
                    continue
                kept.append(s)
                counts[k] = counts.get(k, 0) + 1
            entrants = kept[:max(0, tn - len(shares))]

            pv2 = cash + sum(sh * (row.get(s) if not pd.isna(row.get(s, np.nan)) else 0.0)
                             for s, sh in shares.items())
            bought: dict = {}
            wmap: dict = {}
            if entrants:
                n = len(shares) + len(entrants)
                stock_w = min(1.0 / n if n else 0.0, cfg["max_weight"])
                tgt = pv2 * stock_w
                wmap = ctx.size_weights(sd, list(shares.keys()) + entrants) or {}
                tgt_map = {s: pv2 * min(float(wmap.get(s, stock_w)), cfg["max_weight"]) for s in entrants}
                tgt_sum = sum(tgt_map.values()) or 1.0
                cash0 = cash
                spent = {s: 0.0 for s in entrants}
                for s in entrants:
                    px = trade.loc[dt, s] if s in trade.columns else np.nan
                    if pd.isna(px) or px <= 0:
                        continue
                    budget = min(tgt_map[s], (cash0 * 0.99) * tgt_map[s] / tgt_sum)
                    if budget <= 0:
                        break
                    sh = math.floor(budget / (px * (1 + slip)))
                    if sh < 1:
                        continue
                    cost = sh * px * (1 + slip)
                    if cost > cash:
                        continue
                    bought[s] = bought.get(s, 0) + sh
                    cash -= cost
                    spent[s] += cost
                min_topup = tgt * 0.10
                if cash > min_topup:
                    for s in entrants:
                        room = tgt_map[s] - spent.get(s, 0)
                        if room < min_topup:
                            continue
                        px = trade.loc[dt, s] if s in trade.columns else np.nan
                        if pd.isna(px) or px <= 0:
                            continue
                        alloc = min(room, cash * 0.99)
                        if alloc < min_topup:
                            continue
                        sh = math.floor(alloc / (px * (1 + slip)))
                        if sh < 1:
                            continue
                        cost = sh * px * (1 + slip)
                        if cost > cash:
                            continue
                        bought[s] = bought.get(s, 0) + sh
                        cash -= cost
                        spent[s] += cost

            actual_buys = {k: int(v) for k, v in g[g.side == "BUY"].groupby("symbol").shares.sum().items()}
            for _, r in g[g.side == "BUY"].iterrows():
                shares[r.symbol] = shares.get(r.symbol, 0) + r.shares

            sec_after: dict = {}
            for h in shares:
                k = ctx.sector_of.get(h)
                if k is None:
                    continue
                sec_after[k] = sec_after.get(k, 0) + 1

            self.rebalances.append(Rebalance(
                signal_date=sd, exec_date=dt, is_bull=ctx.is_bull(sd),
                held_at_open=held_at_open, held_pre_entry=held_pre_entry, cash_pre_entry=float(eq.loc[dt, "cash"]),
                book_value=pv2, actual_stops=actual_stops, actual_rank_exits=actual_rank,
                actual_buys=actual_buys,
                expected_stops_engine=exp_stops["engine"], expected_stops_literal=exp_stops["literal"],
                expected_stops_signal_only=exp_stops["signal_only"], expected_rank_exits=exp_rank,
                expected_entrants=entrants, expected_shares={k: int(v) for k, v in bought.items()},
                entry_pool=set(ranked[:tn + cfg["exit_buffer"]]), target_weights=wmap,
                vol63={s: float(ivol_std.loc[sd, s]) for s in entrants
                       if s in ivol_std.columns and not pd.isna(ivol_std.loc[sd, s])},
                sector_counts_after=sec_after,
            ))
