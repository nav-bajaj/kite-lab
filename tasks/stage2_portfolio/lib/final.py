"""Final S2 checks: stop ladder, size sensitivity, exposure profile, overlap.

The variant is chosen on the IS window only (C_nofresh has the best IS Sharpe
and Calmar). D_blend is carried alongside and labelled for what it is: an
OOS-selected config, reported but not claimed.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.path.insert(0, str(HERE.parents[2]))

from lib.run_s2 import build_context, run_one, metrics

IS = ("2009-09-01", "2016-12-31")
OOS = ("2017-01-01", None)


def exposure_profile(res):
    eq = res["equity"].copy()
    eq["date"] = pd.to_datetime(eq["date"])
    eq = eq.set_index("date")
    inv = 1.0 - eq["cash_pct"]
    return {
        "mean_invested_pct": round(float(inv.mean()) * 100, 1),
        "pct_days_under_50_invested": round(float((inv < 0.5).mean()) * 100, 1),
        "mean_holdings": round(float(eq["holdings"].mean()), 1),
        "pct_days_full_book": round(float((eq["holdings"] >= 22).mean()) * 100, 1),
    }


def main():
    ctx = build_context()
    bench = ctx["benchmark"]
    rows = []

    print("--- stop ladder (sector cap 4, trim, top 22) ---")
    for variant in ["C_nofresh", "D_blend"]:
        for stop in [0.0, 0.20, 0.25]:
            for win, (s, e) in (("IS", IS), ("OOS", OOS)):
                res = run_one(ctx, variant=variant, top_n=22, exit_buffer=10,
                              stop=stop, weight_mode="trim", sector_cap=4,
                              start=s, end=e)
                m = metrics(res, benchmark=bench)
                m.update(variant=variant, stop=stop, window=win, top_n=22,
                         test="stop_ladder", **exposure_profile(res))
                rows.append(m)
                print(f"  {variant:10s} stop={stop:.2f} {win:3s}  "
                      f"CAGR {m['cagr_pct']:6.2f}%  DD {m['max_dd_pct']:7.2f}%  "
                      f"Sh {m['sharpe']:.2f}  Cal {m['calmar']:.2f}  "
                      f">100% trades {m.get('pct_gt_100', 0):.1f}%")

    print("\n--- size sensitivity (no stop, cap 4) ---")
    for variant in ["C_nofresh", "D_blend"]:
        for top_n in [20, 22, 25]:
            for win, (s, e) in (("IS", IS), ("OOS", OOS)):
                res = run_one(ctx, variant=variant, top_n=top_n, exit_buffer=10,
                              stop=0.0, weight_mode="trim", sector_cap=4,
                              start=s, end=e)
                m = metrics(res, benchmark=bench)
                m.update(variant=variant, stop=0.0, window=win, top_n=top_n,
                         test="size", **exposure_profile(res))
                rows.append(m)
                print(f"  {variant:10s} top{top_n} {win:3s}  "
                      f"CAGR {m['cagr_pct']:6.2f}%  DD {m['max_dd_pct']:7.2f}%  "
                      f"Sh {m['sharpe']:.2f}  Cal {m['calmar']:.2f}")

    print("\n--- sector cap sensitivity (C_nofresh, no stop) ---")
    for cap in [0, 3, 4, 6]:
        for win, (s, e) in (("IS", IS), ("OOS", OOS)):
            res = run_one(ctx, variant="C_nofresh", top_n=22, exit_buffer=10,
                          stop=0.0, weight_mode="trim", sector_cap=cap,
                          start=s, end=e)
            m = metrics(res, benchmark=bench)
            m.update(variant="C_nofresh", stop=0.0, window=win, top_n=22,
                     sector_cap=cap, test="sector_cap", **exposure_profile(res))
            rows.append(m)
            print(f"  cap={cap} {win:3s}  CAGR {m['cagr_pct']:6.2f}%  "
                  f"DD {m['max_dd_pct']:7.2f}%  Sh {m['sharpe']:.2f}  "
                  f"Cal {m['calmar']:.2f}")

    df = pd.DataFrame(rows)
    df.to_csv(HERE.parent / "data" / "final_checks.csv", index=False)

    print("\n--- exposure profile, IS-selected config (C_nofresh, OOS) ---")
    res = run_one(ctx, variant="C_nofresh", top_n=22, exit_buffer=10, stop=0.0,
                  weight_mode="trim", sector_cap=4, start=OOS[0])
    ep = exposure_profile(res)
    for k, v in ep.items():
        print(f"  {k:28s} {v}")
    m = metrics(res, benchmark=bench)
    print(f"  exit mix: {m.get('exit_mix')}")
    print(f"  win rate {m.get('win_rate_pct')}%  avg win {m.get('avg_win_pct')}%  "
          f"avg loss {m.get('avg_loss_pct')}%  median hold {m.get('median_hold_days')}d")
    print(f"  trades >+100%: {m.get('pct_gt_100')}%")

    print(f"\n[wrote] data/final_checks.csv ({len(df)} rows)")


if __name__ == "__main__":
    main()
