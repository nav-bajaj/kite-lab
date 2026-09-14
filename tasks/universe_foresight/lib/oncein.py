"""Phase 7 -- "once in NSE 500, always eligible" as the universe (founder, 2026-09-11).

Run on BOTH panels. The narrow panel is the union of ever-members of the four NSE
indices, and this universe is a subset of NSE 500's ever-members, so the two panels
must agree exactly. If they do, the result is free of the coverage limitation that
reversed the b5 pool in Phase 4.
"""
from __future__ import annotations

import json, sys
from pathlib import Path

TASK = Path(__file__).resolve().parent.parent
sys.path.insert(0, "/Users/navdeep/kite-lab/tasks/mm_rebuild/lib")
sys.path.insert(0, str(TASK / "lib"))
import run as MM, windows as W, buckets as B, run_ladder as L  # noqa: E402

SUB = [("2016-19", "2016-01-01", "2019-12-31"), ("2020-22", "2020-01-01", "2022-12-31"), ("2023-26", "2023-01-01", "2099-12-31")]


def line(tag, eq, is_a):
    w = {k: W.stats(eq, a, z) for k, (a, z) in {"IS": (is_a, "2015-12-31"), "OOS": ("2016-01-01", "2099-12-31")}.items()}
    sub = [W.stats(eq, a, z)["sharpe"] for _, a, z in SUB]
    r3 = W.stats(eq, "2023-09-11", "2099-12-31")
    print(f"  {tag:<28} OOS {100*w['OOS']['cagr']:5.1f}% / {w['OOS']['sharpe']:4.2f} / {100*w['OOS']['maxdd']:4.0f}%"
          f"  subs " + "/".join(f"{x:.2f}" for x in sub)
          + f"  G3 {'PASS' if min(sub) >= 0.6 else 'FAIL'}"
          + f"  | trailing 3y {100*r3['cagr']:5.1f}% / {r3['sharpe']:4.2f}", flush=True)
    return dict(oos={m: float(w["OOS"][m]) for m in ("cagr", "sharpe", "maxdd")}, subs=[float(x) for x in sub],
                g3="PASS" if min(sub) >= 0.6 else "FAIL", trailing3y={m: float(r3[m]) for m in ("cagr", "sharpe", "maxdd")})


def run_on(panel_name, panel, runs):
    runs.mkdir(exist_ok=True); (runs / "membership").mkdir(exist_ok=True)
    MM.RUNS = runs; W.REG = runs / "registry.csv"
    MM.om.PANEL = panel; B.PANEL = panel; B.CACHE = runs; B.OUT = runs / "membership"
    MM.om._cache.clear()
    print(f"\n===== panel: {panel_name} ({len(list(panel.glob('*_day.csv')))} symbols) =====", flush=True)
    unis = {"nse500 PIT": B.MASTER / "membership/nse500.csv",
            "once-in, no floor": B.build_once_in("nse500"),
            "once-in + Rs 2 cr": B.build_once_in("nse500", 2e7),
            "once-in + Rs 5 cr": B.build_once_in("nse500", 5e7)}
    for k, v in unis.items():
        MM.om.MEMBERSHIP[f"P_{k}"] = v
    MM.om.MEMBERSHIP["P_nifty250"] = B.MASTER / "membership/nifty250.csv"
    res = {}
    for name in ("MM", "OM25 v4"):
        spec = L.BOOKS[name]; is_a = spec["start"][:4] + "-01-01"
        print(f"\n{name}", flush=True); res[name] = {}
        for tag in ["P_nifty250", "P_nse500 PIT", "P_once-in, no floor", "P_once-in + Rs 2 cr", "P_once-in + Rs 5 cr"]:
            cfg, _ = MM.run_candidate(universe=tag, start=spec["start"], end=None, **spec["cfg"])
            rid = MM.cfg_id(cfg); eq = W.equity(runs / rid)
            res[name][tag[2:]] = line(tag[2:], eq, is_a)
            W.register(cfg, rid, W.stats(eq, is_a, "2015-12-31"), "oncein")
    return res


if __name__ == "__main__":
    out = {"narrow": run_on("narrow (ever-members of the 4 indices)", B.MASTER / "panels/pr", TASK / "runs"),
           "full": run_on("full (2519 adjusted symbols)", B.MASTER / "panels/pr_full", TASK / "runs_full")}
    json.dump(out, open(TASK / "report/oncein_summary.json", "w"), indent=1)
