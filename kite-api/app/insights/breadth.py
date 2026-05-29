"""Market-breadth signal panel — NSE 500 cross-sectional metrics.

Promoted from `tasks/nifty_trader/breadth_signals.py` into the kite-api
runtime so the API routes (Phase 2) and Daily Quant Note generator
(Phase 1) can import it without going through the tasks/ folder.

Output: a daily-indexed `pd.DataFrame` with these columns:
  pct_above_50dma     fraction of NSE 500 stocks with close > 50-DMA
  pct_above_100dma    same, 100-DMA
  pct_above_200dma    same, 200-DMA
  ad_diff_pct         (#advancers - #decliners) / #active
  cumulative_ad       running sum of ad_diff_pct (A-D line proxy)
  mcclellan_osc       EMA19(ad_diff_pct) - EMA39(ad_diff_pct)
  new_52w_highs_pct   fraction of active stocks at trailing 252d close-high
  new_52w_lows_pct    fraction at trailing 252d close-low
  net_new_highs_pct   new_52w_highs_pct - new_52w_lows_pct
  dispersion          cross-sectional stdev of daily returns
  n_active            denominator (count of stocks with non-NaN price)

Caching strategy:
  - Disk cache at `<data_dir>/cache/insights/breadth_panel.pkl`
  - Invalidated when the universe file or any sample stock CSV is newer
    than the cache (mtime-based, fast)
  - In-memory `@lru_cache` on the loader for hot-path API requests
  - First cold build takes ~10 seconds; cached reload is <50ms

Survivorship bias: the universe is the "current" NSE 500
(data/static/nse500_universe.csv). Stocks delisted before today are
absent — flagged in the insight-engine PLAN.md caveats.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

from app.config import get_settings


def _repo_root() -> Path:
    return get_settings().data_dir


def _prices_dir() -> Path:
    # Long-history split-adjusted panel for breadth (16y deep).
    # Production live data ("nse500_data") is shorter; the merged panel is
    # what we want for percentile-style breadth metrics.
    return _repo_root() / "nse500_data_merged"


def _universe_file() -> Path:
    return _repo_root() / "data" / "static" / "nse500_universe.csv"


def _cache_file() -> Path:
    return _repo_root() / "cache" / "insights" / "breadth_panel.pkl"


def load_universe(path: Path | None = None) -> list[str]:
    df = pd.read_csv(path or _universe_file())
    return df["Symbol"].astype(str).tolist()


def load_close_panel(symbols: Iterable[str],
                      prices_dir: Path | None = None) -> pd.DataFrame:
    """Return wide DataFrame: rows=date, cols=symbol, values=close."""
    prices_dir = prices_dir or _prices_dir()
    series_list = []
    missing: list[str] = []
    for sym in symbols:
        p = prices_dir / f"{sym}_day.csv"
        if not p.exists():
            missing.append(sym)
            continue
        df = pd.read_csv(p, parse_dates=["date"])[["date", "close"]]
        df = df.rename(columns={"close": sym}).set_index("date")
        series_list.append(df[sym])
    if missing:
        # Logged at info level, not failure — recent IPOs / non-NSE500 names
        # legitimately won't have files in this snapshot.
        print(f"[breadth.load_close_panel] {len(missing)} symbols missing price files: "
              f"{missing[:5]}{'…' if len(missing) > 5 else ''}")
    return pd.concat(series_list, axis=1).sort_index()


def compute_breadth_panel(close_panel: pd.DataFrame) -> pd.DataFrame:
    """Compute daily breadth signals over the cross-section."""
    close = close_panel.copy()
    close = close.ffill(limit=5)

    sma_50 = close.rolling(50, min_periods=50).mean()
    sma_100 = close.rolling(100, min_periods=100).mean()
    sma_200 = close.rolling(200, min_periods=200).mean()
    daily_ret = close.pct_change(fill_method=None)
    high_252 = close.rolling(252, min_periods=100).max()
    low_252 = close.rolling(252, min_periods=100).min()

    n_active = close.notna().sum(axis=1).astype(float)

    above_50 = (close > sma_50).sum(axis=1).astype(float)
    above_100 = (close > sma_100).sum(axis=1).astype(float)
    above_200 = (close > sma_200).sum(axis=1).astype(float)
    have_50 = sma_50.notna().sum(axis=1).astype(float)
    have_100 = sma_100.notna().sum(axis=1).astype(float)
    have_200 = sma_200.notna().sum(axis=1).astype(float)

    pct_50 = (above_50 / have_50).replace([np.inf, -np.inf], np.nan)
    pct_100 = (above_100 / have_100).replace([np.inf, -np.inf], np.nan)
    pct_200 = (above_200 / have_200).replace([np.inf, -np.inf], np.nan)

    n_adv = (daily_ret > 0).sum(axis=1).astype(float)
    n_dec = (daily_ret < 0).sum(axis=1).astype(float)
    n_total_ad = n_adv + n_dec
    ad_diff_pct = ((n_adv - n_dec) / n_total_ad).replace([np.inf, -np.inf], np.nan)
    cumulative_ad = ad_diff_pct.cumsum()

    mcclellan = (ad_diff_pct.ewm(span=19, adjust=False).mean()
                 - ad_diff_pct.ewm(span=39, adjust=False).mean())

    new_high = (close == high_252).sum(axis=1).astype(float)
    new_low = (close == low_252).sum(axis=1).astype(float)
    have_252 = high_252.notna().sum(axis=1).astype(float)
    new_high_pct = (new_high / have_252).replace([np.inf, -np.inf], np.nan)
    new_low_pct = (new_low / have_252).replace([np.inf, -np.inf], np.nan)
    net_new_highs_pct = new_high_pct - new_low_pct

    dispersion = daily_ret.std(axis=1)

    return pd.DataFrame({
        "pct_above_50dma":   pct_50,
        "pct_above_100dma":  pct_100,
        "pct_above_200dma":  pct_200,
        "ad_diff_pct":       ad_diff_pct,
        "cumulative_ad":     cumulative_ad,
        "mcclellan_osc":     mcclellan,
        "new_52w_highs_pct": new_high_pct,
        "new_52w_lows_pct":  new_low_pct,
        "net_new_highs_pct": net_new_highs_pct,
        "dispersion":        dispersion,
        "n_active":          n_active,
    })


def _cache_is_fresh(cache_path: Path) -> bool:
    """Cache is fresh iff it exists AND is newer than the universe file
    AND newer than the most recently-modified stock CSV in the prices dir.

    We only stat ONE representative stock file (RELIANCE) rather than all
    500 — the daily pipeline writes the whole panel together, so mtime on
    a single file is a reliable proxy."""
    if not cache_path.exists():
        return False
    cache_mtime = cache_path.stat().st_mtime
    uni = _universe_file()
    if uni.exists() and uni.stat().st_mtime > cache_mtime:
        return False
    sentinel = _prices_dir() / "RELIANCE_day.csv"
    if sentinel.exists() and sentinel.stat().st_mtime > cache_mtime:
        return False
    return True


@lru_cache(maxsize=1)
def get_breadth_panel(force_rebuild: bool = False) -> pd.DataFrame:
    """Return the breadth panel, building if needed and caching to disk.

    @lru_cache keeps it in memory per process; the cache key (just the
    force_rebuild flag) means subsequent calls return the same DataFrame
    instance unless explicitly rebuilt. Disk cache survives restarts.
    """
    cache = _cache_file()
    if not force_rebuild and _cache_is_fresh(cache):
        return pd.read_pickle(cache)  # noqa: S301  # internal cache only

    print("[breadth] cache stale or missing — rebuilding from NSE 500 panel")
    symbols = load_universe()
    close = load_close_panel(symbols)
    print(f"  panel shape: {close.shape}  "
          f"({close.index.min().date()} → {close.index.max().date()})")
    breadth = compute_breadth_panel(close)
    cache.parent.mkdir(parents=True, exist_ok=True)
    breadth.to_pickle(cache)
    print(f"[breadth] wrote {cache.relative_to(_repo_root())}")
    return breadth


def clear_cache() -> None:
    """Drop both in-memory and on-disk cache. Use after a data refresh
    to force a rebuild on next call."""
    get_breadth_panel.cache_clear()
    cache = _cache_file()
    if cache.exists():
        cache.unlink()
