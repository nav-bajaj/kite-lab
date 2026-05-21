"""T4-T6 — Sensitivity sweeps for COMBO breadth-3state.

T4: threshold sensitivity (bear_entry × deep_entry, 3×3 = 9 variants)
T5: breadth-metric sensitivity (avg_dist / pct_above_200dma / net_new_highs_pct / mcclellan_sum)
T6: bear-exposure sensitivity (0.3 / 0.5 / 0.7)

For each variant: full-span backtest (2009-09 → 2026-05), then metrics
sliced per window. Compares to A_PROD baseline (which is held fixed
across all sweeps).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts._clean_engine import run_strategy, fridays, biweekly_fridays  # noqa: E402
from scripts._momentum_engine import (  # noqa: E402
    build_momentum_panels, make_momentum_score, lookback_months_to_days,
)
from scripts.om25_v3 import (  # noqa: E402
    LOCKED as OM25_LOCKED, build_regime_panel_confirmed, make_om25_tilt_score,
)
from scripts.combo_defensive import LOCKED as COMBO_LOCKED, make_combo_score_fn  # noqa: E402
from scripts.backtest_momentum import load_price_panels, load_benchmark  # noqa: E402
from scripts.build_om25_signals import load_universe  # noqa: E402

from tasks.breadth_atlas.combo_3state.combo_breadth_3state import (  # noqa: E402
    build_three_state_regime_sticky_deep, build_combo_score, load_breadth_panel,
    STATE_BULL, STATE_BEAR, STATE_DEEP, WINDOWS,
)


def run_one(*, label, score_fn, regime_panel, close_panel, trade_panel, calendar,
            benchmark_aligned, sma_200, atr_20, entry_dates, weekly_dates,
            initial_capital):
    res = run_strategy(
        close_panel=close_panel, trade_panel=trade_panel,
        calendar=calendar, benchmark_aligned=benchmark_aligned,
        entry_signal_dates=entry_dates, weekly_signal_dates=weekly_dates,
        signal_function=score_fn, signal_function_args={},
        sma_200_panel=sma_200, atr_20_panel=atr_20,
        top_n=COMBO_LOCKED["top_n"], exit_buffer=COMBO_LOCKED["exit_buffer"],
        max_weight=COMBO_LOCKED["max_weight"], slippage=COMBO_LOCKED["slippage"],
        atr_mult=0.0, atr_min_floor=0.0,
        use_trailing_stop=False, use_dma_exit=False, weekly_rank_check=False,
        regime_panel=regime_panel,
        bear_exposure=0.0,  # unused with float panel
        bear_skips_entries=False,
        regime_redeploy_on_increase=True,
        min_hold_days=COMBO_LOCKED["min_hold_days"],
        initial_capital=initial_capital,
    )
    return res


def metrics_for(eq, start, end):
    pv = eq.set_index("date")["pv"].astype(float)
    pv = pv.loc[(pv.index >= start) & (pv.index <= end)]
    if len(pv) < 2:
        return {}
    rets = pv.pct_change().dropna()
    years = max((pv.index[-1] - pv.index[0]).days / 365.25, 1e-9)
    cagr = (pv.iloc[-1] / pv.iloc[0]) ** (1 / years) - 1
    vol = rets.std() * math.sqrt(252)
    sharpe = (cagr - 0.05) / vol if vol > 0 else 0.0
    dd = (pv / pv.cummax() - 1).min()
    calmar = cagr / abs(dd) if dd < 0 else np.nan
    return {"cagr_pct": round(cagr * 100, 2), "sharpe": round(sharpe, 3),
            "max_dd_pct": round(dd * 100, 2),
            "calmar": round(float(calmar), 3) if not pd.isna(calmar) else None}


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prices-dir", type=Path, default=ROOT / "nse500_data_merged")
    ap.add_argument("--benchmark", type=Path, default=ROOT / "data/benchmarks/nifty100.csv")
    ap.add_argument("--regime-index", type=Path, default=ROOT / COMBO_LOCKED["regime_index_path"])
    ap.add_argument("--breadth-panel", type=Path, default=ROOT / "data/breadth/breadth_daily.csv")
    ap.add_argument("--initial-capital", type=float, default=1_000_000)
    ap.add_argument("--tests", nargs="+", default=["T4", "T5", "T6"],
                    choices=["T4", "T5", "T6"])
    ap.add_argument("--output-dir", type=Path, default=None)
    return ap.parse_args()


# Threshold sweeps for T4 (around the default avg_dist_from_200dma config)
T4_THRESHOLDS = [
    (-0.05, 0.00, -0.15),  # bear_entry, bear_exit, deep_entry
    (-0.05, 0.00, -0.10),
    (-0.05, 0.00, -0.05),
    (0.00, 0.05, -0.15),
    (0.00, 0.05, -0.10),    # DEFAULT (D_BREADTH)
    (0.00, 0.05, -0.05),
    (0.05, 0.10, -0.15),
    (0.05, 0.10, -0.10),
    (0.05, 0.10, -0.05),
]

# Metric configs for T5 (each with its own atlas-derived thresholds)
T5_METRICS = {
    "avg_dist_from_200dma": (0.00, 0.05, -0.10),
    "pct_above_200dma":     (0.40, 0.50, 0.20),
    "net_new_highs_pct":    (0.00, 0.03, -0.10),
    "mcclellan_sum":        (2.50, 2.70, 1.50),
}

# Bear-exposure levels for T6
T6_EXPOSURES = [0.3, 0.5, 0.7]


def main():
    args = parse_args()
    ts = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
    out_dir = args.output_dir or ROOT / "tasks/breadth_atlas/combo_3state/runs" / f"sensitivity_{ts}"
    out_dir.mkdir(parents=True, exist_ok=True)

    print("[load] price panels")
    close_panel, trade_panel = load_price_panels(args.prices_dir)
    calendar = close_panel.index
    benchmark = load_benchmark(args.benchmark).reindex(calendar).ffill()
    sma_200 = close_panel.rolling(200, min_periods=200).mean()
    atr_20 = close_panel.pct_change().rolling(20).std()

    combo_score = build_combo_score(close_panel, calendar, args.regime_index)
    breadth = load_breadth_panel(args.breadth_panel)

    full_start = pd.Timestamp(WINDOWS["FULL"][0])
    full_end = pd.Timestamp(WINDOWS["FULL"][1])
    entry_dates = biweekly_fridays(calendar)
    entry_dates = entry_dates[(entry_dates >= full_start) & (entry_dates <= full_end)]
    weekly = fridays(calendar)
    weekly_dates = weekly[(weekly >= full_start) & (weekly <= full_end)]

    rows = []

    if "T4" in args.tests:
        print("\n=== T4: threshold sensitivity (avg_dist_from_200dma, bear_exp=0.5) ===")
        for bear_in, bear_out, deep_in in T4_THRESHOLDS:
            label = f"T4_be{bear_in:+.2f}_be_out{bear_out:+.2f}_de{deep_in:+.2f}"
            regime = build_three_state_regime_sticky_deep(
                breadth["avg_dist_from_200dma"],
                bear_entry=bear_in, bear_exit=bear_out, deep_entry=deep_in,
                higher_is_bull=True, confirm_days=3, calendar=calendar,
            )
            exposure = regime.map({STATE_BULL: 1.0, STATE_BEAR: 0.5, STATE_DEEP: 1.0}).astype(float)
            print(f"  {label}")
            res = run_one(label=label, score_fn=combo_score, regime_panel=exposure,
                          close_panel=close_panel, trade_panel=trade_panel, calendar=calendar,
                          benchmark_aligned=benchmark, sma_200=sma_200, atr_20=atr_20,
                          entry_dates=entry_dates, weekly_dates=weekly_dates,
                          initial_capital=args.initial_capital)
            if res is None: continue
            eq = res["equity"].copy(); eq["date"] = pd.to_datetime(eq["date"])
            eq.to_csv(out_dir / f"{label}_equity.csv", index=False)
            for win in WINDOWS:
                s, e = pd.Timestamp(WINDOWS[win][0]), pd.Timestamp(WINDOWS[win][1])
                m = metrics_for(eq, s, e)
                if m:
                    rows.append({"test": "T4", "label": label, "bear_entry": bear_in,
                                 "deep_entry": deep_in, "window": win, **m})

    if "T5" in args.tests:
        print("\n=== T5: breadth-metric sensitivity (bear_exp=0.5) ===")
        for metric, (bear_in, bear_out, deep_in) in T5_METRICS.items():
            label = f"T5_{metric}"
            if metric not in breadth.columns:
                print(f"  {label} — column not in breadth panel; skipping")
                continue
            regime = build_three_state_regime_sticky_deep(
                breadth[metric],
                bear_entry=bear_in, bear_exit=bear_out, deep_entry=deep_in,
                higher_is_bull=True, confirm_days=3, calendar=calendar,
            )
            exposure = regime.map({STATE_BULL: 1.0, STATE_BEAR: 0.5, STATE_DEEP: 1.0}).astype(float)
            print(f"  {label}")
            res = run_one(label=label, score_fn=combo_score, regime_panel=exposure,
                          close_panel=close_panel, trade_panel=trade_panel, calendar=calendar,
                          benchmark_aligned=benchmark, sma_200=sma_200, atr_20=atr_20,
                          entry_dates=entry_dates, weekly_dates=weekly_dates,
                          initial_capital=args.initial_capital)
            if res is None: continue
            eq = res["equity"].copy(); eq["date"] = pd.to_datetime(eq["date"])
            eq.to_csv(out_dir / f"{label}_equity.csv", index=False)
            for win in WINDOWS:
                s, e = pd.Timestamp(WINDOWS[win][0]), pd.Timestamp(WINDOWS[win][1])
                m = metrics_for(eq, s, e)
                if m:
                    rows.append({"test": "T5", "label": label, "metric": metric,
                                 "window": win, **m})

    if "T6" in args.tests:
        print("\n=== T6: bear-exposure sensitivity (avg_dist_from_200dma, default thresholds) ===")
        regime = build_three_state_regime_sticky_deep(
            breadth["avg_dist_from_200dma"],
            bear_entry=0.00, bear_exit=0.05, deep_entry=-0.10,
            higher_is_bull=True, confirm_days=3, calendar=calendar,
        )
        for be in T6_EXPOSURES:
            label = f"T6_bear_exp_{be}"
            exposure = regime.map({STATE_BULL: 1.0, STATE_BEAR: be, STATE_DEEP: 1.0}).astype(float)
            print(f"  {label}")
            res = run_one(label=label, score_fn=combo_score, regime_panel=exposure,
                          close_panel=close_panel, trade_panel=trade_panel, calendar=calendar,
                          benchmark_aligned=benchmark, sma_200=sma_200, atr_20=atr_20,
                          entry_dates=entry_dates, weekly_dates=weekly_dates,
                          initial_capital=args.initial_capital)
            if res is None: continue
            eq = res["equity"].copy(); eq["date"] = pd.to_datetime(eq["date"])
            eq.to_csv(out_dir / f"{label}_equity.csv", index=False)
            for win in WINDOWS:
                s, e = pd.Timestamp(WINDOWS[win][0]), pd.Timestamp(WINDOWS[win][1])
                m = metrics_for(eq, s, e)
                if m:
                    rows.append({"test": "T6", "label": label, "bear_exposure": be,
                                 "window": win, **m})

    df = pd.DataFrame(rows)
    df.to_csv(out_dir / "sensitivity_metrics.csv", index=False)

    print("\n=== Summary by test (FULL + 2021+ windows) ===")
    for test in ["T4", "T5", "T6"]:
        if test not in args.tests:
            continue
        sub = df[(df["test"] == test) & (df["window"].isin(["FULL", "2021+"]))]
        if sub.empty: continue
        print(f"\n--- {test} ---")
        cols = ["label", "window", "cagr_pct", "sharpe", "max_dd_pct", "calmar"]
        print(sub[cols].to_string(index=False))

    print(f"\n[wrote] {out_dir.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
