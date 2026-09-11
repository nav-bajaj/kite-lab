"""Fetch daily prices for reconstructed ex-members that have no price file.

Source is chosen per symbol rather than globally:

  * Kite for anything still listed on NSE. It is the same feed the existing
    panel was built from, so the adjustment convention matches. It serves
    day candles back to 2010.
  * GDF for the rest. Kite's historical API needs an instrument token, which
    only exists for live instruments, so delisted scrips are invisible to it.
    GDF serves them right up to their delisting date, from a 2009 floor.

The two feeds do NOT agree on adjustments: GDF quoted INFY about 2.165% above
the Kite panel across a contiguous 14-day window in mid-2026, the signature of
a dividend applied on one side only. So GDF output is written to a separate
directory and must not be blindly concatenated with Kite-sourced history.

Writes to new directories; nothing under nse500_data/ is touched.
"""
from __future__ import annotations

import argparse, asyncio, csv, os, sys
import pandas as pd

REPO = "/Users/navdeep/kite-lab"
sys.path.insert(0, os.path.join(REPO, "scripts"))
sys.path.insert(0, REPO)

TASK_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGETS = os.path.join(TASK_DIR, "data", "price_backfill_targets.csv")
KITE_DIR = os.path.join(REPO, "nse500_data_backfill")
GDF_DIR = os.path.join(REPO, "nse500_data_backfill_gdf")
START = "2010-01-01"
GDF_START = "2009-01-01"


def load_targets():
    """Split targets by feed.

    Anything Kite can serve goes to Kite, for adjustment consistency with the
    existing panel. Everything else - delisted, or listed only on BSE - goes
    to GDF, still asked for under its NSE symbol, because these are all former
    NSE index constituents and that is the ticker their history is filed under.
    """
    kite, other = [], []
    for r in csv.DictReader(open(TARGETS)):
        (kite if r["fetchable"] == "kite-nse" else other).append(r["symbol"])
    return kite, other


def run_kite(symbols, limit=None):
    from history_utils import init_kite_client, download_batches
    os.makedirs(KITE_DIR, exist_ok=True)
    todo = [s for s in symbols
            if not os.path.exists(os.path.join(KITE_DIR, f"{s}_day.csv"))]
    if limit:
        todo = todo[:limit]
    if not todo:
        print("kite: nothing to do")
        return {}
    print(f"kite: fetching {len(todo)} symbols from {START}")
    cfg = [{"interval": "day", "start": pd.Timestamp(START),
            "end": pd.Timestamp(pd.Timestamp.today().date()),
            "output_dir": KITE_DIR, "suffix": "day",
            "step": pd.Timedelta(days=1)}]
    return download_batches(init_kite_client(), todo, cfg)


async def _gdf(symbols):
    from dotenv import load_dotenv
    load_dotenv(os.path.join(REPO, ".env"))
    from data_pipeline.gdf_client import GDFClient
    os.makedirs(GDF_DIR, exist_ok=True)
    ok, empty, failed = [], [], []
    async with GDFClient(timeout=30) as c:
        for s in symbols:
            dest = os.path.join(GDF_DIR, f"{s}_day.csv")
            if os.path.exists(dest):
                continue
            try:
                df = await c.get_history(s, GDF_START, "2026-09-08")
                if df.empty:
                    empty.append(s)
                    continue
                df.to_csv(dest, index=False)
                ok.append((s, len(df), df["date"].min().date(), df["date"].max().date()))
            except Exception as e:
                failed.append((s, f"{type(e).__name__}: {e}"))
    return ok, empty, failed


def run_gdf(symbols):
    if not symbols:
        return
    print(f"\ngdf: fetching {len(symbols)} symbols from {GDF_START}")
    ok, empty, failed = asyncio.run(_gdf(symbols))
    for s, n, a, b in ok:
        print(f"   {s:12s} {n:5d} bars  {a} .. {b}")
    if empty:
        print(f"   no data: {empty}")
    if failed:
        print(f"   failed : {failed}")


def main() -> None:
    # history_utils resolves access_token.txt relative to the working
    # directory, so run from the repo root regardless of where invoked
    os.chdir(REPO)
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, help="cap the Kite batch, for a trial run")
    ap.add_argument("--source", choices=["kite", "gdf", "both"], default="both")
    a = ap.parse_args()
    kite_syms, other_syms = load_targets()
    print(f"targets: {len(kite_syms)} via Kite, {len(other_syms)} via GDF")
    if a.source in ("kite", "both"):
        fails = run_kite(kite_syms, a.limit)
        if fails:
            print("kite failures:", fails)
    if a.source in ("gdf", "both"):
        run_gdf(other_syms)


if __name__ == "__main__":
    main()
