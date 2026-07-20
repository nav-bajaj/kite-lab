"""Phase 1 — E1 robustness. Is lambda=1.0 a knife-edge?

Two sweeps, both judged on OOS (never IS):
  1. lambda surface: DIV vs L6 CAGR/Calmar delta across a fine lambda grid
     for every OOS window. A real effect shows a contiguous PLATEAU of
     positive deltas; a knife-edge shows one spiky lambda that works while
     neighbours hurt.
  2. crowd-window sensitivity: lambda=1.0 with the residual correlation
     window at 42 / 63 / 126 days, to confirm 63 wasn't cherry-picked.

Run:  python tasks/raam_transplant/e1_robustness.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from scripts.backtest_momentum import load_price_panels, load_benchmark  # noqa: E402
from scripts.build_om25_signals import load_universe  # noqa: E402
from scripts._momentum_engine import (  # noqa: E402
    BASELINE as L6, build_momentum_panels, make_momentum_score,
    lookback_months_to_days,
)
from residuals import build_residual_panel  # noqa: E402
from e1_l6div import (  # noqa: E402
    make_l6div_score, _run_with_score, metrics, load_index_close,
    NSE500_UNIVERSE_CSV, NIFTY100_INDEX, OOS_WINDOWS, IS_WINDOW,
)

LAMBDA_GRID = [0.0, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0]
CROWD_WINDOWS = [42, 63, 126]


def main():
    ts = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
    out_dir = ROOT / "tasks/raam_transplant/runs" / f"e1_robust_{ts}"
    out_dir.mkdir(parents=True, exist_ok=True)

    print("[load] panels + residual panel")
    close_panel, trade_panel = load_price_panels(ROOT / "nse500_data_merged")
    calendar = close_panel.index
    benchmark = load_benchmark(ROOT / "data/benchmarks/nifty100.csv").reindex(calendar).ffill()
    sma_200 = close_panel.rolling(200, min_periods=200).mean()
    atr_20 = close_panel.pct_change().rolling(20).std()
    nse500 = load_universe(ROOT / NSE500_UNIVERSE_CSV)
    cols = [s for s in close_panel.columns if s in nse500]
    nifty100 = load_index_close(ROOT / NIFTY100_INDEX).reindex(calendar).ffill()
    lookback = lookback_months_to_days(L6["lookback_months"])
    l6_panels = build_momentum_panels(close_panel[cols], lookback_days=lookback,
                                      skip_days=L6["skip_days"])
    l6_score = make_momentum_score(l6_panels, vol_floor=L6["vol_floor"],
                                   vol_power=L6["vol_power"],
                                   cross_sectional_zscore=L6["cross_sectional_zscore"])
    resid63 = build_residual_panel(close_panel[cols], nifty100)["residual"]

    windows = [IS_WINDOW + ("IS",)] if False else [(s, e, n) for (n, s, e) in OOS_WINDOWS]

    def run(sfn, s, e):
        r = _run_with_score(sfn, close_panel[cols], trade_panel[cols], calendar,
                            benchmark, l6_panels, sma_200, atr_20, s, e, dict(L6))
        return metrics(r, s, e) if r else {"error": "none"}

    # ---- baseline (lambda=0) per window ----
    l6_sfn = make_l6div_score(l6_score, resid63, 0.0)
    base = {n: run(l6_sfn, s, e) for (s, e, n) in windows}

    # ---- 1. lambda surface ----
    print("\n[sweep] lambda surface (OOS)")
    surf_rows = []
    for lam in LAMBDA_GRID:
        sfn = make_l6div_score(l6_score, resid63, lam)
        row = {"lambda": lam}
        cagr_deltas, calmar_wins, cagr_wins = [], 0, 0
        for (s, e, n) in windows:
            m = run(sfn, s, e)
            dcagr = round(m["cagr_pct"] - base[n]["cagr_pct"], 2)
            dcalm = round((m["calmar"] or 0) - (base[n]["calmar"] or 0), 3)
            row[f"{n}_dCAGR"] = dcagr
            row[f"{n}_dCalmar"] = dcalm
            if n != "ERA-2021plus":
                cagr_deltas.append(dcagr)
                calmar_wins += int((m["calmar"] or 0) > (base[n]["calmar"] or 0))
                cagr_wins += int(dcagr > 0)
        row["OOS3_mean_dCAGR"] = round(float(np.mean(cagr_deltas)), 2)
        row["OOS3_calmar_wins"] = calmar_wins
        row["OOS3_cagr_wins"] = cagr_wins
        surf_rows.append(row)
        print(f"  lambda={lam:>4}: meanΔCAGR={row['OOS3_mean_dCAGR']:+5}  "
              f"calmar_wins={calmar_wins}/3  cagr_wins={cagr_wins}/3")
    surf = pd.DataFrame(surf_rows)
    surf.to_csv(out_dir / "lambda_surface.csv", index=False)

    # ---- 2. crowd-window sensitivity at lambda=1.0 ----
    print("\n[sweep] crowd-window sensitivity (lambda=1.0)")
    cw_rows = []
    for cw in CROWD_WINDOWS:
        resid = build_residual_panel(close_panel[cols], nifty100)["residual"]
        sfn = make_l6div_score(l6_score, resid, 1.0, crowd_window=cw)
        row = {"crowd_window": cw}
        cagr_deltas, calmar_wins = [], 0
        for (s, e, n) in windows:
            if n == "ERA-2021plus":
                continue
            m = run(sfn, s, e)
            row[f"{n}_dCAGR"] = round(m["cagr_pct"] - base[n]["cagr_pct"], 2)
            cagr_deltas.append(row[f"{n}_dCAGR"])
            calmar_wins += int((m["calmar"] or 0) > (base[n]["calmar"] or 0))
        row["OOS3_mean_dCAGR"] = round(float(np.mean(cagr_deltas)), 2)
        row["OOS3_calmar_wins"] = calmar_wins
        cw_rows.append(row)
        print(f"  crowd_window={cw:>4}: meanΔCAGR={row['OOS3_mean_dCAGR']:+5}  "
              f"calmar_wins={calmar_wins}/3")
    cw = pd.DataFrame(cw_rows)
    cw.to_csv(out_dir / "crowd_window_sensitivity.csv", index=False)

    # ---- verdict heuristic ----
    pos_band = surf[(surf["lambda"] > 0) & (surf["OOS3_mean_dCAGR"] > 0)
                    & (surf["OOS3_calmar_wins"] >= 2)]
    verdict = {
        "lambdas_tested": LAMBDA_GRID,
        "robust_band": [float(x) for x in pos_band["lambda"].tolist()],
        "is_plateau": len(pos_band) >= 3,   # >=3 contiguous-ish good lambdas
        "crowd_window_all_positive": bool((cw["OOS3_mean_dCAGR"] > 0).all()),
    }
    (out_dir / "verdict.json").write_text(json.dumps(
        {"verdict": verdict, "surface": surf_rows, "crowd_window": cw_rows}, indent=2, default=str))

    pd.set_option("display.width", 200, "display.max_columns", 30)
    print("\n" + "=" * 72)
    print("E1 ROBUSTNESS")
    print("=" * 72)
    print("\nLambda surface (Δ vs L6, OOS):")
    show = ["lambda", "OOS-A_dCAGR", "OOS-B_dCAGR", "OOS-C_dCAGR",
            "OOS3_mean_dCAGR", "OOS3_calmar_wins", "OOS3_cagr_wins"]
    print(surf[[c for c in show if c in surf.columns]].to_string(index=False))
    print("\nCrowd-window sensitivity (lambda=1.0):")
    print(cw.to_string(index=False))
    print("\nVerdict:", json.dumps(verdict, indent=2))
    print(f"\nwrote {out_dir}")


if __name__ == "__main__":
    main()
