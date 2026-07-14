"""End-of-day engine readout: turn the engine's signal-day decision into a
membership-only ``proposed_orders_<exec_date>.csv`` + a regime / drawdown
summary, ready for the rebalance page to display.

How it works (see ``tasks/rebalance_page/PLAN.md`` Phase 2):

The strategy engine in ``scripts/_clean_engine.py:run_strategy`` is strict
signal/execution split — it never records a rebalance until the **next**
trading bar exists in the calendar. On the signal day (typically a Friday)
at 16:00 IST, the bar we need has not yet happened. So we:

1. Load the real price panels (close, trade-OHLC/4).
2. Pick the **signal date** (latest entry date in the strategy's cadence
   that is in our data).
3. Append a **placeholder** next-trading-day bar to every panel where each
   column equals that symbol's signal-day close. This:
   - puts a date past ``signal_date`` into the calendar so
     ``map_signal_to_trade`` returns it,
   - gives the engine a fill price (signal-day close) for any BUY/SELL it
     wants to do at the rebalance; the price is a stand-in and irrelevant
     because we surface weights, not absolute fills.
4. Run the engine over the extended calendar. It executes the rebalance on
   the placeholder day.
5. Slice the engine's trade ledger at the placeholder date and turn it
   into a membership-only proposal via
   ``data_pipeline.engine_readout.partition_membership_by_date`` (the gotcha
   from PLAN: ignore partial trims on continuing names; act only on the
   net 0↔held transitions).
6. Compute target weights for the **post-rebalance** holdings from the
   engine's own holdings × signal-day close ÷ engine-end portfolio value
   (= ``contribution_pct`` semantics).
7. Hand it to ``data_pipeline.rebalance_proposal.build_proposal`` which
   writes SELL / BUY / HOLD with optional rupee sizing.
8. Write ``proposed_orders_<exec_date>.csv`` + ``proposed_regime.json``
   into ``<run-dir>/backtests/baseline/`` (same place the dashboard sync
   reads from).

Strategy dispatch lives in ``_STRATEGIES``. Adding a new one means writing
a small ``_prepare_<strategy>`` that returns the kwargs ``run_strategy``
needs (panels, score_fn, entry_dates, weekly_dates, regime_panel, etc.).
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from data_pipeline.engine_readout import (
    holdings_from_trades,
    partition_membership_by_date,
)
from data_pipeline.loaders import load_benchmark, load_price_panels
from data_pipeline.rebalance_proposal import build_proposal


# ============================================================
# Strategy prep — one adapter per supported strategy
# ============================================================

@dataclass
class StrategyState:
    """Everything ``run_strategy`` needs to compute the signal-day rebalance.

    Strategy-agnostic container so the EOD producer can dispatch by name
    and the engine call below stays one function for every strategy.
    """
    close_panel: pd.DataFrame
    trade_panel: pd.DataFrame
    benchmark_aligned: pd.Series
    sma_200: pd.DataFrame
    atr_20: pd.DataFrame
    score_fn: Callable
    entry_signal_dates: pd.DatetimeIndex
    weekly_signal_dates: pd.DatetimeIndex
    top_n: int
    exit_buffer: int
    max_weight: float
    slippage: float
    drawdown_stop: float
    weekly_rank_check: bool = False
    regime_panel: Optional[pd.Series] = None
    bear_exposure: float = 0.0
    # Minimum trading-days a holding must sit before rank-out can fire on
    # it. l6_v2's BASELINE sets this to 8; om25_v3 / tl25_v3 leave it at
    # the engine default (0) because they lean on exit_buffer + weekly
    # rank-exit for churn control. Missing this on l6_v2 causes freshly
    # bought names to be rank-out'd on the very next signal day, which
    # is not what the daily-runner backtest does (verified via BHARATFORG
    # bought 2026-06-29, showing up as SELL on the 2026-07-02 proposal
    # before this fix).
    min_hold_days: int = 0
    # Effective-dated universe membership (mirrors each runner's
    # --membership resolution). None = legacy snapshot behavior. Missing
    # this while the runners have it would make proposals force-exit
    # grandfathered ex-members the daily backtest keeps holding.
    membership_fn: Optional[Callable] = None


def _prepare_om25_v3(*, prices_dir: Path) -> StrategyState:
    from scripts._clean_engine import biweekly_fridays, fridays
    from scripts.build_om25_signals import load_universe
    from scripts.om25_v3 import (
        LOCKED, build_regime_panel_confirmed, make_om25_tilt_score,
    )

    close_panel, trade_panel = load_price_panels(prices_dir)
    benchmark = load_benchmark(ROOT / "data/benchmarks/nifty100.csv")
    calendar = close_panel.index
    benchmark_aligned = benchmark.reindex(calendar).ffill()
    sma_200 = close_panel.rolling(200, min_periods=200).mean()
    atr_20 = close_panel.pct_change().rolling(20).std()

    weekly_filt = fridays(calendar)
    entry_dates = biweekly_fridays(calendar)

    from scripts.universe_membership import resolve_universe
    universe, membership_fn, candidate_fn = resolve_universe(
        ROOT / "data/static/nifty250_membership.csv",
        ROOT / LOCKED["universe_csv"])
    cols = [s for s in close_panel.columns if s in universe]
    returns_uni = close_panel[cols].pct_change()

    # LOCKED["regime_index_path"] defaults to indices_data_historical/... which
    # only exists locally. On Railway the live NIFTY_100 CSV is refreshed each
    # daily_pipeline by scripts/fetch_indices_history.py at indices_data/. The
    # production runners (scripts/update_all_portfolios.py line 77) point at
    # that live path via --regime-index indices_data/NIFTY_100.csv. Match that
    # here, falling back to the LOCKED path for local dev where the historical
    # dir is the source of truth.
    regime_candidates = [
        ROOT / "indices_data" / "NIFTY_100.csv",         # Railway daily-runner path
        ROOT / "data" / "indices_data" / "NIFTY_100.csv",# alt persistent-volume symlink
        ROOT / LOCKED["regime_index_path"],              # local research default
    ]
    regime_index_path = next((p for p in regime_candidates if p.is_file()),
                              regime_candidates[-1])
    regime = build_regime_panel_confirmed(
        regime_index_path,
        LOCKED["regime_ma_window"], LOCKED["regime_confirm_days"],
        calendar=calendar,
    )

    score_fn = make_om25_tilt_score(
        returns_uni, regime,
        bull_w_uc=LOCKED["bull_w_uc"], bull_w_cr=LOCKED["bull_w_cr"],
        bear_w_uc=LOCKED["bear_w_uc"], bear_w_cr=LOCKED["bear_w_cr"],
        return_filter=LOCKED["return_filter"],
        lookback=LOCKED["lookback"], min_obs=LOCKED["min_obs"],
        candidate_fn=candidate_fn,
    )

    return StrategyState(
        close_panel=close_panel, trade_panel=trade_panel,
        benchmark_aligned=benchmark_aligned,
        sma_200=sma_200, atr_20=atr_20,
        score_fn=score_fn,
        entry_signal_dates=entry_dates, weekly_signal_dates=weekly_filt,
        top_n=LOCKED["top_n"], exit_buffer=LOCKED["exit_buffer"],
        max_weight=LOCKED["max_weight"], slippage=LOCKED["slippage"],
        drawdown_stop=LOCKED["drawdown_stop_pct"],
        weekly_rank_check=False,
        # IMPORTANT: production `run_om25_v3_portfolio.py` passes
        # ``regime_panel=None`` — regime is consumed only through the
        # score function (via ``make_om25_tilt_score`` bull/bear weight
        # tilt). Passing it here too would activate the engine's
        # ``bear_skips_entries=True`` + ``bear_exposure=0.0`` scale-down
        # path, which the production runner deliberately doesn't use;
        # over an 8-year warmup that empties the book and the producer
        # emits "0 continuing, 25 entries" every cycle. Score fn already
        # captured the regime signal via the closure above.
        regime_panel=None, bear_exposure=0.0,
        membership_fn=membership_fn,
    )


def _prepare_tl25_v3(*, prices_dir: Path) -> StrategyState:
    from scripts._clean_engine import biweekly_fridays, fridays
    from scripts.build_om25_signals import load_universe
    from scripts.tl25_v3 import V3_LOCKED, build_tl25_panels, make_tl25_score

    close_panel, trade_panel = load_price_panels(prices_dir)
    benchmark = load_benchmark(ROOT / "data/benchmarks/nifty100.csv")
    calendar = close_panel.index
    benchmark_aligned = benchmark.reindex(calendar).ffill()
    sma_200 = close_panel.rolling(200, min_periods=200).mean()
    atr_20 = close_panel.pct_change().rolling(20).std()

    weekly_filt = fridays(calendar)
    entry_dates = biweekly_fridays(calendar)

    from scripts.universe_membership import resolve_universe
    universe, membership_fn, candidate_fn = resolve_universe(
        ROOT / "data/static/nse500_membership.csv",
        ROOT / V3_LOCKED["universe_csv"])
    cols = [s for s in close_panel.columns if s in universe]
    close_uni = close_panel[cols]
    panels = build_tl25_panels(
        close_uni,
        dma_short=V3_LOCKED["dma_short"],
        dma_long=V3_LOCKED["dma_long"],
        dma_persist_ref=V3_LOCKED["dma_persist_ref"],
        persistence_window=V3_LOCKED["persistence_window"],
        drawdown_window=V3_LOCKED["drawdown_window"],
        drawdown_concavity=V3_LOCKED["drawdown_concavity"],
        momentum_window=V3_LOCKED["momentum_window"],
    )
    score_fn = make_tl25_score(
        panels,
        w_persistence=V3_LOCKED["w_persistence"],
        w_drawdown=V3_LOCKED["w_drawdown"],
        w_momentum=V3_LOCKED["w_momentum"],
        candidate_fn=candidate_fn,
    )

    return StrategyState(
        close_panel=close_panel, trade_panel=trade_panel,
        benchmark_aligned=benchmark_aligned,
        sma_200=sma_200, atr_20=atr_20,
        score_fn=score_fn,
        entry_signal_dates=entry_dates, weekly_signal_dates=weekly_filt,
        top_n=V3_LOCKED["top_n"], exit_buffer=V3_LOCKED["exit_buffer"],
        max_weight=V3_LOCKED["max_weight"], slippage=V3_LOCKED["slippage"],
        drawdown_stop=V3_LOCKED["atr_min_floor"],
        weekly_rank_check=True,
        regime_panel=None, bear_exposure=0.0,
        membership_fn=membership_fn,
    )


def _prepare_l6_v2(*, prices_dir: Path) -> StrategyState:
    """Core Momentum (l6_v2) — weekly Thursday-signal cadence.

    Reuses ``scripts._momentum_engine.build_momentum_panels`` +
    ``make_momentum_score`` (the same L6 config the daily runner in
    ``scripts/run_l6_v2_portfolio.py`` uses). BASELINE lives in
    ``_momentum_engine.BASELINE``; we don't override.
    """
    from scripts._clean_engine import thursdays
    from scripts._momentum_engine import (
        BASELINE, build_momentum_panels, lookback_months_to_days,
        make_momentum_score,
    )
    from scripts.build_om25_signals import load_universe

    close_panel, trade_panel = load_price_panels(prices_dir)
    # L6's daily runner uses the nifty100 benchmark by default (nse500-index
    # data isn't part of the price panel dir); the score is universe-relative
    # so the choice of benchmark doesn't affect signal membership, only the
    # equity-curve comparison line.
    benchmark = load_benchmark(ROOT / "data/benchmarks/nifty100.csv")
    calendar = close_panel.index
    benchmark_aligned = benchmark.reindex(calendar).ffill()
    sma_200 = close_panel.rolling(200, min_periods=200).mean()
    atr_20 = close_panel.pct_change().rolling(20).std()

    # Weekly Thursday entry + weekly Thursday DD-check (same series). L6 has
    # no biweekly parity to preserve — every trading Thursday is a signal.
    entry_dates = thursdays(calendar)
    weekly_dates = entry_dates

    from scripts.universe_membership import resolve_universe
    universe, membership_fn, _candidate_fn = resolve_universe(
        ROOT / "data/static/nse500_membership.csv",
        ROOT / BASELINE["universe_csv"])
    cols = [s for s in close_panel.columns if s in universe]
    close_uni = close_panel[cols]

    lookback_days = lookback_months_to_days(BASELINE["lookback_months"])
    panels = build_momentum_panels(
        close_uni,
        lookback_days=lookback_days,
        skip_days=BASELINE["skip_days"],
    )
    score_fn = make_momentum_score(
        panels,
        vol_floor=BASELINE["vol_floor"],
        vol_power=BASELINE["vol_power"],
        cross_sectional_zscore=BASELINE["cross_sectional_zscore"],
    )

    return StrategyState(
        close_panel=close_panel, trade_panel=trade_panel,
        benchmark_aligned=benchmark_aligned,
        sma_200=sma_200, atr_20=atr_20,
        score_fn=score_fn,
        entry_signal_dates=entry_dates, weekly_signal_dates=weekly_dates,
        top_n=BASELINE["top_n"], exit_buffer=BASELINE["exit_buffer"],
        max_weight=BASELINE["max_weight"], slippage=BASELINE["slippage"],
        drawdown_stop=BASELINE["drawdown_stop"],
        weekly_rank_check=False,
        regime_panel=None, bear_exposure=0.0,
        membership_fn=membership_fn,
        min_hold_days=BASELINE["min_hold_days"],
    )


def _prepare_combo_defensive(*, prices_dir: Path) -> StrategyState:
    """Defensive Blend — 50-50 L6 + OM25 v3 with priority dedup + NIFTY 100
    100-DMA regime overlay (bear_exposure=0.5).

    Mirrors ``scripts/run_combo_defensive_portfolio.py`` line-for-line:
    two component score fns, priority dedup via ``make_combo_score_fn``,
    biweekly Friday cadence, portfolio-level regime overlay (unlike
    om25_v3, this strategy DOES use the engine's regime scaling — it's
    what makes it "defensive").
    """
    from scripts._clean_engine import biweekly_fridays, fridays
    from scripts._momentum_engine import (
        BASELINE as MM_BASELINE, build_momentum_panels,
        lookback_months_to_days, make_momentum_score,
    )
    from scripts.build_om25_signals import load_universe
    from scripts.combo_defensive import LOCKED, make_combo_score_fn
    from scripts.om25_v3 import (
        LOCKED as OM25_LOCKED, build_regime_panel_confirmed,
        make_om25_tilt_score,
    )

    close_panel, trade_panel = load_price_panels(prices_dir)
    benchmark = load_benchmark(ROOT / "data/benchmarks/nifty100.csv")
    calendar = close_panel.index
    benchmark_aligned = benchmark.reindex(calendar).ffill()
    sma_200 = close_panel.rolling(200, min_periods=200).mean()
    atr_20 = close_panel.pct_change().rolling(20).std()

    # Same regime-index resolution logic as _prepare_om25_v3 — production
    # writes to indices_data/, local research keeps _historical.
    regime_candidates = [
        ROOT / "indices_data" / "NIFTY_100.csv",
        ROOT / "data" / "indices_data" / "NIFTY_100.csv",
        ROOT / LOCKED["regime_index_path"],
    ]
    regime_index_path = next((p for p in regime_candidates if p.is_file()),
                              regime_candidates[-1])

    from scripts.universe_membership import resolve_universe, union_membership_fns

    # L6 component (NSE 500)
    l6_uni, l6_membership_fn, _l6_candidate_fn = resolve_universe(
        ROOT / "data/static/nse500_membership.csv",
        ROOT / LOCKED["l6_universe_csv"])
    l6_cols = [s for s in close_panel.columns if s in l6_uni]
    l6_panels = build_momentum_panels(
        close_panel[l6_cols],
        lookback_days=lookback_months_to_days(LOCKED["l6_lookback_months"]),
        skip_days=LOCKED["l6_skip_days"],
    )
    l6_score = make_momentum_score(
        l6_panels, vol_floor=LOCKED["l6_vol_floor"],
        vol_power=LOCKED["l6_vol_power"], cross_sectional_zscore=True,
    )

    # OM25 v3 component (Nifty 250) — carries its own regime tilt in the
    # score fn, separate from the portfolio-level overlay applied by the
    # engine below.
    om25_uni, om25_membership_fn, om25_candidate_fn = resolve_universe(
        ROOT / "data/static/nifty250_membership.csv",
        ROOT / LOCKED["om25_universe_csv"])
    om25_cols = [s for s in close_panel.columns if s in om25_uni]
    om25_returns = close_panel[om25_cols].pct_change()
    om25_regime = build_regime_panel_confirmed(
        regime_index_path,
        OM25_LOCKED["regime_ma_window"], OM25_LOCKED["regime_confirm_days"],
        calendar=calendar,
    )
    om25_score = make_om25_tilt_score(
        om25_returns, om25_regime,
        bull_w_uc=LOCKED["om25_bull_w_uc"], bull_w_cr=LOCKED["om25_bull_w_cr"],
        bear_w_uc=LOCKED["om25_bear_w_uc"], bear_w_cr=LOCKED["om25_bear_w_cr"],
        return_filter=LOCKED["om25_return_filter"],
        lookback=LOCKED["om25_lookback"], min_obs=LOCKED["om25_min_obs"],
        candidate_fn=om25_candidate_fn,
    )

    combo_score = make_combo_score_fn(
        [("L6", l6_score), ("OM25", om25_score)],
        n_per=LOCKED["n_per_strategy"],
    )

    portfolio_regime = build_regime_panel_confirmed(
        regime_index_path,
        LOCKED["regime_ma_window"], LOCKED["regime_confirm_days"],
        calendar=calendar,
    )

    # Biweekly Friday entry, weekly Friday DD checks.
    weekly_dates = fridays(calendar)
    entry_dates = biweekly_fridays(calendar)

    return StrategyState(
        close_panel=close_panel, trade_panel=trade_panel,
        benchmark_aligned=benchmark_aligned,
        sma_200=sma_200, atr_20=atr_20,
        score_fn=combo_score,
        entry_signal_dates=entry_dates, weekly_signal_dates=weekly_dates,
        top_n=LOCKED["top_n"], exit_buffer=LOCKED["exit_buffer"],
        max_weight=LOCKED["max_weight"], slippage=LOCKED["slippage"],
        drawdown_stop=0.0,     # combo relies on regime overlay for defense
        weekly_rank_check=False,
        # Combo DOES use the engine's regime scaling — that's the defensive
        # piece. bear_exposure=0.5 keeps 50% invested when the panel says bear.
        regime_panel=portfolio_regime,
        bear_exposure=LOCKED["regime_bear_exposure"],
        membership_fn=(union_membership_fns([l6_membership_fn,
                                             om25_membership_fn])
                       if (l6_membership_fn or om25_membership_fn) else None),
        min_hold_days=LOCKED["min_hold_days"],
    )


_STRATEGIES = {
    "om25_v3": _prepare_om25_v3,
    "tl25_v3": _prepare_tl25_v3,
    "l6_v2": _prepare_l6_v2,
    "combo_defensive": _prepare_combo_defensive,
}


# ============================================================
# Panel extension — placeholder next-day bar
# ============================================================

def _append_placeholder_bar(state: StrategyState, signal_date: pd.Timestamp,
                             next_trading_day: Optional[Callable] = None,
                             ) -> pd.Timestamp:
    """Extend every date-indexed panel by one trading day, set to signal-day
    levels. Returns the placeholder date (= ``exec_date``).

    ``next_trading_day``: optional ``date -> date`` returning the first NSE
    trading day strictly after its argument (the production caller passes
    ``market_service.next_trading_day_after``). When given, the placeholder /
    exec_date rolls off NSE holidays too, so ``ProposedRebalance.exec_date``
    agrees with ``/summary``'s holiday-aware ``next.exec_date`` (audit L6):
    e.g. a Thursday signal before a Friday holiday resolves to Monday, not the
    closed Friday. Without it, we fall back to a weekend-only bump.
    """
    cal = state.close_panel.index
    if signal_date not in cal:
        raise ValueError(f"Signal date {signal_date.date()} not in price calendar")

    if next_trading_day is not None:
        candidate = pd.Timestamp(next_trading_day(signal_date.date()))
    else:
        # signal_date + 1 calendar day; if it lands on a weekend, push to Monday.
        candidate = signal_date + pd.Timedelta(days=1)
        while candidate.weekday() >= 5:
            candidate += pd.Timedelta(days=1)
    if candidate in cal:
        # Don't double-append if for some reason the next day already exists.
        return candidate

    # Build the placeholder row from signal-date values.
    close_row = state.close_panel.loc[signal_date]
    trade_row = state.trade_panel.loc[signal_date]

    state.close_panel.loc[candidate] = close_row
    state.close_panel.sort_index(inplace=True)
    state.trade_panel.loc[candidate] = trade_row
    state.trade_panel.sort_index(inplace=True)

    # Derived panels: carry forward signal-date values.
    state.sma_200.loc[candidate] = state.sma_200.loc[signal_date]
    state.sma_200.sort_index(inplace=True)
    state.atr_20.loc[candidate] = state.atr_20.loc[signal_date]
    state.atr_20.sort_index(inplace=True)

    # Benchmark + regime — single Series.
    bm_extended = state.benchmark_aligned.reindex(
        state.close_panel.index
    ).ffill()
    state.benchmark_aligned = bm_extended
    if state.regime_panel is not None:
        state.regime_panel = state.regime_panel.reindex(
            state.close_panel.index
        ).ffill()

    return candidate


# ============================================================
# Public entry: build the EOD artifact
# ============================================================

def _pick_signal_date(state: StrategyState,
                       requested: Optional[pd.Timestamp],
                       mode: str = "entry") -> pd.Timestamp:
    """Choose the signal date.

    ``mode="entry"`` (default): the latest **entry-cadence** date at or
    before ``requested`` (or the panel's last trading day if no override).
    Snaps back to the entry-cadence series so a biweekly strategy picks a
    biweekly Friday even when today is an off-week Friday.

    ``mode="exit_only"``: the latest **weekly** cadence date at or before
    ``requested``. For biweekly strategies with weekly exit checks (the
    ``has_weekly_exit`` cadences — om25_v3, tl25_v3, combo_defensive) this
    lets the caller preview an off-week Friday's rank/DD-stop exits before
    Monday's execution bar exists. l6_v2 is weekly Thu-Fri so its "weekly"
    series is the same as its entry series — exit_only ≡ entry for it.
    """
    cap = (requested if requested is not None
           else state.close_panel.index[-1])
    series = (state.weekly_signal_dates if mode == "exit_only"
              else state.entry_signal_dates)
    eligible = series[series <= cap]
    if len(eligible) == 0:
        raise ValueError(
            f"No {mode} signal date on/before {cap.date()} — "
            f"is the cadence index empty?"
        )
    return pd.Timestamp(eligible[-1])


def _assert_panel_fresh(last_bar, require_through, strategy: str) -> None:
    """Refuse to build a proposal from a stale price panel.

    On a real signal day the 16:00 data refresh must have written today's close,
    so the panel's last bar should reach ``require_through`` (today). If the
    refresh silently failed the panel ends earlier and ``_pick_signal_date``
    would pick the *previous* cadence date — emitting a back-dated proposal that
    the API then serves as "upcoming" (audit L5). Raise instead.
    """
    last = pd.Timestamp(last_bar).normalize()
    need = pd.Timestamp(require_through).normalize()
    if last < need:
        raise RuntimeError(
            f"Stale price panel for {strategy}: last bar {last.date()} is before "
            f"required {need.date()} — the data refresh likely failed; refusing "
            f"to emit a back-dated proposal."
        )


def _final_pv(equity_df: pd.DataFrame) -> float:
    return float(equity_df["pv"].iloc[-1])


def _build_target_weights(*, holdings: dict, close_row: pd.Series,
                           final_pv: float) -> dict:
    """target_weights[sym] = shares × signal_day_close ÷ portfolio_value.

    Same semantics as ``momentum_holdings.csv:contribution_pct`` — weights
    sum to ≤1.0 (residual is cash, which naturally appears in bear-regime
    de-risked books).
    """
    out: dict = {}
    if final_pv <= 0:
        return out
    for sym, sh in holdings.items():
        if sh <= 0:
            continue
        p = close_row.get(sym, np.nan)
        if pd.isna(p) or p <= 0:
            continue
        out[sym] = float(sh * p) / final_pv
    return out


def _regime_status(state: StrategyState, signal_date: pd.Timestamp) -> dict:
    """Pull a regime / risk readout for the page's `Regime & risk` strip."""
    if state.regime_panel is None:
        return {"regime": None}
    try:
        rv = state.regime_panel.get(signal_date, None)
    except Exception:
        rv = None
    if rv is None:
        return {"regime": None}
    if isinstance(rv, (bool, np.bool_)):
        return {"regime": "bull" if bool(rv) else "bear"}
    return {"regime": "bull" if float(rv) >= 1.0 else "bear",
            "target_exposure": float(rv)}


def _drawdown_from_peak(equity_df: pd.DataFrame) -> float:
    pv = equity_df["pv"].astype(float)
    peak = pv.cummax()
    return float((pv.iloc[-1] / peak.iloc[-1] - 1.0))


def build_eod_artifact(*,
                        strategy: str,
                        prices_dir: Path,
                        output_dir: Path,
                        signal_date: Optional[pd.Timestamp] = None,
                        initial_capital: float = 1_000_000,
                        backtest_start: str = "2016-01-01",
                        mode: str = "entry",
                        require_panel_through: Optional[pd.Timestamp] = None,
                        next_trading_day: Optional[Callable] = None,
                        ) -> dict:
    """Produce ``proposed_orders_<exec_date>.csv`` + ``proposed_regime.json``.

    Args:
        strategy: key into ``_STRATEGIES``.
        prices_dir: directory of ``<symbol>_day.csv`` panels.
        output_dir: directory to write artifacts to (will be created). The
            convention is ``<run-dir>/backtests/baseline/`` so the dashboard
            sync can find it next to ``momentum_*.csv``.
        signal_date: optional override. If absent, the latest cadence date
            at or before the panel's last trading day is used.
        initial_capital: rupee base for sizing the BUYs in the artifact. The
            client UI re-derives ₹ from its own ``portfolio_value``, but the
            artifact carries a sized version for any admin readout.
        backtest_start: start date for the warmup pass (so signal scores and
            holdings have data prior to ``signal_date``).
        mode: ``"entry"`` (default) picks the latest entry-cadence Friday —
            full rebalance with exits + new entries. ``"exit_only"`` picks
            the latest **weekly** cadence Friday (which for biweekly
            strategies is *every* Friday, including off-week ones), and
            filters ``entry_dates`` so the engine's entry block cannot fire
            — the artifact then surfaces only rank / DD-stop / regime SELLs.
            Semantically a no-op for weekly strategies (l6_v2) where
            weekly ≡ entry, so callers can dispatch either.
        require_panel_through: if set, refuse to run unless the price panel's
            last bar reaches this date. The production cron passes today so a
            failed data refresh raises instead of emitting a back-dated
            proposal. Left None for past-date verification/backfill runs.
        next_trading_day: optional ``date -> date`` (NSE-holiday-aware) used to
            place the exec_date bar; see ``_append_placeholder_bar``. The
            production CLI passes ``market_service.next_trading_day_after`` so
            exec_date labels roll off holidays consistently with ``/summary``.

    Returns:
        Summary dict written to ``proposed_regime.json``.
    """
    if strategy not in _STRATEGIES:
        raise ValueError(
            f"Unknown strategy {strategy!r}; supported: {list(_STRATEGIES)}"
        )
    if mode not in ("entry", "exit_only"):
        raise ValueError(f"Unknown mode {mode!r}; use 'entry' or 'exit_only'")
    print(f"[eod] strategy={strategy} prices={prices_dir.name} mode={mode}")

    state = _STRATEGIES[strategy](prices_dir=prices_dir)
    if require_panel_through is not None:
        _assert_panel_fresh(state.close_panel.index[-1], require_panel_through,
                            strategy)
    signal_ts = _pick_signal_date(state, signal_date, mode=mode)
    print(f"[eod] signal_date = {signal_ts.date()}")

    exec_date = _append_placeholder_bar(state, signal_ts,
                                        next_trading_day=next_trading_day)
    print(f"[eod] placeholder exec_date = {exec_date.date()}")

    # Run the engine over the full extended panel. We need data from
    # `backtest_start` so the engine builds up the holdings book leading
    # into the signal-day rebalance.
    from scripts._clean_engine import run_strategy

    start_ts = pd.Timestamp(backtest_start)
    cal = state.close_panel.index
    entry_dates = state.entry_signal_dates[
        (state.entry_signal_dates >= start_ts)
        & (state.entry_signal_dates <= signal_ts)
    ]
    weekly_dates = state.weekly_signal_dates[
        (state.weekly_signal_dates >= start_ts)
        & (state.weekly_signal_dates <= signal_ts)
    ]
    if mode == "exit_only":
        # Bar the engine from firing an entry rebalance on the exit-check
        # signal by removing today's date from entry_dates. weekly_dates
        # still contains signal_ts so the weekly-exit / DD-stop / regime
        # blocks fire against the placeholder-bar exec.
        entry_dates = entry_dates[entry_dates < signal_ts]
    print(f"[eod] entry_dates={len(entry_dates)} weekly_dates={len(weekly_dates)}")

    res = run_strategy(
        close_panel=state.close_panel,
        trade_panel=state.trade_panel,
        calendar=cal,
        benchmark_aligned=state.benchmark_aligned,
        entry_signal_dates=entry_dates,
        weekly_signal_dates=weekly_dates,
        signal_function=state.score_fn, signal_function_args={},
        sma_200_panel=state.sma_200, atr_20_panel=state.atr_20,
        top_n=state.top_n, exit_buffer=state.exit_buffer,
        max_weight=state.max_weight, slippage=state.slippage,
        atr_mult=0.0, atr_min_floor=state.drawdown_stop,
        use_trailing_stop=state.drawdown_stop > 0,
        use_dma_exit=False,
        weekly_rank_check=state.weekly_rank_check,
        regime_panel=state.regime_panel, bear_exposure=state.bear_exposure,
        membership_fn=state.membership_fn,
        min_hold_days=state.min_hold_days,
        initial_capital=initial_capital,
    )
    if res is None:
        raise RuntimeError(
            "Engine returned no result — empty rebalance set; check that "
            "backtest_start is early enough that warmup completes."
        )

    trades = res["trades"]
    equity = res["equity"]

    # The engine may have executed the rebalance one trading day after the
    # signal — that's `exec_date`. Cap the ledger at this date so subsequent
    # weekly checks (which can't actually happen at EOD-signal-day time)
    # don't leak into the readout.
    trades_capped = trades[pd.to_datetime(trades["date"]) <= exec_date]

    parts = partition_membership_by_date(trades_capped, exec_date=exec_date)
    print(f"[eod] exits={len(parts['exits'])} entries={len(parts['entries'])} "
          f"continuing={len(parts['continuing'])}")

    final_holdings = holdings_from_trades(trades_capped, up_to=exec_date)
    final_pv = _final_pv(equity)
    close_signal = state.close_panel.loc[signal_ts]
    target_weights = _build_target_weights(
        holdings=final_holdings, close_row=close_signal, final_pv=final_pv,
    )

    proposal = build_proposal(
        current_symbols=set(parts["exits"]) | set(parts["continuing"]),
        target_weights=target_weights,
        prices={s: float(close_signal.get(s)) for s in target_weights
                if not pd.isna(close_signal.get(s))},
        capital=initial_capital,
    )

    # Write CSV + JSON.
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / f"proposed_orders_{exec_date.date().isoformat()}.csv"
    pd.DataFrame(proposal.to_rows()).to_csv(csv_path, index=False)

    summary = {
        "strategy": strategy,
        "mode": mode,
        "signal_date": signal_ts.date().isoformat(),
        "exec_date": exec_date.date().isoformat(),
        "data_as_of": signal_ts.date().isoformat(),
        "sell_count": len(proposal.sells),
        "buy_count": len(proposal.buys),
        "hold_count": len(proposal.holds),
        "sells": [o.symbol for o in proposal.sells],
        "buys": [
            {"symbol": o.symbol, "target_weight": o.target_weight,
             "est_notional": o.est_notional, "est_shares": o.est_shares}
            for o in proposal.buys
        ],
        "holds": list(proposal.holds),
        "drawdown_from_peak": _drawdown_from_peak(equity),
        "final_pv": final_pv,
        "initial_capital": initial_capital,
        **_regime_status(state, signal_ts),
    }
    json_path = output_dir / "proposed_regime.json"
    json_path.write_text(json.dumps(summary, indent=2, default=str))

    print(f"[eod] wrote {csv_path.name} ({len(proposal.to_rows())} rows)")
    print(f"[eod] wrote {json_path.name}")
    return summary
