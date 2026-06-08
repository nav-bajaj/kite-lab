"""Cross-asset feature engine — Phase 4.5.

For each registered cross-asset series (e.g., India 10y yield, gold,
USDINR, crude, US 10y), computes standardized features that downstream
consumers can read uniformly:

  - close                today's close
  - z_60d / z_252d       trailing-window z-scores
  - roc_5d / 20d / 60d   percent change over the window
  - dist_from_200dma     (close / 200-DMA) - 1
  - pctile_252d          rank percentile of close within trailing 252d

The engine takes a `close_series` (pd.Series indexed by date) — no
assumptions about asset class. Anything daily-frequency that you can
load into a Series will work.

Built test-first per `tasks/insight_engine/TDD_POLICY.md`. Spec tests
at `tests/test_insights_cross_asset.py`.

Currently-wired assets:
  - india_10y    — NIFTY GS 10YR (Indian 10-year govt securities proxy),
                   ~9y of history at `indices_data_full/NIFTY_GS_10YR.csv`

Deferred assets (need data sourcing, tracked in TASKS.md §4.5):
  - usdinr       — FRED DEXINUS or RBI reference rate; we have very
                   short NIFTY50_USD history but not enough for features
  - gold         — MCXGOLDEX in our panel is only ~4 months long; need
                   a Yahoo / Investing.com backfill for meaningful history
  - us_10y       — FRED DGS10
  - crude        — FRED DCOILBRENTEU

When a deferred asset gets its CSV, register it below and the snapshot
function will start producing real features automatically.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, asdict, field
from functools import lru_cache
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd


# ─────────── data shape ───────────

@dataclass
class AssetFeatures:
    """Per-asset feature row. All numeric fields are Optional — they're
    None when there isn't enough history to compute them. Consumers
    must handle None gracefully."""
    close: Optional[float]
    z_60d: Optional[float]
    z_252d: Optional[float]
    roc_5d: Optional[float]
    roc_20d: Optional[float]
    roc_60d: Optional[float]
    dist_from_200dma: Optional[float]
    pctile_252d: Optional[float]

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class CrossAssetEntry:
    """A registered cross-asset series as exposed to the API + UI."""
    asset_id: str
    label: str
    data_available: bool
    features: AssetFeatures = field(default_factory=lambda: AssetFeatures(
        close=None, z_60d=None, z_252d=None, roc_5d=None, roc_20d=None,
        roc_60d=None, dist_from_200dma=None, pctile_252d=None,
    ))
    as_of_date: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "asset_id": self.asset_id,
            "label": self.label,
            "data_available": self.data_available,
            "as_of_date": self.as_of_date,
            "features": self.features.to_dict(),
        }


# ─────────── feature computation ───────────

def _safe_z(series: pd.Series, window: int) -> Optional[float]:
    """Z-score of today vs trailing `window` days. None if insufficient
    history."""
    if len(series) < window + 1:
        return None
    window_data = series.iloc[-(window + 1):-1]
    today = series.iloc[-1]
    std = window_data.std()
    if std is None or std == 0 or pd.isna(std) or pd.isna(today):
        return None
    return float((today - window_data.mean()) / std)


def _safe_roc(series: pd.Series, lookback: int) -> Optional[float]:
    """Percent change over `lookback` sessions. None if insufficient
    history."""
    if len(series) < lookback + 1:
        return None
    today = series.iloc[-1]
    prior = series.iloc[-(lookback + 1)]
    if pd.isna(today) or pd.isna(prior) or prior == 0:
        return None
    return float((today / prior) - 1.0)


def compute_asset_features(close_series: pd.Series) -> AssetFeatures:
    """Compute the standard feature row for a cross-asset close series.

    Input: pd.Series of close prices indexed by date.
    Output: AssetFeatures dataclass with all fields populated where
    history allows, None where it doesn't.
    """
    s = close_series.dropna()
    if s.empty:
        return AssetFeatures(close=None, z_60d=None, z_252d=None,
                             roc_5d=None, roc_20d=None, roc_60d=None,
                             dist_from_200dma=None, pctile_252d=None)

    close = float(s.iloc[-1])

    dist_200 = None
    if len(s) >= 200:
        sma_200 = float(s.iloc[-200:].mean())
        if sma_200 > 0:
            dist_200 = (close / sma_200) - 1.0

    pctile_252 = None
    if len(s) >= 252:
        window_252 = s.iloc[-252:]
        rank = (window_252 < close).sum() + 0.5 * (window_252 == close).sum()
        pctile_252 = float(rank / len(window_252))

    return AssetFeatures(
        close=close,
        z_60d=_safe_z(s, 60),
        z_252d=_safe_z(s, 252),
        roc_5d=_safe_roc(s, 5),
        roc_20d=_safe_roc(s, 20),
        roc_60d=_safe_roc(s, 60),
        dist_from_200dma=dist_200,
        pctile_252d=pctile_252,
    )


# ─────────── registry + loading ───────────

# Where the OHLC CSVs live. Must stay in lockstep with the writer at
# scripts/fetch_cross_asset_history.py (_resolve_output_dir) — same resolution
# order so the engine reads the directory the fetcher just wrote. The old
# hardcoded Mac path meant this engine never saw the data on Railway (the
# /data volume), so cross-asset features were permanently data_available=False
# in prod regardless of what the fetcher produced.
def _resolve_indices_dir() -> Path:
    override = os.environ.get("CROSS_ASSET_OUTPUT_DIR")
    if override:
        return Path(override)
    root = os.environ.get("KITE_BACKUP_SOURCE_ROOT")
    if root:
        return Path(root) / "indices_data_full"
    if Path("/data").is_dir():
        return Path("/data") / "indices_data_full"
    return Path.home() / "Documents" / "stock_data" / "indices_data_full"


INDICES_DIR = _resolve_indices_dir()


# (asset_id, label, csv_filename or None for deferred)
#
# `csv_filename` is interpreted relative to INDICES_DIR. The engine
# tolerates missing files: if the CSV isn't present, the asset appears
# in the snapshot with data_available=False and all features None.
# Drop a CSV at the named path and the engine picks it up automatically
# on the next cache clear.
REGISTERED_ASSETS: list[tuple[str, str, Optional[str]]] = [
    ("india_10y", "India 10y govt yield (NIFTY GS 10YR)", "NIFTY_GS_10YR.csv"),
    # Phase 4.5 — fetcher at scripts/fetch_cross_asset_history.py lands
    # these CSVs from Kite Connect continuous front-month futures.
    ("usdinr",    "USDINR (continuous front-month future)",       "USDINR.csv"),
    ("gold",      "Gold (MCX continuous front-month, INR/10g)",   "GOLD.csv"),
    ("crude",     "Crude oil (MCX continuous front-month, INR/bbl)", "CRUDEOIL.csv"),
    # Still deferred — US 10y has no Kite Connect path; needs FRED or yfinance.
    ("us_10y",    "US 10y Treasury yield",  None),
]


def _load_close_series(csv_filename: str) -> Optional[pd.Series]:
    path = INDICES_DIR / csv_filename
    if not path.exists():
        return None
    df = pd.read_csv(path, parse_dates=["date"]).set_index("date").sort_index()
    if "close" not in df.columns:
        return None
    return df["close"]


def clear_cache() -> None:
    get_cross_asset_snapshot.cache_clear()


@lru_cache(maxsize=1)
def get_cross_asset_snapshot() -> dict[str, CrossAssetEntry]:
    """Return the per-asset feature snapshot dict.

    Registered assets without a CSV (deferred) appear in the dict with
    `data_available=False` and all feature fields None. Consumers can
    iterate the dict and find every registered asset, gracefully
    handling missing data.
    """
    out: dict[str, CrossAssetEntry] = {}
    for asset_id, label, csv_filename in REGISTERED_ASSETS:
        if csv_filename is None:
            out[asset_id] = CrossAssetEntry(
                asset_id=asset_id, label=label, data_available=False,
            )
            continue
        series = _load_close_series(csv_filename)
        if series is None or series.empty:
            out[asset_id] = CrossAssetEntry(
                asset_id=asset_id, label=label, data_available=False,
            )
            continue
        out[asset_id] = CrossAssetEntry(
            asset_id=asset_id,
            label=label,
            data_available=True,
            features=compute_asset_features(series),
            as_of_date=series.index.max().date().isoformat(),
        )
    return out
