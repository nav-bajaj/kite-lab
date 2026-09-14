"""b5 -- the investability pool as the universe, swept over the turnover floor.

The placebo said breadth pays and the selection rule hurts, so the candidate is
the pool with no rule on top. Each (book, floor) is a real trial and is written
to this folder's own registry, so the deflated-Sharpe count for this line of work
stays honest and separate from mm_rebuild's.
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

MM.RUNS = TASK / "runs"; MM.RUNS.mkdir(parents=True, exist_ok=True)
W.REG = TASK / "runs/registry.csv"
(TASK / "report").mkdir(exist_ok=True)
FLOORS = [1e7, 2e7, 5e7, 10e7]


def show(name, tag, eq, is_a):
    w = {k: W.stats(eq, a, z) for k, (a, z) in
         {"IS": (is_a, "2015-12-31"), "OOS": ("2016-01-01", "2099-12-31"), "2020+": ("2020-01-01", "2099-12-31")}.items()}
    print(f"  {tag:<26} " + " | ".join(
        f"{k} {100*v['cagr']:5.1f}% / {v['sharpe']:4.2f} / {100*v['maxdd']:4.0f}%" for k, v in w.items()), flush=True)
    return w


if __name__ == "__main__":
    for f in FLOORS:
        B.build_floor(f"floor{int(f/1e7)}", f)
        MM.om.MEMBERSHIP[f"floor{int(f/1e7)}"] = B.OUT / f"floor{int(f/1e7)}.csv"
    L.register_universes()
    res = {}
    for name, spec in L.BOOKS.items():
        print(f"\n{name} (book rules unchanged, from {spec['start']})", flush=True)
        is_a = spec["start"][:4] + "-01-01"; res[name] = {}
        for tag, uni, extra in ([("b0 honest index", f"{spec['base']}_b0", {})]
                                + [(f"b5 floor Rs {int(f/1e7)} cr", f"floor{int(f/1e7)}", {}) for f in FLOORS]
                                + [("b0 honest, no sector cap", f"{spec['base']}_b0", dict(sector_cap=0)),
                                   ("b5 floor Rs 2 cr, no sec cap", "floor2", dict(sector_cap=0))]):
            cfg, _ = MM.run_candidate(universe=uni, start=spec["start"], end=None, **{**spec["cfg"], **extra})
            rid = MM.cfg_id(cfg); eq = W.equity(MM.RUNS / rid)
            res[name][tag] = show(name, tag, eq, is_a)
            W.register(cfg, rid, res[name][tag]["IS"], "b5")
    json.dump({b: {t: {w: {m: float(s[m]) for m in ("cagr", "sharpe", "maxdd")} for w, s in v.items()}
                   for t, v in d.items()} for b, d in res.items()},
              open(TASK / "report/wide_summary.json", "w"), indent=1)
    print(f"\ntrials in this folder's registry: {W.n_trials()}", flush=True)
