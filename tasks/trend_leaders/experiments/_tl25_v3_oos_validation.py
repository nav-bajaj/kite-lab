"""TL25 v3 — OOS validation of the IS-locked config.

IS-locked config (from prior phases):
  Universe: NSE 500
  Cadence: biweekly entry + weekly exit checks
  Score: Offensive P+M, weights 0.40 / 0.20 / 0.40
  Windows: persistence 252d, drawdown 126d (squared), momentum 63d
  Top-N: 25, exit-buffer: 20
  Stop: Fixed 20% from peak (weekly), no 200 DMA exit
  Sizing: Equal 1/N, 7.5% max, drift after entry
  Slippage: 20 bps
  No regime tilt (single config for OM25 diversification)

Validates against multi-window OOS pass criteria (per
tasks/oos_retune_2026/PLAN.md):
  - IS Sharpe >= 1.0 (sanity)
  - OOS-full Sharpe >= 1.0
  - OOS-A (2017-19) Sharpe >= 0.7
  - OOS-B (2020-22) Sharpe >= 0.7
  - OOS-C (2023-26) Sharpe >= 0.7
  - OOS-full Max DD >= -45%
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
UNIVERSE = ROOT / "data/static/nse500_universe.csv"


def yearly(eq, label):
    pv = eq.set_index("date")["pv"].astype(float).sort_index()
    pv.index = pd.to_datetime(pv.index)
    rows = []
    for y, gp in pv.groupby(pv.index.year):
        if len(gp) < 5: continue
        r = gp.pct_change().dropna()
        cagr = gp.iloc[-1]/gp.iloc[0] - 1
        vol = r.std() * math.sqrt(252)
        sh = (r.mean()*252)/vol if vol > 0 else 0
        cum = gp/gp.cummax()
        dd = (cum.min() - 1) * 100
        era = "IS" if y <= 2016 else ("OOS_A" if y<=2019 else ("OOS_B" if y<=2022 else "OOS_C"))
        rows.append({"year": y, "era": era,
                     "ret_pct": round(cagr*100, 2),
                     "sharpe": round(sh, 2),
                     "dd_pct": round(dd, 1)})
    return pd.DataFrame(rows)


def main():
    print("[load] price panels...", flush=True)
    close_panel, trade_panel = load_price_panels(PRICES_DIR)
    calendar = close_panel.index
    benchmark = load_benchmark(BENCHMARK)
    benchmark_aligned = benchmark.reindex(calendar).ffill()
    sma_200 = close_panel.rolling(200, min_periods=200).mean()
    weekly_fri = fridays(calendar)
    biweekly_fri = biweekly_fridays(calendar)
    weekly_filt = weekly_fri[weekly_fri >= close_panel.index[252]]
    entry_dates = biweekly_fri[biweekly_fri >= close_panel.index[252]]

    print("[universe + panels] NSE 500 with 252/126/63 windows...", flush=True)
    universe = load_universe(UNIVERSE)
    cols = [s for s in close_panel.columns if s in universe]
    close_uni = close_panel[cols]
    panels = build_tl25_panels(close_uni)

    score_fn = make_tl25_score(panels, w_persistence=0.40, w_drawdown=0.20, w_momentum=0.40)

    print(f"  universe: {len(cols)} symbols, {len(entry_dates)} entry dates", flush=True)
    print(f"[backtest] running v3 on full 2009-2026 panel...", flush=True)
    t0 = time.time()
    res = run_strategy(
        close_panel=close_panel, trade_panel=trade_panel, calendar=calendar,
        benchmark_aligned=benchmark_aligned,
        entry_signal_dates=entry_dates, weekly_signal_dates=weekly_filt,
        signal_function=score_fn, signal_function_args={},
        sma_200_panel=sma_200,
        atr_20_panel=close_panel.pct_change().rolling(20).std(),
        top_n=25, exit_buffer=20, max_weight=0.075, slippage=0.002,
        atr_mult=0.0, atr_min_floor=0.20,
        use_trailing_stop=True, use_dma_exit=False,
        regime_panel=None, bear_exposure=0.0,
    )
    print(f"  done in {time.time()-t0:.0f}s", flush=True)

    eq = res["equity"].copy()
    eq["date"] = pd.to_datetime(eq["date"])
    trades = res["trades"].copy()
    exits = res["exits"].copy()

    # Multi-window evaluation
    win_eval = evaluate_all_windows(eq)
    ok, reasons = passes_criteria(win_eval)

    print(f"\n{'=' * 95}")
    print("TL25 v3 — OOS VALIDATION (multi-window)")
    print(f"{'=' * 95}")
    print(win_eval[["window", "yrs", "cagr_pct", "vol_pct", "sharpe", "max_dd_pct"]]
          .to_string(index=False))

    print(f"\n=== Pass criteria ===")
    for r in reasons:
        print(f"  {r}")
    print(f"\nOverall: {'PASS' if ok else 'FAIL'}")

    # Year-by-year
    yr_df = yearly(eq, "v3")
    print(f"\n=== Year-by-year ===")
    print(yr_df.to_string(index=False))

    # Exit breakdown
    if not exits.empty and "reason" in exits.columns:
        print(f"\n=== Exit breakdown (full period) ===")
        grp = exits.groupby("reason").agg(
            n=("pnl_pct", "count"),
            avg_pnl=("pnl_pct", "mean"),
            median_pnl=("pnl_pct", "median"),
            hit=("pnl_pct", lambda s: (s > 0).mean()),
            avg_hold=("hold_days", "mean"),
        ).round(3)
        print(grp.to_string())

    # Save artifacts
    out_dir = ROOT / "tasks/oos_retune_2026/winner_artifacts"
    eq.to_csv(out_dir / "tl25_v3_winner_equity.csv", index=False)
    trades.to_csv(out_dir / "tl25_v3_winner_trades.csv", index=False)
    exits.to_csv(out_dir / "tl25_v3_winner_exits.csv", index=False)
    win_eval.to_csv(out_dir / "tl25_v3_winner_windows.csv", index=False)
    yr_df.to_csv(out_dir / "tl25_v3_winner_yearly.csv", index=False)
    print(f"\n[wrote] tl25_v3_winner_* artifacts to {out_dir}/")


if __name__ == "__main__":
    main()
