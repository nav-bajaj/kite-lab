"""Momentum strategy engine — customized layer atop scripts/_clean_engine.py.

Builds on the no-lookahead `run_strategy` engine but adds momentum-specific
helpers:

  - `build_momentum_panels()`: pre-compute per-(skip_days, lookback) momentum
    and realized-volatility panels once. Reused across many sweep configs.
  - `make_momentum_score()`: closure factory returning a score_fn for
    `_clean_engine.run_strategy`. Implements the L6 score:
        score = momentum_N / max(realized_vol_N, vol_floor) ** vol_power
    with optional cross-sectional z-scoring.
  - `BASELINE`: current production L6 config (NSE 500, L6, weekly,
    min_hold 8d, vol_floor 0.05).
  - `run_momentum`: thin wrapper that loads context, applies a single config,
    runs `_clean_engine.run_strategy`, and returns the result.

The `min_hold_days` parameter was added to `_clean_engine.run_strategy` in
this same commit (backward-compatible, default=0) so the rank-exit block
respects holding period.
"""
from __future__ import annotations

from typing import Optional

import numpy as np
import pandas as pd

from scripts._clean_engine import (
    run_strategy, fridays, biweekly_fridays, monthly_first_trading_day,
    thursdays, biweekly_thursdays,
)


# ============================================================
# Current production L6 — used as the BASELINE comparator
# ============================================================

BASELINE = dict(
    universe_csv="data/static/nse500_universe.csv",
    lookback_months=6,         # L6 = 126 trading days
    skip_days=0,
    top_n=24,
    exit_buffer=0,             # production doesn't use exit buffer
    rebalance="weekly",        # weekly entry — signal_day controls Thu vs Fri
    signal_day="thursday",     # production uses Thursday signal → Friday exec
    vol_floor=0.05,
    vol_power=1.0,
    min_hold_days=8,
    cross_sectional_zscore=True,
    max_weight=0.075,
    slippage=0.002,
    drawdown_stop=0.0,         # %-from-peak trailing stop; 0.0 = disabled
                               # (production has no stop; OM25/TL25 v3 use 0.20)
)


# ============================================================
# Panel builder — compute momentum + realized-vol panels once
# ============================================================

