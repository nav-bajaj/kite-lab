"""Sector map for the engine's sector_cap hook: NSE's current 21 sectors, historical labels mapped onto them."""
from __future__ import annotations
from pathlib import Path
import pandas as pd

LOOKUP = Path(__file__).resolve().parents[2] / "data/static/sectors/sector_v2_lookup.csv"   # git-tracked, shipped in the image (P2, 2026-09-12); refreshed at each reconstitution


def load_sector_map(path: Path = LOOKUP) -> dict:
    """symbol -> sector; priority current NSE scheme > 2014-20 > 2006-13 > Zerodha, latest snapshot within a scheme."""
    lk = pd.read_csv(path, parse_dates=["as_of_first", "as_of"])
    out = {}
    for sym, g in lk.groupby("symbol"):
        g = g.sort_values(["pri", "as_of"], ascending=[True, False]); out[sym] = g.sector_v2.iloc[0]
    return out
