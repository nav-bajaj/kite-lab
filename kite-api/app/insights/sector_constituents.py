"""Sector constituent loader — reads the dated snapshots produced by
`scripts/fetch_sector_constituents.py` and exposes them as a structured
mapping for downstream insight modules.

The constituents change rarely (NSE rebalances every 6 months + occasional
ad-hoc changes), so we cache the latest snapshot in memory for the
process lifetime. Pass `force_rebuild=True` to re-read from disk after a
new snapshot is fetched.

Snapshots live at:
  <data_dir>/data/static/sector_constituents/<YYYY-MM>/<SECTOR>.csv

Sectors with known partial price-data coverage are flagged here so
downstream code (sector_breadth.py) can label them as low-confidence in
the published output. The current PARTIAL_COVERAGE set is documented in
`tests/test_sector_constituents.py` and tracked via task 0.5a.
"""
from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import pandas as pd

from app.config import get_settings


# Sectors where the snapshot includes small-caps outside our NSE 500 price
# panel. Downstream breadth output should flag these as low-confidence
# until task 0.5a closes the price-data gap.
PARTIAL_COVERAGE_SECTORS: frozenset[str] = frozenset({"NIFTY_MEDIA"})


@dataclass(frozen=True)
class Sector:
    """One sector's constituent list + metadata."""
    name: str                      # e.g. "NIFTY_BANK"
    snapshot_date: str             # "YYYY-MM"
    symbols: tuple[str, ...]       # constituent symbols in alphabetical order
    industries: dict[str, str]     # symbol → industry string from NSE
    company_names: dict[str, str]  # symbol → full company name
    is_partial_coverage: bool

    @property
    def n(self) -> int:
        return len(self.symbols)


def _root() -> Path:
    return get_settings().data_dir / "data" / "static" / "sector_constituents"


def _latest_snapshot_dir() -> Path:
    """Return path to the latest YYYY-MM snapshot directory."""
    root = _root()
    if not root.exists():
        raise FileNotFoundError(
            f"No sector_constituents directory at {root}. "
            f"Run scripts/fetch_sector_constituents.py first."
        )
    candidates = sorted(p for p in root.iterdir() if p.is_dir())
    if not candidates:
        raise FileNotFoundError(
            f"No snapshot subdirectories under {root}. "
            f"Run scripts/fetch_sector_constituents.py first."
        )
    return candidates[-1]


def _load_one_sector(name: str, snapshot_dir: Path) -> Sector:
    path = snapshot_dir / f"{name}.csv"
    if not path.exists():
        raise FileNotFoundError(f"Missing sector CSV for {name}: {path}")
    df = pd.read_csv(path)
    # Defensive: trim whitespace + cast Symbol to str
    df["Symbol"] = df["Symbol"].astype(str).str.strip()
    df["Industry"] = df["Industry"].astype(str).str.strip()
    df["Company Name"] = df["Company Name"].astype(str).str.strip()

    symbols = tuple(sorted(df["Symbol"].unique().tolist()))
    industries = dict(zip(df["Symbol"], df["Industry"]))
    names = dict(zip(df["Symbol"], df["Company Name"]))

    return Sector(
        name=name,
        snapshot_date=snapshot_dir.name,
        symbols=symbols,
        industries=industries,
        company_names=names,
        is_partial_coverage=(name in PARTIAL_COVERAGE_SECTORS),
    )


@lru_cache(maxsize=1)
def get_all_sectors() -> dict[str, Sector]:
    """Return {sector_name: Sector} for the latest snapshot.

    Cached for process lifetime; call `clear_cache()` after fetching a
    new snapshot to pick up changes.
    """
    snapshot_dir = _latest_snapshot_dir()
    sectors: dict[str, Sector] = {}
    for csv_path in sorted(snapshot_dir.glob("*.csv")):
        name = csv_path.stem
        sectors[name] = _load_one_sector(name, snapshot_dir)
    return sectors


def get_sector(name: str) -> Sector:
    """Get a single sector. Raises KeyError if not present in the snapshot."""
    sectors = get_all_sectors()
    if name not in sectors:
        raise KeyError(
            f"Sector {name!r} not in latest snapshot. "
            f"Available: {sorted(sectors.keys())}"
        )
    return sectors[name]


@lru_cache(maxsize=1)
def get_symbol_to_sectors() -> dict[str, tuple[str, ...]]:
    """Reverse mapping: symbol → tuple of sectors that contain it.

    Many stocks appear in multiple sectors (e.g., HDFCBANK is in NIFTY_BANK
    AND NIFTY_FIN_SERVICE AND NIFTY_CONSUMPTION). Returned tuples are sorted.
    """
    sectors = get_all_sectors()
    out: dict[str, list[str]] = {}
    for sector_name, sector in sectors.items():
        for sym in sector.symbols:
            out.setdefault(sym, []).append(sector_name)
    return {sym: tuple(sorted(lst)) for sym, lst in out.items()}


def get_sectors_for(symbol: str) -> tuple[str, ...]:
    """Return tuple of sector names that contain `symbol`. Empty if none."""
    return get_symbol_to_sectors().get(symbol, ())


def clear_cache() -> None:
    """Drop in-memory cache. Call after fetching a new snapshot."""
    get_all_sectors.cache_clear()
    get_symbol_to_sectors.cache_clear()
