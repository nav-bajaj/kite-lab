"""OM25 winner — sweep hard %-from-peak drawdown stop levels.

Engine trick: the existing trailing-stop machinery already supports a
fixed % drawdown from peak. With atr_mult=0 and atr_min_floor=X and
use_trailing_stop=True, the trail distance becomes max(0, X) = X,
giving a clean "exit if drawdown from peak > X" rule.

Sweep: stop at 15%, 20%, 25%, 30% from peak. Plus baseline (no stop).
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from scripts._clean_engine import (
    run_strategy, fridays, biweekly_fridays,
)
from scripts.backtest_momentum import load_price_panels, load_benchmark
from scripts.build_om25_signals import load_universe
from scripts.multi_window_oos_eval import evaluate_all_windows, passes_criteria
from tasks.om25.experiments._om25_regime_100dma_3conf import (
    build_regime_panel_confirmed,
)
from tasks.om25.experiments._om25_regime_weight_tilt import make_om25_tilt_score


PRICES_DIR = ROOT / "nse500_data_merged"
BENCHMARK = ROOT / "data/benchmarks/nifty100.csv"


def run_one(label, *, stop_pct=None):
    close_panel, trade_panel = load_price_panels(PRICES_DIR)
    calendar = close_panel.index
    benchmark = load_benchmark(BENCHMARK)
    benchmark_aligned = benchmark.reindex(calendar).ffill()
    sma_200 = close_panel.rolling(200, min_periods=200).mean()
    atr_20 = close_panel.pct_change().rolling(20).std()

    weekly_fri = fridays(calendar)
    biweekly_fri = biweekly_fridays(calendar)
    weekly_filt = weekly_fri[weekly_fri >= close_panel.index[252]]
    entry_dates = biweekly_fri[biweekly_fri >= close_panel.index[252]]

    universe = load_universe(ROOT / "data/static/nifty250_universe.csv")
    cols = [s for s in close_panel.columns if s in universe]
    returns_uni = close_panel[cols].pct_change()

    regime = build_regime_panel_confirmed(
        ROOT / "indices_data_historical/NIFTY_100.csv", 100, 3, calendar=calendar
    )
    score_fn = make_om25_tilt_score(
        returns_uni, regime,
        bull_uc=0.5, bull_cr=0.5, bear_uc=0.0, bear_cr=1.0,
        return_filter=True, lookback=252, min_obs=220,
    )

    use_stop = stop_pct is not None
    res = run_strategy(
        close_panel=close_panel, trade_panel=trade_panel,
        calendar=calendar, benchmark_aligned=benchmark_aligned,
        entry_signal_dates=entry_dates,
        weekly_signal_dates=weekly_filt,
        signal_function=score_fn, signal_function_args={},
        sma_200_panel=sma_200, atr_20_panel=atr_20,
        top_n=25, exit_buffer=20,
        atr_mult=0.0, atr_min_floor=stop_pct if use_stop else 0.0,
        max_weight=0.075, slippage=0.002,
        use_trailing_stop=use_stop,
        use_dma_exit=False,
        regime_panel=None, bear_exposure=0.0,
    )
    eq = res["equity"]
    trades = res["trades"]
    exits = res["exits"]
    win_eval = evaluate_all_windows(eq)
    ok, _ = passes_criteria(win_eval)
    oos = win_eval[win_eval["window"] == "OOS_full"].iloc[0]

    # Exit reason breakdown (rename atr_stop -> drawdown_stop for clarity)
    by_reason = {}
    if not exits.empty and "reason" in exits.columns:
        by_reason = exits["reason"].value_counts().to_dict()

    print(f"\n=== {label} ===")
    print(f"  exits total: {len(exits)}")
    for r, n in by_reason.items():
        print(f"    {r:>12}: {n:>4} ({n/len(exits)*100:.1f}%)")
    if not exits.empty and "reason" in exits.columns and "pnl_pct" in exits.columns:
        grp = exits.groupby("reason").agg(
            count=("pnl_pct", "count"),
            avg_pnl=("pnl_pct", "mean"),
            median_pnl=("pnl_pct", "median"),
            hit_rate=("pnl_pct", lambda s: (s > 0).mean()),
            avg_hold=("hold_days", "mean"),
        ).round(3)
        print(grp.to_string())
    print(f"  OOS: CAGR={oos['cagr_pct']:.2f}%  Sharpe={oos['sharpe']:.2f}  "
          f"DD={oos['max_dd_pct']:.2f}%  PASS={ok}")

    return {
        "label": label, "stop_pct": stop_pct,
        "exits": len(exits), "by_reason": by_reason,
        "oos_cagr": oos["cagr_pct"], "oos_sharpe": oos["sharpe"],
        "oos_dd": oos["max_dd_pct"], "passes": ok,
    }


variants = [
    ("Baseline (no stop)", None),
    ("Stop 15% from peak", 0.15),
    ("Stop 20% from peak", 0.20),
    ("Stop 25% from peak", 0.25),
    ("Stop 30% from peak", 0.30),
]

results = []
for label, sp in variants:
    results.append(run_one(label, stop_pct=sp))

print(f"\n{'=' * 80}")
print("SWEEP COMPARISON (OOS_full)")
print(f"{'=' * 80}")
df = pd.DataFrame([{
    "label": r["label"],
    "stop": r["stop_pct"],
    "exits": r["exits"],
    "n_stop": r["by_reason"].get("atr_stop", 0),
    "n_rank": r["by_reason"].get("rank", 0),
    "OOS_cagr": r["oos_cagr"],
    "OOS_sharpe": r["oos_sharpe"],
    "OOS_dd": r["oos_dd"],
    "passes": r["passes"],
} for r in results])
print(df.to_string(index=False))

out = ROOT / "tasks/oos_retune_2026/winner_artifacts"
df.to_csv(out / "om25_dd_stop_sweep.csv", index=False)
print(f"\n[wrote] {out}/om25_dd_stop_sweep.csv")
