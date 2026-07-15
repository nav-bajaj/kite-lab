"""Per-stock Zerodha sector loader.

Reads the flat mapping produced by `scripts/fetch_zerodha_sectors.py` and
exposes it as symbol -> sector lookups for the insight modules and the API.

This is the finer, per-stock counterpart to `sector_constituents.py`: that
module groups stocks by the 12 NSE thematic *indices* (partial coverage, a
stock can be in several); this one gives every tracked stock exactly one
canonical Zerodha sector from the 35-sector taxonomy.

Source file (committed, ships in the image the same way the sector_constituents
snapshots do):
    <data_dir>/data/static/zerodha_sectors.csv
        symbol, company, zerodha_sector, zerodha_sector_slug, source_exchange

The mapping changes only when the script is re-run (at an NSE reconstitution),
so we cache it in memory keyed on the file's mtime signature — a rewrite busts
the cache automatically, matching the self-invalidating pattern in
`app.insights._freshness`.
"""
from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path

from app.config import get_settings
from app.insights._freshness import file_signature


def _path() -> Path:
    return get_settings().data_dir / "data" / "static" / "zerodha_sectors.csv"


def _signature() -> tuple:
    """Cache key: the mapping file's mtime. Returns a stable sentinel when the
    file is absent so a later-arriving file still busts the cache."""
    return (file_signature(_path()),)


@lru_cache(maxsize=2)
def _load(signature) -> dict[str, dict[str, str]]:
    path = _path()
    if not path.exists():
        raise FileNotFoundError(
            f"No Zerodha sector map at {path}. "
            f"Run scripts/fetch_zerodha_sectors.py first."
        )
    out: dict[str, dict[str, str]] = {}
    with path.open() as fh:
        for r in csv.DictReader(fh):
            sym = (r.get("symbol") or "").strip()
            sector = (r.get("zerodha_sector") or "").strip()
            if not sym or not sector:
                continue  # unresolved rows carry no sector; skip
            out[sym] = {
                "sector": sector,
                "slug": (r.get("zerodha_sector_slug") or "").strip(),
            }
    return out


def get_symbol_to_sector() -> dict[str, str]:
    """{canonical symbol -> Zerodha sector display name}."""
    return {sym: rec["sector"] for sym, rec in _load(_signature()).items()}


def get_sector_for(symbol: str) -> str | None:
    """Zerodha sector for `symbol`, or None if not mapped / unresolved."""
    rec = _load(_signature()).get(symbol)
    return rec["sector"] if rec else None


def get_sector_to_symbols() -> dict[str, tuple[str, ...]]:
    """Reverse index: {sector -> sorted tuple of member symbols}."""
    out: dict[str, list[str]] = {}
    for sym, rec in _load(_signature()).items():
        out.setdefault(rec["sector"], []).append(sym)
    return {sector: tuple(sorted(syms)) for sector, syms in out.items()}


def clear_cache() -> None:
    """Drop the in-memory cache. Call after re-running the fetch script."""
    _load.cache_clear()
