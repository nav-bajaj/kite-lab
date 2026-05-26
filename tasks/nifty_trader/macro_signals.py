"""Macro / cross-asset / sector signal construction for the nifty_trader strategy.

Signals built:
  vix_close          : India VIX close
  vix_zscore_60d     : 60-day z-score of VIX (where in vol regime are we)
  vix_zscore_252d    : 252-day z-score (annual vol regime)
  vix_roc_5d         : 5-day rate of change (vol expansion / contraction)
  vix_above_20       : binary: VIX above 20 (stress threshold)

  usd_inr_roc_5d     : USDINR 5-day change (proxy for FX-stress; rising = stress)
  gold_roc_20d       : MCXGOLDEX 20-day return (risk-off signal)

  sector_pct_above_200dma : fraction of 10 sector indices above 200-DMA
  sector_dispersion_20d   : cross-sector stdev of 20d returns
  sector_breadth_st_lt    : sector pct_above_50dma minus pct_above_200dma
                            (short-term vs long-term sector breadth — rotation signal)

All signals are end-of-day, lagged by 1 day at usage.
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

INDICES_DIR = Path("/Users/navdeep/Documents/stock_data/indices_data_full")
HERE = Path(__file__).resolve().parent
CACHE_DIR = HERE / "cache"

# Sector indices with long history (≥10 years). Verified at construction time.
SECTOR_INDICES = [
    "NIFTY_BANK", "NIFTY_IT", "NIFTY_PHARMA", "NIFTY_FMCG", "NIFTY_AUTO",
    "NIFTY_METAL", "NIFTY_REALTY", "NIFTY_FIN_SERVICE", "NIFTY_ENERGY",
    "NIFTY_MEDIA",  # may be shorter — handled gracefully
]


def _load_close(name: str) -> pd.Series:
    p = INDICES_DIR / f"{name}.csv"
    if not p.exists():
        return pd.Series(dtype=float)
    df = pd.read_csv(p, parse_dates=["date"])[["date", "close"]]
    return df.set_index("date")["close"].sort_index()


def compute_macro_panel() -> pd.DataFrame:
    out = {}

    # --- India VIX ---
    vix = _load_close("INDIA_VIX")
    out["vix_close"] = vix
    out["vix_zscore_60d"]  = (vix - vix.rolling(60, min_periods=30).mean()) / vix.rolling(60, min_periods=30).std()
    out["vix_zscore_252d"] = (vix - vix.rolling(252, min_periods=100).mean()) / vix.rolling(252, min_periods=100).std()
    out["vix_roc_5d"] = vix.pct_change(5, fill_method=None)
    out["vix_above_20"] = (vix > 20).astype(float)

    # --- Cross-asset: NIFTY50_USD and MCXGOLDEX historical data is too sparse
    # for the backtest window (<150 rows starting 2025+). Dropped from v1.
    # If we later import USDINR + gold history from another source, restore
    # the usd_inr_roc_5d and gold_roc_20d signals here. ---

    # --- Sector breadth ---
    sector_closes = {}
    for s in SECTOR_INDICES:
        ser = _load_close(s)
        if not ser.empty and len(ser) > 252:
            sector_closes[s] = ser
    if sector_closes:
        sector_panel = pd.concat(sector_closes, axis=1).sort_index()
        # % of sectors above 50/200 DMA
        sma50 = sector_panel.rolling(50, min_periods=50).mean()
        sma200 = sector_panel.rolling(200, min_periods=200).mean()
        n50 = sma50.notna().sum(axis=1)
        n200 = sma200.notna().sum(axis=1)
        out["sector_pct_above_50dma"]  = (sector_panel > sma50).sum(axis=1) / n50.replace(0, np.nan)
        out["sector_pct_above_200dma"] = (sector_panel > sma200).sum(axis=1) / n200.replace(0, np.nan)
        out["sector_breadth_st_lt"] = out["sector_pct_above_50dma"] - out["sector_pct_above_200dma"]
        # Cross-sector dispersion of 20d returns
        sector_ret_20 = sector_panel.pct_change(20, fill_method=None)
        out["sector_dispersion_20d"] = sector_ret_20.std(axis=1)

    df = pd.concat(out, axis=1).sort_index()
    return df


def build_or_load(force: bool = False) -> pd.DataFrame:
    CACHE_DIR.mkdir(exist_ok=True)
    cache = CACHE_DIR / "macro_panel.pkl"
    if cache.exists() and not force:
        return pd.read_pickle(cache)  # noqa: S301  # internal cache only
    print("[macro] computing signals…")
    df = compute_macro_panel()
    df.to_pickle(cache)
    print(f"  shape: {df.shape}  ({df.index.min().date()} → {df.index.max().date()})")
    return df


if __name__ == "__main__":
    p = build_or_load(force=True)
    print(f"Macro panel shape: {p.shape}")
    print(f"\nColumns:")
    for c in p.columns:
        n = p[c].notna().sum()
        print(f"  {c:<32} {n:>5} obs  range [{p[c].min():.3f}, {p[c].max():.3f}]")
    print(f"\nDescribe (key):")
    print(p[["vix_close", "vix_zscore_60d", "sector_pct_above_200dma", "sector_dispersion_20d"]].describe().round(3).to_string())