def build_momentum_panels(close_panel: pd.DataFrame, *,
                           lookback_days: int = 126,
                           skip_days: int = 0,
                           vol_window_days: Optional[int] = None) -> dict:
    """Pre-compute momentum and realized-volatility panels.

    Args:
      close_panel: Date×Symbol close prices.
      lookback_days: Window for momentum and (default) volatility.
      skip_days: Skip-window before measuring momentum (e.g., 0, 5, 21).
      vol_window_days: Override volatility window (default = lookback_days).

    Returns:
      dict with:
        momentum: Date×Symbol N-day price return (skip-adjusted)
        realized_vol: Date×Symbol N-day rolling std of daily returns
    """
    if vol_window_days is None:
        vol_window_days = lookback_days

    past = close_panel.shift(skip_days)
    momentum = past / past.shift(lookback_days) - 1.0
    daily_ret = close_panel.pct_change()
    realized_vol = daily_ret.shift(skip_days).rolling(
        vol_window_days, min_periods=max(20, vol_window_days // 2)
    ).std()

    return {
        "momentum": momentum,
        "realized_vol": realized_vol,
    }


# ============================================================
# Score factory — momentum / vol with cross-sectional z-score
# ============================================================

def make_momentum_score(panels: dict, *,
                         vol_floor: float = 0.05,
                         vol_power: float = 1.0,
                         cross_sectional_zscore: bool = True):
    """Return a score_fn(signal_date, **_) closure for run_strategy.

    Score = momentum / max(realized_vol, vol_floor) ** vol_power
    Optionally z-scored cross-sectionally per date.
    """
    momentum = panels["momentum"]
    realized_vol = panels["realized_vol"]

    def score_fn(signal_date, **_):
        if signal_date not in momentum.index:
            return pd.Series(dtype=float)

        mom_row = momentum.loc[signal_date]
        vol_row = realized_vol.loc[signal_date]

        # Clip vol to floor; raise to vol_power
        denom = vol_row.clip(lower=vol_floor)
        if abs(vol_power - 1.0) > 1e-9:
            denom = denom.pow(vol_power)

        score = mom_row / denom
        score = score.replace([np.inf, -np.inf], np.nan).dropna()
        if score.empty:
            return score

        if cross_sectional_zscore and len(score) > 1:
            mu = score.mean()
            sd = score.std()
            if sd is not None and sd > 0:
                score = (score - mu) / sd

        return score

    return score_fn


# ============================================================
# Convenience helpers for sweep harnesses
# ============================================================

def lookback_months_to_days(months: int) -> int:
    """Convert calendar months to ~trading days (21 per month)."""
    return months * 21


def entry_dates_for_rebalance(calendar, rebalance: str,
                                signal_day: str = "thursday") -> pd.DatetimeIndex:
    """Map rebalance label + signal day to entry-date series.

    signal_day controls Thursday-vs-Friday signal anchoring. Production L6
    uses Thursday (→ Friday execution, 1 trading day earlier than Friday-anchored
    strategies like OM25/TL25 v3).
    """
    use_thu = signal_day == "thursday"
    if rebalance == "weekly":
        return thursdays(calendar) if use_thu else fridays(calendar)
    if rebalance == "biweekly":
        return biweekly_thursdays(calendar) if use_thu else biweekly_fridays(calendar)
    if rebalance == "monthly":
        return monthly_first_trading_day(calendar)
    raise ValueError(f"unknown rebalance {rebalance!r}")


# ============================================================
# Thin wrapper — apply a single config and return engine result
# ============================================================

def run_momentum(*, close_panel, trade_panel, calendar, benchmark_aligned,
                  panels, sma_200_panel, atr_20_panel,
                  start, end, config: dict,
                  regime_panel=None, bear_exposure: float = 0.0) -> Optional[dict]:
    """Run a single momentum config over [start, end] entry dates.

    `config` is a dict merging BASELINE with overrides. Returns the
    `_clean_engine.run_strategy` result dict, or None if no entry dates.

    Optional regime params:
      regime_panel: pd.Series[date]→bool (True=bull). When False (bear),
        gross exposure is scaled to bear_exposure (0=cash, 1=full).
        Built by scripts.om25_v3.build_regime_panel_confirmed.
      bear_exposure: 0..1 fraction of capital deployed during bear regime.
    """
    cfg = {**BASELINE, **config}
    sd = cfg.get("signal_day", "thursday")
    entry_all = entry_dates_for_rebalance(calendar, cfg["rebalance"], sd)
    s = pd.Timestamp(start); e = pd.Timestamp(end)
    entry_dates = entry_all[(entry_all >= s) & (entry_all <= e)]
    # Weekly DD-stop check aligned with the signal day so the check + trade
    # cadence matches entries (e.g. Thu signal → Fri exec).
    weekly_signal_all = thursdays(calendar) if sd == "thursday" else fridays(calendar)
    weekly_filt = weekly_signal_all[(weekly_signal_all >= s)
                                      & (weekly_signal_all <= e)]
    if len(entry_dates) == 0:
        return None

    score_fn = make_momentum_score(
        panels,
        vol_floor=cfg["vol_floor"],
        vol_power=cfg["vol_power"],
        cross_sectional_zscore=cfg["cross_sectional_zscore"],
    )
    dd_stop = cfg.get("drawdown_stop", 0.0)
    return run_strategy(
        close_panel=close_panel, trade_panel=trade_panel,
        calendar=calendar, benchmark_aligned=benchmark_aligned,
        entry_signal_dates=entry_dates, weekly_signal_dates=weekly_filt,
        signal_function=score_fn, signal_function_args={},
        sma_200_panel=sma_200_panel, atr_20_panel=atr_20_panel,
        top_n=cfg["top_n"], exit_buffer=cfg["exit_buffer"],
        max_weight=cfg["max_weight"], slippage=cfg["slippage"],
        # Trailing stop: atr_mult=0 + atr_min_floor=dd_stop = fixed %-from-peak stop
        atr_mult=0.0, atr_min_floor=dd_stop,
        use_trailing_stop=dd_stop > 0.0,
        use_dma_exit=False,
        weekly_rank_check=False,    # momentum doesn't use weekly rank-exit
        regime_panel=regime_panel, bear_exposure=bear_exposure,
        min_hold_days=cfg["min_hold_days"],
        initial_capital=1_000_000,
    )
