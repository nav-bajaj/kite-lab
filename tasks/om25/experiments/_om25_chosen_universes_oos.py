"""OM25 chosen config: full OOS multi-window evaluation across 3 universes × 2 cadences.

Same config as _om25_chosen_universes.py but runs on FULL signal dates
(through 2026), then slices the equity into IS / OOS-A / OOS-B / OOS-C /
OOS-full and reports per-window metrics + pass/fail.

Config:
  - 50/50 weights (UC + CR)
  - lookback=252, min_obs=220
  - top_n=25, exit_buffer=20
  - return_filter=ON
  - no ATR stop
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from tasks.om25.experiments._om25_oos_retune import (
    run_config, PRICES_DIR, BENCHMARK,
)
from scripts._clean_engine import (
    fridays, biweekly_fridays, monthly_first_trading_day,
)
from scripts.backtest_momentum import load_price_panels, load_benchmark
from scripts.build_om25_signals import load_universe
from scripts.multi_window_oos_eval import (
    evaluate_all_windows, passes_criteria,
)


CHOSEN = dict(
    w_uc=0.5, w_cr=0.5,
    return_filter=True,
    lookback=252, min_obs=220,
    top_n=25, exit_buffer=20,
    atr_mult=0.0, atr_min_floor=0.0,
)

UNIVERSES = [
    ("NSE_500",   ROOT / "data/static/nse500_universe.csv"),
    ("Nifty_250", ROOT / "data/static/nifty250_universe.csv"),
    ("Nifty_100", ROOT / "data/static/nifty100_universe.csv"),
]
CADENCES = ["monthly", "biweekly"]


def main():
    ts = pd.Timestamp.now().strftime("%Y%m%d%H%M%S")
    out_dir = ROOT / f"experiments/oos_retune/{ts}_om25_universes_oos"
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"[run dir] {out_dir}")

    print(f"\n[load] prices from {PRICES_DIR}")
    close_panel, trade_panel = load_price_panels(PRICES_DIR)
    calendar = close_panel.index
    benchmark = load_benchmark(BENCHMARK)
    benchmark_aligned = benchmark.reindex(calendar).ffill()

    sma_200 = close_panel.rolling(200, min_periods=200).mean()
    atr_20 = close_panel.pct_change().rolling(20).std()

    weekly_fri = fridays(calendar)
    monthly_first = monthly_first_trading_day(calendar)
    biweekly_fri = biweekly_fridays(calendar)
    weekly_filt = weekly_fri[weekly_fri >= close_panel.index[252]]

    summary_rows = []
    all_window_rows = []
    t0 = time.time()

    for univ_name, univ_path in UNIVERSES:
        universe = load_universe(univ_path)
        cols = [c for c in close_panel.columns if c in universe]
        if not cols:
            continue
        returns_uni = close_panel[cols].pct_change()
        print(f"\n[{univ_name}] {len(cols)} symbols")

        for cadence in CADENCES:
            cfg = CHOSEN | dict(cadence=cadence)
            label = f"{univ_name}_{cadence}"

            # Run on full signal dates (no IS-only filter)
            res = run_config(
                returns_uni=returns_uni, close_panel=close_panel,
                trade_panel=trade_panel, calendar=calendar,
                benchmark_aligned=benchmark_aligned,
                sma_200=sma_200, atr_20=atr_20,
                weekly_filt=weekly_filt,
                monthly_first=monthly_first, biweekly_fri=biweekly_fri,
                cfg=cfg, is_only=False,
            )
            eq = res["_equity"]
            eq.to_csv(out_dir / f"{label}_equity.csv", index=False)

            # Multi-window evaluation
            win_eval = evaluate_all_windows(eq)
            win_eval.insert(0, "universe", univ_name)
            win_eval.insert(1, "cadence", cadence)
            all_window_rows.append(win_eval)

            ok, _reasons = passes_criteria(win_eval)

            elapsed = time.time() - t0
            print(f"  [{cadence:>8s}] (run {elapsed:.0f}s) "
                  f"{'PASS' if ok else 'FAIL'}")

            row = {"universe": univ_name, "cadence": cadence, "passes": ok}
            for _, w in win_eval.iterrows():
                lbl = w["window"]
                row[f"{lbl}_cagr"] = w.get("cagr_pct")
                row[f"{lbl}_sharpe"] = w.get("sharpe")
                row[f"{lbl}_dd"] = w.get("max_dd_pct")
            summary_rows.append(row)

    summary_df = pd.DataFrame(summary_rows)
    summary_df.to_csv(out_dir / "summary.csv", index=False)
    pd.concat(all_window_rows, ignore_index=True).to_csv(
        out_dir / "all_windows.csv", index=False
    )

    # Print compact comparison table
    print(f"\n{'=' * 100}")
    print("OOS MULTI-WINDOW COMPARISON — OM25 50/50 / 252 / top-25/buf-20 / RF on")
    print(f"{'=' * 100}\n")

    # Build compact view: per (univ, cadence) row, columns = window stats
    rows = []
    for r in summary_rows:
        rows.append({
            "univ": r["universe"],
            "cad": r["cadence"],
            "PASS": "✓" if r["passes"] else "✗",
            "IS_sh": r.get("IS_sharpe"),
            "OOS_A_sh": r.get("OOS_A_sharpe"),
            "OOS_B_sh": r.get("OOS_B_sharpe"),
            "OOS_C_sh": r.get("OOS_C_sharpe"),
            "OOS_full_sh": r.get("OOS_full_sharpe"),
            "OOS_full_cagr": r.get("OOS_full_cagr"),
            "OOS_full_dd": r.get("OOS_full_dd"),
        })
    print(pd.DataFrame(rows).to_string(index=False))
    print(f"\n[wrote] {out_dir}")


if __name__ == "__main__":
    main()
