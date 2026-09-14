"""Phase 10 -- "NSE 500 plus demotions for 12 months only", held out (founder).

Same pre-registered protocol as Phase 9: fit 2006-2023, select on 2016-2023
Sharpe after G3/G4, score 2024-> exactly once. Shipped rules AND a refit, so the
universe gets tested both as a drop-in and as something tuned for.

Phase 9's calibration travels with this: refitting nifty250 -- a book with an
1,800-trial pedigree -- produced a cell that BEAT shipped on the fit window
(1.29 vs 1.21) and LOST on the hold-out (0.97 vs 1.21). Any fit-window win here
has to be read against that.
"""
from __future__ import annotations

import json, sys
from pathlib import Path

import pandas as pd

TASK = Path(__file__).resolve().parent.parent
sys.path.insert(0, "/Users/navdeep/kite-lab/tasks/mm_rebuild/lib")
sys.path.insert(0, str(TASK / "lib"))
import run as MM, windows as W, buckets as B, run_ladder as L, refit as R  # noqa: E402

MM.RUNS = TASK / "runs"; W.REG = TASK / "runs/registry.csv"; B.OUT = TASK / "runs/membership"
HOLD = ("2024-01-01", "2099-12-31")
UNI = "P_decay12"


def yearly(eq):
    out = {}
    for y, g in eq.groupby(eq.index.year):
        prev = eq[eq.index < f"{y}-01-01"]
        out[y] = 100 * (g.iloc[-1] / (prev.iloc[-1] if len(prev) else g.iloc[0]) - 1)
    return out


def show(label, eq):
    s = W.stats(eq, *R.SEL); h = W.stats(eq, *HOLD); y = yearly(eq)
    print(f"{label:<38}{100*s['cagr']:8.1f}% /{s['sharpe']:5.2f}   |{100*h['cagr']:9.1f}% /{h['sharpe']:5.2f} /{100*h['maxdd']:4.0f}%"
          f"   {y.get(2024, float('nan')):+7.1f}{y.get(2025, float('nan')):+7.1f}{y.get(2026, float('nan')):+7.1f}", flush=True)
    return dict(fit={k: float(s[k]) for k in ("cagr", "sharpe", "maxdd")},
                hold={k: float(h[k]) for k in ("cagr", "sharpe", "maxdd")},
                y2024=y.get(2024), y2025=y.get(2025), y2026=y.get(2026))


if __name__ == "__main__":
    MM.om.MEMBERSHIP["P_n250"] = B.MASTER / "membership/nifty250.csv"
    MM.om.MEMBERSHIP["P_once"] = B.OUT / "nse500_oncein.csv"
    MM.om.MEMBERSHIP[UNI] = B.build_decay("nse500", 12)
    spec = L.BOOKS["OM25 v4"]

    rows = []
    for i, c in enumerate(R.GRID, 1):
        r, _ = R.evaluate(UNI, c)
        r.update(dict(mix_w=c[0], top_n=c[1], buffer=c[2], sector_cap=c[3], cell=c))
        rows.append(r)
        if i % 20 == 0: print(f"  grid {i}/{len(R.GRID)}", flush=True)
    df = pd.DataFrame(rows)
    ok = df[(df.sel_dd >= -0.40) & (df.subs.apply(lambda s: min(s) >= 0.6))]
    print(f"\n{'='*104}\nSELECTION on the fit window only (2016-2023)\n{'='*104}")
    print(f"decay12: {len(ok)} of {len(df)} cells survive G3+G4 | grid SEL Sharpe median {df.sel_sharpe.median():.2f}, max {df.sel_sharpe.max():.2f}")
    w = ok.loc[ok.sel_sharpe.idxmax()]
    print(f"  WINNER  mix_w {w.mix_w}  top_n {int(w.top_n)}  buffer {int(w.buffer)}  sector_cap {int(w.sector_cap)}"
          f"   SEL {100*w.sel_cagr:.1f}% / {w.sel_sharpe:.2f} / {100*w.sel_dd:.0f}%")
    nb = ok[(ok.top_n == w.top_n) & (ok.buffer == w.buffer) & (ok.sector_cap == w.sector_cap)].sort_values("mix_w")
    print(f"  mix_w neighbourhood: " + ", ".join(f"{r.mix_w}:{r.sel_sharpe:.2f}" for r in nb.itertuples()))

    print(f"\n{'='*104}\nHOLD-OUT 2024-> (scored once, after the above)\n{'='*104}")
    print(f"{'':38}{'FIT 2016-2023':>20}   {'HOLD-OUT 2024->':>28}   {'2024':>6}{'2025':>7}{'2026':>7}")
    out = {}
    cfg, _ = MM.run_candidate(universe="P_n250", start=spec["start"], end=None, **spec["cfg"])
    out["shipped OM25 v4 (nifty250)"] = show("shipped OM25 v4 (nifty250)  [the bar]", W.equity(MM.RUNS / MM.cfg_id(cfg)))
    cfg, _ = MM.run_candidate(universe="P_once", start=spec["start"], end=None, **spec["cfg"])
    out["shipped rules on once-in"] = show("shipped rules on once-in (no expiry)", W.equity(MM.RUNS / MM.cfg_id(cfg)))
    cfg, _ = MM.run_candidate(universe=UNI, start=spec["start"], end=None, **spec["cfg"])
    out["shipped rules on decay12"] = show("shipped rules on decay12", W.equity(MM.RUNS / MM.cfg_id(cfg)))
    cell = (w.mix_w, int(w.top_n), int(w.buffer), int(w.sector_cap))
    cfg, _ = MM.run_candidate(universe=UNI, start="2006-02-01", end=None, **R.cell_cfg(cell))
    out["REFIT decay12"] = show(f"REFIT decay12 mix{cell[0]}/n{cell[1]}/b{cell[2]}/s{cell[3]}", W.equity(MM.RUNS / MM.cfg_id(cfg)))
    json.dump(dict(winner=[float(cell[0])] + [int(x) for x in cell[1:]], results=out,
                   grid=df.assign(subs=df.subs.apply(list), cell=df.cell.apply(list)).to_dict("records")),
              open(TASK / "report/decay12_summary.json", "w"), indent=1, default=float)
