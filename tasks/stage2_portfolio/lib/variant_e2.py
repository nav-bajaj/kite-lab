"""Founder spec, then the two single guards added back.

The ablation says the stage-age minimum is the load-bearing one. This prices
the founder's exact spec against restoring it, and against also restoring the
sector cap - everything else in the founder spec kept as asked.
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
from lib.final import exposure_profile

IS = ("2009-09-01", "2016-12-31")
OOS = ("2017-01-01", None)

E = dict(variant="E_rs_unext", top_n=20, exit_buffer=10, stop=0.0,
         weight_mode="drift", sector_cap=0)

CONFIGS = [
    ("E as specified",                  E,                        0),
    ("E + stage-age 21 restored",       E,                       21),
    ("E + stage-age 21 + sector cap 4", dict(E, sector_cap=4),   21),
    ("D_blend baseline (reference)",    dict(variant="D_blend", top_n=22,
                                             exit_buffer=10, stop=0.0,
                                             weight_mode="trim",
                                             sector_cap=4),      21),
]


def main():
    rows = []
    for basis, mcsv in (("survivorship_free", MEMBERSHIP_RECON),
                        ("snapshot", MEMBERSHIP_PROD)):
        ctxs = {a: build_context(membership_csv=mcsv, min_stage_age=a)
                for a in (0, 21)}
        print(f"\n=== {basis} ===")
        print(f"  {'config':34s} {'IS CAGR':>8s} {'IS DD':>8s} {'IS Cal':>7s} |"
              f" {'OOS CAGR':>9s} {'OOS DD':>8s} {'OOS Sh':>7s} {'OOS Cal':>8s}"
              f" {'alpha':>9s} {'trd/y':>6s} {'hold':>5s} {'pkSect':>7s}")
        for label, kw, age in CONFIGS:
            ctx = ctxs[age]
            out = {}
            for win, (s, e) in (("IS", IS), ("OOS", OOS)):
                res = run_one(ctx, start=s, end=e, **kw)
                m = metrics(res, benchmark=ctx["benchmark"])
                if win == "OOS":
                    m.update(concentration(res, ctx["prices"]["close"],
                                           ctx["sector_map"]))
                    m.update(exposure_profile(res))
                out[win] = m
            i, o = out["IS"], out["OOS"]
            print(f"  {label:34s} {i['cagr_pct']:7.2f}% {i['max_dd_pct']:7.2f}%"
                  f" {i['calmar']:7.2f} | {o['cagr_pct']:8.2f}%"
                  f" {o['max_dd_pct']:7.2f}% {o['sharpe']:7.2f} {o['calmar']:8.2f}"
                  f" {o.get('alpha_cagr_pp', np.nan):+8.2f}pp"
                  f" {o['buys_per_year']:6.0f} {o.get('median_hold_days',0):4d}d"
                  f" {o.get('peak_sector_wt_pct',0):6.1f}%")
            rows.append(dict(basis=basis, config=label, stage_age=age,
                             **{f"IS_{k}": v for k, v in i.items()
                                if not isinstance(v, dict)},
                             **{f"OOS_{k}": v for k, v in o.items()
                                if not isinstance(v, dict)}))
    pd.DataFrame(rows).to_csv(HERE.parent / "data" / "variant_e_guards.csv",
                              index=False)
    print("\n[wrote] data/variant_e_guards.csv")


if __name__ == "__main__":
    main()
