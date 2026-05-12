"""TL25 v3 — OOS validation across all 3 universes (NSE 500 / Nifty 250 / Nifty 100).

Same locked-in config from IS:
  Score: Offensive P+M, weights 0.40 / 0.20 / 0.40
  Windows: persistence 252d, drawdown 126d (squared), momentum 63d
  Top-N: 25, exit-buffer: 20
  Cadence: biweekly entry + weekly exit checks
  Stop: Fixed 20% from peak, no 200 DMA exit
  No regime tilt

Tests OOS multi-window pass criteria on each universe to see if the
universe choice generalizes.
"""
from __future__ import annotations

import math
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from scripts._clean_engine import run_strategy, fridays, biweekly_fridays
from scripts.backtest_momentum import load_price_panels, load_benchmark
from scripts.build_om25_signals import load_universe
from scripts.multi_window_oos_eval import evaluate_all_windows, passes_criteria
from scripts.tl25_v3 import build_tl25_panels, make_tl25_score


PRICES_DIR = ROOT / "nse500_data_merged"
BENCHMARK = ROOT / "data/benchmarks/nifty100.csv"

UNIVERSES = [
    ("NSE 500",   ROOT / "data/static/nse500_universe.csv"),
    ("Nifty 250", ROOT / "data/static/nifty250_universe.csv"),
    ("Nifty 100", ROOT / "data/static/nifty100_universe.csv"),
]


def main():
    print("[load] price panels...", flush=True)
    close_panel, trade_panel = load_price_panels(PRICES_DIR)
    calendar = close_panel.index
    benchmark = load_benchmark(BENCHMARK)
    benchmark_aligned = benchmark.reindex(calendar).ffill()
    sma_200 = close_panel.rolling(200, min_periods=200).mean()
    atr_panel = close_panel.pct_change().rolling(20).std()
    weekly_fri = fridays(calendar)
    biweekly_fri = biweekly_fridays(calendar)
    weekly_filt = weekly_fri[weekly_fri >= close_panel.index[252]]
    entry_dates = biweekly_fri[biweekly_fri >= close_panel.index[252]]

    out_dir = ROOT / f"experiments/oos_retune/{pd.Timestamp.now().strftime('%Y%m%d%H%M%S')}_tl25_v3_oos_all_univ"
    out_dir.mkdir(parents=True, exist_ok=True)

    per_universe_summaries = []
    all_window_rows = []

    for univ_name, univ_path in UNIVERSES:
        print(f"\n[universe] {univ_name} — building panels + running ...", flush=True)
        universe = load_universe(univ_path)
        cols = [s for s in close_panel.columns if s in universe]
        close_uni = close_panel[cols]
        panels = build_tl25_panels(close_uni)
        score_fn = make_tl25_score(panels, w_persistence=0.40, w_drawdown=0.20, w_momentum=0.40)

        t0 = time.time()
        res = run_strategy(
            close_panel=close_panel, trade_panel=trade_panel, calendar=calendar,
            benchmark_aligned=benchmark_aligned,
            entry_signal_dates=entry_dates, weekly_signal_dates=weekly_filt,
            signal_function=score_fn, signal_function_args={},
            sma_200_panel=sma_200, atr_20_panel=atr_panel,
            top_n=25, exit_buffer=20, max_weight=0.075, slippage=0.002,
            atr_mult=0.0, atr_min_floor=0.20,
            use_trailing_stop=True, use_dma_exit=False,
            regime_panel=None, bear_exposure=0.0,
        )
        eq = res["equity"].copy()
        eq["date"] = pd.to_datetime(eq["date"])
        win_eval = evaluate_all_windows(eq)
        ok, reasons = passes_criteria(win_eval)

        print(f"  done {time.time()-t0:.0f}s. PASS={ok}", flush=True)

        # Save equity per universe
        slug = univ_name.lower().replace(" ", "_")
        eq.to_csv(out_dir / f"{slug}_equity.csv", index=False)

        # Add to combined output
        for _, r in win_eval.iterrows():
            row = {"universe": univ_name, "univ_size": len(cols), **r.to_dict()}
            all_window_rows.append(row)

        per_universe_summaries.append({
            "universe": univ_name,
            "univ_size": len(cols),
            "passes": ok,
            "fail_reasons": "; ".join(r for r in reasons if r.startswith("FAIL")),
            **{f"{r['window']}_cagr": r.get("cagr_pct") for _, r in win_eval.iterrows()},
            **{f"{r['window']}_sharpe": r.get("sharpe") for _, r in win_eval.iterrows()},
            **{f"{r['window']}_dd": r.get("max_dd_pct") for _, r in win_eval.iterrows()},
        })

    # Side-by-side report
    print(f"\n{'=' * 105}")
    print("TL25 v3 — OOS across universes (A3 score, NSE 500 biweekly config — universe varies)")
    print(f"{'=' * 105}")
    df_windows = pd.DataFrame(all_window_rows)
    pivot_metric = lambda metric: df_windows.pivot(
        index="window", columns="universe", values=metric
    ).reindex(["IS", "OOS_A", "OOS_B", "OOS_C", "OOS_full"])

    print("\n--- CAGR (%) by window × universe ---")
    print(pivot_metric("cagr_pct").round(2).to_string())
    print("\n--- Sharpe by window × universe ---")
    print(pivot_metric("sharpe").round(2).to_string())
    print("\n--- Max DD (%) by window × universe ---")
    print(pivot_metric("max_dd_pct").round(2).to_string())

    print(f"\n--- Pass criteria ---")
    for s in per_universe_summaries:
        status = "PASS" if s["passes"] else "FAIL"
        reasons_str = (f" — {s['fail_reasons']}" if not s["passes"] else "")
        print(f"  {s['universe']:9s} ({s['univ_size']:>3d} stocks): {status}{reasons_str}")

    pd.DataFrame(per_universe_summaries).to_csv(out_dir / "summary.csv", index=False)
    df_windows.to_csv(out_dir / "all_windows.csv", index=False)
    print(f"\n[wrote] {out_dir}/")


if __name__ == "__main__":
    main()
