"""Compare raw 6M-return ranking (TradingView-style) vs L6 v2 mom/vol ranking.

Uses local nse500_data (through 2026-05-12) and the production universe file.
"""
import pandas as pd
from pathlib import Path

DATA = Path("/Users/navdeep/Documents/stock_data/nse500_data")
UNIVERSE = Path("/Users/navdeep/kite-lab/data/static/nse500_universe.csv")

symbols = pd.read_csv(UNIVERSE)["Symbol"].tolist()

closes = {}
for sym in symbols:
    f = DATA / f"{sym}_day.csv"
    if not f.exists():
        continue
    df = pd.read_csv(f, parse_dates=[0], index_col=0)
    closes[sym] = df.iloc[:, 3]  # close column

panel = pd.DataFrame(closes).sort_index()
last = panel.index[-1]
print(f"As-of date: {last.date()}  |  symbols with data: {panel.shape[1]}")

LOOKBACK = 126
mom = panel.iloc[-1] / panel.iloc[-1 - LOOKBACK] - 1.0
daily_ret = panel.pct_change()
vol = daily_ret.tail(LOOKBACK).std() * (252 ** 0.5)  # annualized for readability

valid = mom.dropna().index.intersection(vol.dropna().index)
mom, vol = mom[valid], vol[valid]
score = mom / vol.clip(lower=0.05)

raw_top = mom.sort_values(ascending=False)
adj_top = score.sort_values(ascending=False)

raw24 = list(raw_top.head(24).index)
adj24 = list(adj_top.head(24).index)

print(f"\nOverlap raw-6M top-24 vs mom/vol top-24: {len(set(raw24) & set(adj24))}/24")

print("\nRaw 6M top-24 (TradingView-style)          vs   mom/vol top-24 (L6 v2 score)")
for i in range(24):
    r, a = raw24[i], adj24[i]
    print(f"{i+1:>2}. {r:<12} {raw_top[r]*100:>7.1f}%  vol {vol[r]*100:>5.1f}%   |  "
          f"{a:<12} score {adj_top[a]:>5.2f}  (6M {mom[a]*100:>6.1f}%, vol {vol[a]*100:>5.1f}%)")

print("\nIn raw top-24 but demoted by vol-adjustment:")
for s in raw24:
    if s not in adj24:
        adj_rank = list(adj_top.index).index(s) + 1
        print(f"  {s:<12} raw #{raw24.index(s)+1:>2} -> adj #{adj_rank:>3}  (6M {mom[s]*100:>6.1f}%, vol {vol[s]*100:>5.1f}%)")

print("\nPromoted into adj top-24 despite lower raw 6M:")
for s in adj24:
    if s not in raw24:
        raw_rank = list(raw_top.index).index(s) + 1
        print(f"  {s:<12} raw #{raw_rank:>3} -> adj #{adj24.index(s)+1:>2}  (6M {mom[s]*100:>6.1f}%, vol {vol[s]*100:>5.1f}%)")
