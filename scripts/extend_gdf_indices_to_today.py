"""Extend each indices_data_historical/ file forward from its last date
through today, using GDF.

For indices that exist in `indices_data_historical/` (from the 2009-2019
backfill) plus also any NSE_IDX symbols not yet on disk, this script
fetches 2020-01-01 -> today and appends/creates so the panel becomes a
single GDF source for all indices.

Resumable: skips a symbol only if its file's last date >= today - 2 days.
"""
from __future__ import annotations

import argparse
import asyncio
import re
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
from scripts.backfill_gdf_indices import (
    SYMBOL_FILE, OUT_DIR, safe_filename, load_symbols, write_csv,
    SKIP_SYMBOLS,
)

# Chunks for the post-2020 extension
TODAY = pd.Timestamp.today().normalize()
CHUNKS_EXT = [
    ("2020-01-01", "2021-12-31"),
    ("2022-01-01", "2023-12-31"),
    ("2024-01-01", "2025-12-31"),
    ("2026-01-01", TODAY.strftime("%Y-%m-%d")),
]


def existing_last_date(stem: str) -> pd.Timestamp:
    p = OUT_DIR / f"{stem}.csv"
    if not p.exists():
        return None
    df = pd.read_csv(p, parse_dates=["date"])
    if df.empty:
        return None
    return df["date"].max()


async def fetch_chunks(client: GDFClient, sym: str, start, end) -> pd.DataFrame:
    """Fetch a single symbol over [start, end] in 2-year chunks."""
    s = pd.Timestamp(start)
    e = pd.Timestamp(end)
    frames = []
    cursor = s
    while cursor <= e:
        # Fetch 2-year chunks
        chunk_end = min(cursor + pd.DateOffset(years=2) - pd.Timedelta(days=1), e)
        try:
            df = await client.get_history(sym, cursor, chunk_end,
                                          exchange="NSE_IDX",
                                          tag="indices_extend")
        except GDFAPIError as e_:
            if "no data" in str(e_).lower() or "not found" in str(e_).lower():
                cursor = chunk_end + pd.Timedelta(days=1)
                continue
            raise
        if not df.empty:
            frames.append(df)
        cursor = chunk_end + pd.Timedelta(days=1)
        await asyncio.sleep(0.05)
    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True).drop_duplicates("date").sort_values("date").reset_index(drop=True)


async def run(symbols: List[str]) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    n_total = len(symbols)
    today_minus_2 = TODAY - pd.Timedelta(days=2)
    print(f"[start] {n_total} indices to extend through {TODAY.date()}")

    fetched = updated = skipped = 0
    empties = []
    failures = []
    t0 = time.time()

    async with GDFClient() as client:
        for i, sym in enumerate(symbols, 1):
            stem = safe_filename(sym)
            last = existing_last_date(stem)
            if last is not None and last >= today_minus_2:
                skipped += 1
                continue

            # Determine fetch start: day after existing last date, or 2020-01-01 if no file
            fetch_start = (last + pd.Timedelta(days=1)).strftime("%Y-%m-%d") if last is not None else "2020-01-01"
            try:
                new_df = await fetch_chunks(client, sym, fetch_start, TODAY.strftime("%Y-%m-%d"))
            except Exception as e:
                msg = str(e)[:120]
                failures.append((sym, msg))
                print(f"  [{i:3d}/{n_total}] {sym:32s} ERROR: {msg[:80]}")
                if "Access Denied" in str(e) or "1011" in str(e):
                    break
                continue

            if new_df.empty:
                empties.append(sym)
                print(f"  [{i:3d}/{n_total}] {sym:32s} no new data")
                continue

            # Merge with existing
            p = OUT_DIR / f"{stem}.csv"
            if p.exists():
                old_df = pd.read_csv(p, parse_dates=["date"])
                old_df["date"] = pd.to_datetime(old_df["date"]).dt.tz_localize(None).dt.normalize()
                new_df["date"] = pd.to_datetime(new_df["date"]).dt.tz_localize(None).dt.normalize()
                combined = pd.concat([old_df, new_df], ignore_index=True)
                combined = combined.drop_duplicates(subset=["date"]).sort_values("date").reset_index(drop=True)
                write_csv(combined, p)
                updated += 1
            else:
                write_csv(new_df, p)
                fetched += 1

            elapsed = time.time() - t0
            rate = (fetched + updated) / elapsed if elapsed > 0 else 0
            print(f"  [{i:3d}/{n_total}] {sym:32s} new_rows={len(new_df):4d}  "
                  f"first={new_df['date'].min().date()}  last={new_df['date'].max().date()}  "
                  f"({rate:.1f}/s)")

    elapsed = time.time() - t0
    print(f"\n[done] new files={fetched}  updated={updated}  skipped={skipped}  "
          f"empty={len(empties)}  errors={len(failures)}  elapsed={elapsed/60:.1f}min")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", nargs="*")
    ap.add_argument("--limit", type=int)
    args = ap.parse_args()

    syms = args.symbols or load_symbols()
    if args.limit:
        syms = syms[: args.limit]
    print(f"[symbols] {len(syms)} indices")
    asyncio.run(run(syms))


if __name__ == "__main__":
    main()
