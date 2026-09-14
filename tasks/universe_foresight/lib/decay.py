"""Phase 8b -- sweep the post-demotion grace period.

Derived from the Phase 8a diagnosis rather than grid-searched: the ex-member
sleeve decays with age, so cap its age. Reported on the full OOS AND on the
recent window the founder is worried about, with the trial count registered.
"""
from __future__ import annotations

import json, sys
from pathlib import Path

import pandas as pd

TASK = Path(__file__).resolve().parent.parent
sys.path.insert(0, "/Users/navdeep/kite-lab/tasks/mm_rebuild/lib")
sys.path.insert(0, str(TASK / "lib"))
import run as MM, windows as W, buckets as B, run_ladder as L  # noqa: E402

MM.RUNS = TASK / "runs"; W.REG = TASK / "runs/registry.csv"; B.OUT = TASK / "runs/membership"
SUB = [("16-19", "2016-01-01", "2019-12-31"), ("20-22", "2020-01-01", "2022-12-31"), ("23-26", "2023-01-01", "2099-12-31")]
GRACE = [0, 12, 24, 36, 60, 120]

if __name__ == "__main__":
    MM.om.MEMBERSHIP["P_nifty250"] = B.MASTER / "membership/nifty250.csv"
    MM.om.MEMBERSHIP["P_once"] = B.OUT / "nse500_oncein.csv"
    for m in GRACE:
        MM.om.MEMBERSHIP[f"P_decay{m}"] = B.build_decay("nse500", m)
    res = {}
    for book in ("OM25 v4", "MM"):
        spec = L.BOOKS[book]; res[book] = {}
        print(f"\n{book}\n{'universe':<22}{'OOS':>24}{'subs':>20}{'G3':>6}{'trail 3y':>16}{'trail 1y':>16}")
        for lab, uni in ([("nifty250 (shipped)", "P_nifty250")]
                         + [(f"nse500 + {m}m grace" if m else "nse500 PIT (0m)", f"P_decay{m}") for m in GRACE]
                         + [("once-in (no expiry)", "P_once")]):
            cfg, _ = MM.run_candidate(universe=uni, start=spec["start"], end=None, **spec["cfg"])
            eq = W.equity(MM.RUNS / MM.cfg_id(cfg))
            o = W.stats(eq, "2016-01-01", "2099-12-31")
            sub = [W.stats(eq, a, z)["sharpe"] for _, a, z in SUB]
            t3 = W.stats(eq, "2023-09-11", "2099-12-31"); t1 = W.stats(eq, "2025-09-11", "2099-12-31")
            g3 = "PASS" if min(sub) >= 0.6 else "FAIL"
            print(f"{lab:<22}{100*o['cagr']:8.1f}% /{o['sharpe']:5.2f} /{100*o['maxdd']:4.0f}%"
                  f"   {'/'.join(f'{x:.2f}' for x in sub):>18}{g3:>6}"
                  f"{100*t3['cagr']:9.1f}% /{t3['sharpe']:5.2f}{100*t1['cagr']:9.1f}% /{t1['sharpe']:5.2f}", flush=True)
            res[book][lab] = dict(oos={m: float(o[m]) for m in ("cagr", "sharpe", "maxdd")}, subs=[float(x) for x in sub],
                                  g3=g3, t3={m: float(t3[m]) for m in ("cagr", "sharpe")}, t1={m: float(t1[m]) for m in ("cagr", "sharpe")})
            W.register(cfg, MM.cfg_id(cfg), W.stats(eq, spec["start"][:4] + "-01-01", "2015-12-31"), "decay")
    json.dump(res, open(TASK / "report/decay_summary.json", "w"), indent=1)
    print(f"\ntrials in this folder: {W.n_trials()}", flush=True)
