"""Work out which dividend convention each feed uses, empirically.

Compares GDF against the existing Kite panel for a spread of dividend payers
and collects every distinct price ratio between them. If the panel adjusted
for ALL dividends there would be small ratios (a 0.5% dividend gives 1.005).
If it adjusts only "above-normal" ones there is a floor - which is what NSE's
own index methodology does: the divisor is left alone unless a dividend
exceeds a threshold percentage of price.
"""
from __future__ import annotations

import asyncio, os, sys
sys.path.insert(0, "/Users/navdeep/kite-lab")
from dotenv import load_dotenv
load_dotenv("/Users/navdeep/kite-lab/.env")
import pandas as pd
from data_pipeline.gdf_client import GDFClient

PANEL = "/Users/navdeep/kite-lab/nse500_data/{}_day.csv"
SYMS = ["INFY", "TCS", "ITC", "COALINDIA", "HINDUNILVR", "NESTLEIND",
        "HEROMOTOCO", "WIPRO", "HCLTECH", "TECHM", "POWERGRID", "NTPC",
        "ONGC", "IOC", "BPCL", "GAIL", "SBIN", "HDFCBANK", "ICICIBANK",
        "BAJAJ-AUTO", "MARUTI", "ULTRACEMCO", "GRASIM", "TATASTEEL",
        "HINDZINC", "REDINGTON", "OFSS", "CASTROLIND", "PFC"]
# VEDL excluded: its 2026 demerger is a separate, known adjustment already
# recorded in data/corporate_actions.json, and it swamps the dividend signal.
START, END = "2024-01-01", "2026-09-08"


async def main() -> None:
    rows = []
    async with GDFClient(timeout=30) as c:
        for s in SYMS:
            path = PANEL.format(s)
            if not os.path.exists(path):
                continue
            try:
                g = await c.get_history(s, START, END)
            except Exception as e:
                print(f"  {s}: {type(e).__name__}: {e}")
                continue
            k = pd.read_csv(path)
            k["date"] = pd.to_datetime(k["date"]).dt.tz_localize(None).dt.normalize()
            m = g.merge(k[["date", "close"]], on="date", suffixes=("_g", "_k"))
            if m.empty:
                continue
            m["ratio"] = m.close_g / m.close_k
            # A back-adjustment is a step that PERSISTS: the ratio sits at one
            # level before the ex-date and another after. A single bad print in
            # either feed also moves the ratio, but it snaps back the next day.
            # Comparing the median of the 5 days either side separates them.
            before = m["ratio"].rolling(5).median().shift(1)
            after = m["ratio"][::-1].rolling(5).median()[::-1].shift(-1)
            for i, r in enumerate(m.itertuples()):
                b, a = before.iloc[i], after.iloc[i]
                if pd.isna(b) or pd.isna(a):
                    continue
                step = a / b - 1
                if abs(step) > 0.002:
                    rows.append((s, r.date.date(), step * 100))

    if not rows:
        print("no adjustment gaps found")
        return
    # the rolling comparison flags the same event on several adjacent days;
    # collapse runs within a symbol into one event at its largest step
    rows.sort(key=lambda x: (x[0], x[1]))
    events, run = [], []
    for r in rows:
        if run and r[0] == run[-1][0] and (r[1] - run[-1][1]).days <= 7:
            run.append(r)
        else:
            if run:
                events.append(max(run, key=lambda x: abs(x[2])))
            run = [r]
    if run:
        events.append(max(run, key=lambda x: abs(x[2])))

    print(f"{'symbol':12s} {'date':12s} {'persistent step':>17s}")
    for s, d, pct in sorted(events, key=lambda x: abs(x[2])):
        print(f"{s:12s} {str(d):12s} {pct:16.3f}%")
    pcts = [abs(p) for _, _, p in events]
    print(f"\nsteps: {len(pcts)}   smallest {min(pcts):.3f}%   largest {max(pcts):.3f}%")
    small = [p for p in pcts if p < 2.0]
    print(f"steps below 2%: {len(small)}  -> " + ("some sub-2% adjustments exist"
          if small else "NONE, consistent with an above-normal-dividend threshold"))


asyncio.run(main())
