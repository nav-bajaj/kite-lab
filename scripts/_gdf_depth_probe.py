"""Probe GDF historical depth — how far back does daily data go?

Pulls successive 2-year windows for RELIANCE & INFY from 2008-2026 and reports
row count + first/last date per window. Confirms whether a per-request bar cap exists.
"""
from __future__ import annotations
import asyncio, sys
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")
from data_pipeline.gdf_client import GDFClient  # noqa


WINDOWS = [
    ("2008-01-01", "2009-12-31"),
    ("2010-01-01", "2011-12-31"),
    ("2012-01-01", "2013-12-31"),
    ("2014-01-01", "2015-12-31"),
    ("2016-01-01", "2017-12-31"),
    ("2018-01-01", "2019-12-31"),
    ("2020-01-01", "2021-12-31"),
    ("2022-01-01", "2023-12-31"),
    ("2024-01-01", "2025-12-31"),
]


async def probe(symbol: str):
    print(f"\n=== {symbol} ===")
    async with GDFClient() as c:
        for start, end in WINDOWS:
            try:
                df = await c.get_history(symbol, start, end)
                if df.empty:
                    print(f"  {start} -> {end}   EMPTY")
                else:
                    print(f"  {start} -> {end}   rows={len(df):4d}  "
                          f"first={df['date'].min().date()}  "
                          f"last={df['date'].max().date()}")
            except Exception as e:
                print(f"  {start} -> {end}   ERROR: {e}")


async def main():
    syms = sys.argv[1:] or ["RELIANCE", "INFY"]
    for s in syms:
        await probe(s)
        await asyncio.sleep(2)  # let server release session


asyncio.run(main())
