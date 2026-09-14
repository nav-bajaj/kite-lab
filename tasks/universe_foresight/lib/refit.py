"""Phase 9 -- refit for the once-in universe with the recent window HELD OUT.

Pre-registered protocol, declared here before any hold-out number is computed:

  FIT      2006-01-01 .. 2023-12-31.  Selection uses ONLY this.
           IS  2006-2015 (reported, not selected on)
           SEL 2016-2023 (the selection window)
  HOLD-OUT 2024-01-01 .. today.  Touched exactly once, after selection, as a test.

  Selection rule, in order:
    1. drop cells with SEL max drawdown worse than -40%            (G4)
    2. drop cells whose 2016-19 or 2020-23 Sharpe is below 0.6     (G3)
    3. among survivors take the highest SEL Sharpe
    4. report the neighbourhood of the winner -- a spike is overfitting,
       a plateau is a finding

BOTH universes get the same grid. Refitting the wide universe and comparing it
to an untuned narrow book is the unfair comparison that has already bitten this
folder twice; the narrow book gets the same number of shots.
"""
from __future__ import annotations

import itertools, json, sys
from pathlib import Path

import numpy as np
import pandas as pd

TASK = Path(__file__).resolve().parent.parent
sys.path.insert(0, "/Users/navdeep/kite-lab/tasks/mm_rebuild/lib")
sys.path.insert(0, str(TASK / "lib"))
import run as MM, windows as W, buckets as B, run_ladder as L  # noqa: E402

MM.RUNS = TASK / "runs"; W.REG = TASK / "runs/registry.csv"; B.OUT = TASK / "runs/membership"
FIT_END, HOLD_START = "2023-12-31", "2024-01-01"
SEL = ("2016-01-01", FIT_END)
G3W = [("2016-01-01", "2019-12-31"), ("2020-01-01", FIT_END)]
BASE = dict(kind="mix", skip=21, lookback=252, min_obs=220, cadence="monthly", exit_cadence="same",
            stop_check="monthly", fill_from_buffer=True, trailing_stop=0.2, sizing="invvol", max_weight=0.10,
            iv_window=63, dyn_n_bear=15, dyn_mode="hold", bear_buffer=20, regime_kind="roc", roc_n=31, confirm=3)
GRID = list(itertools.product([0.3, 0.4, 0.5, 0.6, 0.7], [20, 25, 30], [10, 20], [0, 5]))
UNIS = {"nifty250": "P_n250", "once-in": "P_once"}


def cell_cfg(c):
    mix_w, top_n, buf, cap = c
    return dict(BASE, mix_w=mix_w, top_n=top_n, exit_buffer=buf, sector_cap=cap)


def evaluate(uni_key, c):
    cfg, _ = MM.run_candidate(universe=uni_key, start="2006-02-01", end=None, **cell_cfg(c))
    eq = W.equity(MM.RUNS / MM.cfg_id(cfg))
    s = W.stats(eq, *SEL)
    return dict(cfg_id=MM.cfg_id(cfg), sel_cagr=s["cagr"], sel_sharpe=s["sharpe"], sel_dd=s["maxdd"],
                subs=[W.stats(eq, a, z)["sharpe"] for a, z in G3W],
                is_sharpe=W.stats(eq, "2006-01-01", "2015-12-31")["sharpe"]), eq


if __name__ == "__main__":
    MM.om.MEMBERSHIP["P_n250"] = B.MASTER / "membership/nifty250.csv"
    MM.om.MEMBERSHIP["P_once"] = B.OUT / "nse500_oncein.csv"
    res, eqs = {}, {}
    for uname, ukey in UNIS.items():
        rows = []
        for i, c in enumerate(GRID, 1):
            r, eq = evaluate(ukey, c)
            r.update(dict(mix_w=c[0], top_n=c[1], buffer=c[2], sector_cap=c[3]))
            rows.append(r); eqs[(uname, c)] = eq
            if i % 15 == 0: print(f"  {uname}: {i}/{len(GRID)}", flush=True)
        res[uname] = pd.DataFrame(rows)
    picks = {}
    print(f"\n{'='*92}\nSELECTION -- fit window only (2016-{FIT_END[:4]}), hold-out untouched\n{'='*92}")
    for uname, df in res.items():
        ok = df[(df.sel_dd >= -0.40) & (df.subs.apply(lambda s: min(s) >= 0.6))]
        print(f"\n{uname}: {len(ok)} of {len(df)} cells survive G3+G4")
        if not len(ok):
            print("  none survive"); continue
        w = ok.loc[ok.sel_sharpe.idxmax()]
        picks[uname] = w
        print(f"  WINNER  mix_w {w.mix_w}  top_n {int(w.top_n)}  buffer {int(w.buffer)}  sector_cap {int(w.sector_cap)}"
              f"   SEL {100*w.sel_cagr:.1f}% / {w.sel_sharpe:.2f} / {100*w.sel_dd:.0f}%  subs {'/'.join(f'{x:.2f}' for x in w.subs)}")
        print(f"  grid SEL Sharpe: median {df.sel_sharpe.median():.2f}, p90 {df.sel_sharpe.quantile(.9):.2f}, max {df.sel_sharpe.max():.2f}")
        nb = ok[(ok.top_n == w.top_n) & (ok.buffer == w.buffer) & (ok.sector_cap == w.sector_cap)].sort_values("mix_w")
        print(f"  mix_w neighbourhood at the winner's other settings: "
              + ", ".join(f"{r.mix_w}:{r.sel_sharpe:.2f}" for r in nb.itertuples()))
    json.dump({u: d.assign(subs=d.subs.apply(list)).to_dict("records") for u, d in res.items()},
              open(TASK / "report/refit_grid.json", "w"), indent=1, default=float)
    json.dump({u: {k: (v.item() if hasattr(v, "item") else v) for k, v in p.items() if k != "subs"}
               for u, p in picks.items()}, open(TASK / "report/refit_picks.json", "w"), indent=1)
    print("\nselection complete and written. hold-out NOT evaluated in this run.")
