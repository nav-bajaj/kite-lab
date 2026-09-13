"""Signal A4 — daily share of the PIT universe above its own 50-day.

`breadth.symbol_flags` is reproduced here with a `c > s50` flag added rather
than edited in place (breadth.py is outside this task folder). The recipe is
copied exactly: adjusted_pr panels, dedup + sort, drop names with < 260 bars,
flags NaN until the 200-day exists, inner-join to the point-in-time universe,
days with fewer than 50 names dropped.

Validation: pct_above_200 recomputed the same way must match
`trend_screen_2026/data/breadth.parquet` to ~1e-9.
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd

REPO = "/Users/navdeep/kite-lab"
PANELS = f"{REPO}/data/master/prices/adjusted_pr"
OUT = f"{REPO}/tasks/regime_allocation_2026/data/pct_above_50.parquet"


def flags(sym: str):
    f = os.path.join(PANELS, f"{sym}.csv")
    if not os.path.exists(f):
        return None
    df = pd.read_csv(f, parse_dates=["date"]).dropna(subset=["close"]).set_index("date")
    df = df[~df.index.duplicated()].sort_index()
    if len(df) < 260:
        return None
    c = df.close
    s200, s50 = c.rolling(200).mean(), c.rolling(50).mean()
    out = pd.DataFrame({"above200": (c > s200).astype(float),
                        "above50": (c > s50).astype(float)})
    out[s200.isna()] = np.nan
    return out.assign(symbol=sym).reset_index()


def main():
    os.chdir(REPO)
    pit = pd.read_parquet(f"{REPO}/tasks/breakout_calls_2026/data/pit_universe.parquet",
                          columns=["date", "symbol", "adv", "eligible"])
    uni = pit[pit.eligible].drop(columns=["eligible"]).drop_duplicates(["date", "symbol"])
    # the trend screen's universe is the top 500 by trailing turnover INSIDE
    # the scaled-floor eligible set, not the whole eligible set
    uni = (uni.sort_values(["date", "adv"], ascending=[True, False])
              .groupby("date", sort=False).head(500).drop(columns=["adv"]))
    syms = sorted(uni.symbol.unique())
    print(f"{len(syms)} symbols", flush=True)
    parts = []
    for i, s in enumerate(syms, 1):
        r = flags(s)
        if r is not None:
            parts.append(r)
        if i % 500 == 0:
            print(f"  {i}/{len(syms)}", flush=True)
    fl = pd.concat(parts, ignore_index=True).merge(uni, on=["date", "symbol"],
                                                   how="inner")
    b = fl.groupby("date").agg(n=("above200", "size"),
                               pct_above_200=("above200", "mean"),
                               pct_above_50=("above50", "mean"))
    b = b[b.n >= 50]
    ref = pd.read_parquet(f"{REPO}/tasks/trend_screen_2026/data/breadth.parquet")
    j = b.join(ref[["pct_above_200"]].rename(columns={"pct_above_200": "ref"}),
               how="inner")
    d = (j.pct_above_200 - j.ref).abs()
    print(f"overlap {len(j)} of {len(b)} / ref {len(ref)}; "
          f"max |diff| pct_above_200 = {d.max():.3e}; mean {d.mean():.3e}", flush=True)
    b.to_parquet(OUT)
    print(f"wrote {OUT} rows={len(b)} span {b.index.min().date()}..{b.index.max().date()}")


if __name__ == "__main__":
    main()
