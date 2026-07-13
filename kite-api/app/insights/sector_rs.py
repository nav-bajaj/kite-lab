"""Sector relative-strength rankings.

For each NIFTY sector index, computes its return over multiple lookback
windows minus Nifty 50's return over the same window, then ranks all
sectors against each other.

Powers the "sector rotation map" content in the Daily Quant Note and
the /insights/sectors web page. Where `sector_breadth.py` answers
"how broad is each sector's rally" at the constituent level, this
module answers "which sectors are leading right now and which are
moving up the leaderboard."

  RS_window(sector) = sector_return(window) − nifty50_return(window)
  rank_window(sector) = ranking among all valid sectors that window
                         (1 = strongest, N = weakest, NaN excluded)

Windows: 5/20/60/120/252 trading days (≈ 1w / 1m / 3m / 6m / 1y).

Universe: 10 sectors with ≥10 years of index history. The two newer/
shorter-history sectors (NIFTY_CONSUMER_DURABLES, NIFTY_CONSUMPTION)
are constituent-level only — they appear in sector_constituents and
sector_breadth but not in sector_rs because their index series doesn't
go back far enough for stable ranking.

Outputs:
  compute_sector_rs_panel() → wide DataFrame, MultiIndex columns
                              (sector, window, metric), date index.
                              metrics: 'rs_score', 'rank'.

  get_sector_rs_snapshot(asof=None) → dict[sector → SectorRSSnapshot]
                                       for one date (default: latest).
                                       Includes today's score+rank for
                                       each window AND the rank delta
                                       vs 5 trading days ago (climbed/
                                       fell on the leaderboard).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from functools import lru_cache
from pathlib import Path

import numpy as np
import pandas as pd

from app.config import get_settings
from app.insights._freshness import file_signature
from app.insights.sector_breadth import get_sector_breadth_snapshot


# Sectors with ≥10y of index history (same set as macro.py).
SECTOR_INDICES = [
    "NIFTY_BANK", "NIFTY_IT", "NIFTY_PHARMA", "NIFTY_FMCG", "NIFTY_AUTO",
    "NIFTY_METAL", "NIFTY_REALTY", "NIFTY_FIN_SERVICE", "NIFTY_ENERGY",
    "NIFTY_MEDIA",
]

# Lookback windows in trading days
WINDOWS_TD: dict[str, int] = {
    "5d":   5,
    "20d":  20,
    "60d":  60,
    "120d": 120,
    "252d": 252,
}

# Week-over-week comparison distance for rank-change tracking
WOW_TD = 5


@dataclass
class SectorRSSnapshot:
    """RS + rank snapshot for one sector on one date."""
    sector: str
    date: pd.Timestamp
    sector_close: float | None
    sector_chg_today_pct: float | None

    # Per-window RS score (decimal, e.g. 0.05 = sector +5pp vs Nifty)
    rs_5d: float | None
    rs_20d: float | None
    rs_60d: float | None
    rs_120d: float | None
    rs_252d: float | None

    # Per-window rank (1 = strongest among ranked sectors; None if NaN)
    rank_5d: int | None
    rank_20d: int | None
    rank_60d: int | None
    rank_120d: int | None
    rank_252d: int | None

    # Week-over-week rank change (positive = climbed; negative = fell).
    # E.g., went from rank 6 to rank 3 over 5 trading days = +3.
    rank_change_wow_20d: int | None  # tracking 20d-window rank movement
    rank_change_wow_60d: int | None
    rank_change_wow_120d: int | None
    rank_change_wow_252d: int | None

    # Constituent-level breadth context (from sector_breadth.py).
    # Lets downstream commentary call out narrow vs broad rallies.
    pct_above_200dma: float | None = None
    is_partial_coverage: bool = False

    def to_dict(self) -> dict:
        d = asdict(self)
        d["date"] = self.date.isoformat() if isinstance(self.date, pd.Timestamp) else self.date
        return d


def _indices_dir() -> Path:
    settings = get_settings()
    external = Path("/Users/navdeep/Documents/stock_data/indices_data_full")
    if external.exists():
        return external
    return settings.data_dir / "indices_data_historical"


def _load_index_close(name: str) -> pd.Series:
    p = _indices_dir() / f"{name}.csv"
    if not p.exists():
        return pd.Series(dtype=float)
    return (pd.read_csv(p, parse_dates=["date"])
              .set_index("date")["close"]
              .sort_index())


def _sector_signature() -> tuple:
    """Sector-index panel signature. The pipeline writes all indices together,
    so a representative sector sentinel (NIFTY_BANK) tracks the whole set."""
    return (file_signature(_indices_dir() / "NIFTY_BANK.csv"),)


def _nifty_signature() -> tuple:
    return (file_signature(_indices_dir() / "NIFTY_50.csv"),)


def _load_sector_panel() -> pd.DataFrame:
    """Wide DataFrame: rows=date, cols=sector_name, values=close."""
    return _load_sector_panel_cached(_sector_signature())


@lru_cache(maxsize=2)
def _load_sector_panel_cached(signature) -> pd.DataFrame:
    series = {}
    for name in SECTOR_INDICES:
        s = _load_index_close(name)
        if s.empty:
            continue
        series[name] = s
    if not series:
        return pd.DataFrame()
    return pd.concat(series, axis=1).sort_index()


_load_sector_panel.cache_clear = _load_sector_panel_cached.cache_clear


def _nifty_close() -> pd.Series:
    return _nifty_close_cached(_nifty_signature())


@lru_cache(maxsize=2)
def _nifty_close_cached(signature) -> pd.Series:
    return _load_index_close("NIFTY_50")


_nifty_close.cache_clear = _nifty_close_cached.cache_clear


def compute_sector_rs_panel() -> pd.DataFrame:
    """Time series of RS scores + ranks per sector × window.

    Wide DataFrame, MultiIndex columns (sector, window, metric),
    where metric ∈ {'rs_score', 'rank'}.
    """
    return _compute_sector_rs_panel_cached(_sector_signature() + _nifty_signature())


@lru_cache(maxsize=2)
def _compute_sector_rs_panel_cached(signature) -> pd.DataFrame:
    sector_panel = _load_sector_panel()
    if sector_panel.empty:
        return pd.DataFrame()
    nifty = _nifty_close().reindex(sector_panel.index).ffill()

    out: dict[tuple[str, str, str], pd.Series] = {}
    for window_name, n_days in WINDOWS_TD.items():
        sector_ret = sector_panel.pct_change(n_days, fill_method=None)
        nifty_ret = nifty.pct_change(n_days, fill_method=None)
        rs = sector_ret.sub(nifty_ret, axis=0)
        # Rank 1 = highest RS. NaN inputs become NaN ranks (excluded).
        rank = rs.rank(axis=1, ascending=False, method="min")
        for sector in sector_panel.columns:
            out[(sector, window_name, "rs_score")] = rs[sector]
            out[(sector, window_name, "rank")] = rank[sector]

    df = pd.DataFrame(out)
    df.columns = pd.MultiIndex.from_tuples(
        df.columns, names=["sector", "window", "metric"]
    )
    return df.sort_index(axis=1)


def get_sector_rs_snapshot(
    asof: pd.Timestamp | None = None,
) -> dict[str, SectorRSSnapshot]:
    """Per-sector RS snapshot for `asof` (default: latest trading day).

    For each sector, returns scores + ranks across all 5 windows plus
    week-over-week rank deltas on the 20/60/120/252-day windows. Also
    pulls the constituent-level pct_above_200dma from sector_breadth
    so downstream commentary has the narrow-vs-broad context attached.
    """
    panel = compute_sector_rs_panel()
    if panel.empty:
        return {}

    if asof is None:
        asof = panel.index.max()
    asof = pd.Timestamp(asof)
    valid = panel.index[panel.index <= asof]
    if valid.empty:
        return {}
    asof = valid.max()

    # Find the date 5 trading days ago for WoW comparison
    asof_pos = panel.index.get_loc(asof)
    wow_date = panel.index[asof_pos - WOW_TD] if asof_pos >= WOW_TD else None

    # Per-sector close + today's % change
    sector_panel = _load_sector_panel()
    sector_panel_at = sector_panel.loc[:asof]
    today_close = sector_panel_at.iloc[-1] if len(sector_panel_at) else pd.Series(dtype=float)
    yest_close = sector_panel_at.iloc[-2] if len(sector_panel_at) >= 2 else None
    if yest_close is not None:
        today_chg = (today_close / yest_close) - 1.0
    else:
        today_chg = pd.Series(np.nan, index=today_close.index)

    # Constituent-level breadth (gives us the narrow/broad overlay)
    breadth_snaps = get_sector_breadth_snapshot(asof)

    out: dict[str, SectorRSSnapshot] = {}
    for sector in panel.columns.get_level_values("sector").unique():
        today_row = panel.loc[asof, sector]
        wow_row = panel.loc[wow_date, sector] if wow_date is not None else None

        def _rank(window: str) -> int | None:
            v = today_row.get((window, "rank"))
            return int(v) if pd.notna(v) else None

        def _rs(window: str) -> float | None:
            v = today_row.get((window, "rs_score"))
            return float(v) if pd.notna(v) else None

        def _wow_change(window: str) -> int | None:
            """Positive = climbed leaderboard since 5 days ago."""
            if wow_row is None:
                return None
            old = wow_row.get((window, "rank"))
            new = today_row.get((window, "rank"))
            if pd.isna(old) or pd.isna(new):
                return None
            return int(old) - int(new)

        bsnap = breadth_snaps.get(sector)

        out[sector] = SectorRSSnapshot(
            sector=sector,
            date=asof,
            sector_close=float(today_close.get(sector, np.nan))
                if pd.notna(today_close.get(sector, np.nan)) else None,
            sector_chg_today_pct=float(today_chg.get(sector, np.nan))
                if pd.notna(today_chg.get(sector, np.nan)) else None,
            rs_5d=_rs("5d"),
            rs_20d=_rs("20d"),
            rs_60d=_rs("60d"),
            rs_120d=_rs("120d"),
            rs_252d=_rs("252d"),
            rank_5d=_rank("5d"),
            rank_20d=_rank("20d"),
            rank_60d=_rank("60d"),
            rank_120d=_rank("120d"),
            rank_252d=_rank("252d"),
            rank_change_wow_20d=_wow_change("20d"),
            rank_change_wow_60d=_wow_change("60d"),
            rank_change_wow_120d=_wow_change("120d"),
            rank_change_wow_252d=_wow_change("252d"),
            pct_above_200dma=(bsnap.pct_above_200dma if bsnap else None),
            is_partial_coverage=(bsnap.is_partial_coverage if bsnap else False),
        )
    return out


def get_leaderboard(
    window: str = "60d",
    asof: pd.Timestamp | None = None,
) -> list[SectorRSSnapshot]:
    """Return all sectors sorted by `window`'s rank (best first).

    Convenience wrapper around get_sector_rs_snapshot for the Daily
    Quant Note's "sector rotation" section.
    """
    snaps = get_sector_rs_snapshot(asof)
    rank_attr = f"rank_{window}"
    return sorted(
        snaps.values(),
        key=lambda s: (getattr(s, rank_attr) or 9999),
    )


compute_sector_rs_panel.cache_clear = _compute_sector_rs_panel_cached.cache_clear


def clear_cache() -> None:
    _load_sector_panel_cached.cache_clear()
    _nifty_close_cached.cache_clear()
    _compute_sector_rs_panel_cached.cache_clear()
