"""Macro signals — India VIX + sector breadth aggregates.

Promoted from `tasks/nifty_trader/macro_signals.py`. Same caching pattern
as `breadth.py` (disk + in-memory lru_cache).

Output columns:
  vix_close              India VIX close
  vix_zscore_60d         60-day z-score of VIX (where in vol regime are we)
  vix_zscore_252d        252-day z-score (annual vol regime)
  vix_roc_5d             5-day rate of change (vol expansion / contraction)
  vix_above_20           binary: VIX above 20 (stress threshold)
  sector_pct_above_50dma fraction of sector INDICES above 50-DMA
  sector_pct_above_200dma fraction of sector INDICES above 200-DMA
  sector_breadth_st_lt   pct_above_50dma - pct_above_200dma
                          (rotation signal: ST vs LT sector breadth)
  sector_dispersion_20d  cross-sector stdev of 20d returns

Note: this module's sector-breadth metrics are computed on the sector
INDEX series themselves (NIFTY BANK closing > 200-DMA etc), not on the
individual constituents of each sector. The constituent-level breadth
lives in `app.insights.sector_breadth` (Phase 0 task 0.7) — those give
much richer "narrow vs broad rally" reads. This module's signals are
still useful for the regime classifier and the headline stress score.

Cross-asset signals (USDINR, gold, US 10y, crude) and FII/DII flows live
separately in `cross_asset.py` and `fii_dii.py` (Phase 0 tasks 0.10, 0.11).
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

from app.config import get_settings
from app.insights._freshness import dir_signature
from app.insights._paths import indices_dir as _indices_dir


# Sector indices with long history (≥10 years). Verified at runtime.
SECTOR_INDICES = [
    "NIFTY_BANK", "NIFTY_IT", "NIFTY_PHARMA", "NIFTY_FMCG", "NIFTY_AUTO",
    "NIFTY_METAL", "NIFTY_REALTY", "NIFTY_FIN_SERVICE", "NIFTY_ENERGY",
    "NIFTY_MEDIA",
]


def _cache_file() -> Path:
    return get_settings().data_dir / "cache" / "insights" / "macro_panel.pkl"


def _load_close(name: str) -> pd.Series:
    p = _indices_dir() / f"{name}.csv"
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

    # --- Sector breadth (sector-INDEX level, not constituent-level) ---
    sector_closes = {}
    for s in SECTOR_INDICES:
        ser = _load_close(s)
        if not ser.empty and len(ser) > 252:
            sector_closes[s] = ser
    if sector_closes:
        sector_panel = pd.concat(sector_closes, axis=1).sort_index()
        sma50 = sector_panel.rolling(50, min_periods=50).mean()
        sma200 = sector_panel.rolling(200, min_periods=200).mean()
        n50 = sma50.notna().sum(axis=1)
        n200 = sma200.notna().sum(axis=1)
        out["sector_pct_above_50dma"]  = (sector_panel > sma50).sum(axis=1) / n50.replace(0, np.nan)
        out["sector_pct_above_200dma"] = (sector_panel > sma200).sum(axis=1) / n200.replace(0, np.nan)
        out["sector_breadth_st_lt"] = out["sector_pct_above_50dma"] - out["sector_pct_above_200dma"]
        sector_ret_20 = sector_panel.pct_change(20, fill_method=None)
        out["sector_dispersion_20d"] = sector_ret_20.std(axis=1)

    return pd.concat(out, axis=1).sort_index()


def _cache_is_fresh(cache_path: Path) -> bool:
    if not cache_path.exists():
        return False
    cache_mtime = cache_path.stat().st_mtime
    vix_file = _indices_dir() / "INDIA_VIX.csv"
    if vix_file.exists() and vix_file.stat().st_mtime > cache_mtime:
        return False
    return True


def _signature() -> tuple:
    """Cache key: the indices directory (INDIA_VIX sentinel). The pipeline
    rewrites the whole indices set together, so one sentinel tracks the VIX
    and sector-index inputs this panel reads."""
    return (dir_signature(_indices_dir(), sentinel="INDIA_VIX.csv"),)


def get_macro_panel(force_rebuild: bool = False) -> pd.DataFrame:
    """Return the macro panel, building if needed and caching to disk."""
    if force_rebuild:
        _get_macro_panel_cached.cache_clear()
        cache = _cache_file()
        if cache.exists():
            cache.unlink()
    return _get_macro_panel_cached(_signature())


@lru_cache(maxsize=2)
def _get_macro_panel_cached(signature) -> pd.DataFrame:
    cache = _cache_file()
    if _cache_is_fresh(cache):
        return pd.read_pickle(cache)  # noqa: S301  # internal cache only

    print("[macro] cache stale or missing — rebuilding from VIX + sector indices")
    df = compute_macro_panel()
    cache.parent.mkdir(parents=True, exist_ok=True)
    df.to_pickle(cache)
    print(f"[macro] wrote {cache.relative_to(get_settings().data_dir)} ({df.shape})")
    return df


get_macro_panel.cache_clear = _get_macro_panel_cached.cache_clear


def clear_cache() -> None:
    _get_macro_panel_cached.cache_clear()
    cache = _cache_file()
    if cache.exists():
        cache.unlink()
