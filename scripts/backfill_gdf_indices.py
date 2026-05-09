"""One-time GDF backfill of pre-Kite index data.

Fetches every NSE_IDX symbol from GDF for 2009-03-05 -> 2019-12-31 and
saves in Kite-compatible CSV format. Stitch-target is indices_data/
(which has 2020-onwards data from Kite).

Symbol source: /Users/navdeep/Documents/NSE_CM_Symbol_List_06-05-2026 2/NSE_INDEX Symbols.txt
(comma-separated list of "<NAME>.NSE_IDX" entries)

Resumable: skips symbols whose target file already exists with rows.

Usage:
    python scripts/backfill_gdf_indices.py
    python scripts/backfill_gdf_indices.py --symbols "NIFTY 100" "NIFTY 50"
    python scripts/backfill_gdf_indices.py --limit 5
"""
from __future__ import annotations

import argparse
import asyncio
import csv
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


SYMBOL_FILE = Path("/Users/navdeep/Documents/NSE_CM_Symbol_List_06-05-2026 2/NSE_INDEX Symbols.txt")
OUT_DIR = ROOT / "indices_data_historical"

# Same chunking as the equity backfill — keeps within GDF per-request bar cap
CHUNKS = [
    ("2009-03-05", "2010-12-31"),
    ("2011-01-01", "2012-12-31"),
    ("2013-01-01", "2014-12-31"),
    ("2015-01-01", "2016-12-31"),
    ("2017-01-01", "2018-12-31"),
    ("2019-01-01", "2019-12-31"),
]

# Test symbols to skip
SKIP_SYMBOLS = {"INDEX1 NSETEST", "INDEX2 NSETEST"}


def safe_filename(symbol: str) -> str:
    """Convert 'NIFTY 100' -> 'NIFTY_100', 'INDIA VIX' -> 'INDIA_VIX', etc.

    Mirrors how indices_data/ already names files (NIFTY_100.csv, etc).
    """
    # Replace spaces, &, /, etc with underscore
    s = re.sub(r"[\s/&\\]+", "_", symbol)
    # Strip any other punctuation that could break paths
    s = re.sub(r"[^A-Za-z0-9_\-.]", "", s)
    return s


def load_symbols() -> List[str]:
    raw = SYMBOL_FILE.read_text().strip()
    syms = []
    for token in raw.split(","):
        token = token.strip()
        if not token:
            continue
        # Strip ".NSE_IDX" suffix
        if token.upper().endswith(".NSE_IDX"):
            token = token[: -len(".NSE_IDX")]
        token = token.strip()
        if not token or token in SKIP_SYMBOLS:
            continue
        syms.append(token)
    # de-dup preserving order
    seen = set()
    out = []
    for s in syms:
        if s not in seen:
            seen.add(s)
            out.append(s)
    return out


def already_done(sym: str) -> bool:
    p = OUT_DIR / f"{safe_filename(sym)}.csv"
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
            df = await client.get_history(sym, start, end,
                                          exchange="NSE_IDX",
                                          tag="indices_backfill")
        except GDFAPIError as e:
            msg = str(e).lower()
            if "no data" in msg or "not found" in msg:
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


def write_csv(df: pd.DataFrame, path: Path) -> None:
    """Write in indices_data/ schema (date,open,high,low,close,volume?)."""
    cols = [c for c in ["date", "open", "high", "low", "close", "volume"]
            if c in df.columns]
    df = df[cols].copy()
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
    df.to_csv(path, index=False)


async def run(symbols: List[str], force: bool, max_retries: int = 3) -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    n_total = len(symbols)
    n_done = sum(1 for s in symbols if already_done(s))
    n_skip = 0 if force else n_done
    print(f"[start] {n_total} indices, {n_skip} on disk -> {n_total - n_skip} to fetch")

    todo = [s for s in symbols if force or not already_done(s)]
    pending = list(todo)
    empties: set = set()  # symbols GDF returns no data for — don't retry
    errors_only_pending: list = []
    attempt = 0
    t0 = time.time()
    fetched = 0

    while pending and attempt < max_retries:
        attempt += 1
        errors_only_pending = []
        try:
            async with GDFClient() as client:
                for i, sym in enumerate(pending, 1):
                    try:
                        df = await fetch_symbol(client, sym)
                    except Exception as e:
                        msg = str(e)[:120]
                        errors_only_pending.append(sym)
                        print(f"  [{i:3d}/{len(pending)}] {sym:32s} ERROR: {msg[:80]}")
                        if "Access Denied" in str(e) or "1011" in str(e) or "closed" in str(e).lower():
                            print("  [session error — reconnecting]")
                            pending = pending[i:]
                            break
                        continue

                    if df.empty:
                        empties.add(sym)
                        print(f"  [{i:3d}/{len(pending)}] {sym:32s} EMPTY (no pre-2020 history)")
                        continue

                    write_csv(df, OUT_DIR / f"{safe_filename(sym)}.csv")
                    fetched += 1
                    elapsed = time.time() - t0
                    rate = fetched / elapsed if elapsed > 0 else 0
                    print(f"  [{i:3d}/{len(pending)}] {sym:32s} rows={len(df):4d}  "
                          f"first={df['date'].min().date()}  last={df['date'].max().date()}  "
                          f"({rate:.1f}/s)")
                else:
                    pending = []
        except Exception as e:
            print(f"  [conn error: {e}] retrying")

        # Only retry actual errors — not empties
        if not pending:
            pending = errors_only_pending
        else:
            pending = [s for s in pending if not already_done(s) and s not in empties]
        if attempt < max_retries and pending:
            print(f"  [round {attempt} done; {len(pending)} errors pending; sleeping 5s]")
            await asyncio.sleep(5)

    failed_errors = [s for s in todo if not already_done(s) and s not in empties]
    elapsed = time.time() - t0
    print(f"\n[done] fetched={fetched}  empty(no-history)={len(empties)}  "
          f"failed(errors)={len(failed_errors)}  elapsed={elapsed/60:.1f}min")
    if empties:
        print(f"  empty (no pre-2020 data): {sorted(empties)[:20]}{'...' if len(empties)>20 else ''}")
    if failed_errors:
        print(f"  failed errors: {failed_errors[:20]}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--symbols", nargs="*", help="Specific symbols (default: full list)")
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()

    syms = args.symbols or load_symbols()
    if args.limit:
        syms = syms[: args.limit]
    print(f"[symbols] {len(syms)} indices to process")

    asyncio.run(run(syms, args.force))


if __name__ == "__main__":
    main()
