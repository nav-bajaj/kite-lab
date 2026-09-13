"""Daily trend features — every session, not just month-ends.

`trend_screen_2026/lib/features.py` samples the last session of each month
because the threshold sweep had to re-read 2,914 price files per candidate
set. The call tape inherited that cadence as an artifact. This module emits
the same ingredients on every session so a trigger can fire the day a name
qualifies.

Long format only: ~2,161 names x ~5,300 sessions never exists as a wide
symbol x date panel, it is streamed per symbol and concatenated once.
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, "tasks/trend_screen_2026/lib")
from features import classify  # noqa: E402

PANELS = "data/master/prices/adjusted_pr"
UNIVERSE = "tasks/breakout_calls_2026/data/pit_universe.parquet"
BREADTH = "tasks/trend_screen_2026/data/breadth.parquet"
BENCH = "data/master/benchmarks/NIFTY_500.csv"

COLS = ["date", "symbol", "close", "s50", "s100", "s150", "s200", "s200_21",
        "hi52", "lo52", "state", "above_low"]


def eligible_universe() -> pd.DataFrame:
    """(date, symbol, adv) pairs that were investable on that date.

    Top 500 by trailing turnover AND past the scaled Rs 10cr floor. Both
    conditions are point-in-time; nothing here knows what a name did next.
    """
    u = pd.read_parquet(UNIVERSE, columns=["date", "symbol", "adv", "eligible"])
    u = u.drop_duplicates(["symbol", "date"])
    u["advrk"] = u.groupby("date")["adv"].rank(ascending=False, method="first")
    u = u[(u["advrk"] <= 500) & u["eligible"]]
    return u[["date", "symbol", "adv"]].reset_index(drop=True)


def daily_features(sym: str, allow: set) -> pd.DataFrame | None:
    """One name's full session history, then cut to the eligible dates.

    The indicators and the state are computed on the UNCUT series: a name that
    drops out of the top 500 for a week has not changed state, and cutting
    first would fabricate a state entry when it returns.
    """
    f = os.path.join(PANELS, f"{sym}.csv")
    if not os.path.exists(f):
        return None
    df = pd.read_csv(f, parse_dates=["date"]).dropna(subset=["close"]).set_index("date")
    df = df[~df.index.duplicated()].sort_index()
    if len(df) < 300:
        return None
    c, h, l = df.close, df.high, df.low
    out = pd.DataFrame(index=df.index)
    out["close"] = c
    out["s50"] = c.rolling(50).mean()
    out["s100"] = c.rolling(100).mean()
    out["s150"] = c.rolling(150).mean()
    out["s200"] = c.rolling(200).mean()
    out["s200_21"] = out["s200"].shift(21)
    out["hi52"] = h.rolling(252).max()
    out["lo52"] = l.rolling(252).min()
    out = out.dropna(subset=["s200", "s150", "s200_21", "hi52", "lo52"])
    if not len(out):
        return None
    out["state"] = classify(out)
    out["above_low"] = out["close"] / out["lo52"] - 1.0
    # prev_state comes from the uncut series; the cut happens after.
    out["prev_state"] = out["state"].shift(1)
    out = out[out.index.isin(allow)]
    if not len(out):
        return None
    out.insert(0, "symbol", sym)
    return out.reset_index().rename(columns={"index": "date"})


def regime_gate(enter: float = 0.60, exit_: float = 0.40) -> pd.Series:
    """Hysteresis on % above the 200-day. On at >=60, off below 40, hold in
    between. The raw direction switch flips ~26x a year; this one does not."""
    b = pd.read_parquet(BREADTH)
    p = b["pct_above_200"].dropna().sort_index()
    on = False
    vals = []
    for v in p.to_numpy():
        if not on and v >= enter:
            on = True
        elif on and v < exit_:
            on = False
        vals.append(on)
    return pd.Series(vals, index=p.index, name="gate_on")


def benchmark() -> pd.Series:
    b = pd.read_csv(BENCH, parse_dates=["date"]).set_index("date")["close"]
    return b[~b.index.duplicated()].sort_index()
