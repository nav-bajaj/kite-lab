"""Market-breadth signal construction from the NSE 500 stock panel.

All signals are computed end-of-day and lagged by one day at usage time
(see backtest engine) to avoid look-ahead. Pre-listing handled via NaN
prices → excluded from per-day breadth denominator.

Outputs cached to `cache/breadth_panel.pkl` (regenerable in ~10s
from the 500-stock CSVs).

Signals:
  pct_above_50dma     : fraction of NSE 500 stocks with close > 50-DMA
  pct_above_100dma    : same, 100-DMA
  pct_above_200dma    : same, 200-DMA
  ad_diff_pct         : (#advancers − #decliners) / #active each day
  cumulative_ad       : running sum of ad_diff_pct (≈ A-D line)
  mcclellan_osc       : EMA19(ad_diff_pct) − EMA39(ad_diff_pct)
  new_52w_highs_pct   : fraction of active stocks at trailing 252d close-high
  new_52w_lows_pct    : fraction at trailing 252d close-low
  net_new_highs_pct   : new_52w_highs_pct − new_52w_lows_pct
  dispersion          : cross-sectional stdev of daily returns
  n_active            : denominator (count of stocks with non-NaN price)

Surviorship bias: the universe is the "current" NSE 500 (data/static/
nse500_universe.csv). Stocks delisted before today are absent. This may
slightly inflate breadth readings, especially pre-2015. Acknowledged
in PLAN.md; not fixable in v1.
"""
from __future__ import annotations

from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
CACHE_DIR = HERE / "cache"
PRICES_DIR = ROOT / "nse500_data_merged"
UNIVERSE_FILE = ROOT / "data/static/nse500_universe.csv"


def load_universe(path: Path = UNIVERSE_FILE) -> list[str]:
    df = pd.read_csv(path)
    return df["Symbol"].astype(str).tolist()


def load_close_panel(symbols: Iterable[str],
                      prices_dir: Path = PRICES_DIR) -> pd.DataFrame:
    """Return wide DataFrame: rows=date, cols=symbol, values=close."""
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
        print(f"  [load_close_panel] {len(missing)} symbols missing price files: "
              f"{missing[:5]}{'…' if len(missing) > 5 else ''}")
    panel = pd.concat(series_list, axis=1).sort_index()
    return panel


def compute_breadth_panel(close_panel: pd.DataFrame) -> pd.DataFrame:
    """Compute daily breadth signals over the cross-section."""
    close = close_panel.copy()
    # Forward-fill at most 5 days to handle the occasional missing-day quirk
    # (single-stock data hiccups), but DON'T forward-fill across pre-listing.
    # Once a stock has its first price it stays "alive" in the panel.
    close = close.ffill(limit=5)

    # Per-stock features
    sma_50 = close.rolling(50, min_periods=50).mean()
    sma_100 = close.rolling(100, min_periods=100).mean()
    sma_200 = close.rolling(200, min_periods=200).mean()

    daily_ret = close.pct_change(fill_method=None)

    # Trailing 52-week (252 trading days) high/low — use shifted window
    # to avoid the current day's close being trivially the max of itself
    # (it would always be the high on a rising series). Use trailing 252d
    # max INCLUSIVE of today: new_high = close == rolling_max(close, 252).
    # This matches the common definition: "today closed at a 52-week high".
    high_252 = close.rolling(252, min_periods=100).max()
    low_252 = close.rolling(252, min_periods=100).min()

    # Cross-sectional aggregates
    n_active = close.notna().sum(axis=1).astype(float)

    above_50 = (close > sma_50).sum(axis=1).astype(float)
    above_100 = (close > sma_100).sum(axis=1).astype(float)
    above_200 = (close > sma_200).sum(axis=1).astype(float)

    # Denominators differ per metric: only stocks with valid MA count
    have_50 = (sma_50.notna()).sum(axis=1).astype(float)
    have_100 = (sma_100.notna()).sum(axis=1).astype(float)
    have_200 = (sma_200.notna()).sum(axis=1).astype(float)

    pct_50 = (above_50 / have_50).replace([np.inf, -np.inf], np.nan)
    pct_100 = (above_100 / have_100).replace([np.inf, -np.inf], np.nan)
    pct_200 = (above_200 / have_200).replace([np.inf, -np.inf], np.nan)

    # Advance/decline
    n_adv = (daily_ret > 0).sum(axis=1).astype(float)
    n_dec = (daily_ret < 0).sum(axis=1).astype(float)
    n_total_ad = n_adv + n_dec  # ignore unchanged
    ad_diff_pct = ((n_adv - n_dec) / n_total_ad).replace([np.inf, -np.inf], np.nan)
    cumulative_ad = ad_diff_pct.cumsum()

    # McClellan Oscillator
    mcclellan = ad_diff_pct.ewm(span=19, adjust=False).mean() \
              - ad_diff_pct.ewm(span=39, adjust=False).mean()

    # 52-week highs/lows (only count when 252d window is filled)
    new_high = (close == high_252).sum(axis=1).astype(float)
    new_low = (close == low_252).sum(axis=1).astype(float)
    have_252 = (high_252.notna()).sum(axis=1).astype(float)
    new_high_pct = (new_high / have_252).replace([np.inf, -np.inf], np.nan)
    new_low_pct = (new_low / have_252).replace([np.inf, -np.inf], np.nan)
    net_new_highs_pct = new_high_pct - new_low_pct

    # Cross-sectional dispersion (std of daily returns across active stocks)
    dispersion = daily_ret.std(axis=1)

    out = pd.DataFrame({
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
    return out


def build_or_load(force: bool = False) -> pd.DataFrame:
    """Cached entry point. Pass force=True to rebuild."""
    CACHE_DIR.mkdir(exist_ok=True)
    cache_file = CACHE_DIR / "breadth_panel.pkl"
    if cache_file.exists() and not force:
        return pd.read_pickle(cache_file)  # noqa: S301  # internal cache only

    print(f"[breadth] loading NSE 500 universe + close panel…")
    symbols = load_universe()
    close = load_close_panel(symbols)
    print(f"  panel shape: {close.shape}  "
          f"({close.index.min().date()} → {close.index.max().date()})")
    print(f"[breadth] computing signals…")
    breadth = compute_breadth_panel(close)
    breadth.to_pickle(cache_file)
    print(f"  wrote {cache_file}")
    return breadth


if __name__ == "__main__":
    panel = build_or_load(force=True)
    print(f"\nBreadth panel shape: {panel.shape}")
    print(f"Date range: {panel.index.min().date()} → {panel.index.max().date()}")
    print(f"\nColumns: {list(panel.columns)}")
    print(f"\nHead:")
    print(panel.dropna().head(3).round(3).to_string())
    print(f"\nTail:")
    print(panel.dropna().tail(3).round(3).to_string())
    print(f"\nDescriptive stats:")
    print(panel.describe().round(3).to_string())
