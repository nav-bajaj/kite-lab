"""Backfill US equity daily OHLCV from EODHD into us_equities_data/.

Requires a paid EODHD token (free/demo will fail on most symbols). Reads the
universe from data/static/us_equities_universe.csv. Resumable: skips symbols
whose CSV already exists with size > 100 bytes (override with --force).

Run from repo root with venv active:
    python scripts/fetch_us_equities_history.py
    python scripts/fetch_us_equities_history.py --symbols AAPL MSFT NVDA
    python scripts/fetch_us_equities_history.py --limit 10 --start 2010-01-01
    python scripts/fetch_us_equities_history.py --force
"""
from __future__ import annotations

import argparse
import csv
import os
import sys
import time
from pathlib import Path
from typing import List

import pandas as pd
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from data_pipeline.eodhd_client import EODHDClient, EODHDAPIError  # noqa: E402
from data_pipeline.storage import save_dataframe  # noqa: E402


UNIVERSE_CSV = ROOT / "data" / "static" / "us_equities_universe.csv"
OUT_DIR = ROOT / "us_equities_data"
MIN_CSV_BYTES = 100


def load_symbols(only: List[str] | None, limit: int | None) -> List[str]:
    syms: List[str] = []
    with open(UNIVERSE_CSV) as f:
        for row in csv.DictReader(f):
            s = (row.get("Symbol") or "").strip()
            if s:
                syms.append(s)
    if only:
        wanted = {s.upper() for s in only}
        syms = [s for s in syms if s.upper() in wanted]
    if limit:
        syms = syms[:limit]
    return syms


def already_done(symbol: str, force: bool) -> bool:
    if force:
        return False
    p = OUT_DIR / f"{symbol}_day.csv"
    return p.exists() and p.stat().st_size > MIN_CSV_BYTES


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbols", nargs="+", default=None)
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--rate-per-min", type=int,
                        default=int(os.environ.get("EODHD_RATE_PER_MIN", 300)))
    parser.add_argument("--start", default="2000-01-01")
    parser.add_argument("--end", default=None,
                        help="default: today")
    parser.add_argument("--raw", action="store_true",
                        help="adjusted=False (for diagnostic runs)")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    end = args.end or pd.Timestamp.utcnow().strftime("%Y-%m-%d")

    syms = load_symbols(args.symbols, args.limit)
    print(f"[ok] {len(syms)} symbols   rate={args.rate_per_min}/min   "
          f"adjusted={not args.raw}   range={args.start}..{end}")

    client = EODHDClient(rate_per_min=args.rate_per_min)
    started = time.time()
    ok = skipped = failed = 0
    failures = []

    for i, sym in enumerate(syms, 1):
        if already_done(sym, args.force):
            skipped += 1
            continue
        try:
            df = client.get_history(sym, start=args.start, end=end,
                                    adjusted=not args.raw)
        except EODHDAPIError as e:
            failed += 1
            failures.append((sym, str(e)[:140]))
            print(f"  [{i:3d}/{len(syms)}] {sym:8s}  ERROR: {e}")
            continue
        if df.empty:
            failed += 1
            failures.append((sym, "empty response"))
            print(f"  [{i:3d}/{len(syms)}] {sym:8s}  EMPTY")
            continue
        save_dataframe(df, OUT_DIR / f"{sym}_day.csv")
        ok += 1
        print(f"  [{i:3d}/{len(syms)}] {sym:8s}  rows={len(df):5d}  "
              f"{df['date'].iloc[0]}..{df['date'].iloc[-1]}")

    elapsed = time.time() - started
    print(f"\n[done] ok={ok}  skipped={skipped}  failed={failed}  "
          f"elapsed={elapsed:.1f}s")
    if failures:
        print("failures:")
        for s, msg in failures:
            print(f"  {s:8s}  {msg}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
