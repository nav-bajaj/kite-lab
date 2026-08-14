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
from app.insights._freshness import dir_signature, file_signature


def _repo_root() -> Path:
    return get_settings().data_dir


def _prices_dir() -> Path:
    # Long-history split-adjusted panel for breadth (16y deep).
    # Production live data ("nse500_data") is shorter; the merged panel is
    # what we want for percentile-style breadth metrics.
    return _repo_root() / "nse500_data_merged"


# Universe selector support (insights_dashboard_v2): breadth panels can be
# scoped to any committed universe snapshot. "nse500" keeps the legacy
# file/cache names so existing prod caches and callers stay valid.
BREADTH_UNIVERSES = ("nse500", "nifty250", "nifty100", "nifty50")

_UNIVERSE_FILENAMES = {
    "nse500": "nse500_universe.csv",
    "nifty250": "nifty250_universe.csv",
    "nifty100": "nifty100_universe.csv",
    "nifty50": "nifty50_universe.csv",
}


def _check_universe(universe: str) -> None:
    if universe not in _UNIVERSE_FILENAMES:
        raise ValueError(
            f"Unknown universe {universe!r}; expected one of {BREADTH_UNIVERSES}"
        )


def _universe_file(universe: str = "nse500") -> Path:
    _check_universe(universe)
    # eslint-style note: fixed mapping keyed by validated literal
    return _repo_root() / "data" / "static" / _UNIVERSE_FILENAMES[universe]


def _cache_file(universe: str = "nse500") -> Path:
    name = "breadth_panel.pkl" if universe == "nse500" else f"breadth_panel_{universe}.pkl"
    return _repo_root() / "cache" / "insights" / name


def load_universe(path: Path | None = None, universe: str = "nse500") -> list[str]:
    df = pd.read_csv(path or _universe_file(universe))
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

    sma_21 = close.rolling(21, min_periods=21).mean()
    sma_50 = close.rolling(50, min_periods=50).mean()
    sma_100 = close.rolling(100, min_periods=100).mean()
    sma_200 = close.rolling(200, min_periods=200).mean()
    daily_ret = close.pct_change(fill_method=None)
    high_252 = close.rolling(252, min_periods=100).max()
    low_252 = close.rolling(252, min_periods=100).min()

    n_active = close.notna().sum(axis=1).astype(float)

    above_21 = (close > sma_21).sum(axis=1).astype(float)
    above_50 = (close > sma_50).sum(axis=1).astype(float)
    above_100 = (close > sma_100).sum(axis=1).astype(float)
    above_200 = (close > sma_200).sum(axis=1).astype(float)
    have_21 = sma_21.notna().sum(axis=1).astype(float)
    have_50 = sma_50.notna().sum(axis=1).astype(float)
    have_100 = sma_100.notna().sum(axis=1).astype(float)
    have_200 = sma_200.notna().sum(axis=1).astype(float)

    pct_21 = (above_21 / have_21).replace([np.inf, -np.inf], np.nan)
    pct_50 = (above_50 / have_50).replace([np.inf, -np.inf], np.nan)
    pct_100 = (above_100 / have_100).replace([np.inf, -np.inf], np.nan)
    pct_200 = (above_200 / have_200).replace([np.inf, -np.inf], np.nan)

    # Continuous sibling of pct_above_200dma (Breadth Atlas: ρ 0.97, but
    # its tails carry ~4x the sample of the binary form's extreme bucket).
    avg_dist_200 = (close / sma_200 - 1.0).mean(axis=1)

    n_adv = (daily_ret > 0).sum(axis=1).astype(float)
    n_dec = (daily_ret < 0).sum(axis=1).astype(float)
    n_total_ad = n_adv + n_dec
    ad_diff_pct = ((n_adv - n_dec) / n_total_ad).replace([np.inf, -np.inf], np.nan)
    cumulative_ad = ad_diff_pct.cumsum()

    mcclellan = (ad_diff_pct.ewm(span=19, adjust=False).mean()
                 - ad_diff_pct.ewm(span=39, adjust=False).mean())
    mcclellan_sum = mcclellan.cumsum()

    new_high = (close == high_252).sum(axis=1).astype(float)
    new_low = (close == low_252).sum(axis=1).astype(float)
    have_252 = high_252.notna().sum(axis=1).astype(float)
    new_high_pct = (new_high / have_252).replace([np.inf, -np.inf], np.nan)
    new_low_pct = (new_low / have_252).replace([np.inf, -np.inf], np.nan)
    net_new_highs_pct = new_high_pct - new_low_pct

    dispersion = daily_ret.std(axis=1)

    return pd.DataFrame({
        "pct_above_21dma":      pct_21,
        "pct_above_50dma":      pct_50,
        "pct_above_100dma":     pct_100,
        "pct_above_200dma":     pct_200,
        "avg_dist_from_200dma": avg_dist_200,
        "ad_diff_pct":          ad_diff_pct,
        "cumulative_ad":        cumulative_ad,
        "mcclellan_osc":        mcclellan,
        "mcclellan_sum":        mcclellan_sum,
        "new_52w_highs_pct":    new_high_pct,
        "new_52w_lows_pct":     new_low_pct,
        "net_new_highs_pct":    net_new_highs_pct,
        "dispersion":           dispersion,
        "n_active":             n_active,
    })


