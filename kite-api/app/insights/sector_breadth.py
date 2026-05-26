"""Constituent-level sector breadth.

Where `macro.py` computes sector breadth at the INDEX level (NIFTY BANK
above its 200-DMA — yes/no), this module computes breadth WITHIN each
sector by looking at its individual constituents (how many of the 14
banks in NIFTY BANK are above their 200-DMA right now).

This is the layer that lets us tell readers "Banks are leading, but
it's mostly HDFCBANK and ICICIBANK doing the work — only 4 of 14 are
above Nifty in 6-month RS." The sector INDEX hides that asymmetry; the
constituent panel exposes it.

Outputs:

  `compute_sector_breadth_panel()` →
      wide DataFrame, MultiIndex columns (sector, metric), date index.
      Used for historical analysis (analog finder, conditional distributions).

  `get_sector_breadth_snapshot(asof)` →
      dict[sector_name → snapshot_dict] for one date.
      Used by the Daily Quant Note to populate the "Sectors" section.

Snapshot fields per sector:
  n_constituents, n_covered, coverage          (sizing)
  pct_above_50dma, pct_above_100dma,           (breadth)
    pct_above_200dma
  pct_advancing_today                          (daily activity)
  dispersion_20d, median_ret_20d               (internal dynamics)
  rs_leaders   = [(symbol, rs_score), ...]     (top 3 vs Nifty 6m)
  rs_laggards  = [(symbol, rs_score), ...]     (bottom 3 vs Nifty 6m)
  thrust_day                                    (≥80% constituents up today)
  is_partial_coverage                           (flag from sector_constituents)
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

from app.config import get_settings
from app.insights.breadth import load_close_panel
from app.insights.sector_constituents import (
    PARTIAL_COVERAGE_SECTORS,
    get_all_sectors,
)


# Relative-strength benchmark — we score each sector constituent's 6-month
# return against Nifty 50's 6-month return.
_RS_LOOKBACK_DAYS = 126  # ~6 months of trading days
_THRUST_THRESHOLD = 0.80  # >80% advancing → thrust day
_DISPERSION_WINDOW = 20


def _nifty_close() -> pd.Series:
    """Nifty 50 close series — RS benchmark."""
    settings = get_settings()
    # Same fallback as macro.py
    external = Path("/Users/navdeep/Documents/stock_data/indices_data_full")
    indices_dir = external if external.exists() else settings.data_dir / "indices_data_historical"
    p = indices_dir / "NIFTY_50.csv"
    if not p.exists():
        raise FileNotFoundError(f"NIFTY_50.csv not at {p}")
    return (pd.read_csv(p, parse_dates=["date"])
              .set_index("date")["close"]
              .sort_index())


@dataclass
class SectorBreadthSnapshot:
    """Per-sector breadth + leadership snapshot for one date."""
    sector: str
    date: pd.Timestamp
    n_constituents: int
    n_covered: int
    coverage: float

    # Breadth (fractions in [0, 1])
    pct_above_50dma: float | None
    pct_above_100dma: float | None
    pct_above_200dma: float | None

    # Daily activity
    pct_advancing_today: float | None
    n_advancing: int
    n_declining: int

    # Internal dynamics
    dispersion_20d: float | None      # cross-sectional stdev of 20d returns
    median_ret_20d: float | None

    # Leadership — list of (symbol, rs_score) tuples
    rs_leaders: list[tuple[str, float]] = field(default_factory=list)
    rs_laggards: list[tuple[str, float]] = field(default_factory=list)

    # Flags
    thrust_day: bool = False
    is_partial_coverage: bool = False

    def to_dict(self) -> dict:
        d = asdict(self)
        d["date"] = self.date.isoformat() if isinstance(self.date, pd.Timestamp) else self.date
        return d


# ---------- panel builder (historical time series) ----------

@lru_cache(maxsize=1)
def _build_stock_panel() -> pd.DataFrame:
    """Wide stock-price panel covering every symbol in any sector + Nifty."""
    sectors = get_all_sectors()
    all_symbols = sorted({sym for s in sectors.values() for sym in s.symbols})
    return load_close_panel(all_symbols)


@lru_cache(maxsize=1)
def compute_sector_breadth_panel() -> pd.DataFrame:
    """Time series of per-sector breadth.

    Returns wide DataFrame with MultiIndex columns (sector, metric).
    Metrics: pct_above_50dma, pct_above_100dma, pct_above_200dma,
    pct_advancing, dispersion_20d, n_covered, thrust_day.
    Rows: trading days.
    """
    sectors = get_all_sectors()
    close = _build_stock_panel()
    if close.empty:
        return pd.DataFrame()

    # Per-stock features used by all sectors
    sma_50 = close.rolling(50, min_periods=50).mean()
    sma_100 = close.rolling(100, min_periods=100).mean()
    sma_200 = close.rolling(200, min_periods=200).mean()
    daily_ret = close.pct_change(fill_method=None)
    ret_20d = close.pct_change(_DISPERSION_WINDOW, fill_method=None)

    rows: dict[tuple[str, str], pd.Series] = {}
    for sector_name, sector in sectors.items():
        covered = [s for s in sector.symbols if s in close.columns]
        if not covered:
            continue
        sub_close = close[covered]
        sub_50 = sma_50[covered]
        sub_100 = sma_100[covered]
        sub_200 = sma_200[covered]
        sub_ret = daily_ret[covered]
        sub_ret_20 = ret_20d[covered]

        have_50 = sub_50.notna().sum(axis=1)
        have_100 = sub_100.notna().sum(axis=1)
        have_200 = sub_200.notna().sum(axis=1)
        n_covered = sub_close.notna().sum(axis=1)

        above_50 = (sub_close > sub_50).sum(axis=1)
        above_100 = (sub_close > sub_100).sum(axis=1)
        above_200 = (sub_close > sub_200).sum(axis=1)
        n_adv = (sub_ret > 0).sum(axis=1)
        n_dec = (sub_ret < 0).sum(axis=1)
        n_ad_total = (n_adv + n_dec).replace(0, np.nan)

        rows[(sector_name, "n_constituents")]  = pd.Series(sector.n, index=close.index)
        rows[(sector_name, "n_covered")]       = n_covered.astype(float)
        rows[(sector_name, "pct_above_50dma")] = (above_50 / have_50.replace(0, np.nan))
        rows[(sector_name, "pct_above_100dma")]= (above_100 / have_100.replace(0, np.nan))
        rows[(sector_name, "pct_above_200dma")]= (above_200 / have_200.replace(0, np.nan))
        rows[(sector_name, "pct_advancing")]   = (n_adv / n_ad_total)
        rows[(sector_name, "dispersion_20d")]  = sub_ret_20.std(axis=1)
        rows[(sector_name, "median_ret_20d")]  = sub_ret_20.median(axis=1)
        rows[(sector_name, "thrust_day")]      = ((n_adv / n_ad_total) > _THRUST_THRESHOLD).astype(float)

    df = pd.DataFrame(rows)
    df.columns = pd.MultiIndex.from_tuples(df.columns, names=["sector", "metric"])
    return df.sort_index(axis=1)


# ---------- per-day snapshot (for the Daily Quant Note) ----------

def get_sector_breadth_snapshot(
    asof: pd.Timestamp | None = None,
) -> dict[str, SectorBreadthSnapshot]:
    """Per-sector breadth snapshot for `asof` (default: most recent date).

    Cheap to call repeatedly because the underlying panel is cached.
    """
    panel = compute_sector_breadth_panel()
    if panel.empty:
        return {}

    if asof is None:
        asof = panel.index.max()
    else:
        asof = pd.Timestamp(asof)
        # Snap to most-recent trading day on or before asof
        valid = panel.index[panel.index <= asof]
        if valid.empty:
            return {}
        asof = valid.max()

    sectors = get_all_sectors()
    close = _build_stock_panel()
    nifty = _nifty_close()

    # Compute 6m relative strength for every covered symbol once
    rs_scores = _compute_rs_scores(close, nifty, asof, _RS_LOOKBACK_DAYS)

    snapshots: dict[str, SectorBreadthSnapshot] = {}
    for sector_name, sector in sectors.items():
        covered = [s for s in sector.symbols if s in close.columns]
        n_total = sector.n
        n_covered = len(covered)
        coverage = n_covered / n_total if n_total else 0

        # Read scalar metrics from the panel
        if sector_name in panel.columns.get_level_values("sector"):
            row = panel.loc[asof, sector_name]
        else:
            row = pd.Series(dtype=float)

        # Today's advance/decline
        if covered:
            sub_close = close[covered].loc[:asof]
            if len(sub_close) >= 2:
                today_ret = sub_close.iloc[-1] / sub_close.iloc[-2] - 1
                n_adv = int((today_ret > 0).sum())
                n_dec = int((today_ret < 0).sum())
            else:
                n_adv = n_dec = 0
        else:
            n_adv = n_dec = 0

        # RS leaders / laggards within this sector. Ensure leaders/laggards
        # are DISJOINT — when n_covered < 6, top-3 and bottom-3 would otherwise
        # overlap (the partial-coverage NIFTY_MEDIA case).
        sector_rs = sorted(
            ((s, rs_scores.get(s)) for s in covered if s in rs_scores),
            key=lambda kv: (kv[1] if kv[1] is not None else float("-inf")),
        )
        sector_rs_with_score = [(s, sc) for s, sc in sector_rs if sc is not None]
        n_ranked = len(sector_rs_with_score)
        if n_ranked <= 1:
            rs_leaders = list(reversed(sector_rs_with_score))
            rs_laggards = []
        else:
            half = min(3, n_ranked // 2)
            rs_laggards = sector_rs_with_score[:half]
            rs_leaders = list(reversed(sector_rs_with_score[-half:]))

        snapshots[sector_name] = SectorBreadthSnapshot(
            sector=sector_name,
            date=asof,
            n_constituents=n_total,
            n_covered=n_covered,
            coverage=coverage,
            pct_above_50dma=_safe_float(row.get("pct_above_50dma")),
            pct_above_100dma=_safe_float(row.get("pct_above_100dma")),
            pct_above_200dma=_safe_float(row.get("pct_above_200dma")),
            pct_advancing_today=_safe_float(row.get("pct_advancing")),
            n_advancing=n_adv,
            n_declining=n_dec,
            dispersion_20d=_safe_float(row.get("dispersion_20d")),
            median_ret_20d=_safe_float(row.get("median_ret_20d")),
            rs_leaders=rs_leaders,
            rs_laggards=rs_laggards,
            thrust_day=bool(row.get("thrust_day", 0) or 0),
            is_partial_coverage=(sector_name in PARTIAL_COVERAGE_SECTORS),
        )
    return snapshots


# ---------- helpers ----------

def _compute_rs_scores(
    close: pd.DataFrame, nifty: pd.Series, asof: pd.Timestamp, lookback: int,
) -> dict[str, float]:
    """6-month relative strength = stock_ret - nifty_ret over lookback."""
    valid_close = close.loc[:asof]
    if len(valid_close) < lookback + 1:
        return {}
    end_prices = valid_close.iloc[-1]
    start_prices = valid_close.iloc[-(lookback + 1)]
    stock_ret = (end_prices / start_prices) - 1.0

    nifty_valid = nifty.loc[:asof]
    if len(nifty_valid) < lookback + 1:
        return {}
    nifty_ret = nifty_valid.iloc[-1] / nifty_valid.iloc[-(lookback + 1)] - 1.0

    rs = stock_ret - nifty_ret
    return {sym: float(score) for sym, score in rs.items() if pd.notna(score)}


def _safe_float(x) -> float | None:
    if x is None or (isinstance(x, float) and (np.isnan(x))):
        return None
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    if np.isnan(v):
        return None
    return v


def clear_cache() -> None:
    _build_stock_panel.cache_clear()
    compute_sector_breadth_panel.cache_clear()
