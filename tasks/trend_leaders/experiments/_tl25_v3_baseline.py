"""TL25 v3 baseline + IS sweep on 2009-2016 IS window.

Step 1: reproduce V2 baseline on the GDF-merged panel — establish IS
numbers we'll compare against.

Step 2: explore stop variants on IS only (no OOS peeking). TL25 V2 has
TWO stops (200 DMA + 5× ATR-equivalent). Test:
  - Current V2 (both stops)
  - No stops at all
  - 200 DMA only (drop ATR)
  - ATR only (drop 200 DMA)
  - Fixed 20% DD stop (like OM25 v3, no 200 DMA)
  - ATR 3×, 5×, 7×

This mirrors the OM25 stop investigation. We learned there that the V2
"ATR" (which was actually 20-day return-vol, not true OHLC ATR) hurt
performance. TL25 uses the same atr_20_panel, so the same caveats apply.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from scripts._clean_engine import (
    run_strategy, fridays, biweekly_fridays, monthly_first_trading_day,
)
from scripts.backtest_momentum import load_price_panels, load_benchmark
from scripts.build_om25_signals import load_universe
from scripts.multi_window_oos_eval import period_metrics
from scripts.tl25_v3 import V2_LOCKED, build_tl25_panels, make_tl25_score


PRICES_DIR = ROOT / "nse500_data_merged"
BENCHMARK = ROOT / "data/benchmarks/nifty100.csv"
UNIVERSE = ROOT / "data/static/nse500_universe.csv"
IS_END = "2016-12-31"


def setup():
    print("[load] panels...", flush=True)
    close_panel, trade_panel = load_price_panels(PRICES_DIR)
    calendar = close_panel.index
    benchmark = load_benchmark(BENCHMARK)
    benchmark_aligned = benchmark.reindex(calendar).ffill()

    print("[compute] TL25 panels (sma, persistence, drawdown, momentum)...", flush=True)
    universe = load_universe(UNIVERSE)
    cols = [s for s in close_panel.columns if s in universe]
    close_uni = close_panel[cols]
    panels = build_tl25_panels(close_uni)

    sma_200_full = close_panel.rolling(200, min_periods=200).mean()
    weekly_fri = fridays(calendar)
    biweekly_fri = biweekly_fridays(calendar)
    monthly_first = monthly_first_trading_day(calendar)
    weekly_filt = weekly_fri[weekly_fri >= close_panel.index[252]]
    entry_dates = biweekly_fri[biweekly_fri >= close_panel.index[252]]

    return dict(
        close_panel=close_panel, trade_panel=trade_panel, calendar=calendar,
        benchmark_aligned=benchmark_aligned, sma_200=sma_200_full,
        weekly_filt=weekly_filt, entry_dates=entry_dates,
        biweekly_fri=biweekly_fri, monthly_first=monthly_first,
        panels=panels,
    )


def run_one(label, ctx, *, atr_panel=None, atr_mult=0.0, atr_min_floor=0.0,
            use_trailing_stop=False, use_dma_exit=False,
            w_persistence=1/3, w_drawdown=1/3, w_momentum=1/3):
    t0 = time.time()
    print(f"  [run] {label} ...", flush=True)

    if atr_panel is None:
        atr_panel = ctx["close_panel"].pct_change().rolling(20).std()

    score_fn = make_tl25_score(
        ctx["panels"],
        w_persistence=w_persistence,
        w_drawdown=w_drawdown,
        w_momentum=w_momentum,
    )

    res = run_strategy(
        close_panel=ctx["close_panel"], trade_panel=ctx["trade_panel"],
        calendar=ctx["calendar"], benchmark_aligned=ctx["benchmark_aligned"],
        entry_signal_dates=ctx["entry_dates"], weekly_signal_dates=ctx["weekly_filt"],
        signal_function=score_fn, signal_function_args={},
        sma_200_panel=ctx["sma_200"], atr_20_panel=atr_panel,
        top_n=25, exit_buffer=20, max_weight=0.075, slippage=0.002,
        atr_mult=atr_mult, atr_min_floor=atr_min_floor,
        use_trailing_stop=use_trailing_stop, use_dma_exit=use_dma_exit,
        regime_panel=None, bear_exposure=0.0,
    )
    eq = res["equity"]
    trades = res["trades"]
    exits = res["exits"]
    is_m = period_metrics(eq, "IS", "2009-09-01", IS_END)

    if not exits.empty:
        exits["exit_date"] = pd.to_datetime(exits["exit_date"])
        is_exits = exits[exits["exit_date"] <= pd.Timestamp(IS_END)]
    else:
        is_exits = exits
    by_reason = is_exits["reason"].value_counts().to_dict() if not is_exits.empty else {}

    elapsed = time.time() - t0
    is_cagr = is_m.get("cagr_pct", "?")
    is_sh = is_m.get("sharpe", "?")
    is_dd = is_m.get("max_dd_pct", "?")
    print(f"      done {elapsed:.0f}s — CAGR={is_cagr} Sharpe={is_sh} DD={is_dd}  "
          f"exits={len(is_exits)}  ({by_reason})", flush=True)

    return {
        "label": label,
        "is_cagr": is_cagr,
        "is_sharpe": is_sh,
        "is_dd": is_dd,
        "is_vol": is_m.get("vol_pct"),
        "exits_total_is": len(is_exits),
        "exits_rank_is": by_reason.get("rank", 0),
        "exits_atr_is": by_reason.get("atr_stop", 0),
        "exits_dma_is": by_reason.get("200dma", 0),
    }


def main():
    ctx = setup()
    out_dir = ROOT / f"experiments/oos_retune/{pd.Timestamp.now().strftime('%Y%m%d%H%M%S')}_tl25_v3_baseline_is"
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n[sweep] IS-only stop variants on TL25 V2 score (equal 1/3 weights)\n", flush=True)
    rows = []

    # Baseline: V2 production (200 DMA + 5x ATR-equivalent on default panel)
    rows.append(run_one(
        "V2 baseline: 200 DMA + 5x ATR(return-vol)", ctx,
        atr_mult=5.0, atr_min_floor=0.0,
        use_trailing_stop=True, use_dma_exit=True,
    ))

    # No stops at all
    rows.append(run_one(
        "No stops (rank-only exit)", ctx,
        atr_mult=0.0, atr_min_floor=0.0,
        use_trailing_stop=False, use_dma_exit=False,
    ))

    # 200 DMA only
    rows.append(run_one(
        "200 DMA only", ctx,
        atr_mult=0.0, atr_min_floor=0.0,
        use_trailing_stop=False, use_dma_exit=True,
    ))

    # ATR(return-vol) only — drop 200 DMA, test ATR multipliers
    for mult in (3.0, 5.0, 7.0):
        rows.append(run_one(
            f"ATR(return-vol) {mult}x only (no 200 DMA)", ctx,
            atr_mult=mult, atr_min_floor=0.0,
            use_trailing_stop=True, use_dma_exit=False,
        ))

    # Fixed % DD stop only (atr_mult=0 + min_floor=X)
    for pct in (0.15, 0.20, 0.25):
        rows.append(run_one(
            f"Fixed {int(pct*100)}% DD stop only", ctx,
            atr_mult=0.0, atr_min_floor=pct,
            use_trailing_stop=True, use_dma_exit=False,
        ))

    # 200 DMA + fixed 20% DD
    rows.append(run_one(
        "200 DMA + Fixed 20% DD", ctx,
        atr_mult=0.0, atr_min_floor=0.20,
        use_trailing_stop=True, use_dma_exit=True,
    ))

    df = pd.DataFrame(rows)
    df.to_csv(out_dir / "is_stop_sweep.csv", index=False)

    print(f"\n{'=' * 100}")
    print("TL25 V3 — IS-only stop sweep (2009-09-01 → 2016-12-31). OOS not shown.")
    print(f"{'=' * 100}")
    print(df.to_string(index=False))
    print(f"\n[wrote] {out_dir}/is_stop_sweep.csv")


if __name__ == "__main__":
    main()
