"""The foresight ladder: each book run on b0..b3, one rung of hindsight at a time.

Runs go to tasks/universe_foresight/runs so the mm_rebuild trial registry -- which
deflates that search's Sharpe -- is not polluted. These are fixed-rule diagnostics,
not candidates, so nothing is registered.
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

MM.RUNS = TASK / "runs"; MM.RUNS.mkdir(parents=True, exist_ok=True)
(TASK / "report").mkdir(exist_ok=True)

RUNGS = ["b0", "b1", "b1f", "b2", "b3", "b4"]
BREADTH = {"nifty250": 250, "nse500": 500}   # b4 is breadth-matched to the index it replaces
LABEL = {"b0": "b0 honest (point-in-time)", "b1": "b1 + immortality", "b1f": "b1f + blow-up avoidance only",
         "b2": "b2 + early access", "b3": "b3 backdated list (the legacy bug)",
         "b4": "b4 PIT turnover screen (no foresight)"}
BOOKS = {
    "MM": dict(base="nifty250", start="2006-02-01", cfg=dict(
        kind="voladj", skip=21, lookback=252, min_obs=219, top_n=25, exit_buffer=20, fill_from_buffer=True,
        cadence="monthly", exit_cadence="same", stop_check="monthly", trailing_stop=0.2, sizing="invvol",
        max_weight=0.10, iv_window=63, sector_cap=5, dyn_n_bear=15, dyn_mode="hold", bear_buffer=20,
        regime_kind="roc", roc_n=31, confirm=3)),
    "OM25 v4": dict(base="nifty250", start="2006-02-01", cfg=dict(
        kind="mix", mix_w=0.5, skip=21, lookback=252, min_obs=220, top_n=25, exit_buffer=20, fill_from_buffer=True,
        cadence="monthly", exit_cadence="same", stop_check="monthly", trailing_stop=0.2, sizing="invvol",
        max_weight=0.10, iv_window=63, sector_cap=5, dyn_n_bear=15, dyn_mode="hold", bear_buffer=20,
        regime_kind="roc", roc_n=31, confirm=3)),
    "L6 v2": dict(base="nse500", start="2010-01-01", cfg=dict(
        kind="voladj", lookback=126, min_obs=110, skip=0, top_n=24, exit_buffer=0, cadence="weekly_thu",
        exit_cadence="same", max_weight=0.075, min_hold_days=8, trailing_stop=0.0)),
}


def register_universes():
    paths = {}
    for u in sorted({b["base"] for b in BOOKS.values()}):
        built = B.build(u)
        built["b4"] = B.build_liquidity(u, BREADTH[u])
        for tag, p in built.items():
            key = f"{u}_{tag}"
            MM.om.MEMBERSHIP[key] = p
            paths[key] = str(p)
    return paths


def run_book(name: str, spec: dict) -> dict:
    out, end = {}, None
    for rung in RUNGS:
        cfg, _ = MM.run_candidate(universe=f"{spec['base']}_{rung}", start=spec["start"], end=None, **spec["cfg"])
        eq = W.equity(MM.RUNS / MM.cfg_id(cfg)); end = str(eq.index[-1].date())
        is_a = spec["start"][:4] + "-01-01"
        out[rung] = {"IS": W.stats(eq, is_a, "2015-12-31"), "OOS": W.stats(eq, "2016-01-01", "2099-12-31"),
                     "full": W.stats(eq, is_a, "2099-12-31")}
        print(f"  {LABEL[rung]:<32} "
              + " | ".join(f"{w} {100*out[rung][w]['cagr']:5.1f}% / {out[rung][w]['sharpe']:4.2f} / {100*out[rung][w]['maxdd']:4.0f}%"
                           for w in ("IS", "OOS")), flush=True)
    return {"end": end, "rungs": out}


def steps(r: dict, window="OOS") -> dict:
    g = lambda k: 100 * r["rungs"][k][window]["cagr"]
    return {"survivorship (b0->b1)": g("b1") - g("b0"), "  of which blow-ups only (b0->b1f)": g("b1f") - g("b0"),
            "early access (b1->b2)": g("b2") - g("b1"), "list narrowing (b2->b3)": g("b3") - g("b2"),
            "TOTAL hindsight (b0->b3)": g("b3") - g("b0"),
            "-- honest alternative --": float("nan"),
            "PIT turnover universe (b0->b4)": g("b4") - g("b0"),
            "irreducible foresight (b4->b2)": g("b2") - g("b4")}


if __name__ == "__main__":
    paths = register_universes()
    res = {}
    for name, spec in BOOKS.items():
        print(f"\n{name} ({spec['base']}, from {spec['start']})", flush=True)
        res[name] = run_book(name, spec)
        print("  --- OOS CAGR attribution (pp) ---", flush=True)
        for k, v in steps(res[name]).items():
            print(f"  {k:<36}" + ("" if v != v else f" {v:+6.1f}"), flush=True)
    json.dump({"universes": paths, "books": {k: {"end": v["end"], "steps": steps(v),
               "rungs": {r: {w: {m: s[m] for m in ("cagr", "sharpe", "maxdd")} for w, s in d.items()}
                         for r, d in v["rungs"].items()}} for k, v in res.items()}},
              open(TASK / "report/ladder_summary.json", "w"), indent=1, default=float)
    print("\nwrote report/ladder_summary.json", flush=True)
