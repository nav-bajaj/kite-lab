"""TL25 v3 — windows + Top-N/buffer sweep on IS (A3, NSE 500 biweekly).

Locked from prior phases:
  Universe: NSE 500
  Cadence: biweekly
  Score: A3 Offensive P+M (0.40/0.20/0.40)
  Stop: Fixed 20% DD from peak, no 200 DMA exit

Vary one parameter at a time from V2 default baseline:
  Persistence window: 126, 252 (default), 378
  Drawdown window:    63,  126 (default), 252
  Momentum window:    21,  63 (default),  126
  Top-N:              20,  25 (default),  30
  Exit buffer:        15,  20 (default),  25
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from scripts._clean_engine import run_strategy, biweekly_fridays, fridays
from scripts.backtest_momentum import load_price_panels, load_benchmark
from scripts.build_om25_signals import load_universe
from scripts.multi_window_oos_eval import period_metrics
from scripts.tl25_v3 import build_tl25_panels, make_tl25_score


PRICES_DIR = ROOT / "nse500_data_merged"
BENCHMARK = ROOT / "data/benchmarks/nifty100.csv"
UNIVERSE = ROOT / "data/static/nse500_universe.csv"

# Defaults
DEFAULT = dict(
    persistence_window=252,
    drawdown_window=126,
    momentum_window=63,
    top_n=25,
    exit_buffer=20,
)

# Variants (param to vary, value)
VARIANTS = [
    # Persistence
    ("persistence_window", 126),
    ("persistence_window", 252),  # baseline
    ("persistence_window", 378),
    # Drawdown
    ("drawdown_window", 63),
    ("drawdown_window", 126),  # baseline (duplicate of baseline; skip-dedup)
    ("drawdown_window", 252),
    # Momentum
    ("momentum_window", 21),
    ("momentum_window", 63),  # baseline
    ("momentum_window", 126),
    # Top-N
    ("top_n", 20),
    ("top_n", 25),  # baseline
    ("top_n", 30),
    # Exit buffer
    ("exit_buffer", 15),
    ("exit_buffer", 20),  # baseline
    ("exit_buffer", 25),
]


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

    universe = load_universe(UNIVERSE)
    cols = [s for s in close_panel.columns if s in universe]
    close_uni = close_panel[cols]
    atr_panel = close_panel.pct_change().rolling(20).std()

    out_dir = ROOT / f"experiments/oos_retune/{pd.Timestamp.now().strftime('%Y%m%d%H%M%S')}_tl25_v3_windows_topn_is"
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    # Pre-cache panels by (persistence, drawdown, momentum) tuple
    panel_cache = {}

    for param_name, value in VARIANTS:
        cfg = {**DEFAULT, param_name: value}
        pw, dw, mw = cfg["persistence_window"], cfg["drawdown_window"], cfg["momentum_window"]

        key = (pw, dw, mw)
        if key not in panel_cache:
            panel_cache[key] = build_tl25_panels(
                close_uni, persistence_window=pw, drawdown_window=dw, momentum_window=mw
            )
        panels = panel_cache[key]

        score_fn = make_tl25_score(panels, w_persistence=0.40, w_drawdown=0.20, w_momentum=0.40)
        label = f"{param_name}={value}"
        t0 = time.time()
        print(f"  [run] {label} (top_n={cfg['top_n']}, buf={cfg['exit_buffer']}) ...", flush=True)

        res = run_strategy(
            close_panel=close_panel, trade_panel=trade_panel, calendar=calendar,
            benchmark_aligned=benchmark_aligned,
            entry_signal_dates=entry_dates, weekly_signal_dates=weekly_filt,
            signal_function=score_fn, signal_function_args={},
            sma_200_panel=sma_200, atr_20_panel=atr_panel,
            top_n=cfg["top_n"], exit_buffer=cfg["exit_buffer"],
            max_weight=0.075, slippage=0.002,
            atr_mult=0.0, atr_min_floor=0.20,
            use_trailing_stop=True, use_dma_exit=False,
            regime_panel=None, bear_exposure=0.0,
        )
        eq = res["equity"]
        is_m = period_metrics(eq, "IS", "2009-09-01", "2016-12-31")
        elapsed = time.time() - t0
        print(f"      done {elapsed:.0f}s — CAGR={is_m.get('cagr_pct')} "
              f"Sharpe={is_m.get('sharpe')} DD={is_m.get('max_dd_pct')}", flush=True)

        rows.append({
            "varying": param_name,
            "value": value,
            "persistence_window": pw,
            "drawdown_window": dw,
            "momentum_window": mw,
            "top_n": cfg["top_n"],
            "exit_buffer": cfg["exit_buffer"],
            "is_cagr": is_m.get("cagr_pct"),
            "is_sharpe": is_m.get("sharpe"),
            "is_dd": is_m.get("max_dd_pct"),
        })

    df = pd.DataFrame(rows)
    df.to_csv(out_dir / "is_windows_topn.csv", index=False)

    print(f"\n{'=' * 95}")
    print("TL25 v3 — Windows + Top-N/buffer sweep (IS only). Vary one param at a time.")
    print(f"{'=' * 95}")
    # Group by varying param and show
    for param in ["persistence_window", "drawdown_window", "momentum_window", "top_n", "exit_buffer"]:
        sub = df[df["varying"] == param].sort_values("is_sharpe", ascending=False)
        print(f"\n--- Vary {param} (others at baseline) ---")
        print(sub[["value", "is_sharpe", "is_cagr", "is_dd"]].to_string(index=False))
    print(f"\n[wrote] {out_dir}/is_windows_topn.csv")


if __name__ == "__main__":
    main()
