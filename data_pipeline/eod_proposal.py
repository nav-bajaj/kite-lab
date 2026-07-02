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

    universe = load_universe(ROOT / LOCKED["universe_csv"])
    cols = [s for s in close_panel.columns if s in universe]
    returns_uni = close_panel[cols].pct_change()

    regime = build_regime_panel_confirmed(
        ROOT / LOCKED["regime_index_path"],
        LOCKED["regime_ma_window"], LOCKED["regime_confirm_days"],
        calendar=calendar,
    )

    score_fn = make_om25_tilt_score(
        returns_uni, regime,
        bull_w_uc=LOCKED["bull_w_uc"], bull_w_cr=LOCKED["bull_w_cr"],
        bear_w_uc=LOCKED["bear_w_uc"], bear_w_cr=LOCKED["bear_w_cr"],
        return_filter=LOCKED["return_filter"],
        lookback=LOCKED["lookback"], min_obs=LOCKED["min_obs"],
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
        regime_panel=regime, bear_exposure=0.0,
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

    universe = load_universe(ROOT / V3_LOCKED["universe_csv"])
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

    universe = load_universe(ROOT / BASELINE["universe_csv"])
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
        min_hold_days=BASELINE["min_hold_days"],
    )


_STRATEGIES = {
    "om25_v3": _prepare_om25_v3,
    "tl25_v3": _prepare_tl25_v3,
    "l6_v2": _prepare_l6_v2,
}


# ============================================================
# Panel extension — placeholder next-day bar
# ============================================================

def _append_placeholder_bar(state: StrategyState, signal_date: pd.Timestamp,
                             ) -> pd.Timestamp:
    """Extend every date-indexed panel by one trading day, set to signal-day
    levels. Returns the placeholder date (= ``exec_date``).

    The placeholder is signal_date + 1 calendar day, then bumped onto the
    next weekday so we don't land on a Saturday/Sunday. (NSE holidays are
    handled implicitly: the holiday calendar would already have removed any
    intervening trading day from real data; for the live EOD path the
    caller — the scheduler — must already be running on a signal weekday,
    so signal_date + 1..3 always lands on a real next trading day in the
    extended calendar we build here.)
    """
    cal = state.close_panel.index
    if signal_date not in cal:
        raise ValueError(f"Signal date {signal_date.date()} not in price calendar")

    # signal_date + 1 calendar day; if that lands on a weekend, push to Monday.
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
                       requested: Optional[pd.Timestamp]) -> pd.Timestamp:
    """Choose the signal date — the latest cadence-Friday in our panels at
    or before ``requested`` (or the last calendar day if no override)."""
    cap = (requested if requested is not None
           else state.close_panel.index[-1])
    eligible = state.entry_signal_dates[state.entry_signal_dates <= cap]
    if len(eligible) == 0:
        raise ValueError(
            f"No signal date in cadence on/before {cap.date()} — "
            f"is the cadence index empty?"
        )
    return pd.Timestamp(eligible[-1])


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
                        ) -> dict:
    """Produce ``proposed_orders_<exec_date>.csv`` + ``proposed_regime.json``.

    Args:
        strategy: key into ``_STRATEGIES`` — currently ``om25_v3``, ``tl25_v3``.
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

    Returns:
        Summary dict written to ``proposed_regime.json``.
    """
    if strategy not in _STRATEGIES:
        raise ValueError(
            f"Unknown strategy {strategy!r}; supported: {list(_STRATEGIES)}"
        )
    print(f"[eod] strategy={strategy} prices={prices_dir.name}")

    state = _STRATEGIES[strategy](prices_dir=prices_dir)
    signal_ts = _pick_signal_date(state, signal_date)
    print(f"[eod] signal_date = {signal_ts.date()}")

    exec_date = _append_placeholder_bar(state, signal_ts)
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
