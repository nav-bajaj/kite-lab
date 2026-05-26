"""Fetch current NSE sector-index constituents.

Source: NSE archives (https://nsearchives.nseindia.com/content/indices/), one
static CSV per sector index. Schema matches the existing universe files in
`data/static/` — Company Name, Industry, Symbol, Series, ISIN Code — so the
downstream insights code can load these with the same readers used for the
NSE 500 / Nifty 100 / Nifty 250 universes.

Snapshots are written to `data/static/sector_constituents/<YYYY-MM>/<SECTOR>.csv`,
one directory per monthly snapshot. Re-running in the same month overwrites
that month's snapshot.

Behaviour:
  - Best-effort: if any individual sector fails, log + continue with the rest
  - Exits non-zero if more than `--max-failures` sectors failed (default: 2)
  - Re-running is idempotent (overwrites)

Usage:
    python scripts/fetch_sector_constituents.py
    python scripts/fetch_sector_constituents.py --snapshot 2026-05  # override
    python scripts/fetch_sector_constituents.py --dry-run           # print URLs only
    python scripts/fetch_sector_constituents.py --sectors NIFTY_BANK NIFTY_IT
"""
from __future__ import annotations

import argparse
import io
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = REPO_ROOT / "data" / "static" / "sector_constituents"

# Sector → NSE archive CSV filename. Verified URL pattern:
# https://nsearchives.nseindia.com/content/indices/<filename>
SECTOR_FILES: dict[str, str] = {
    "NIFTY_BANK":              "ind_niftybanklist.csv",
    "NIFTY_IT":                "ind_niftyitlist.csv",
    "NIFTY_PHARMA":            "ind_niftypharmalist.csv",
    "NIFTY_FMCG":              "ind_niftyfmcglist.csv",
    "NIFTY_AUTO":              "ind_niftyautolist.csv",
    "NIFTY_METAL":             "ind_niftymetallist.csv",
    "NIFTY_REALTY":            "ind_niftyrealtylist.csv",
    "NIFTY_ENERGY":            "ind_niftyenergylist.csv",
    "NIFTY_MEDIA":             "ind_niftymedialist.csv",
    "NIFTY_FIN_SERVICE":       "ind_niftyfinancelist.csv",
    "NIFTY_CONSUMER_DURABLES": "ind_niftyconsumerdurableslist.csv",
    "NIFTY_CONSUMPTION":       "ind_niftyconsumptionlist.csv",
}

BASE_URL = "https://nsearchives.nseindia.com/content/indices"

EXPECTED_COLUMNS = {"Company Name", "Industry", "Symbol", "Series", "ISIN Code"}

# Plausible per-sector size band — fails the row count check if outside.
# Calibrated to NSE methodology (10-30 stocks per typical sector index).
SECTOR_SIZE_RANGE: dict[str, tuple[int, int]] = {
    "NIFTY_BANK":              (8, 20),
    "NIFTY_IT":                (8, 20),
    "NIFTY_PHARMA":            (8, 25),
    "NIFTY_FMCG":              (8, 20),
    "NIFTY_AUTO":              (8, 20),
    "NIFTY_METAL":             (8, 20),
    "NIFTY_REALTY":            (5, 20),
    "NIFTY_ENERGY":            (8, 50),  # broad NSE definition (~40 stocks: power + oil & gas + capital goods)
    "NIFTY_MEDIA":             (3, 15),
    "NIFTY_FIN_SERVICE":       (15, 35),
    "NIFTY_CONSUMER_DURABLES": (8, 20),
    "NIFTY_CONSUMPTION":       (15, 40),
}

