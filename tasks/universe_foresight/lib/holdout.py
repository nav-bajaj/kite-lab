"""Phase 9b -- the hold-out test. Run ONCE, after refit.py has chosen.

Reads the winners refit.py wrote from the fit window alone and scores them on
2024-01-01 -> today, which nothing in the selection saw. Also scores the shipped
book unchanged, so the question is not "is the refit good" but "is the refit
better than what we already run, on data neither was fitted to".
"""
from __future__ import annotations

import json, sys
from pathlib import Path

import pandas as pd

TASK = Path(__file__).resolve().parent.parent
sys.path.insert(0, "/Users/navdeep/kite-lab/tasks/mm_rebuild/lib")
sys.path.insert(0, str(TASK / "lib"))
import run as MM, windows as W, buckets as B, run_ladder as L, refit as R  # noqa: E402

MM.RUNS = TASK / "runs"; B.OUT = TASK / "runs/membership"
HOLD = ("2024-01-01", "2099-12-31")


def score(eq, label):
    h = W.stats(eq, *HOLD); s = W.stats(eq, *R.SEL)
    yr = {}
    for y, g in eq.groupby(eq.index.year):
        prev = eq[eq.index < f"{y}-01-01"]
        yr[y] = 100 * (g.iloc[-1] / (prev.iloc[-1] if len(prev) else g.iloc[0]) - 1)
    print(f"{label:<34}{100*s['cagr']:8.1f}% /{s['sharpe']:5.2f}   |{100*h['cagr']:9.1f}% /{h['sharpe']:5.2f} /{100*h['maxdd']:4.0f}%"
          f"   {yr.get(2024,float('nan')):+7.1f}{yr.get(2025,float('nan')):+7.1f}{yr.get(2026,float('nan')):+7.1f}")
    return dict(sel={k: float(s[k]) for k in ("cagr", "sharpe")}, hold={k: float(h[k]) for k in ("cagr", "sharpe", "maxdd")},
                y2024=yr.get(2024), y2025=yr.get(2025), y2026=yr.get(2026))


if __name__ == "__main__":
    MM.om.MEMBERSHIP["P_n250"] = B.MASTER / "membership/nifty250.csv"
    MM.om.MEMBERSHIP["P_once"] = B.OUT / "nse500_oncein.csv"
    picks = json.load(open(TASK / "report/refit_picks.json"))
    out = {}
    print(f"\n{'':34}{'FIT 2016-2023':>20}   {'HOLD-OUT 2024->':>28}   {'2024':>6}{'2025':>7}{'2026':>7}")
    print("-" * 112)
    spec = L.BOOKS["OM25 v4"]
    cfg, _ = MM.run_candidate(universe="P_n250", start=spec["start"], end=None, **spec["cfg"])
    out["shipped OM25 v4 (nifty250)"] = score(W.equity(MM.RUNS / MM.cfg_id(cfg)), "shipped OM25 v4 (nifty250)")
    cfg, _ = MM.run_candidate(universe="P_once", start=spec["start"], end=None, **spec["cfg"])
    out["shipped rules on once-in"] = score(W.equity(MM.RUNS / MM.cfg_id(cfg)), "shipped rules on once-in")
    for uname, p in picks.items():
        c = (p["mix_w"], int(p["top_n"]), int(p["buffer"]), int(p["sector_cap"]))
        cfg, _ = MM.run_candidate(universe=R.UNIS[uname], start="2006-02-01", end=None, **R.cell_cfg(c))
        lab = f"REFIT {uname} mix{c[0]}/n{c[1]}/b{c[2]}/s{c[3]}"
        out[lab] = score(W.equity(MM.RUNS / MM.cfg_id(cfg)), lab)
    json.dump(out, open(TASK / "report/holdout_summary.json", "w"), indent=1)
