"""Phase 13 -- a capped sleeve for DROPPED Nifty 250 names (founder, 2026-09-11).

Core stays Nifty 250 point-in-time. A fixed K of 25 slots is reserved for names
that WERE in Nifty 250 and were dropped, on the argument that a dropped name can
surge and NSE re-includes it only after the move. Structurally different from
once-in, where ex-members competed freely for every slot and took as many as they
ranked into -- the cap bounds exactly the exposure that produced once-in's -12.0%
in 2025.

Different from the satellite test already rejected in mm_rebuild §14, which drew
its sleeve from the current 251-500 band. This draws from ex-Nifty-250 names.

Same sealed protocol as Phase 9: fit 2006-2023, select nothing on the hold-out,
score 2024-> once.
"""
from __future__ import annotations

import json, sys
from pathlib import Path

import pandas as pd

TASK = Path(__file__).resolve().parent.parent
sys.path.insert(0, "/Users/navdeep/kite-lab/tasks/mm_rebuild/lib")
sys.path.insert(0, str(TASK / "lib"))
sys.path.insert(0, "/Users/navdeep/kite-lab")
import run as MM, windows as W, buckets as B, run_ladder as L, refit as R  # noqa: E402
from scripts.universe_membership import load_membership, members_asof  # noqa: E402

MM.RUNS = TASK / "runs"; W.REG = TASK / "runs/registry.csv"; B.OUT = TASK / "runs/membership"
HOLD = ("2024-01-01", "2099-12-31")
SUB = [("16-19", "2016-01-01", "2019-12-31"), ("20-23", "2020-01-01", "2023-12-31")]


def show(label, eq):
    f = W.stats(eq, *R.SEL); h = W.stats(eq, *HOLD)
    sub = [W.stats(eq, a, z)["sharpe"] for _, a, z in SUB]
    y = {}
    for yr, g in eq.groupby(eq.index.year):
        prev = eq[eq.index < f"{yr}-01-01"]
        y[yr] = 100 * (g.iloc[-1] / (prev.iloc[-1] if len(prev) else g.iloc[0]) - 1)
    print(f"{label:<28}{100*f['cagr']:7.1f}% /{f['sharpe']:5.2f} /{100*f['maxdd']:4.0f}%  {'/'.join(f'{x:.2f}' for x in sub):>10}"
          f"   |{100*h['cagr']:8.1f}% /{h['sharpe']:5.2f} /{100*h['maxdd']:4.0f}%"
          f"{y.get(2024,float('nan')):+8.1f}{y.get(2025,float('nan')):+7.1f}{y.get(2026,float('nan')):+7.1f}", flush=True)
    return dict(fit={k: float(f[k]) for k in ("cagr", "sharpe", "maxdd")}, subs=[float(x) for x in sub],
                hold={k: float(h[k]) for k in ("cagr", "sharpe", "maxdd")},
                y2024=y.get(2024), y2025=y.get(2025), y2026=y.get(2026))


if __name__ == "__main__":
    MM.om.MEMBERSHIP["nifty250"] = B.MASTER / "membership/nifty250.csv"      # the core mask the engine reads
    MM.om.MEMBERSHIP["P_n250"] = B.MASTER / "membership/nifty250.csv"
    MM.om.MEMBERSHIP["P_n250_once"] = B.build_once_in("nifty250")
    MM.om.MEMBERSHIP["P_nse500_once"] = B.OUT / "nse500_oncein.csv"

    n250 = load_membership(B.MASTER / "membership/nifty250.csv")
    once = load_membership(B.OUT / "nifty250_oncein.csv")
    print("dropped-name pool available to the sleeve:")
    for d in ["2016-06-30", "2019-06-30", "2022-06-30", "2025-06-30"]:
        t = pd.Timestamp(d)
        print(f"  {d}: core {len(members_asof(n250, t)):3d}, dropped {len(members_asof(once, t) - members_asof(n250, t)):3d}")

    spec = L.BOOKS["OM25 v4"]
    print(f"\n{'':28}{'FIT 2016-2023':>22}{'subs':>11}   {'HOLD-OUT 2024->':>26}{'2024':>7}{'2025':>7}{'2026':>7}")
    print("-" * 118)
    out = {}
    cfg, _ = MM.run_candidate(universe="P_n250", start=spec["start"], end=None, **spec["cfg"])
    out["shipped"] = show("shipped OM25 v4  [the bar]", W.equity(MM.RUNS / MM.cfg_id(cfg)))
    for k in (4, 5, 6):
        cfg, _ = MM.run_candidate(universe="P_n250_once", start=spec["start"], end=None,
                                  **{**spec["cfg"], "satellite_slots": k})
        out[f"sat{k}"] = show(f"core 250 + {k} dropped ({100*k//25}%)", W.equity(MM.RUNS / MM.cfg_id(cfg)))
        W.register(cfg, MM.cfg_id(cfg), W.stats(W.equity(MM.RUNS / MM.cfg_id(cfg)), "2006-01-01", "2015-12-31"), "sat")
    cfg, _ = MM.run_candidate(universe="P_n250_once", start=spec["start"], end=None, **spec["cfg"])
    out["n250 once-in uncapped"] = show("nifty250 once-in, UNCAPPED", W.equity(MM.RUNS / MM.cfg_id(cfg)))
    cfg, _ = MM.run_candidate(universe="P_nse500_once", start=spec["start"], end=None, **spec["cfg"])
    out["nse500 once-in"] = show("nse500 once-in (Phase 7)", W.equity(MM.RUNS / MM.cfg_id(cfg)))
    json.dump(out, open(TASK / "report/satellite_summary.json", "w"), indent=1)
