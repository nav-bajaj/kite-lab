"""GDF full backfill: 765 NSE symbols, 2009-2023.

Phase B+C of tasks/gdf_full_backfill/PLAN.md. Fetches deepest-available
daily OHLCV history from Global Data Feeds for the Nifty 500 + Nifty
Microcap 250 + pre-2026-drop NSE 500 union, capping at 2023-12-31 so
the GDF mid-2024 coverage gap doesn't contaminate the output.

Probe findings (from scripts/_gdf_limits_probe.py + tasks/gdf_full_backfill/
PROBE_RESULTS.md, 2026-05-18):

  - GDF earliest data: ~2009-03-05 for liquid large caps; later for
    listings after that
  - No per-request bar cap — fetch full date range in one call
  - No 100-symbol per-session cap — single websocket session OK
  - GDF coverage 2024+ is patchy (~64% Q2-Q4 2024); use Kite for 2024+
  - Each symbol fetches in ~1-2s; 765 symbols ≈ 15-25 min total

Behavior:

  - Reads universe from data/static/gdf_backfill/gdf_backfill_universe.csv
  - For each symbol, single GetHistory(2009-01-01, 2023-12-31)
  - Writes <output>/<symbol>_day.csv with columns
      date, open, high, low, close, volume, oi
    (matching the existing nse500_data_historical schema, plus oi
    which GDF returns and the old fetch dropped)
  - Resumable: skips symbols whose output CSV already exists and is
    non-empty. Restart-safe.
  - Logs to <output>/.fetch.log with timestamps + counts

Usage:

  python scripts/gdf_full_backfill.py
  python scripts/gdf_full_backfill.py --output /custom/path
  python scripts/gdf_full_backfill.py --universe /custom/universe.csv
  python scripts/gdf_full_backfill.py --start 2009-01-01 --end 2023-12-31
  python scripts/gdf_full_backfill.py --dry-run    # list symbols, no fetch
"""
from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from data_pipeline.gdf_client import GDFClient, GDFAuthError, GDFAPIError  # noqa: E402


DEFAULT_UNIVERSE = ROOT / "data/static/gdf_backfill/gdf_backfill_universe.csv"
DEFAULT_OUTPUT = Path.home() / "Documents/stock_data/nse500_data_gdf_full"
DEFAULT_START = "2009-01-01"
DEFAULT_END = "2023-12-31"

# CSV column ordering (matches existing nse500_data_historical/*_day.csv).
OUTPUT_COLUMNS = ["date", "open", "high", "low", "close", "volume", "oi"]


def load_universe(path: Path) -> list[str]:
    df = pd.read_csv(path)
    if "Symbol" not in df.columns:
        raise SystemExit(f"{path} missing 'Symbol' column")
    return df["Symbol"].astype(str).str.strip().tolist()


def existing_outputs(output_dir: Path) -> set[str]:
    """Symbols that already have a non-empty CSV in output_dir."""
    if not output_dir.exists():
        return set()
    out: set[str] = set()
    for p in output_dir.glob("*_day.csv"):
        try:
            if p.stat().st_size > 100:  # > just-header bytes
                out.add(p.stem.replace("_day", ""))
        except OSError:
            continue
    return out


def log(log_file, *args) -> None:
    line = " ".join(str(a) for a in args)
    print(line)
    log_file.write(line + "\n")
    log_file.flush()


async def fetch_one(client: GDFClient, symbol: str, start: str, end: str) -> pd.DataFrame:
    """One GetHistory call. Caller handles retries + persistence."""
    return await client.get_history(symbol, start, end, tag="full_backfill")


