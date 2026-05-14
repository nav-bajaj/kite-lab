"""Re-run the full IS sweep sequence on Thursday signals (corrected default).

Pretty-prints a side-by-side comparison with the earlier Friday-signal sweep
so we can tell which IS conclusions survive the day-of-week correction.

For each param dimension, sweeps the same candidate values on L6 and L9
tracks (with previous Friday-sweep locks in place) and identifies the
Thursday IS-best.
"""
from __future__ import annotations

import math
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts._momentum_engine import (
    BASELINE, build_momentum_panels, run_momentum,
    lookback_months_to_days,
)
from scripts.backtest_momentum import load_price_panels, load_benchmark
from scripts.build_om25_signals import load_universe
from scripts.multi_window_oos_eval import period_metrics


IS_START = "2009-09-01"
IS_END = "2016-12-31"


def metrics(res):
    eq = res["equity"]; trades = res["trades"]; exits = res["exits"]
    m = period_metrics(eq, "is", IS_START, IS_END)
    cagr = m.get("cagr_pct"); dd = m.get("max_dd_pct")
    calmar = (cagr / abs(dd)) if (cagr is not None and dd not in (None, 0)
                                   and abs(dd) > 1e-6) else None
    rets = eq["pv"].astype(float).pct_change().dropna()
    downside = rets[rets < 0]
    sortino = ((rets.mean() * 252 - 0.05) / (downside.std() * math.sqrt(252))
               if len(downside) > 1 and downside.std() > 0 else None)
    yrs = (pd.Timestamp(IS_END) - pd.Timestamp(IS_START)).days / 365.25
    return {
        "cagr_pct": round(cagr, 2) if cagr is not None else None,
        "sharpe": round(m.get("sharpe"), 2) if m.get("sharpe") is not None else None,
        "sortino": round(sortino, 2) if sortino is not None else None,
        "calmar": round(calmar, 2) if calmar is not None else None,
        "max_dd_pct": round(dd, 2) if dd is not None else None,
        "rt_per_year": round(len(exits) / yrs, 1) if yrs > 0 else None,
    }


def run_sweep(ctx, panel_cache, param_name, values, locks, label):
    rows = []
    for v in values:
        cfg = {**locks, param_name: v}
        lb_m = cfg.get("lookback_months", BASELINE["lookback_months"])
        skip = cfg.get("skip_days", BASELINE["skip_days"])
        key = (lb_m, skip)
        if key not in panel_cache:
            panel_cache[key] = build_momentum_panels(
                ctx["close_uni"],
                lookback_days=lookback_months_to_days(lb_m),
                skip_days=skip,
            )
        panels = panel_cache[key]
        res = run_momentum(
            close_panel=ctx["close_panel"], trade_panel=ctx["trade_panel"],
            calendar=ctx["calendar"], benchmark_aligned=ctx["benchmark_aligned"],
            panels=panels, sma_200_panel=ctx["sma_200"], atr_20_panel=ctx["atr_20"],
            start=IS_START, end=IS_END, config=cfg,
        )
        if res is None or res["equity"].empty:
            continue
        m = metrics(res)
        rows.append({"label": f"{param_name}={v}", "value": v, **m})
    return pd.DataFrame(rows)


def main():
    print("[load] panels ...")
    close_panel, trade_panel = load_price_panels(ROOT / "nse500_data_merged")
    calendar = close_panel.index
    benchmark = load_benchmark(ROOT / "data/benchmarks/nifty100.csv")
    benchmark_aligned = benchmark.reindex(calendar).ffill()
    sma_200 = close_panel.rolling(200, min_periods=200).mean()
    atr_20 = close_panel.pct_change().rolling(20).std()
    universe = load_universe(ROOT / BASELINE["universe_csv"])
    cols = [s for s in close_panel.columns if s in universe]
    close_uni = close_panel[cols]
    print(f"  {len(cols)} symbols")

    ctx = dict(close_panel=close_panel, trade_panel=trade_panel,
               calendar=calendar, benchmark_aligned=benchmark_aligned,
               sma_200=sma_200, atr_20=atr_20, close_uni=close_uni)

    panel_cache = {}
    out_dir = ROOT / "tasks/MM-tuning/sweeps_thursday"
    out_dir.mkdir(parents=True, exist_ok=True)

    print("\n=== Sequential param sweep on Thursday signals ===")
    print(f"  IS window: {IS_START} → {IS_END}  (signal_day inherited from BASELINE = Thursday)\n")

    # 1. lookback_months — independent (no other locks)
    locks = {}
    df = run_sweep(ctx, panel_cache, "lookback_months",
                    [3, 6, 9, 12], locks, "lookback")
    df.to_csv(out_dir / "is_lookback_months.csv", index=False)
    print("1. lookback_months sweep:")
    print(df.to_string(index=False))

    # Carry forward L6 and L9 as parallel tracks
    for lb in [6, 9]:
        track_dir = out_dir / f"L{lb}"
        track_dir.mkdir(exist_ok=True)
        locks = {"lookback_months": lb}

        print(f"\n--- TRACK L{lb} ---")
        # 2. top_n
        df = run_sweep(ctx, panel_cache, "top_n", [15, 20, 24, 30, 40], locks, "top_n")
        df.to_csv(track_dir / "is_top_n.csv", index=False)
        print(f"top_n: {df.to_string(index=False)}")

        locks["top_n"] = 24

        # 3. min_hold_days
        df = run_sweep(ctx, panel_cache, "min_hold_days", [0, 8, 15], locks, "min_hold")
        df.to_csv(track_dir / "is_min_hold_days.csv", index=False)
        print(f"min_hold_days: {df.to_string(index=False)}")

        locks["min_hold_days"] = 8

        # 4. vol_floor
        df = run_sweep(ctx, panel_cache, "vol_floor",
                       [0.01, 0.03, 0.05, 0.10, 0.20], locks, "vol_floor")
        df.to_csv(track_dir / "is_vol_floor.csv", index=False)
        print(f"vol_floor: {df.to_string(index=False)}")

        # 5. skip_days (test under default vol_floor=0.05 to compare)
        sd_locks = {**locks, "vol_floor": 0.05}
        df = run_sweep(ctx, panel_cache, "skip_days", [0, 5, 21], sd_locks, "skip")
        df.to_csv(track_dir / "is_skip_days.csv", index=False)
        print(f"skip_days (vf=0.05): {df.to_string(index=False)}")

        # 6. exit_buffer (test under default config)
        eb_locks = {**locks, "vol_floor": 0.05, "skip_days": 5}
        df = run_sweep(ctx, panel_cache, "exit_buffer", [0, 3, 6, 12], eb_locks, "exit_buffer")
        df.to_csv(track_dir / "is_exit_buffer.csv", index=False)
        print(f"exit_buffer (vf=0.05, skip=5): {df.to_string(index=False)}")


if __name__ == "__main__":
    main()