def _cache_is_fresh(cache_path: Path, universe: str = "nse500") -> bool:
    """Cache is fresh iff it exists AND is newer than the universe file
    AND newer than the most recently-modified stock CSV in the prices dir.

    We only stat ONE representative stock file (RELIANCE) rather than all
    500 — the daily pipeline writes the whole panel together, so mtime on
    a single file is a reliable proxy."""
    if not cache_path.exists():
        return False
    cache_mtime = cache_path.stat().st_mtime
    uni = _universe_file(universe)
    if uni.exists() and uni.stat().st_mtime > cache_mtime:
        return False
    sentinel = _prices_dir() / "RELIANCE_day.csv"
    if sentinel.exists() and sentinel.stat().st_mtime > cache_mtime:
        return False
    return True


def _signature(universe: str = "nse500") -> tuple:
    """In-memory cache key: changes when the universe list or the price panel
    changes. Stats only the RELIANCE sentinel (the pipeline writes the panel
    as a batch) plus the universe file — the same inputs `_cache_is_fresh`
    already checks. Keeping the lru keyed on this makes the worker reload on
    the next request after the daily pipeline rewrites the panel, instead of
    serving a frozen in-memory copy until redeploy."""
    return (
        universe,
        file_signature(_universe_file(universe)),
        dir_signature(_prices_dir(), sentinel="RELIANCE_day.csv"),
    )


def get_breadth_panel(universe: str = "nse500", force_rebuild: bool = False) -> pd.DataFrame:
    """Return the breadth panel for `universe`, building if needed and
    caching to disk.

    The in-memory cache is keyed on `_signature()`, so it self-invalidates
    when the source files change. Disk cache survives restarts.
    """
    _check_universe(universe)
    if force_rebuild:
        _get_breadth_panel_cached.cache_clear()
        cache = _cache_file(universe)
        if cache.exists():
            cache.unlink()
    return _get_breadth_panel_cached(_signature(universe))


# Columns the current code version emits that older pickles may lack —
# the mtime freshness check can't see code changes, so the load path
# verifies schema before trusting a "fresh" cache (added with the
# Breadth Atlas columns, insights_dashboard_v2 Slice 2.5).
_SCHEMA_SENTINEL_COLUMNS = ("avg_dist_from_200dma", "mcclellan_sum", "pct_above_21dma")


@lru_cache(maxsize=8)
def _get_breadth_panel_cached(signature) -> pd.DataFrame:
    universe = signature[0]
    cache = _cache_file(universe)
    if _cache_is_fresh(cache, universe):
        panel = pd.read_pickle(cache)  # noqa: S301  # internal cache only
        if all(c in panel.columns for c in _SCHEMA_SENTINEL_COLUMNS):
            return panel
        print("[breadth] cache schema outdated — rebuilding")

    print(f"[breadth] cache stale or missing — rebuilding {universe} panel")
    symbols = load_universe(universe=universe)
    close = load_close_panel(symbols)
    print(f"  panel shape: {close.shape}  "
          f"({close.index.min().date()} → {close.index.max().date()})")
    breadth = compute_breadth_panel(close)
    cache.parent.mkdir(parents=True, exist_ok=True)
    breadth.to_pickle(cache)
    print(f"[breadth] wrote {cache.relative_to(_repo_root())}")
    return breadth


# Preserve `get_breadth_panel.cache_clear()` for any external caller.
get_breadth_panel.cache_clear = _get_breadth_panel_cached.cache_clear


def clear_cache() -> None:
    """Drop both in-memory and on-disk caches (all universes). Use after
    a data refresh to force a rebuild on next call."""
    _get_breadth_panel_cached.cache_clear()
    for universe in BREADTH_UNIVERSES:
        cache = _cache_file(universe)
        if cache.exists():
            cache.unlink()
