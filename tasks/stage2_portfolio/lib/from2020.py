"""L6 v2 (and the rest of the lineup) from 2020 onward.

Two windows:
  prod      2020-01-01 -> panel end. What the daily pipeline actually runs
            (scripts/update_all_portfolios.py passes --start 2020-01-01).
  published 2020-07-10 -> 2026-02-02. The exact window docs/portfolios.md
            quotes for L6 v2 (CAGR 59.4%, Sharpe 1.92, MaxDD -30.0%).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parents[2]))

from lib.lineup import (build_full_context, native, stitched_nifty100, S2V2,
                        MEMBERSHIP_RECON, MEMBERSHIP_PROD, N250_RECON, N250_PROD)
from lib.run_s2 import run_one, metrics
from lib.panels import ROOT

WINDOWS = [("prod 2020-01-01+", "2020-01-01", None),
           ("published window", "2020-07-10", "2026-02-02")]
NPOS = {"OM25v3": 25, "TL25v3": 25, "L6v2": 24, "COMBO": 24, "S2v2": 20}


def main():
    rows = []
    for basis, mcsv, n250 in (("snapshot", MEMBERSHIP_PROD, N250_PROD),
                              ("survivorship_free", MEMBERSHIP_RECON, N250_RECON)):
        ctx = build_full_context(mcsv, n250)
        reg = stitched_nifty100(ctx["prices"]["calendar"])
        bench = ctx["benchmark"]
        for wlabel, s, e in WINDOWS:
            print(f"\n=== {basis} | {wlabel} ===")
            print(f"  {'book':9s}  CAGR      DD     Sharpe Sortino Calmar "
                  f"medHold turn  win%   alpha")
            for nm in ("L6v2", "OM25v3", "TL25v3", "COMBO", "S2v2"):
                res = (run_one(ctx, start=s, end=e, **S2V2) if nm == "S2v2"
                       else native(ctx, nm, reg)(s, e))
                m = metrics(res, benchmark=bench)
                h = res["exits"]["hold_days"].dropna()
                print(f"  {nm:9s} {m['cagr_pct']:6.2f}% {m['max_dd_pct']:7.2f}%  "
                      f"{m['sharpe']:5.2f}  {m['sortino']:5.2f}  {m['calmar']:5.2f} "
                      f"{h.median():6.0f}d {m['buys_per_year']/NPOS[nm]:4.1f} "
                      f"{m.get('win_rate_pct', 0):5.1f}% "
                      f"{m.get('alpha_cagr_pp', np.nan):+7.2f}pp")
                rows.append(dict(basis=basis, window=wlabel, book=nm,
                                 median_hold=float(h.median()),
                                 turnover_x=round(m["buys_per_year"]/NPOS[nm], 1),
                                 **{k: v for k, v in m.items()
                                    if not isinstance(v, dict)}))
        (ROOT / "tmp_nifty100_stitched.csv").unlink(missing_ok=True)
    pd.DataFrame(rows).to_csv(HERE.parent / "data" / "from2020.csv", index=False)
    print(f"\n[wrote] data/from2020.csv")


if __name__ == "__main__":
    main()
