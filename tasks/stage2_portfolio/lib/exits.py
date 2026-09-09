"""Does S2 cut its winners short?

Median hold on the baseline is 21 days, which is not a stage-2 holding period.
The exit fires when a name leaves the top (top_n + exit_buffer) of the ranking.
Widening exit_buffer moves the book toward the pure Weinstein exit: hold until
the stage-2 gate itself fails (a name that fails the gate stops being scored,
so it leaves the ranking entirely and is sold whatever the buffer).

exit_buffer 400 ~= gate-only exit, since the gate rarely passes that many names.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parents[2]))

from lib.run_s2 import build_context, run_one, metrics

IS = ("2009-09-01", "2016-12-31")
OOS = ("2017-01-01", None)


def main():
    ctx = build_context()
    bench = ctx["benchmark"]
    rows = []
    print("--- exit discipline (C_nofresh, top22, cap4, trim, no stop) ---")
    print("    buffer  minhold  win   CAGR      DD    Sharpe  Calmar  medHold  >50%  >100%  trades/y")
    for eb in [10, 20, 40, 100, 400]:
        for mh in [0, 30]:
            for win, (s, e) in (("IS", IS), ("OOS", OOS)):
                res = run_one(ctx, variant="C_nofresh", top_n=22,
                              exit_buffer=eb, stop=0.0, weight_mode="trim",
                              sector_cap=4, min_hold_days=mh, start=s, end=e)
                m = metrics(res, benchmark=bench)
                ex = res["exits"].dropna(subset=["pnl_pct"])
                gt50 = round((ex["pnl_pct"] > 0.5).mean() * 100, 2) if len(ex) else 0
                m.update(variant="C_nofresh", exit_buffer=eb, min_hold_days=mh,
                         window=win, pct_gt_50=gt50)
                rows.append(m)
                print(f"    {eb:6d}  {mh:7d}  {win:3s}  {m['cagr_pct']:6.2f}%  "
                      f"{m['max_dd_pct']:7.2f}%  {m['sharpe']:5.2f}  "
                      f"{m['calmar']:5.2f}  {m.get('median_hold_days',0):6d}d  "
                      f"{gt50:5.2f}% {m.get('pct_gt_100',0):5.2f}%  "
                      f"{m['buys_per_year']:6.0f}")
    pd.DataFrame(rows).to_csv(HERE.parent / "data" / "exit_ladder.csv",
                              index=False)
    print(f"\n[wrote] data/exit_ladder.csv ({len(rows)} rows)")


if __name__ == "__main__":
    main()