# Mozilla UA — NSE blocks requests without a browser-like User-Agent.
REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/csv,application/csv,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def fetch_one(sector: str, filename: str, timeout: int = 30) -> pd.DataFrame:
    url = f"{BASE_URL}/{filename}"
    response = requests.get(url, headers=REQUEST_HEADERS, timeout=timeout)
    response.raise_for_status()
    text = response.text

    # NSE serves CSV but occasionally with a BOM
    if text.startswith("﻿"):
        text = text.lstrip("﻿")

    df = pd.read_csv(io.StringIO(text))
    df.columns = [c.strip() for c in df.columns]

    missing = EXPECTED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(
            f"{sector}: expected columns {sorted(EXPECTED_COLUMNS)}, "
            f"got {sorted(df.columns)}; missing: {sorted(missing)}"
        )

    # Drop fully-empty rows (occasionally present)
    df = df.dropna(how="all").reset_index(drop=True)
    # Coerce strings (Symbol sometimes parsed as float for purely-numeric tickers)
    for col in ["Company Name", "Industry", "Symbol", "Series", "ISIN Code"]:
        df[col] = df[col].astype(str).str.strip()

    # Filter NSE's "DUMMY*" placeholder rows. NSE publishes these as
    # temporary slots in sector indices for pending corporate actions
    # (e.g., the Vedanta demerger has 4 DUMMYVEDL1-4 entries in NIFTY METAL
    # pending the demerger's completion). They have no price data and would
    # otherwise pollute downstream breadth calculations.
    pre = len(df)
    dummy_mask = df["Symbol"].str.upper().str.startswith("DUMMY")
    if dummy_mask.any():
        dropped = df[dummy_mask]["Symbol"].tolist()
        print(f"  [info] {sector}: dropping {len(dropped)} DUMMY placeholder rows: {dropped}")
        df = df[~dummy_mask].reset_index(drop=True)
    return df


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--snapshot",
        default=datetime.now().strftime("%Y-%m"),
        help="Snapshot directory name (default: current YYYY-MM)",
    )
    ap.add_argument("--sectors", nargs="+", default=None,
                    help="Only fetch these sectors (default: all)")
    ap.add_argument("--dry-run", action="store_true",
                    help="Print URLs and exit without fetching")
    ap.add_argument("--max-failures", type=int, default=2,
                    help="Exit non-zero if more than N sectors failed")
    args = ap.parse_args()

    sectors = args.sectors or list(SECTOR_FILES.keys())
    unknown = [s for s in sectors if s not in SECTOR_FILES]
    if unknown:
        print(f"ERROR: unknown sectors: {unknown}", file=sys.stderr)
        print(f"Known sectors: {sorted(SECTOR_FILES)}", file=sys.stderr)
        return 2

    out_dir = OUTPUT_DIR / args.snapshot
    print(f"[fetch_sector_constituents] snapshot dir: {out_dir}")

    if args.dry_run:
        print("\nDRY RUN — would fetch:")
        for sector in sectors:
            print(f"  {sector:<26} {BASE_URL}/{SECTOR_FILES[sector]}")
        return 0

    out_dir.mkdir(parents=True, exist_ok=True)

    failures: list[tuple[str, str]] = []
    succeeded: list[tuple[str, int]] = []
    for sector in sectors:
        filename = SECTOR_FILES[sector]
        try:
            df = fetch_one(sector, filename)
        except Exception as exc:
            print(f"  [FAIL] {sector:<26} ({filename}): {exc}")
            failures.append((sector, str(exc)))
            continue

        # Size sanity check (warn but don't fail)
        n = len(df)
        lo, hi = SECTOR_SIZE_RANGE.get(sector, (1, 100))
        if not (lo <= n <= hi):
            print(f"  [WARN] {sector:<26} returned {n} rows; expected {lo}-{hi} — saving anyway")

        out_path = out_dir / f"{sector}.csv"
        df.to_csv(out_path, index=False)
        succeeded.append((sector, n))
        print(f"  [OK]   {sector:<26} {n:>3} constituents → {out_path.relative_to(REPO_ROOT)}")

    print(f"\nSummary: {len(succeeded)} succeeded, {len(failures)} failed")
    if failures:
        print("\nFailures:")
        for sector, msg in failures:
            print(f"  {sector}: {msg}")

    if len(failures) > args.max_failures:
        print(f"\nExceeded --max-failures={args.max_failures}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
