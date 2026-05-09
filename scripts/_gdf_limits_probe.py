"""Probe GDF limits: per-request bar cap, 2024-25 gap, and 100-symbol cap.

Test 1 — single-year RELIANCE 2024 to see if 2024-25 gap is a request cap or real data gap.
Test 2 — fetch 110 unique symbols in one session and see if the 100-symbol cap kicks in.
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


SYMBOLS_110 = [
    "RELIANCE","INFY","TCS","HDFCBANK","ICICIBANK","SBIN","ITC","AXISBANK","LT","MARUTI",
    "HCLTECH","TECHM","WIPRO","BHARTIARTL","KOTAKBANK","HINDUNILVR","ASIANPAINT","BAJFINANCE",
    "BAJAJFINSV","HDFCLIFE","SBILIFE","ICICIPRULI","NESTLEIND","BRITANNIA","DABUR","TITAN",
    "ULTRACEMCO","GRASIM","JSWSTEEL","TATASTEEL","HINDALCO","COALINDIA","ONGC","NTPC",
    "POWERGRID","ADANIENT","ADANIPORTS","ADANIPOWER","ADANIGREEN","DRREDDY","CIPLA",
    "DIVISLAB","SUNPHARMA","APOLLOHOSP","TATAMOTORS","M&M","EICHERMOT","HEROMOTOCO",
    "BAJAJ-AUTO","TVSMOTOR","INDUSINDBK","FEDERALBNK","BANKBARODA","CANBK","PNB","BOB",
    "IOC","BPCL","HPCL","GAIL","VEDL","HINDZINC","NMDC","SAIL","JINDALSTEL","TATACONSUM",
    "MARICO","COLPAL","GODREJCP","MCDOWELL-N","UBL","HAVELLS","VOLTAS","CROMPTON","LICHSGFIN",
    "BAJAJHLDNG","SHREECEM","ACC","AMBUJACEM","PIDILITIND","BERGEPAINT","DLF","GODREJPROP",
    "OBEROIRLTY","PRESTIGE","TRENT","ZOMATO","NYKAA","DMART","JIOFIN","LTIM","MPHASIS",
    "PERSISTENT","COFORGE","TATAELXSI","NAUKRI","MOTHERSON","BOSCHLTD","ASHOKLEY","BHEL",
    "BEL","HAL","INDHOTEL","CHOLAFIN","SHRIRAMFIN","RECLTD","PFC","IRFC","IDFCFIRSTB",
    "BANDHANBNK","CONCOR","CESC","TORNTPOWER",
]


async def test_request_cap():
    """Probe whether 2024-25 gap is real data or per-request cap."""
    print("\n=== TEST 1: per-request bar cap on RELIANCE 2024 (1 year) ===")
    async with GDFClient() as c:
        df = await c.get_history("RELIANCE", "2024-01-01", "2024-12-31")
        print(f"  RELIANCE 2024-01-01 to 2024-12-31 -> rows={len(df)}")
        if not df.empty:
            print(f"  first={df['date'].min().date()}  last={df['date'].max().date()}")
        # Now try just Jan-Mar 2024
        df2 = await c.get_history("RELIANCE", "2024-01-01", "2024-03-31")
        print(f"  RELIANCE 2024-01-01 to 2024-03-31 -> rows={len(df2)}")
        # Now Jul-Dec 2024
        df3 = await c.get_history("RELIANCE", "2024-07-01", "2024-12-31")
        print(f"  RELIANCE 2024-07-01 to 2024-12-31 -> rows={len(df3)}")
        # And Apr-Jun 2024 to see where data exists
        df4 = await c.get_history("RELIANCE", "2024-04-01", "2024-06-30")
        print(f"  RELIANCE 2024-04-01 to 2024-06-30 -> rows={len(df4)}")


async def test_symbol_cap():
    """Try 110 unique symbols in one session — is 100-symbol cap a hard wall?"""
    print(f"\n=== TEST 2: fetch 110 unique symbols in one session ===")
    ok, fail = 0, 0
    fail_msgs = {}
    async with GDFClient() as c:
        for i, sym in enumerate(SYMBOLS_110):
            try:
                df = await c.get_history(sym, "2026-05-01", "2026-05-09")
                ok += 1
                if i in (0, 49, 99, 100, 101, 105, 109):
                    print(f"  #{i+1:3d} {sym:14s} -> rows={len(df)}  OK")
            except Exception as e:
                fail += 1
                msg = str(e)[:80]
                fail_msgs.setdefault(msg, []).append(sym)
                print(f"  #{i+1:3d} {sym:14s} -> ERROR: {msg}")
                if fail >= 5:
                    print("  [stopping after 5 failures]")
                    break
    print(f"  total ok={ok} fail={fail}")
    for msg, syms in fail_msgs.items():
        print(f"    error \"{msg}\" hit on: {syms[:3]}{'...' if len(syms)>3 else ''}")


async def main():
    await test_request_cap()
    await asyncio.sleep(3)
    await test_symbol_cap()


asyncio.run(main())
