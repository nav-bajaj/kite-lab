"""Founder spec 2026-09-09 - S2 variant E.

Changes from D_blend:
  score        relative strength + un-extension only (0.5 / 0.5)
  gate         stage-age minimum REMOVED (structure + RS only)
  book         20 names
  sector cap   removed
  weighting    drift after entry, no trim back to 7.5%
  exit         gate failure or leaving the top (20 + 10) - no stop
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
from lib.panels import MEMBERSHIP_PROD, MEMBERSHIP_RECON
from lib.compare import run_signal, build_signals
from lib.stage2 import make_s2_score, VARIANTS
from lib.sweep2 import concentration
from lib.final import exposure_profile

IS = ("2009-09-01", "2016-12-31")
OOS = ("2017-01-01", None)

# the founder's config
E = dict(variant="E_rs_unext", top_n=20, exit_buffer=10, stop=0.0,
         weight_mode="drift", sector_cap=0)


def main():
    rows = []
    for basis, mcsv in (("snapshot", MEMBERSHIP_PROD),
                        ("survivorship_free", MEMBERSHIP_RECON)):
        # stage-age minimum removed from the gate
        ctx = build_context(membership_csv=mcsv, min_stage_age=0)
        bench, close, sm = ctx["benchmark"], ctx["prices"]["close"], ctx["sector_map"]
        print(f"\n=== {basis} (n={ctx['prices']['n_symbols']}) ===")
        print("  window  CAGR      DD     Sharpe Calmar  alpha    trades/y  "
              "medHold  win%   peakName peakSector  invested%")
        for win, (s, e) in (("IS", IS), ("OOS", OOS)):
            res = run_one(ctx, start=s, end=e, **E)
            m = metrics(res, benchmark=bench)
            m.update(basis=basis, window=win, **E)
            m.update(concentration(res, close, sm))
            m.update(exposure_profile(res))
            rows.append(m)
            print(f"  {win:6s} {m['cagr_pct']:6.2f}% {m['max_dd_pct']:7.2f}%  "
                  f"{m['sharpe']:5.2f} {m['calmar']:5.2f} "
                  f"{m.get('alpha_cagr_pp', np.nan):+6.2f}pp {m['buys_per_year']:7.0f}  "
                  f"{m.get('median_hold_days', 0):6d}d {m.get('win_rate_pct', 0):5.1f}%  "
                  f"{m.get('peak_name_wt_pct', 0):6.1f}% {m.get('peak_sector_wt_pct', 0):8.1f}%  "
                  f"{m['mean_invested_pct']:8.1f}%")

    pd.DataFrame(rows).to_csv(HERE.parent / "data" / "variant_e.csv", index=False)
    print(f"\n[wrote] data/variant_e.csv")


if __name__ == "__main__":
    main()
