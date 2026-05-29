"""Panic-bounce strategy.

  Trigger: Nifty 10-day return < drop_threshold AND VIX > vix_threshold
  Entry confirmation (optional): wait for first up-day after trigger
  Hold: hold_days trading days (default 20), OR exit on trailing-low stop
  Side: LONG only (Phase 1 EDA confirmed short alpha is absent in Nifty)

State machine:
  FLAT  → if trigger fires AND (entry_confirm=False or last day was up):
             → enter LONG at this day's close (modelled as next-day position)
  LONG  → hold; exit on time stop OR trailing stop
        → after exit: 'cooldown' for `cooldown_days` (don't re-enter immediately)
        → otherwise hold
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass
class PanicConfig:
    # Trigger
    drop_window: int = 10                 # measure return over this window
    drop_threshold: float = -0.05         # 10-day return must be below this (negative)
    vix_threshold: float = 22.0           # VIX must be above this
    # Entry timing
    entry_confirm_required: bool = False  # if True, require an up-day before entering
    # Exit
    hold_days: int = 20                   # max holding period
    trailing_stop_lookback: int = 10      # exit if close < trailing N-day low (False = disabled)
    use_trailing_stop: bool = True
    # Hygiene
    cooldown_days: int = 5                # after exit, wait this many days before re-entry
    # Sizing
    long_size: float = 1.0


def run_panic_bounce(nifty: pd.Series, panel: pd.DataFrame,
                      cfg: PanicConfig) -> pd.Series:
    """Return position series in {0, cfg.long_size}."""
    nifty = nifty.sort_index()
    aligned = panel.reindex(nifty.index).ffill()

    ret_w = nifty.pct_change(cfg.drop_window, fill_method=None)
    vix = aligned["vix_close"]
    daily_ret = nifty.pct_change(fill_method=None)
    trail_low = nifty.rolling(cfg.trailing_stop_lookback,
                               min_periods=cfg.trailing_stop_lookback).min().shift(1)

    pos = pd.Series(0.0, index=nifty.index)
    state = "FLAT"
    days_held = 0
    cooldown = 0

    close = nifty.values
    ret_w_v = ret_w.values
    vix_v = vix.values
    dret_v = daily_ret.values
    tl_v = trail_low.values

    for i in range(len(close)):
        if state == "FLAT":
            if cooldown > 0:
                cooldown -= 1
                pos.iloc[i] = 0.0
                continue
            trigger = (
                (not np.isnan(ret_w_v[i])) and
                (ret_w_v[i] < cfg.drop_threshold) and
                (not np.isnan(vix_v[i])) and
                (vix_v[i] > cfg.vix_threshold)
            )
            confirm_ok = True
            if cfg.entry_confirm_required:
                confirm_ok = (not np.isnan(dret_v[i])) and (dret_v[i] > 0)
            if trigger and confirm_ok:
                state = "LONG"
                days_held = 1
                pos.iloc[i] = cfg.long_size
            else:
                pos.iloc[i] = 0.0

        elif state == "LONG":
            time_stop = days_held >= cfg.hold_days
            stop_hit = (cfg.use_trailing_stop and
                        not np.isnan(tl_v[i]) and
                        close[i] < tl_v[i])
            if time_stop or stop_hit:
                state = "FLAT"
                days_held = 0
                cooldown = cfg.cooldown_days
                pos.iloc[i] = 0.0
            else:
                pos.iloc[i] = cfg.long_size
                days_held += 1

    return pos
