"""OM25 v3 production utilities — regime-tilted UC/CR composite.

Locked-in May 2026 retune (see tasks/oos_retune_2026/RESULTS.md):

  Score (bull regime):
      0.5 × pct_rank(upside_capture) + 0.5 × pct_rank(capture_ratio)

  Score (bear regime):
      pct_rank(capture_ratio)   ← defensive tilt

  Regime signal:
      NIFTY 100 close vs 100-day MA, with 3-day confirmation hysteresis

  Eligibility:
      ≥220 valid daily returns in 252-day window
      ≥50 market-up days AND ≥50 market-down days
      Positive 252d total return (return filter)

  Sizing / exits:
      Top-25, exit-buffer 20 (drop below rank 45)
      Equal 1/N, max 7.5% per stock, drift after entry
      20%-from-peak drawdown stop (weekly check, OHLC/4 next-day exec)
      No ATR trailing, no 200 DMA exit

This module exposes two utilities used by the production pipeline:
  1. `build_regime_panel_confirmed(...)` — bull/bear regime panel
  2. `make_om25_tilt_score(...)` — closure-based score function

Both are designed to be passed directly to `_clean_engine.run_strategy`.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd


# Locked-in defaults
LOCKED = dict(
    universe_csv="data/static/nifty250_universe.csv",
    cadence="biweekly",
    lookback=252,
    min_obs=220,
    top_n=25,
    exit_buffer=20,
    max_weight=0.075,
    slippage=0.002,
    return_filter=True,
    bull_w_uc=0.5,
    bull_w_cr=0.5,
    bear_w_uc=0.0,
    bear_w_cr=1.0,
    regime_index_path="indices_data_historical/NIFTY_100.csv",
    regime_ma_window=100,
    regime_confirm_days=3,
    drawdown_stop_pct=0.20,
)


def build_regime_panel_confirmed(idx_path: Path, ma_window: int = 100,
                                  confirm_days: int = 3,
                                  calendar: Optional[pd.DatetimeIndex] = None
                                  ) -> pd.Series:
    """Bull/bear regime panel using close-vs-MA with N-day confirmation.

    Hysteresis: regime starts as bull (default). Flips to bear only after
    `confirm_days` consecutive closes below the MA. Flips to bull only
    after `confirm_days` consecutive closes above the MA. Sticky in
    between. Lagged by 1 trading day to avoid lookahead.

    Returns: pd.Series indexed by date with True=bull / False=bear.
    """
    df = pd.read_csv(idx_path, parse_dates=["date"])
    df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None).dt.normalize()
    df = df.sort_values("date").set_index("date")
    ma = df["close"].rolling(ma_window, min_periods=ma_window).mean()
    above = (df["close"] > ma)
    n_above = above.rolling(confirm_days, min_periods=confirm_days).sum()

    state = True
    regime_vals = []
    for v in n_above.values:
        if np.isnan(v):
            regime_vals.append(state)
            continue
        if state and v == 0:
            state = False
        elif not state and v == confirm_days:
            state = True
        regime_vals.append(state)
    regime = pd.Series(regime_vals, index=df.index, dtype=bool)
    regime_lagged = regime.shift(1)
    if calendar is not None:
        regime_lagged = regime_lagged.reindex(calendar).ffill()
    return regime_lagged


def make_om25_tilt_score(returns_universe: pd.DataFrame,
                          regime_panel: pd.Series, *,
                          bull_w_uc: float = 0.5, bull_w_cr: float = 0.5,
                          bear_w_uc: float = 0.0, bear_w_cr: float = 1.0,
                          return_filter: bool = True,
                          lookback: int = 252, min_obs: int = 220):
    """Score factory — returns `score_fn(signal_date)` for run_strategy.

    Computes each stock's upside_capture (UC) and capture_ratio (CR =
    UC/DC) over a `lookback`-day window. Pct-ranks each metric across
    eligible stocks. Blends with weights determined by regime at
    signal_date (bull vs bear).
    """
    def score_fn(signal_date, **_):
        if signal_date not in returns_universe.index:
            return pd.Series(dtype=float)
        idx = returns_universe.index.get_loc(signal_date)
        if idx < lookback:
            return pd.Series(dtype=float)
        try:
            rv = regime_panel.get(signal_date, True)
            is_bull = bool(rv) if rv is not None else True
        except Exception:
            is_bull = True
        if is_bull:
            w_uc, w_cr = bull_w_uc, bull_w_cr
        else:
            w_uc, w_cr = bear_w_uc, bear_w_cr
        if w_uc + w_cr <= 0:
            return pd.Series(dtype=float)
        w_sum = w_uc + w_cr
        w_uc_n, w_cr_n = w_uc / w_sum, w_cr / w_sum

        window = returns_universe.iloc[idx - lookback + 1:idx + 1]
        market_ret = window.mean(axis=1)
        results = {}
        for sym in window.columns:
            r = window[sym].dropna()
            if len(r) < min_obs:
                continue
            if return_filter and ((1 + r).prod() - 1) <= 0:
                continue
            common = r.index.intersection(market_ret.index)
            sr = r.loc[common]
            mr = market_ret.loc[common]
            up = mr > 0
            dn = mr < 0
            if up.sum() < 50 or dn.sum() < 50:
                continue
            uc = sr[up].mean() / mr[up].mean() if mr[up].mean() > 0 else 0
            dc = sr[dn].mean() / mr[dn].mean() if mr[dn].mean() < 0 else 1
            ratio = uc / dc if dc > 0 else uc
            results[sym] = {"up": uc, "ratio": ratio}
        if not results:
            return pd.Series(dtype=float)
        df = pd.DataFrame(results).T
        up_pct = df["up"].rank(method="average") / len(df)
        cr_pct = df["ratio"].rank(method="average") / len(df)
        return w_uc_n * up_pct + w_cr_n * cr_pct

    return score_fn
