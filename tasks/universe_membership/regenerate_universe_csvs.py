"""Regenerate data/static/*_universe.csv as CURRENT-MEMBERS views.

As of 2026-07-14 the membership files are the source of truth; the
*_universe.csv snapshots are derived views for consumers that want "the
universe today" (fetch fallback, insights breadth/watchlists, research).
Symbols are OUR canonical tickers (price-file names) — NSE renames map back
via CANONICAL, so e.g. the row for JSW Dulux carries symbol AKZOINDIA.

Metadata (Company Name / Industry / Series / ISIN) comes from the dated NSE
lists in data/nse_lists_<date>/. Legacy admin portfolios do NOT read these
files anymore — they are pinned to data/static/legacy_snapshot_2025-11-06/.

Usage: python tasks/universe_membership/regenerate_universe_csvs.py
"""
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
NEW_DIR = Path(__file__).resolve().parent / "data" / "nse_lists_2026-07-14"
STATIC = ROOT / "data" / "static"
sys.path.insert(0, str(ROOT))

from scripts.universe_membership import load_membership, members_asof

CANONICAL = {"JSWDULUX": "AKZOINDIA", "LTM": "LTIM"}
ASOF = "2026-07-15"   # first date the refreshed membership applies

PAIRS = [
    ("nse500", "ind_nifty500list.csv"),
    ("nifty250", "ind_nifty250list.csv"),
    ("nifty100", "ind_nifty100list.csv"),
    ("nifty50", "ind_nifty50list.csv"),
]

for uid, new_name in PAIRS:
    nse = pd.read_csv(NEW_DIR / new_name)
    nse["Symbol"] = nse["Symbol"].astype(str).str.strip().map(
        lambda s: CANONICAL.get(s, s))
    members = members_asof(load_membership(STATIC / f"{uid}_membership.csv"), ASOF)
    missing = members - set(nse["Symbol"])
    extra = set(nse["Symbol"]) - members
    if missing or extra:
        raise SystemExit(f"[{uid}] membership/list mismatch: "
                         f"missing={sorted(missing)} extra={sorted(extra)}")
    out = nse.sort_values("Company Name").reset_index(drop=True)
    out.to_csv(STATIC / f"{uid}_universe.csv", index=False)
    print(f"[{uid}] wrote {len(out)} current members -> {uid}_universe.csv")
