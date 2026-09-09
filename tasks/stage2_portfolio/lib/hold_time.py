"""Can S2 hold winners longer without giving back the drawdown edge?

Two mechanisms, tested together on the founder's variant-E spec:

  exit_confirm_weeks  A name must fail the keep test on N CONSECUTIVE weekly
                      checks before it is sold. Direct mirror of the entry
                      stage-age rule - one bad print is noise on the way out
                      as much as on the way in.

  hold_mode           How loose the hold test is relative to the entry gate:
                      strict = must keep qualifying outright (current)
                      tiered = MA stack + rising 200 DMA only
                      loose  = Weinstein sell rule (above 150 DMA, 150>200)

Reference: on this data TL25 v3 holds 56d median / 5.8x turnover, L6 14d/11.1x.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parents[2]))

from lib.run_s2 import build_context, run_one, metrics
from lib.panels import MEMBERSHIP_RECON, MEMBERSHIP_PROD

IS = ("2009-09-01", "2016-12-31")
OOS = ("2017-01-01", None)
E = dict(variant="E_rs_unext", top_n=20, stop=0.0, weight_mode="drift",
         sector_cap=0)


def row(ctx, res, m):
    h = res["exits"]["hold_days"].dropna()
    ex = res["exits"].dropna(subset=["pnl_pct"])
    return dict(
        median_hold=int(h.median()) if len(h) else 0,
        mean_hold=int(h.mean()) if len(h) else 0,
        p90_hold=int(h.quantile(.90)) if len(h) else 0,
        turnover_x=round(m["buys_per_year"] / 20, 1),
        pct_gt_50=round((ex["pnl_pct"] > 0.5).mean() * 100, 2) if len(ex) else 0,
    )


def main():
    basis = sys.argv[1] if len(sys.argv) > 1 else "survivorship_free"
    mcsv = MEMBERSHIP_RECON if basis == "survivorship_free" else MEMBERSHIP_PROD
    ctxs = {a: build_context(membership_csv=mcsv, min_stage_age=a)
            for a in (0, 21)}
    rows = []
    print(f"=== {basis} - founder spec E (RS+unext, 20 names, no cap, drift) ===")
    print(f"  {'age':>3s} {'hold':6s} {'cfm':>3s} {'buf':>3s} |"
          f" {'IS Cal':>7s} | {'OOS CAGR':>9s} {'OOS DD':>8s} {'OOS Sh':>7s}"
          f" {'OOS Cal':>8s} {'medHold':>8s} {'meanHold':>9s} {'p90':>5s}"
          f" {'turn':>5s} {'>50%':>6s}")
    for age in (21, 0):
        for hold_mode in ("strict", "tiered", "loose"):
            for cfm in (1, 2, 3):
                for buf in (10, 20):
                    if hold_mode == "strict" and buf == 20:
                        continue
                    ctx = ctxs[age]
                    kw = dict(E, exit_buffer=buf, hold_mode=hold_mode,
                              exit_confirm_weeks=cfm)
                    out = {}
                    for win, (s, e) in (("IS", IS), ("OOS", OOS)):
                        r = run_one(ctx, start=s, end=e, **kw)
                        mm = metrics(r, benchmark=ctx["benchmark"])
                        out[win] = (r, mm)
                    (ri, mi), (ro, mo) = out["IS"], out["OOS"]
                    ext = row(ctx, ro, mo)
                    print(f"  {age:3d} {hold_mode:6s} {cfm:3d} {buf:3d} |"
                          f" {mi['calmar']:7.2f} | {mo['cagr_pct']:8.2f}%"
                          f" {mo['max_dd_pct']:7.2f}% {mo['sharpe']:7.2f}"
                          f" {mo['calmar']:8.2f} {ext['median_hold']:7d}d"
                          f" {ext['mean_hold']:8d}d {ext['p90_hold']:5d}"
                          f" {ext['turnover_x']:5.1f} {ext['pct_gt_50']:5.2f}%")
                    rows.append(dict(basis=basis, stage_age=age,
                                     hold_mode=hold_mode, exit_confirm=cfm,
                                     exit_buffer=buf, IS_calmar=mi["calmar"],
                                     IS_cagr=mi["cagr_pct"], IS_dd=mi["max_dd_pct"],
                                     **{f"OOS_{k}": v for k, v in mo.items()
                                        if not isinstance(v, dict)}, **ext))
    pd.DataFrame(rows).to_csv(HERE.parent / "data" / f"hold_time_{basis}.csv",
                              index=False)
    print(f"\n[wrote] data/hold_time_{basis}.csv")


if __name__ == "__main__":
    main()
