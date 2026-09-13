"""§4 runner — sweep the exit grid on the E1 tape, report the grid median."""
from __future__ import annotations

import itertools
import os
import sys
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from exits import load_panel, run_config  # noqa: E402

REPO = "/Users/navdeep/kite-lab"
TASK = f"{REPO}/tasks/breakout_calls_2026"

GRID = dict(
    stop_mode=["fixed", "structure"],
    stop_pct=[0.06, 0.08, 0.10],
    trail=["ma50", "ma150", "chandelier", "none"],
    partial_r=[None, 2.0, 3.0],
    timestop=[None, 40],
)
ATR_MULT = 3.0


def main():
    os.chdir(REPO)
    tape = pd.read_csv(f"{TASK}/data/signals_standard_no_l6.csv")
    tape = tape[tape.kind == "E1"]
    syms = sorted(tape.symbol.unique())
    print(f"loading {len(syms)} panels", flush=True)
    panels = {}
    for s in syms:
        p = load_panel(s)
        if p is not None:
            panels[s] = p

    keys = list(GRID)
    combos = [dict(zip(keys, v)) for v in itertools.product(*GRID.values())]
    # a "none" trail with no time stop and no partial is a pure stop-and-hold;
    # keep it, it is the honest control
    print(f"{len(combos)} configurations on {len(tape):,} E1 signals", flush=True)

    rows = []
    for i, cfg in enumerate(combos, 1):
        cfg = dict(cfg, atr_mult=ATR_MULT)
        d = run_config(tape, panels, cfg)
        if not len(d):
            continue
        rows.append(dict(
            stop_mode=cfg["stop_mode"], stop_pct=cfg["stop_pct"], trail=cfg["trail"],
            partial_r=cfg["partial_r"], timestop=cfg["timestop"],
            n=len(d), meanR=d.r.mean(), medR=d.r.median(),
            win=(d.ret > 0).mean(), meanRet=d.ret.mean(), hold=d.hold.median(),
            era1=d[d.year <= 2012].r.mean(), era2=d[(d.year > 2012) & (d.year <= 2019)].r.mean(),
            era3=d[d.year > 2019].r.mean(),
        ))
        if i % 20 == 0:
            print(f"  {i}/{len(combos)}", flush=True)

    g = pd.DataFrame(rows).sort_values("meanR", ascending=False)
    g.to_csv(f"{TASK}/data/exit_grid.csv", index=False)
    print(f"\nwrote {len(g)} cells -> data/exit_grid.csv")
    print(f"\nGRID MEDIAN meanR : {g.meanR.median():.3f}R   (this is the headline)")
    print(f"grid best   meanR : {g.meanR.max():.3f}R   (a selection artifact)")
    print(f"grid worst  meanR : {g.meanR.min():.3f}R")
    print("§3 reference exit : 0.467R\n")
    print("top 12 cells:")
    print(g.head(12).round(3).to_string(index=False))
    print("\nmedian meanR by axis:")
    for ax in ["trail", "stop_mode", "stop_pct", "partial_r", "timestop"]:
        print(f"  {ax}:")
        print(g.groupby(ax, dropna=False).meanR.agg(["median", "max", "size"]).round(3).to_string())


if __name__ == "__main__":
    main()
