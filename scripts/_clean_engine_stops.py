"""Stop-loss panel utilities for use with `_clean_engine.run_strategy`.

Builds two kinds of pre-computed panels:

1. True ATR (OHLC-based) → returned as ATR / close (pct of price)
2. Donchian rolling low (close-based)

True ATR can be passed to run_strategy as atr_20_panel. The engine's
trail-from-peak logic computes trail = atr_mult * atr_pct and exits when
close/peak - 1 < -trail.

Donchian uses a different mechanism — exit if close < N-day rolling low.
A wrapper script (e.g. _om25_atr_donchian_test.py) handles that with its
own check loop or via post-hoc equity adjustment.
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional, Set

import numpy as np
import pandas as pd


def load_ohlc_panels(prices_dir: Path, universe: Optional[Set[str]] = None):
    """Load high/low/close panels for ATR / Donchian computations.

    Returns (high_panel, low_panel, close_panel) aligned by date.
    """
    high_rows, low_rows, close_rows = [], [], []
    for csv_path in sorted(prices_dir.glob("*_day.csv")):
        symbol = csv_path.stem.replace("_day", "")
        if universe is not None and symbol not in universe:
            continue
        df = pd.read_csv(csv_path, parse_dates=["date"])
        if df.empty or not {"high", "low", "close"}.issubset(df.columns):
            continue
        df["symbol"] = symbol
        high_rows.append(df[["date", "symbol", "high"]])
        low_rows.append(df[["date", "symbol", "low"]])
        close_rows.append(df[["date", "symbol", "close"]])
    if not close_rows:
        raise RuntimeError(f"No OHLC files in {prices_dir}")
    H = pd.concat(high_rows).pivot(index="date", columns="symbol", values="high").sort_index()
    L = pd.concat(low_rows).pivot(index="date", columns="symbol", values="low").sort_index()
    C = pd.concat(close_rows).pivot(index="date", columns="symbol", values="close").sort_index()
    # Align columns
    cols = sorted(set(H.columns) & set(L.columns) & set(C.columns))
    return H[cols], L[cols], C[cols]


def compute_true_atr_pct(high: pd.DataFrame, low: pd.DataFrame,
                         close: pd.DataFrame, window: int = 14) -> pd.DataFrame:
    """True ATR as a percentage of close (Date × Symbol).

    TR = max(H-L, |H - prev_C|, |L - prev_C|)
    ATR = simple moving average of TR over `window` days.
    Returns ATR / close.
    """
    prev_close = close.shift(1)
    hl = (high - low).abs().values
    hc = (high - prev_close).abs().values
    lc = (low - prev_close).abs().values
    # Element-wise max ignoring NaN by treating NaN as 0 in hc/lc only on
    # the very first row where prev_close is NaN
    hc = np.where(np.isnan(hc), hl, hc)
    lc = np.where(np.isnan(lc), hl, lc)
    tr_arr = np.maximum.reduce([hl, hc, lc])
    tr = pd.DataFrame(tr_arr, index=close.index, columns=close.columns)
    atr = tr.rolling(window, min_periods=window).mean()
    atr_pct = atr / close
    return atr_pct


def compute_donchian_low(low: pd.DataFrame, window: int = 20) -> pd.DataFrame:
    """N-day Donchian lower band: lowest LOW of the past `window` days,
    EXCLUDING today (shifted by 1).

    Convention: exit if today's close < this band. Today's value is
    excluded so a new N-day low actually triggers (otherwise the close
    would always be >= rolling_min(low) including today).
    """
    return low.rolling(window, min_periods=window).min().shift(1)
