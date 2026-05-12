"""TL25 v3 — universe × cadence sweep on IS (A3 score, Fixed 20% DD stop).

Locked from prior phases:
  Score: Offensive P+M (w_persistence=0.40, w_drawdown=0.20, w_momentum=0.40)
  Stop: Fixed 20% DD from peak, no 200 DMA exit
  Top-N: 25, exit-buffer: 20
  Windows: persistence 252d, drawdown 126d squared, momentum 63d

Sweep:
  Universe × Cadence  = 3 × 2 = 6 configs
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from scripts._clean_engine import (
    run_strategy, fridays, biweekly_fridays, monthly_first_trading_day,
)
from scripts.backtest_momentum import load_price_panels, load_benchmark
from scripts.build_om25_signals import load_universe
from scripts.multi_window_oos_eval import period_metrics
from scripts.tl25_v3 import build_tl25_panels, make_tl25_score


PRICES_DIR = ROOT / "nse500_data_merged"
BENCHMARK = ROOT / "data/benchmarks/nifty100.csv"

# Locked from prior phases
W_PERS, W_DD, W_MOM = 0.40, 0.20, 0.40
STOP_PCT = 0.20
TOP_N, EXIT_BUFFER = 25, 20

UNIVERSES = [
    ("NSE 500",   ROOT / "data/static/nse500_universe.csv"),
    ("Nifty 250", ROOT / "data/static/nifty250_universe.csv"),
    ("Nifty 100", ROOT / "data/static/nifty100_universe.csv"),
]
CADENCES = ["monthly", "biweekly"]


def main():
    print("[load] price panels...", flush=True)
    close_panel, trade_panel = load_price_panels(PRICES_DIR)
    calendar = close_panel.index
    benchmark = load_benchmark(BENCHMARK)
    benchmark_aligned = benchmark.reindex(calendar).ffill()
    sma_200 = close_panel.rolling(200, min_periods=200).mean()
    weekly_fri = fridays(calendar)
    biweekly_fri = biweekly_fridays(calendar)
    monthly_first = monthly_first_trading_day(calendar)
    weekly_filt = weekly_fri[weekly_fri >= close_panel.index[252]]

    out_dir = ROOT / f"experiments/oos_retune/{pd.Timestamp.now().strftime('%Y%m%d%H%M%S')}_tl25_v3_univ_cad_is"
    out_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    for univ_name, univ_path in UNIVERSES:
        universe = load_universe(univ_path)
        cols = [s for s in close_panel.columns if s in universe]
        close_uni = close_panel[cols]
        panels = build_tl25_panels(close_uni)

        for cad in CADENCES:
            if cad == "biweekly":
                entry_all = biweekly_fri
            else:
                entry_all = monthly_first
            entry_dates = entry_all[entry_all >= close_panel.index[252]]

            score_fn = make_tl25_score(
                panels,
                w_persistence=W_PERS, w_drawdown=W_DD, w_momentum=W_MOM,
            )
            label = f"{univ_name:9s} {cad}"
            t0 = time.time()
            print(f"  [run] {label}  (univ={len(cols)} stocks, entries={len(entry_dates)}) ...", flush=True)
            res = run_strategy(
                close_panel=close_panel, trade_panel=trade_panel, calendar=calendar,
                benchmark_aligned=benchmark_aligned,
                entry_signal_dates=entry_dates, weekly_signal_dates=weekly_filt,
                signal_function=score_fn, signal_function_args={},
                sma_200_panel=sma_200,
                atr_20_panel=close_panel.pct_change().rolling(20).std(),
                top_n=TOP_N, exit_buffer=EXIT_BUFFER,
                max_weight=0.075, slippage=0.002,
                atr_mult=0.0, atr_min_floor=STOP_PCT,
                use_trailing_stop=True, use_dma_exit=False,
                regime_panel=None, bear_exposure=0.0,
            )
            eq = res["equity"]
            exits = res["exits"]
            is_m = period_metrics(eq, "IS", "2009-09-01", "2016-12-31")
            elapsed = time.time() - t0
            print(f"      done {elapsed:.0f}s — CAGR={is_m.get('cagr_pct')} "
                  f"Sharpe={is_m.get('sharpe')} DD={is_m.get('max_dd_pct')}", flush=True)
            rows.append({
                "universe": univ_name,
                "cadence": cad,
                "univ_size": len(cols),
                "is_cagr": is_m.get("cagr_pct"),
                "is_sharpe": is_m.get("sharpe"),
                "is_dd": is_m.get("max_dd_pct"),
                "is_vol": is_m.get("vol_pct"),
            })

    df = pd.DataFrame(rows)
    df.to_csv(out_dir / "is_universe_cadence.csv", index=False)

    df_sorted = df.sort_values("is_sharpe", ascending=False)
    print(f"\n{'=' * 90}")
    print("TL25 v3 — Universe × Cadence sweep (IS only). A3 score, Fixed 20% DD.")
    print(f"{'=' * 90}")
    print(df_sorted.to_string(index=False))
    print(f"\n[wrote] {out_dir}/is_universe_cadence.csv")


if __name__ == "__main__":
    main()
