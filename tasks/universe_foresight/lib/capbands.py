"""Phase 11 -- is the hold-out window a Nifty 250-favouring regime, and is the
shipped book a hidden cap bet? (founder, 2026-09-11)

Two questions, one construction. Build equal-weight point-in-time baskets for
three disjoint cap bands from our own membership files and panel, so they are
mutually consistent and survivorship-free:

  LARGE  Nifty 100 members
  MID    Nifty 250 minus Nifty 100          (the Midcap 150 band)
  SMALL  NSE 500 minus Nifty 250            (the 251-500 band)

The shipped book's universe is LARGE + MID. once-in adds SMALL plus demoted names.
If 2024-26 is simply a LARGE+MID period, the hold-out verdict is confounded.
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


def bands() -> pd.DataFrame:
    """Equal-weight daily total return of each band, rebalanced monthly, PIT."""
    cache = TASK / "report/capbands.csv"
    if cache.exists():
        return pd.read_csv(cache, parse_dates=["date"]).set_index("date")
    close = MM.om.panels()["close"]
    n100 = load_membership(B.MASTER / "membership/nifty100.csv")
    n250 = load_membership(B.MASTER / "membership/nifty250.csv")
    n500 = load_membership(B.MASTER / "membership/nse500.csv")
    r = close.pct_change()
    cal = close.index
    months = pd.Series(cal, index=cal).groupby([cal.year, cal.month]).first().tolist()
    out = {}
    for name in ("LARGE", "MID", "SMALL"):
        w = pd.DataFrame(0.0, index=cal, columns=close.columns)
        for i, d in enumerate(months):
            end = months[i + 1] if i + 1 < len(months) else cal[-1] + pd.Timedelta(days=1)
            a, b_, c = members_asof(n100, d), members_asof(n250, d), members_asof(n500, d)
            mem = {"LARGE": a, "MID": b_ - a, "SMALL": c - b_}[name]
            cols = [s for s in mem if s in close.columns and not np.isnan(close.loc[d, s])]
            if not cols: continue
            m = (cal >= d) & (cal < end)
            w.loc[m, cols] = 1.0 / len(cols)
        out[name] = (w.shift(1) * r).sum(axis=1)
    df = pd.DataFrame(out)
    df.to_csv(cache)
    return df


if __name__ == "__main__":
    bd = bands()
    cum = (1 + bd).cumprod()

    def cagr(s, a, z):
        x = s[(s.index >= a) & (s.index <= z)]
        return 100 * ((x.iloc[-1] / x.iloc[0]) ** (365.25 / (x.index[-1] - x.index[0]).days) - 1)

    print("Equal-weight point-in-time cap bands, CAGR %\n")
    print(f"{'window':<24}{'LARGE':>9}{'MID':>9}{'SMALL':>9}   leader")
    for lab, a, z in [("IS 2006-2015", "2006-01-01", "2015-12-31"), ("fit 2016-2023", "2016-01-01", "2023-12-31"),
                      ("HOLD-OUT 2024-26", "2024-01-01", "2099-12-31"),
                      ("  2024", "2024-01-01", "2024-12-31"), ("  2025", "2025-01-01", "2025-12-31"),
                      ("  2026", "2026-01-01", "2099-12-31")]:
        v = {k: cagr(cum[k], a, z) for k in bd.columns}
        print(f"{lab:<24}" + "".join(f"{v[k]:+8.1f}%" for k in bd.columns) + f"   {max(v, key=v.get)}")

    print("\n\nConditional test: does the shipped book only win when its own bands lead?\n")
    MM.om.MEMBERSHIP["P_n250"] = B.MASTER / "membership/nifty250.csv"
    MM.om.MEMBERSHIP["P_once"] = B.OUT / "nse500_oncein.csv"
    spec = L.BOOKS["OM25 v4"]
    eq = {}
    for lab, uni in [("shipped", "P_n250"), ("once-in", "P_once")]:
        cfg, _ = MM.run_candidate(universe=uni, start=spec["start"], end=None, **spec["cfg"])
        eq[lab] = W.equity(MM.RUNS / MM.cfg_id(cfg)).pct_change()
    # regime from the PRIOR 12 months only, so the split uses no forward information
    lead = (cum["SMALL"].pct_change(252) - cum["LARGE"].pct_change(252)).shift(1)
    m = pd.DataFrame(eq).join(lead.rename("spread")).dropna()
    m = m[m.index >= "2016-01-01"]
    for lab, mask in [("SMALL leading (trailing 12m)", m.spread > 0), ("LARGE leading (trailing 12m)", m.spread <= 0)]:
        g = m[mask]
        days = len(g)
        st = {k: (100 * ((1 + g[k]).prod() ** (252 / days) - 1), (g[k].mean() * 252 - 0.05) / (g[k].std() * np.sqrt(252)))
              for k in ("shipped", "once-in")}
        print(f"{lab:<32} {days:5d} days ({100*days/len(m):.0f}% of OOS)")
        for k in ("shipped", "once-in"):
            print(f"    {k:<10} annualised {st[k][0]:6.1f}%   Sharpe {st[k][1]:5.2f}")
    print("\n(annualised within each regime's days only; not a tradeable series)")
