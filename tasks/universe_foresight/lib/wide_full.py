"""Phase 4 -- the pool re-run on the FULL adjusted panel.

tasks/universe_foresight/RESULTS.md blocked the retune on extending the price
panel beyond ever-members of the four NSE indices. The extension turned out to
be free: data/master/prices/adjusted_pr already carries 2519 adjusted symbols
and data/master/panels/pr is a filtered copy of it, so panels/pr_full is the
same files symlinked whole. Coverage of the investable set goes from 65-85% to
95-100%.

Runs go to runs_full/ because cfg_id does not include the panel: reusing runs/
would silently return the narrow-panel results.
"""
from __future__ import annotations

import json, sys
from pathlib import Path

import pandas as pd

TASK = Path(__file__).resolve().parent.parent
sys.path.insert(0, "/Users/navdeep/kite-lab/tasks/mm_rebuild/lib")
sys.path.insert(0, str(TASK / "lib"))
import run as MM            # noqa: E402
import windows as W         # noqa: E402
import buckets as B         # noqa: E402
import run_ladder as L      # noqa: E402

FULL = B.MASTER / "panels/pr_full"
RUNS = TASK / "runs_full"; RUNS.mkdir(exist_ok=True)
(RUNS / "membership").mkdir(exist_ok=True)
MM.RUNS = RUNS; W.REG = RUNS / "registry.csv"
MM.om.PANEL = FULL; B.PANEL = FULL; B.CACHE = RUNS; B.OUT = RUNS / "membership"
FLOORS = [2e7, 5e7, 10e7]
SUB = [("2016-19", "2016-01-01", "2019-12-31"), ("2020-22", "2020-01-01", "2022-12-31"), ("2023-26", "2023-01-01", "2099-12-31")]


def line(tag, eq, is_a):
    w = {k: W.stats(eq, a, z) for k, (a, z) in
         {"IS": (is_a, "2015-12-31"), "OOS": ("2016-01-01", "2099-12-31")}.items()}
    sub = [W.stats(eq, a, z)["sharpe"] for _, a, z in SUB]
    g3 = "PASS" if min(sub) >= 0.6 else "FAIL"
    print(f"  {tag:<22} " + " | ".join(f"{k} {100*v['cagr']:5.1f}% / {v['sharpe']:4.2f} / {100*v['maxdd']:4.0f}%" for k, v in w.items())
          + "  subs " + "/".join(f"{x:.2f}" for x in sub) + f"  G3 {g3}", flush=True)
    return dict(windows={k: {m: float(v[m]) for m in ("cagr", "sharpe", "maxdd")} for k, v in w.items()},
                subs=[float(x) for x in sub], g3=g3)


if __name__ == "__main__":
    print(f"panel: {len(list(FULL.glob('*_day.csv')))} symbols", flush=True)
    for f in FLOORS:
        B.build_floor(f"floorF{int(f/1e7)}", f)
        MM.om.MEMBERSHIP[f"floorF{int(f/1e7)}"] = B.OUT / f"floorF{int(f/1e7)}.csv"
    for u in ("nifty250", "nse500"):
        MM.om.MEMBERSHIP[f"{u}_b0"] = B.MASTER / f"membership/{u}.csv"
    res = {}
    for name, spec in L.BOOKS.items():
        print(f"\n{name}", flush=True)
        is_a = spec["start"][:4] + "-01-01"; res[name] = {}
        for tag, uni in [("b0 honest index", f"{spec['base']}_b0")] + [(f"b5 floor Rs {int(f/1e7)} cr", f"floorF{int(f/1e7)}") for f in FLOORS]:
            cfg, _ = MM.run_candidate(universe=uni, start=spec["start"], end=None, **spec["cfg"])
            rid = MM.cfg_id(cfg); eq = W.equity(RUNS / rid)
            res[name][tag] = line(tag, eq, is_a)
            W.register(cfg, rid, W.stats(eq, is_a, "2015-12-31"), "full")
    json.dump(res, open(TASK / "report/wide_full_summary.json", "w"), indent=1)
    print(f"\ntrials: {W.n_trials()}", flush=True)
