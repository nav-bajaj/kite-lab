"""Phase 1 — month-end trend features, computed once.

The classifier's thresholds are first-draft and have to be swept. Re-scanning
2,914 price files per configuration would make that unaffordable, so the raw
ingredients of every rule are stored once per name per month-end and every
candidate threshold set is then applied in memory.

Nothing here decides a state. It only records what the state would be decided
from, plus the forward returns that judge it.
"""
from __future__ import annotations

import os
import numpy as np
import pandas as pd

PANELS = "data/master/prices/adjusted_pr"
HORIZONS = (21, 63, 126, 252)


def features(sym: str, allow: set) -> pd.DataFrame | None:
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
    for n in (21, 42, 63):
        out[f"s200_{n}"] = out["s200"].shift(n)
    out["hi52"] = h.rolling(252).max()
    out["lo52"] = l.rolling(252).min()

    arr = c.to_numpy()
    for hz in HORIZONS:
        fwd = np.full(len(arr), np.nan)
        fwd[:-hz] = arr[hz:] / arr[:-hz] - 1
        out[f"f{hz}"] = fwd

    me = out.index.to_series().groupby([out.index.year, out.index.month]).last()
    out = out.loc[out.index.isin(me)]
    out = out[out.index.isin(allow)]
    out = out.dropna(subset=["s200", "s150", "s200_63", "hi52", "lo52"])
    if not len(out):
        return None
    out.insert(0, "symbol", sym)
    return out.reset_index().rename(columns={"index": "date"})


def classify(d: pd.DataFrame, ext: float = 0.20, slope: int = 21,
             above_low: float = 0.30, near_high: float = 0.25) -> pd.Series:
    """Apply one threshold set to the feature table."""
    c, s50, s150, s200 = d.close, d.s50, d.s150, d.s200
    up = s200 > d[f"s200_{slope}"]
    stage2 = ((c > s50) & (s50 > s150) & (s150 > s200) & up
              & (c >= (1 + above_low) * d.lo52) & (c >= (1 - near_high) * d.hi52))
    st = pd.Series("BASING", index=d.index, dtype=object)
    st[(c < s200) & ~up] = "DOWNTREND"
    st[(c < s200) & up] = "WEAKENING"
    st[(c > s200) & (s50 > s200) & ~stage2] = "ADVANCING"
    st[stage2] = "LEADING"
    st[stage2 & (c > s50 * (1 + ext))] = "EXTENDED"
    return st
