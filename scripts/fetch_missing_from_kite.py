"""Fetch missing-from-Kite symbols identified by the GDF backfill stitch.

Reads tasks/gdf_full_backfill/stitch_summary.csv (or any compatible
CSV with `symbol` and `status` columns), filters to rows with status
in {no_data, gdf_only}, and fetches each symbol from Kite over the
configured date range. Output lands in a SIDE directory so the
production `nse500_data/` (which the daily pipeline owns) is never
touched.

The downstream workflow is:

  1. python scripts/fetch_missing_from_kite.py           # this script
  2. # combine the side dir with production Kite data:
     mkdir -p ~/Documents/stock_data/nse500_data_kite_full
     cp -r nse500_data/. ~/Documents/stock_data/nse500_data_kite_full/
     cp -r ~/Documents/stock_data/nse500_data_kite_extra/. \\
            ~/Documents/stock_data/nse500_data_kite_full/
  3. python scripts/stitch_gdf_kite.py \\
       --gdf-dir ~/Documents/stock_data/nse500_data_gdf_full \\
       --kite-dir ~/Documents/stock_data/nse500_data_kite_full \\
       --out-dir ~/Documents/stock_data/nse500_data_full

After that, nse500_data_full/ has the comprehensive panel with
~700 stocks instead of the original 686.

Usage:
    python scripts/fetch_missing_from_kite.py
    python scripts/fetch_missing_from_kite.py --start 2020-01-01
    python scripts/fetch_missing_from_kite.py --dry-run
"""
from __future__ import annotations

import argparse
import datetime as dt
import os
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# history_utils lives in scripts/ alongside this one.
sys.path.insert(0, str(ROOT / "scripts"))
from history_utils import init_kite_client, download_batches  # noqa: E402


DEFAULT_SUMMARY = ROOT / "tasks/gdf_full_backfill/stitch_summary.csv"
DEFAULT_OUTPUT = Path.home() / "Documents/stock_data/nse500_data_kite_extra"
DEFAULT_START = "2017-01-01"  # Kite's deepest reliable historical-data window
# Statuses that mean "no current-Kite coverage of this symbol":
NEED_KITE_STATUSES = {"no_data", "gdf_only"}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY,
                    help=f"Stitch summary CSV (default: {DEFAULT_SUMMARY.relative_to(ROOT)})")
    ap.add_argument("--output", type=Path, default=DEFAULT_OUTPUT,
                    help=f"Output dir (default: {DEFAULT_OUTPUT})")
    ap.add_argument("--start", default=DEFAULT_START)
    ap.add_argument("--end", default=None, help="Default: today")
    ap.add_argument("--dry-run", action="store_true",
                    help="List target symbols + counts; no Kite calls")
    args = ap.parse_args()

    if not args.summary.exists():
        print(f"Stitch summary not found: {args.summary}", file=sys.stderr)
        return 1

    summary = pd.read_csv(args.summary)
    if "status" not in summary.columns or "symbol" not in summary.columns:
        print(f"{args.summary} missing required columns 'symbol' and/or 'status'",
              file=sys.stderr)
        return 1

    targets = summary[summary["status"].isin(NEED_KITE_STATUSES)]["symbol"].tolist()
    print(f"Stitch summary:  {args.summary.relative_to(ROOT)}")
    print(f"Filter:          status in {sorted(NEED_KITE_STATUSES)}")
    print(f"Target symbols:  {len(targets)}")

    by_status = summary[summary["status"].isin(NEED_KITE_STATUSES)]["status"].value_counts()
    for s, n in by_status.items():
        print(f"   {s:14s} {n}")

    if not targets:
        print("Nothing to fetch.")
        return 0

    args.output.mkdir(parents=True, exist_ok=True)
    print(f"Output dir:      {args.output}")
    end_date = args.end or dt.date.today().isoformat()
    print(f"Date range:      {args.start} → {end_date}")
    print()

    if args.dry_run:
        print("[dry-run] sample targets:", targets[:15],
              f"... and {max(0, len(targets) - 15)} more")
        return 0

    # Single daily-bars config covering 2017-01-01 → today, written to
    # the side dir. history_utils.download_batches handles rate-limiting
    # (3 req/sec), retries, and incremental skip (existing files are
    # appended-to, not re-fetched).
    kite = init_kite_client()
    cfg = [{
        "interval": "day",
        "start": pd.Timestamp(args.start),
        "end": pd.Timestamp(end_date),
        "output_dir": str(args.output),
        "suffix": "day",
        "step": pd.Timedelta(days=1),
    }]

    print(f"Fetching {len(targets)} symbols from Kite...")
    print(f"Expected wall-clock: ~{len(targets) / 3 / 60:.1f} min "
          f"at 3 req/sec rate limit + retries.")
    print()

    failures = download_batches(kite, targets, cfg)
    if failures:
        print()
        print(f"!! {len(failures)} symbols failed:")
        for sym, err in list(failures.items())[:20]:
            print(f"   {sym:14s} {err}")
        if len(failures) > 20:
            print(f"   ... and {len(failures) - 20} more")
        return 2

    # Count results
    n_written = len(list(args.output.glob("*_day.csv")))
    print()
    print(f"Done. {n_written} CSVs in {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
