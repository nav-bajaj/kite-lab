"""COMBO Defensive strategy — 50-50 L6 + OM25 v3 + regime overlay.

Locked spec (from tasks/MM-tuning/DD_REDUCTION_RESEARCH.md, 2026-05-14):

  Composition:  50-50 L6 + OM25 v3 with priority dedup (L6 first)
  L6 picks:     Top 12 from NSE 500 using _momentum_engine score
  OM25 picks:   Top 12 from Nifty 250 using OM25 v3 regime-tilted score,
                backfilled non-overlapping with L6's 12
  Cadence:      Bi-weekly entry, Friday signal → Monday OHLC/4 execution
  Top-N:        24 (12 + 12, equal weight)
  Min hold:     8 days
  Max weight:   7.5% per stock, drift after entry
  Slippage:     0.2% (20 bps)
  Regime:       NIFTY 100 vs 100-DMA, 3-day confirm
                Bull: 100% invested; Bear: 50% invested (50% cash)

Use scripts/run_combo_defensive_portfolio.py to run.
"""
from __future__ import annotations

from typing import Callable

import pandas as pd


LOCKED = dict(
    # Composition
    n_per_strategy=12,           # 12 from each → 24 total
    priority_order=("L6", "OM25"),
    top_n=24,
    # L6 component params (matches _momentum_engine.BASELINE)
    l6_universe_csv="data/static/nse500_universe.csv",
    l6_lookback_months=6,
    l6_skip_days=0,
    l6_vol_floor=0.05,
    l6_vol_power=1.0,
    l6_signal_day="thursday",    # L6's native (NOT used here since cadence is shared)
    # OM25 component params (matches scripts.om25_v3.LOCKED)
    om25_universe_csv="data/static/nifty250_universe.csv",
    om25_lookback=252,
    om25_min_obs=220,
    om25_bull_w_uc=0.5,
    om25_bull_w_cr=0.5,
    om25_bear_w_uc=0.0,
    om25_bear_w_cr=1.0,
    om25_return_filter=True,
    # Shared execution
    cadence="biweekly",
    signal_day="friday",         # Friday signal → Monday exec (operational sweet spot)
    max_weight=0.075,
    slippage=0.002,
    min_hold_days=8,
    exit_buffer=0,
    # Regime overlay
    regime_index_path="indices_data_historical/NIFTY_100.csv",
    regime_ma_window=100,
    regime_confirm_days=3,
    regime_bear_exposure=0.5,    # 50% invested during bear
)


def make_combo_score_fn(component_score_fns: list, *,
                         n_per: int = 12) -> Callable:
    """Build a combined score function from a priority-ordered list of
    component score_fns.

    Args:
      component_score_fns: list of (label, score_fn) tuples in priority order.
        First strategy claims its top-n_per; second backfills with its top-n_per
        excluding picks already taken; etc.
      n_per: how many picks each component contributes.

    Returns:
      score_fn(signal_date, **_) → pd.Series indexed by symbol, scores descending.
    """
    def score_fn(signal_date, **_):
        picked = set()
        rows = []
        for _label, sf in component_score_fns:
            scores = sf(signal_date)
            if scores is None or scores.empty:
                continue
            ranked = scores.dropna().sort_values(ascending=False)
            taken = 0
            for sym in ranked.index:
                if sym in picked:
                    continue
                picked.add(sym)
                rows.append(sym)
                taken += 1
                if taken >= n_per:
                    break
        if not rows:
            return pd.Series(dtype=float)
        n = len(rows)
        return pd.Series({sym: float(n - i) for i, sym in enumerate(rows)})
    return score_fn
