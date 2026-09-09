"""One-at-a-time ablation from the D_blend baseline to the founder spec.

Five things changed at once between D_blend and variant E. This isolates each,
so the cost is attributable rather than a single before/after.
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
from lib.panels import MEMBERSHIP_PROD, MEMBERSHIP_RECON
from lib.sweep2 import concentration

IS = ("2009-09-01", "2016-12-31")
OOS = ("2017-01-01", None)

BASE = dict(variant="D_blend", top_n=22, exit_buffer=10, stop=0.0,
            weight_mode="trim", sector_cap=4)
FULL_E = dict(variant="E_rs_unext", top_n=20, exit_buffer=10, stop=0.0,
              weight_mode="drift", sector_cap=0)

# (label, run kwargs override, stage-age minimum)
STEPS = [
    ("baseline D_blend (22/cap4/trim/age21)", {}, 21),
    ("  + score = RS + un-extension only",    dict(variant="E_rs_unext"), 21),
    ("  + stage-age minimum removed",         {}, 0),
    ("  + top_n 22 -> 20",                    dict(top_n=20), 21),
    ("  + sector cap removed",                dict(sector_cap=0), 21),
    ("  + trim removed (drift)",              dict(weight_mode="drift"), 21),
    ("FULL founder spec (all five)",          FULL_E, 0),
]


def main():
    rows = []
    for basis, mcsv in (("survivorship_free", MEMBERSHIP_RECON),
                        ("snapshot", MEMBERSHIP_PROD)):
        ctxs = {age: build_context(membership_csv=mcsv, min_stage_age=age)
                for age in (21, 0)}
        print(f"\n=== {basis} ===")
        print(f"  {'change':40s} {'IS CAGR':>8s} {'IS DD':>8s} {'IS Cal':>7s} |"
              f" {'OOS CAGR':>9s} {'OOS DD':>8s} {'OOS Sh':>7s} {'OOS Cal':>8s}"
              f" {'alpha':>8s} {'peakSect':>9s}")
        for label, over, age in STEPS:
            ctx = ctxs[age]
            kw = dict(BASE if label != "FULL founder spec (all five)" else {})
            kw.update(over)
            if label == "FULL founder spec (all five)":
                kw = dict(FULL_E)
            out = {}
            for win, (s, e) in (("IS", IS), ("OOS", OOS)):
                res = run_one(ctx, start=s, end=e, **kw)
                m = metrics(res, benchmark=ctx["benchmark"])
                if win == "OOS":
                    m.update(concentration(res, ctx["prices"]["close"],
                                           ctx["sector_map"]))
                out[win] = m
            i, o = out["IS"], out["OOS"]
            print(f"  {label:40s} {i['cagr_pct']:7.2f}% {i['max_dd_pct']:7.2f}%"
                  f" {i['calmar']:7.2f} | {o['cagr_pct']:8.2f}%"
                  f" {o['max_dd_pct']:7.2f}% {o['sharpe']:7.2f} {o['calmar']:8.2f}"
                  f" {o.get('alpha_cagr_pp', np.nan):+7.2f}pp"
                  f" {o.get('peak_sector_wt_pct', 0):8.1f}%")
            rows.append(dict(basis=basis, change=label.strip(), stage_age=age,
                             **{f"IS_{k}": v for k, v in i.items()
                                if not isinstance(v, dict)},
                             **{f"OOS_{k}": v for k, v in o.items()
                                if not isinstance(v, dict)}))
    pd.DataFrame(rows).to_csv(HERE.parent / "data" / "ablation_e.csv", index=False)
    print("\n[wrote] data/ablation_e.csv")


if __name__ == "__main__":
    main()
