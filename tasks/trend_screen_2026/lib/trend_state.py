"""Trend-state classification, and the only question that matters about it.

The proposed product tells a subscriber which stocks are trending and which to
avoid. That is a forward-return claim, so it is tested before it is designed
(CLAUDE.md, TDD policy for forward-return claims): classify every name on
every month-end, then measure what each state actually did over the following
1, 3, 6 and 12 months against the universe's own average over the same window.

A state that does not separate forward returns is a label, not a product.

The taxonomy is ordered, from strongest to weakest, and every stock lands in
exactly one bucket:

  LEADING     full Stage-2 template: close > 50 > 150 > 200, 200 rising,
              >=30% off the 52w low and within 25% of the 52w high
  ADVANCING   above a rising 200, 50 above 200, but not the full template
  EXTENDED    Stage-2 structure but stretched far above the 50 — the state a
              subscriber most wants distinguished from LEADING, because the
              chart looks its best exactly when the entry is worst
  BASING      above the 200 but the 50/150 order has broken; consolidating
  WEAKENING   below the 200 with the 200 still rising — a trend rolling over
  DOWNTREND   below a falling 200
"""
from __future__ import annotations

import numpy as np
import pandas as pd

EXTENDED_VS_50 = 0.20       # >20% above the 50-day is "extended"


def classify(df: pd.DataFrame) -> pd.Series:
    c, h, l = df.close, df.high, df.low
    s50, s150, s200 = (c.rolling(n).mean() for n in (50, 150, 200))
    s200_up = s200 > s200.shift(21)
    hi52, lo52 = h.rolling(252).max(), l.rolling(252).min()

    stage2 = (c > s50) & (s50 > s150) & (s150 > s200) & s200_up \
        & (c >= 1.30 * lo52) & (c >= 0.75 * hi52)
    ext = c > s50 * (1 + EXTENDED_VS_50)

    st = pd.Series("BASING", index=df.index, dtype=object)
    st[(c < s200) & ~s200_up] = "DOWNTREND"
    st[(c < s200) & s200_up] = "WEAKENING"
    st[(c > s200) & (s50 > s200) & ~stage2] = "ADVANCING"
    st[stage2] = "LEADING"
    st[stage2 & ext] = "EXTENDED"
    st[s200.isna() | s150.isna()] = np.nan
    return st


def snapshots(sym: str, df: pd.DataFrame, horizons=(21, 63, 126, 252)) -> pd.DataFrame:
    """Month-end state plus realised forward returns from that close."""
    st = classify(df)
    c = df.close
    me = df.index.to_series().groupby([df.index.year, df.index.month]).last()
    idx = {d: i for i, d in enumerate(df.index)}
    rows = []
    arr = c.to_numpy()
    for d in me:
        i = idx[d]
        s = st.iloc[i]
        if not isinstance(s, str):
            continue
        r = dict(symbol=sym, date=d, state=s, close=float(arr[i]))
        for hz in horizons:
            j = i + hz
            r[f"f{hz}"] = float(arr[j] / arr[i] - 1) if j < len(arr) else np.nan
        rows.append(r)
    return pd.DataFrame(rows)
