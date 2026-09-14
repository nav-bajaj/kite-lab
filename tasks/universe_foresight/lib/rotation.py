"""Phase 12 -- does the book rotate into large caps when large caps lead?

The founder's argument: Nifty 100 sits inside Nifty 250, so if large caps become
the RS leaders the ranking should pick them and the book adapts by itself. If
true, the book's LARGE share should rise in large-led years, and its weak showing
there is about momentum paying less in weak markets rather than about being stuck
in midcaps.

Reconstructs actual month-end holdings from the trade log and classifies each by
point-in-time band.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

TASK = Path(__file__).resolve().parent.parent
sys.path.insert(0, "/Users/navdeep/kite-lab/tasks/mm_rebuild/lib")
sys.path.insert(0, str(TASK / "lib"))
sys.path.insert(0, "/Users/navdeep/kite-lab")
import run as MM, windows as W, buckets as B, run_ladder as L, capbands as C  # noqa: E402
from scripts.universe_membership import load_membership, members_asof  # noqa: E402

MM.RUNS = TASK / "runs"; B.OUT = TASK / "runs/membership"


def holdings(book="OM25 v4", uni="P_n250") -> pd.DataFrame:
    spec = L.BOOKS[book]
    cfg, _ = MM.run_candidate(universe=uni, start=spec["start"], end=None, **spec["cfg"])
    tr = pd.read_csv(MM.RUNS / MM.cfg_id(cfg) / "trades.csv", parse_dates=["date"]).sort_values("date")
    pos, rows = {}, []
    dates = sorted(tr.date.unique())
    month_ends = pd.Series(dates, index=dates).groupby([pd.DatetimeIndex(dates).year, pd.DatetimeIndex(dates).month]).last()
    for d in dates:
        for t in tr[tr.date == d].itertuples():
            if t.side == "BUY":
                pos[t.symbol] = pos.get(t.symbol, 0) + t.shares * t.price
            else:
                pos[t.symbol] = pos.get(t.symbol, 0) - t.shares * t.price
                if pos[t.symbol] <= 1: pos.pop(t.symbol, None)
        if d in set(month_ends):
            for s, v in pos.items():
                rows.append(dict(date=d, symbol=s, value=max(v, 0)))
    return pd.DataFrame(rows)


if __name__ == "__main__":
    MM.om.MEMBERSHIP["P_n250"] = B.MASTER / "membership/nifty250.csv"
    n100 = load_membership(B.MASTER / "membership/nifty100.csv")
    h = holdings()
    h = h[h.date >= "2016-01-01"]
    memo = {}
    def is_large(s, d):
        k = d.normalize()
        if k not in memo: memo[k] = members_asof(n100, k)
        return s in memo[k]
    h["large"] = [is_large(s, d) for s, d in zip(h.symbol, h.date)]
    h["yr"] = h.date.dt.year

    bd = C.bands(); cum = (1 + bd).cumprod()
    lead = {}
    for y in range(2016, 2027):
        a, z = f"{y}-01-01", f"{y}-12-31"
        v = {k: (cum[k][(cum[k].index >= a) & (cum[k].index <= z)].iloc[-1] / cum[k][cum[k].index < a].iloc[-1]) - 1 for k in bd.columns}
        lead[y] = "SMALL" if v["SMALL"] > v["LARGE"] else "LARGE"

    # what share of the UNIVERSE is large, for a baseline
    n250 = load_membership(B.MASTER / "membership/nifty250.csv")
    uni_share = {}
    for y in range(2016, 2027):
        d = pd.Timestamp(f"{y}-06-30")
        a, b_ = members_asof(n100, d), members_asof(n250, d)
        uni_share[y] = 100 * len(a & b_) / len(b_)

    print("Shipped OM25 v4 — share of the book in Nifty 100 names, at month-ends\n")
    print(f"{'year':<6}{'regime':>8}{'by count':>11}{'by weight':>11}{'universe':>11}{'tilt vs universe':>19}")
    for y, g in h.groupby("yr"):
        cnt = 100 * g.large.mean()
        wt = 100 * g[g.large].value.sum() / g.value.sum()
        print(f"{y:<6}{lead[y]:>8}{cnt:10.0f}%{wt:10.0f}%{uni_share[y]:10.0f}%{wt-uni_share[y]:+18.0f}pp")
    print()
    for reg in ("LARGE", "SMALL"):
        g = h[h.yr.map(lead) == reg]
        wt = 100 * g[g.large].value.sum() / g.value.sum()
        uni = np.mean([uni_share[y] for y in lead if lead[y] == reg])
        print(f"{reg}-led years: book is {wt:.0f}% large by weight, universe is {uni:.0f}% -> tilt {wt-uni:+.0f}pp")
