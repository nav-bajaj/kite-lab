"""One-time GDF backfill of pre-Kite historical data for NSE 500.

Kite data starts at 2020-01-01 for the bulk of NSE 500. GDF reaches back
to 2009-03-05. We fetch 2009-03-05 -> 2019-12-31 in 2-year chunks per
stock and save in Kite-compatible CSV format to nse500_data_historical/.

Resumable: skips symbols whose target CSV already exists with rows.
Run with venv active:
    python scripts/backfill_gdf_history.py
    python scripts/backfill_gdf_history.py --symbols RELIANCE INFY
    python scripts/backfill_gdf_history.py --limit 50  # first 50 only
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import sys
import time
from pathlib import Path
from typing import List

import pandas as pd
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

from data_pipeline.gdf_client import GDFClient, GDFAPIError  # noqa


UNIVERSE_CSV = ROOT / "data" / "static" / "nse500_universe.csv"
OUT_DIR = ROOT / "nse500_data_historical"

CHUNKS = [
    ("2009-03-05", "2010-12-31"),
    ("2011-01-01", "2012-12-31"),
    ("2013-01-01", "2014-12-31"),
    ("2015-01-01", "2016-12-31"),
    ("2017-01-01", "2018-12-31"),
    ("2019-01-01", "2019-12-31"),
]


def load_symbols() -> List[str]:
    syms = []
    with open(UNIVERSE_CSV) as f:
        r = csv.DictReader(f)
        for row in r:
            s = (row.get("Symbol") or "").strip()
            if s:
                syms.append(s)
    return syms


def already_done(sym: str) -> bool:
    p = OUT_DIR / f"{sym}_day.csv"
    if not p.exists():
        return False
    try:
        return p.stat().st_size > 100
    except OSError:
        return False


async def fetch_symbol(client: GDFClient, sym: str) -> pd.DataFrame:
    frames = []
    for start, end in CHUNKS:
        try:
            df = await client.get_history(sym, start, end, tag="backfill")
        except GDFAPIError as e:
            msg = str(e)
            if "no data" in msg.lower() or "not found" in msg.lower():
                continue
            raise
        if not df.empty:
            frames.append(df)
        await asyncio.sleep(0.05)
    if not frames:
        return pd.DataFrame()
    out = pd.concat(frames, ignore_index=True)
    out = out.drop_duplicates(subset=["date"]).sort_values("date").reset_index(drop=True)
    return out


def write_kite_format(df: pd.DataFrame, path: Path) -> None:
    # Match nse500_data/ CSV: date,open,high,low,close,volume
    cols = ["date", "open", "high", "low", "close", "volume"]
    df = df[[c for c in cols if c in df.columns]].copy()
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
    df.to_csv(path, index=False)


async def run(symbols: List[str], force: bool, max_retries: int = 3) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    n_total = len(symbols)
    n_done = sum(1 for s in symbols if already_done(s))
    n_skip = 0 if force else n_done
    print(f"[start] {n_total} symbols, {n_skip} already on disk -> "
          f"{n_total - n_skip} to fetch")

    todo = [s for s in symbols if force or not already_done(s)]
    pending = list(todo)
    attempt = 0
    t0 = time.time()
    fetched = 0
    failed = []

    while pending and attempt < max_retries:
        attempt += 1
        round_failed = []
        try:
            async with GDFClient() as client:
                for i, sym in enumerate(pending, 1):
                    try:
                        df = await fetch_symbol(client, sym)
                    except Exception as e:
                        round_failed.append((sym, str(e)[:120]))
                        print(f"  [{i:3d}/{len(pending)}] {sym:14s} ERROR: {str(e)[:100]}")
                        # If session-level error, abort this round to reconnect
                        if "Access Denied" in str(e) or "1011" in str(e) or "closed" in str(e).lower():
                            print("  [session error — reconnecting next attempt]")
                            pending = [s for s in pending if s not in {x[0] for x in round_failed[:-1]}]
                            pending = pending[i:]  # symbols still untried
                            break
                        continue

                    if df.empty:
                        round_failed.append((sym, "empty"))
                        print(f"  [{i:3d}/{len(pending)}] {sym:14s} EMPTY")
                        continue

                    write_kite_format(df, OUT_DIR / f"{sym}_day.csv")
                    fetched += 1
                    elapsed = time.time() - t0
                    rate = fetched / elapsed if elapsed > 0 else 0
                    print(f"  [{i:3d}/{len(pending)}] {sym:14s} rows={len(df):4d}  "
                          f"first={df['date'].min().date()}  last={df['date'].max().date()}  "
                          f"({rate:.1f}/s)")
                else:
                    pending = []
        except Exception as e:
            print(f"  [connection error: {e}] — retrying")

        # On a clean run-through, pending was set to [] above. If we broke out
        # due to a session error, pending has the remaining work.
        new_failed = [s for s, _ in round_failed if not already_done(s)]
        if not pending:
            pending = new_failed
        else:
            # remove successes from pending
            pending = [s for s in pending if not already_done(s)]
        if attempt < max_retries and pending:
            print(f"  [round {attempt} done; {len(pending)} still pending; "
                  f"sleeping 5s before reconnect]")
            await asyncio.sleep(5)

    failed = [s for s in todo if not already_done(s)]
    elapsed = time.time() - t0
    print(f"\n[done] fetched={fetched}  failed={len(failed)}  "
          f"elapsed={elapsed/60:.1f}min")
    if failed:
        print(f"  failed: {failed[:30]}{'...' if len(failed)>30 else ''}")
        with open(ROOT / "gdf_test" / "backfill_failures.txt", "w") as f:
            f.write("\n".join(failed))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", nargs="*", help="Specific symbols (default: full universe)")
    ap.add_argument("--limit", type=int, default=None, help="Cap number of symbols")
    ap.add_argument("--force", action="store_true", help="Re-fetch even if file exists")
    args = ap.parse_args()

    syms = args.symbols or load_symbols()
    if args.limit:
        syms = syms[: args.limit]

    asyncio.run(run(syms, args.force))


if __name__ == "__main__":
    main()
