"""One-shot probe: does GDF know about DELISTED scrips, and serve their bars?

The Kite instruments dump only carries live instruments, so companies that
left the Nifty 500 and were later delisted or merged cannot be resolved or
backfilled from it. GDF is the other feed this repo already uses. This asks
it two questions for a handful of known-delisted ex-members:

  1. does its instrument master still list the symbol?  (GetInstrumentsOnSearch)
  2. will it return daily bars for the period the company was live? (GetHistory)

The GDF API key is single-session - an overlapping connection locks the other
one out - so this opens exactly one connection, asks everything, and closes.
"""
from __future__ import annotations

import asyncio, json, os, sys
sys.path.insert(0, "/Users/navdeep/kite-lab")
from dotenv import load_dotenv
load_dotenv("/Users/navdeep/kite-lab/.env")
from data_pipeline.gdf_client import GDFClient

SEARCHES = ["ITD CEM", "ALLAHABAD", "TATA COFFEE", "DEWAN", "MAGMA", "SESA"]
HISTORY = [("ITDCEM", "2018-01-01", "2019-01-01"),
           ("ALBK", "2018-01-01", "2019-01-01"),
           ("TATACOFFEE", "2020-01-01", "2021-01-01")]


async def main() -> None:
    async with GDFClient(timeout=25) as c:
        print("authenticated\n=== instrument search ===")
        for term in SEARCHES:
            req = {"MessageType": "GetInstrumentsOnSearch", "Exchange": "NSE",
                   "Search": term, "InstrumentType": "", "Product": "",
                   "OptionType": "", "UserTag": "probe"}
            try:
                await c._ws.send(json.dumps(req))
                res = await c._await_result()
                names = [r.get("InstrumentIdentifier") or r.get("Name") or str(r)
                         for r in res][:6]
                print(f"  {term:14s} -> {len(res):3d} hits {names}")
            except Exception as e:
                print(f"  {term:14s} -> ERROR {type(e).__name__}: {e}")

        print("\n=== history for delisted symbols ===")
        for sym, a, b in HISTORY:
            try:
                df = await c.get_history(sym, a, b)
                print(f"  {sym:12s} {a}..{b}: {len(df)} bars"
                      + (f"  {df['date'].min().date()}..{df['date'].max().date()}"
                         if len(df) else ""))
            except Exception as e:
                print(f"  {sym:12s} -> ERROR {type(e).__name__}: {e}")


asyncio.run(main())