async def run(universe_path: Path, output_dir: Path,
              start: str, end: str, dry_run: bool) -> int:
    universe = load_universe(universe_path)
    already_done = existing_outputs(output_dir)
    to_fetch = [s for s in universe if s not in already_done]

    print(f"Universe:      {universe_path.relative_to(ROOT) if universe_path.is_absolute() and universe_path.is_relative_to(ROOT) else universe_path}")
    print(f"Output dir:    {output_dir}")
    print(f"Date range:    {start} → {end}")
    print(f"Total symbols: {len(universe)}")
    print(f"Already done:  {len(already_done)}")
    print(f"To fetch:      {len(to_fetch)}")
    print()

    if dry_run:
        print("[dry-run] No fetch performed. Sample of symbols to fetch:")
        for s in to_fetch[:20]:
            print(f"  - {s}")
        if len(to_fetch) > 20:
            print(f"  ... and {len(to_fetch) - 20} more")
        return 0

    if not to_fetch:
        print("Nothing to fetch — all symbols already have output CSVs.")
        return 0

    output_dir.mkdir(parents=True, exist_ok=True)
    log_path = output_dir / ".fetch.log"
    log_file = log_path.open("a")
    started = datetime.utcnow()
    log(log_file, f"=== run started {started.isoformat()}Z ===")
    log(log_file, f"universe={universe_path.name} output={output_dir} range={start}..{end}")
    log(log_file, f"to_fetch={len(to_fetch)} of {len(universe)} total")

    ok = empty = failed = 0
    failures: dict[str, str] = {}

    try:
        async with GDFClient() as client:
            for i, symbol in enumerate(to_fetch, 1):
                t0 = datetime.utcnow()
                try:
                    df = await fetch_one(client, symbol, start, end)
                except (GDFAuthError, GDFAPIError) as exc:
                    failed += 1
                    failures[symbol] = f"{type(exc).__name__}: {exc!s}"
                    log(log_file, f"[{i:4d}/{len(to_fetch):4d}] {symbol:14s} FAIL: {exc!s}")
                    continue
                except Exception as exc:
                    failed += 1
                    failures[symbol] = f"{type(exc).__name__}: {exc!s}"
                    log(log_file, f"[{i:4d}/{len(to_fetch):4d}] {symbol:14s} ERROR: {exc!s}")
                    continue

                if df.empty:
                    empty += 1
                    log(log_file, f"[{i:4d}/{len(to_fetch):4d}] {symbol:14s} EMPTY (no GDF data in range)")
                    # Still write an empty marker so we don't re-fetch.
                    out_path = output_dir / f"{symbol}_day.csv"
                    pd.DataFrame(columns=OUTPUT_COLUMNS).to_csv(out_path, index=False)
                    continue

                # Order + persist
                cols = [c for c in OUTPUT_COLUMNS if c in df.columns]
                df = df[cols].sort_values("date").reset_index(drop=True)
                out_path = output_dir / f"{symbol}_day.csv"
                df.to_csv(out_path, index=False)

                ok += 1
                dt = (datetime.utcnow() - t0).total_seconds()
                first = df["date"].iloc[0].date()
                last = df["date"].iloc[-1].date()
                log(log_file, f"[{i:4d}/{len(to_fetch):4d}] {symbol:14s} rows={len(df):5d} "
                              f"first={first} last={last} ({dt:.2f}s)")
    finally:
        finished = datetime.utcnow()
        elapsed = (finished - started).total_seconds()
        log(log_file, f"=== run finished {finished.isoformat()}Z ===")
        log(log_file, f"ok={ok}  empty={empty}  failed={failed}  total={len(to_fetch)}  elapsed={elapsed:.1f}s")
        if failures:
            log(log_file, "FAILURES:")
            for sym, msg in failures.items():
                log(log_file, f"  {sym}: {msg}")
        log_file.close()

    print()
    print("=" * 60)
    print(f"Backfill complete in {elapsed:.1f}s")
    print(f"  ok      = {ok:4d}")
    print(f"  empty   = {empty:4d}  (no GDF data in range; marker CSV written so re-runs skip)")
    print(f"  failed  = {failed:4d}")
    print(f"  log     = {log_path}")
    print("=" * 60)

    return 0 if failed == 0 else 2


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--universe", type=Path, default=DEFAULT_UNIVERSE,
                    help=f"Universe CSV with a Symbol column (default: {DEFAULT_UNIVERSE.relative_to(ROOT)})")
    ap.add_argument("--output", type=Path, default=DEFAULT_OUTPUT,
                    help=f"Output dir for *_day.csv files (default: {DEFAULT_OUTPUT})")
    ap.add_argument("--start", default=DEFAULT_START)
    ap.add_argument("--end", default=DEFAULT_END)
    ap.add_argument("--dry-run", action="store_true",
                    help="List what would be fetched without making requests")
    args = ap.parse_args()

    return asyncio.run(run(args.universe, args.output, args.start, args.end,
                            args.dry_run))


if __name__ == "__main__":
    sys.exit(main())
