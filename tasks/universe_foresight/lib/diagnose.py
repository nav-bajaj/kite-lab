"""Phase 8a -- why the once-in universe fades recently, and why MM cannot use it.

Both questions reduce to one measurement: the once-in universe is NSE 500 plus
its own ex-members, so split every round trip by which sleeve the name was in ON
THE ENTRY DATE and look at the two sleeves separately, by book and by year.
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
import run as MM, windows as W, buckets as B, run_ladder as L  # noqa: E402
from scripts.universe_membership import load_membership, members_asof  # noqa: E402

MM.RUNS = TASK / "runs"; B.OUT = TASK / "runs/membership"
MM.om.MEMBERSHIP["P_nifty250"] = B.MASTER / "membership/nifty250.csv"
MM.om.MEMBERSHIP["P_once"] = B.OUT / "nse500_oncein.csv"
N5 = load_membership(B.MASTER / "membership/nse500.csv")


def round_trips(book: str, universe: str) -> pd.DataFrame:
    spec = L.BOOKS[book]
    cfg, _ = MM.run_candidate(universe=universe, start=spec["start"], end=None, **spec["cfg"])
    tr = pd.read_csv(MM.RUNS / MM.cfg_id(cfg) / "trades.csv", parse_dates=["date"]).sort_values("date")
    out = []
    for sym, g in tr.groupby("symbol"):
        lots = []
        for t in g.itertuples():
            if t.side == "BUY":
                lots.append([t.shares, t.price, t.date])
            else:
                n = t.shares
                while n > 1e-9 and lots:
                    q = min(n, lots[0][0])
                    out.append(dict(symbol=sym, entry=lots[0][2], exit=t.date, cost=q * lots[0][1],
                                    pnl=q * (t.price - lots[0][1]), reason=t.reason,
                                    held=(t.date - lots[0][2]).days))
                    lots[0][0] -= q; n -= q
                    if lots[0][0] <= 1e-9: lots.pop(0)
    r = pd.DataFrame(out)
    memo = {}
    def sleeve(d):
        k = d.normalize()
        if k not in memo: memo[k] = members_asof(N5, k)
        return memo[k]
    r["current"] = [s in sleeve(d) for s, d in zip(r.symbol, r.entry)]
    r["ret"] = r.pnl / r.cost
    return r[r.entry >= "2016-01-01"]


def report(book):
    print(f"\n{'='*88}\n{book}\n{'='*88}")
    base = round_trips(book, "P_nifty250")
    once = round_trips(book, "P_once")
    print(f"nifty250 baseline: {len(base):4d} trips, total P&L {base.pnl.sum()/1e6:7.1f}m, win {100*(base.ret>0).mean():.0f}%, mean ret {100*base.ret.mean():+5.1f}%")
    for lab, sub in [("  current NSE 500 member", once[once.current]), ("  EX-member sleeve", once[~once.current])]:
        print(f"{lab:<26}: {len(sub):4d} trips, total P&L {sub.pnl.sum()/1e6:7.1f}m "
              f"({100*sub.pnl.sum()/once.pnl.sum():4.0f}% of book), win {100*(sub.ret>0).mean():.0f}%, "
              f"mean ret {100*sub.ret.mean():+5.1f}%, median hold {sub.held.median():.0f}d")
    print(f"\n  ex-member sleeve by entry year (trips / share of that year's P&L / mean return):")
    once["yr"] = once.entry.dt.year
    rows = []
    for y, g in once.groupby("yr"):
        ex = g[~g.current]
        rows.append(dict(year=y, n_ex=len(ex), pct_trips=100 * len(ex) / len(g),
                         pnl_share=100 * ex.pnl.sum() / g.pnl.sum() if g.pnl.sum() else np.nan,
                         mean_ex=100 * ex.ret.mean() if len(ex) else np.nan,
                         mean_cur=100 * g[g.current].ret.mean()))
    d = pd.DataFrame(rows).set_index("year")
    print("   " + "  ".join(f"{y}" for y in d.index))
    print("   " + "  ".join(f"{int(v):4d}" for v in d.n_ex) + "   trips in ex sleeve")
    print("   " + "  ".join(f"{v:4.0f}" for v in d.pnl_share) + "   % of year P&L")
    print("   " + "  ".join(f"{v:+4.0f}" for v in d.mean_ex) + "   mean ret, ex")
    print("   " + "  ".join(f"{v:+4.0f}" for v in d.mean_cur) + "   mean ret, current")
    return once


if __name__ == "__main__":
    for b in ("OM25 v4", "MM"):
        report(b)
