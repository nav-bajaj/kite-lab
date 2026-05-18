"""Validate the output of scripts/gdf_full_backfill.py.

Phase D.1 of tasks/gdf_full_backfill/PLAN.md. Reports per-symbol:

  - row count
  - first / last date
  - calendar-day span
  - largest intra-series gap
  - whether the symbol is in the EMPTY-marker state (no GDF coverage)

Also surfaces aggregate stats and flags suspect symbols (e.g. very
short series for stocks that should have long history).

Usage:

  python scripts/gdf_backfill_validate.py
  python scripts/gdf_backfill_validate.py --output /custom/path
  python scripts/gdf_backfill_validate.py --csv coverage_report.csv
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = Path.home() / "Documents/stock_data/nse500_data_gdf_full"

# Long-listed names that *should* have ~3673 bars from 2009-03-05 through
# 2023-12-29. Anything materially shorter is a quality flag worth eyeing.
EXPECTED_LARGE_CAP = {
    "RELIANCE", "INFY", "TCS", "HDFCBANK", "ICICIBANK", "SBIN", "ITC",
    "AXISBANK", "LT", "HCLTECH", "TECHM", "WIPRO", "BHARTIARTL",
    "KOTAKBANK", "HINDUNILVR", "ASIANPAINT", "BAJFINANCE", "MARUTI",
    "NESTLEIND", "BRITANNIA", "TITAN", "ULTRACEMCO", "GRASIM",
    "JSWSTEEL", "TATASTEEL", "HINDALCO", "COALINDIA", "ONGC",
    "NTPC", "POWERGRID", "DRREDDY", "CIPLA", "SUNPHARMA",
    "TATAMOTORS", "M&M", "EICHERMOT", "HEROMOTOCO", "BAJAJ-AUTO",
}
MIN_EXPECTED_BARS = 3500  # ~14 years × ~250 trading days, allowing some misses


def inspect(path: Path) -> dict:
    """Per-symbol metrics. Returns a dict suitable for a DataFrame row."""
    symbol = path.stem.replace("_day", "")
    try:
        df = pd.read_csv(path, parse_dates=["date"])
    except Exception as exc:
        return {"symbol": symbol, "rows": 0, "error": str(exc)}

    if df.empty:
        return {"symbol": symbol, "rows": 0, "status": "EMPTY-marker",
                "first": None, "last": None, "calendar_days": 0,
                "max_gap_days": 0}

    df = df.sort_values("date").reset_index(drop=True)
    first = df["date"].iloc[0]
    last = df["date"].iloc[-1]
    cal_span = (last - first).days
    diffs = df["date"].diff().dt.days
    max_gap = int(diffs.max()) if len(diffs) > 1 else 0
    return {
        "symbol": symbol,
        "rows": len(df),
        "status": "OK",
        "first": first.date().isoformat(),
        "last": last.date().isoformat(),
        "calendar_days": cal_span,
        "max_gap_days": max_gap,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--output", type=Path, default=DEFAULT_OUTPUT,
                    help=f"Backfill output dir (default: {DEFAULT_OUTPUT})")
    ap.add_argument("--csv", type=Path, default=None,
                    help="Write per-symbol report to this CSV")
    args = ap.parse_args()

    out_dir = args.output
    if not out_dir.exists():
        print(f"Output dir does not exist: {out_dir}", file=sys.stderr)
        return 1

    files = sorted(out_dir.glob("*_day.csv"))
    if not files:
        print(f"No *_day.csv files in {out_dir}", file=sys.stderr)
        return 1

    rows = [inspect(p) for p in files]
    df = pd.DataFrame(rows)

    n = len(df)
    empty = (df["rows"] == 0).sum()
    short = ((df["rows"] > 0) & (df["rows"] < 500)).sum()
    full = (df["rows"] >= MIN_EXPECTED_BARS).sum()

    print(f"=== GDF backfill validation ===")
    print(f"Output dir:     {out_dir}")
    print(f"Total CSVs:     {n}")
    print(f"  full history (>= {MIN_EXPECTED_BARS} rows): {full}")
    print(f"  partial (post-2009 listings):              {n - empty - full}")
    print(f"  short (< 500 rows, recent IPO):            {short}")
    print(f"  EMPTY marker (no GDF coverage):            {empty}")
    print()

    # Large-cap sanity check
    large = df[df["symbol"].isin(EXPECTED_LARGE_CAP)]
    suspect = large[large["rows"] < MIN_EXPECTED_BARS]
    if not suspect.empty:
        print(f"WARNING: {len(suspect)} expected-large-cap symbols have < {MIN_EXPECTED_BARS} rows:")
        for _, r in suspect.iterrows():
            print(f"  {r['symbol']:14s}  rows={r['rows']}  first={r.get('first', '?')}")
    else:
        print(f"All {len(large)} reference large-caps have >= {MIN_EXPECTED_BARS} rows. OK.")
    print()

    # Aggregate
    nonempty = df[df["rows"] > 0]
    if not nonempty.empty:
        total_bars = nonempty["rows"].sum()
        print(f"Total bars across all non-empty symbols: {total_bars:,}")
        print(f"  median rows/symbol: {int(nonempty['rows'].median())}")
        print(f"  earliest first-date in any symbol: {nonempty['first'].min()}")
        print(f"  latest last-date in any symbol:    {nonempty['last'].max()}")
        large_gap = nonempty["max_gap_days"].max()
        worst = nonempty.loc[nonempty["max_gap_days"].idxmax()]
        print(f"  largest intra-series gap: {large_gap} calendar days "
              f"in {worst['symbol']}")

    if args.csv:
        df.to_csv(args.csv, index=False)
        print(f"\nWrote per-symbol report to {args.csv}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
