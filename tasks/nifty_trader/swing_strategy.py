"""Two-layer swing strategy: bias regime + market-structure entry/exit.

  Layer 1 — BIAS (slow):  VIX / breadth determine long-bias / short-bias / no-bias
  Layer 2 — STRUCTURE (fast):  enter on N-day breakout in the biased direction,
                                exit via trailing N-day stop or time stop

This is a CYCLICAL strategy — flat between trades, sharp directional bets when
both the regime and the price action agree. Designed to ride 7-10 day swings.
Many fewer trades than continuous strategies, much higher conviction per trade.

State machine:
  FLAT  → if bias_long  and close > rolling_max(close, entry_lookback).shift(1):
              → enter LONG at next bar open (we model at same-bar close for now)
        → if bias_short and close < rolling_min(close, entry_lookback).shift(1):
              → enter SHORT
  LONG  → exit if close < rolling_min(close, exit_lookback).shift(1)    [trailing stop]
        → exit if days_held >= time_stop_days                            [time stop]
        → exit if bias flips to short                                    [regime flip]
        → otherwise hold
  SHORT → mirror of LONG
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd


@dataclass
class SwingConfig:
    # Bias layer
    bias_pct200_long: float = 0.55     # pct_above_200dma > X → long bias enabled
    bias_pct200_short: float = 0.40    # pct_above_200dma < X → short bias enabled
    bias_vix_z_long_floor: float = -0.5  # require VIX z above this (avoid extreme complacency)
    bias_vix_z_short_floor: float = -0.5  # require VIX z above this for short

    # Entry layer
    entry_lookback: int = 5            # breakout above/below trailing N-day high/low

    # Exit layer
    exit_lookback: int = 5             # trailing stop = rolling N-day low/high
    time_stop_days: int = 10

    # Sizing
    long_size: float = 1.0
    short_size: float = -1.0


def compute_bias(panel: pd.DataFrame, idx: pd.Index, cfg: SwingConfig) -> pd.Series:
    """Return a series of {-1, 0, +1} = short / no / long bias for each date."""
    p = panel.reindex(idx).ffill()
    pct200 = p["pct_above_200dma"]
    vix_z = p["vix_zscore_252d"]

    bias = pd.Series(0, index=idx)
    long_ok = (pct200 > cfg.bias_pct200_long) & (vix_z > cfg.bias_vix_z_long_floor)
    short_ok = (pct200 < cfg.bias_pct200_short) & (vix_z > cfg.bias_vix_z_short_floor)
    bias[long_ok] = 1
    bias[short_ok & ~long_ok] = -1
    return bias


def run_swing(nifty: pd.Series, panel: pd.DataFrame, cfg: SwingConfig) -> pd.Series:
    """Return a position series in {-1, 0, +1} (scaled by long_size/short_size)."""
    nifty = nifty.sort_index()
    bias = compute_bias(panel, nifty.index, cfg)

    # Pre-compute breakout levels: trailing N-day high/low EXCLUDING today
    # (use .shift(1) so we compare today's close to yesterday's trailing window)
    hi_n = nifty.rolling(cfg.entry_lookback, min_periods=cfg.entry_lookback).max().shift(1)
    lo_n = nifty.rolling(cfg.entry_lookback, min_periods=cfg.entry_lookback).min().shift(1)
    exit_hi = nifty.rolling(cfg.exit_lookback, min_periods=cfg.exit_lookback).max().shift(1)
    exit_lo = nifty.rolling(cfg.exit_lookback, min_periods=cfg.exit_lookback).min().shift(1)

    pos = pd.Series(0.0, index=nifty.index)
    state = "FLAT"  # FLAT / LONG / SHORT
    days_held = 0

    # Iterate; this is O(n) and fine for ~4000 days
    close = nifty.values
    bias_v = bias.values
    hi_v = hi_n.values
    lo_v = lo_n.values
    ex_hi_v = exit_hi.values
    ex_lo_v = exit_lo.values

    for i in range(len(close)):
        c = close[i]
        b = bias_v[i]

        if state == "FLAT":
            # Check for entries (need valid breakout level + matching bias)
            if not np.isnan(hi_v[i]) and b == 1 and c > hi_v[i]:
                state = "LONG"
                days_held = 1
                pos.iloc[i] = cfg.long_size
            elif not np.isnan(lo_v[i]) and b == -1 and c < lo_v[i]:
                state = "SHORT"
                days_held = 1
                pos.iloc[i] = cfg.short_size
            else:
                pos.iloc[i] = 0.0

        elif state == "LONG":
            # Check exits
            time_stop = days_held >= cfg.time_stop_days
            stop_hit = (not np.isnan(ex_lo_v[i])) and c < ex_lo_v[i]
            regime_flip = b == -1
            if time_stop or stop_hit or regime_flip:
                state = "FLAT"
                days_held = 0
                pos.iloc[i] = 0.0
            else:
                pos.iloc[i] = cfg.long_size
                days_held += 1

        elif state == "SHORT":
            time_stop = days_held >= cfg.time_stop_days
            stop_hit = (not np.isnan(ex_hi_v[i])) and c > ex_hi_v[i]
            regime_flip = b == 1
            if time_stop or stop_hit or regime_flip:
                state = "FLAT"
                days_held = 0
                pos.iloc[i] = 0.0
            else:
                pos.iloc[i] = cfg.short_size
                days_held += 1

    return pos
