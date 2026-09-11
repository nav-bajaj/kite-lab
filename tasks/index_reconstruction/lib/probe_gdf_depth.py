"""How far back does GDF go, and does it agree with the data we already hold?

Source choice for the backfill depends on both: Kite cannot serve delisted
scrips at all, but if GDF's history is shallow or disagrees with the existing
panel it cannot be the default for live ones either.
"""
from __future__ import annotations

import asyncio, sys
sys.path.insert(0, "/Users/navdeep/kite-lab")
from dotenv import load_dotenv
load_dotenv("/Users/navdeep/kite-lab/.env")
import pandas as pd
from data_pipeline.gdf_client import GDFClient

DEPTH = ["RELIANCE", "ITDCEM", "ALBK", "TATACOFFEE", "BURGERKING", "PEL"]
COMPARE = ["RELIANCE", "INFY"]
EXISTING = "/Users/navdeep/kite-lab/nse500_data/{}_day.csv"


async def main() -> None:
    async with GDFClient(timeout=30) as c:
        print("=== earliest bar available (asked from 2000) ===")
        for sym in DEPTH:
            try:
                df = await c.get_history(sym, "2000-01-01", "2026-09-08")
                if len(df):
                    print(f"  {sym:12s} {len(df):6d} bars  "
                          f"{df['date'].min().date()} .. {df['date'].max().date()}")
                else:
                    print(f"  {sym:12s} no bars")
            except Exception as e:
                print(f"  {sym:12s} ERROR {type(e).__name__}: {e}")

        print("\n=== agreement with the existing panel (close, last 250 days) ===")
        for sym in COMPARE:
            try:
                g = await c.get_history(sym, "2025-01-01", "2026-09-08")
                k = pd.read_csv(EXISTING.format(sym))
                k["date"] = pd.to_datetime(k["date"]).dt.tz_localize(None).dt.normalize()
                m = g.merge(k[["date", "close"]], on="date", suffixes=("_gdf", "_kite"))
                if m.empty:
                    print(f"  {sym:12s} no overlapping dates")
                    continue
                d = (m["close_gdf"] - m["close_kite"]).abs() / m["close_kite"]
                print(f"  {sym:12s} {len(m):4d} common days  "
                      f"max rel diff {d.max():.6f}  median {d.median():.6f}")
            except Exception as e:
                print(f"  {sym:12s} ERROR {type(e).__name__}: {e}")


asyncio.run(main())
