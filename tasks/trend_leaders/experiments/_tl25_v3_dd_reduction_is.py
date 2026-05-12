"""TL25 v3 — IS-only search for DD-reduction tweaks.

Locked baseline: NSE 500, biweekly, A3 weights (0.40/0.20/0.40),
                 windows 252/126/63, top-25, buffer-20, 20% DD stop, 7.5% cap.
Baseline IS: Sharpe 1.61, CAGR 30.57%, DD -28.21%.

Goal: reduce DD without losing too much Sharpe. Three angles:
  A. Score weights — more drawdown-component weight
  B. Stop tightness — 15%, 18%, 22%
  C. Position cap — 5%, 6% (vs 7.5% default)
  D. Combined: best of A + tighter stop + lower cap

NO OOS shown.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from scripts._clean_engine import run_strategy, fridays, biweekly_fridays
from scripts.backtest_momentum import load_price_panels, load_benchmark
from scripts.build_om25_signals import load_universe
from scripts.multi_window_oos_eval import period_metrics
from scripts.tl25_v3 import build_tl25_panels, make_tl25_score


PRICES_DIR = ROOT / "nse500_data_merged"
BENCHMARK = ROOT / "data/benchmarks/nifty100.csv"
UNIVERSE = ROOT / "data/static/nse500_universe.csv"


# Variants. Each: (label, wp, wd, wm, stop_pct, max_weight)
VARIANTS = [
    # Baseline + reference
    ("BASELINE A3 (40/20/40, 20% stop, 7.5% cap)", 0.40, 0.20, 0.40, 0.20, 0.075),

    # A. Score weight tilts (more DD focus)
    ("Weights 40/30/30 (-mom, +DD)",                0.40, 0.30, 0.30, 0.20, 0.075),
    ("Weights 35/30/35 (balanced + DD)",            0.35, 0.30, 0.35, 0.20, 0.075),
    ("Weights 40/40/20 (DD-heavy)",                 0.40, 0.40, 0.20, 0.20, 0.075),
    ("Weights 50/30/20 (P+DD heavy)",               0.50, 0.30, 0.20, 0.20, 0.075),
    ("Weights 45/35/20 (P+DD heavy alt)",           0.45, 0.35, 0.20, 0.20, 0.075),

    # B. Stop tightness (at A3 weights)
    ("A3 + 15% stop (tighter)",                     0.40, 0.20, 0.40, 0.15, 0.075),
    ("A3 + 18% stop (mid)",                         0.40, 0.20, 0.40, 0.18, 0.075),
    ("A3 + 22% stop (looser)",                      0.40, 0.20, 0.40, 0.22, 0.075),

    # C. Position cap (at A3 weights, 20% stop)
    ("A3 + max 5% per stock",                       0.40, 0.20, 0.40, 0.20, 0.05),
    ("A3 + max 6% per stock",                       0.40, 0.20, 0.40, 0.20, 0.06),

    # D. Combined (DD-tilted weights + tighter stop + smaller cap)
    ("Combined: 40/30/30 + 15% stop + 5% cap",      0.40, 0.30, 0.30, 0.15, 0.05),
    ("Combined: 40/30/30 + 18% stop + 6% cap",      0.40, 0.30, 0.30, 0.18, 0.06),
    ("Combined: 45/35/20 + 18% stop + 6% cap",      0.45, 0.35, 0.20, 0.18, 0.06),
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

    universe = load_universe(UNIVERSE)
    cols = [s for s in close_panel.columns if s in universe]
    close_uni = close_panel[cols]
    panels = build_tl25_panels(close_uni)

    out_dir = ROOT / f"experiments/oos_retune/{pd.Timestamp.now().strftime('%Y%m%d%H%M%S')}_tl25_v3_dd_reduction_is"
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    for (label, wp, wd, wm, stop, cap) in VARIANTS:
        score_fn = make_tl25_score(panels,
                                    w_persistence=wp, w_drawdown=wd, w_momentum=wm)
        t0 = time.time()
        print(f"  [run] {label} ...", flush=True)
        res = run_strategy(
            close_panel=close_panel, trade_panel=trade_panel, calendar=calendar,
            benchmark_aligned=benchmark_aligned,
            entry_signal_dates=entry_dates, weekly_signal_dates=weekly_filt,
            signal_function=score_fn, signal_function_args={},
            sma_200_panel=sma_200, atr_20_panel=atr_panel,
            top_n=25, exit_buffer=20,
            max_weight=cap, slippage=0.002,
            atr_mult=0.0, atr_min_floor=stop,
            use_trailing_stop=True, use_dma_exit=False,
            regime_panel=None, bear_exposure=0.0,
        )
        eq = res["equity"]
        is_m = period_metrics(eq, "IS", "2009-09-01", "2016-12-31")
        elapsed = time.time() - t0
        print(f"      done {elapsed:.0f}s — CAGR={is_m.get('cagr_pct')} "
              f"Sharpe={is_m.get('sharpe')} DD={is_m.get('max_dd_pct')}", flush=True)
        rows.append({
            "label": label, "wp": wp, "wd": wd, "wm": wm,
            "stop": stop, "max_weight": cap,
            "is_cagr": is_m.get("cagr_pct"),
            "is_sharpe": is_m.get("sharpe"),
            "is_dd": is_m.get("max_dd_pct"),
            "is_vol": is_m.get("vol_pct"),
        })

    df = pd.DataFrame(rows)
    df.to_csv(out_dir / "is_dd_reduction.csv", index=False)

    print(f"\n{'=' * 105}")
    print("TL25 v3 — DD-reduction tweaks (IS only). Sorted by IS Sharpe.")
    print(f"{'=' * 105}")
    df_sorted = df.sort_values("is_sharpe", ascending=False)
    print(df_sorted[["label","wp","wd","wm","stop","max_weight",
                     "is_sharpe","is_cagr","is_dd"]].to_string(index=False))
    print(f"\n--- Sorted by IS DD (best DD first) ---")
    df_dd = df.sort_values("is_dd", ascending=False)
    print(df_dd[["label","wp","wd","wm","stop","max_weight",
                "is_sharpe","is_cagr","is_dd"]].to_string(index=False))
    print(f"\n[wrote] {out_dir}/is_dd_reduction.csv")


if __name__ == "__main__":
    main()
