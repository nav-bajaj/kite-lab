"""§4 walk-forward — is the exit ladder choosable without hindsight?

The grid's best cell is chosen knowing all 21 years. A trader in 2014 did not
have that. This picks the exit using only data available at the time, applies
it to the following year, and chains the result. A ladder that only works when
chosen with hindsight does not count (TASKS.md §4).
"""
from __future__ import annotations

import itertools
import os
import sys
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from exits import load_panel, run_config  # noqa: E402

REPO = "/Users/navdeep/kite-lab"
TASK = f"{REPO}/tasks/breakout_calls_2026"
MIN_TRAIN_YEARS = 5
MIN_TRAIN_TRADES = 100

GRID = dict(
    stop_mode=["fixed", "structure"],
    stop_pct=[0.06, 0.08, 0.10],
    trail=["ma50", "ma150", "chandelier"],      # 'none' is not a tradeable rule
    partial_r=[None, 2.0, 3.0],
    timestop=[None, 40],
)


def label(c):
    return f"{c['trail']}|{c['stop_mode']}|{c['stop_pct']}|{c['partial_r']}|{c['timestop']}"


def main():
    os.chdir(REPO)
    tape = pd.read_csv(f"{TASK}/data/signals_standard_no_l6.csv")
    tape = tape[tape.kind == "E1"]
    panels = {}
    for s in sorted(tape.symbol.unique()):
        p = load_panel(s)
        if p is not None:
            panels[s] = p

    keys = list(GRID)
    combos = [dict(zip(keys, v)) for v in itertools.product(*GRID.values())]
    print(f"{len(combos)} tradeable configs x {len(tape):,} signals", flush=True)

    per = {}
    for i, cfg in enumerate(combos, 1):
        d = run_config(tape, panels, dict(cfg, atr_mult=3.0))
        per[label(cfg)] = d[["year", "r"]]
        if i % 20 == 0:
            print(f"  {i}/{len(combos)}", flush=True)

    long = pd.concat([d.assign(cfg=k) for k, d in per.items()], ignore_index=True)
    long.to_parquet(f"{TASK}/data/exit_walkforward_trades.parquet", index=False)

    years = sorted(long.year.unique())
    start = years[0] + MIN_TRAIN_YEARS
    rows = []
    for y in [y for y in years if y >= start]:
        train = long[long.year < y]
        if train.groupby("cfg").size().min() < MIN_TRAIN_TRADES:
            continue
        pick = train.groupby("cfg").r.mean().idxmax()
        test = long[(long.year == y) & (long.cfg == pick)]
        if not len(test):
            continue
        rows.append(dict(year=y, chosen=pick, n=len(test), oos_meanR=test.r.mean(),
                         train_meanR=train[train.cfg == pick].r.mean()))
    wf = pd.DataFrame(rows)
    wf.to_csv(f"{TASK}/data/exit_walkforward.csv", index=False)

    # the hindsight benchmark: the single best cell chosen knowing everything
    best = long.groupby("cfg").r.mean().idxmax()
    best_oos = long[(long.cfg == best) & (long.year >= start)].r.mean()
    grid_med = long.groupby("cfg").r.mean().median()

    print("\n=== walk-forward: exit chosen on the past, applied to the next year ===")
    print(wf.round(3).to_string(index=False))
    tot_n = wf.n.sum()
    wf_mean = (wf.oos_meanR * wf.n).sum() / tot_n
    print(f"\n  walk-forward mean R (trade-weighted, {tot_n:,} trades) : {wf_mean:.3f}R")
    print(f"  same window, best cell chosen WITH hindsight         : {best_oos:.3f}R  [{best}]")
    print(f"  grid median across all {long.cfg.nunique()} cells                     : {grid_med:.3f}R")
    print(f"  §3 reference exit                                    : 0.467R")
    print(f"\n  configs ever chosen: {wf.chosen.nunique()} -> {wf.chosen.value_counts().to_dict()}")


if __name__ == "__main__":
    main()
