"""Compare locked-in OM25 winner with vs without 200 DMA exit enabled.

Bug fix: previously `use_trailing_stop=False` disabled BOTH the ATR
trailing stop AND the 200 DMA exit (both gated behind same flag). Now
they're independent toggles. This run tests whether adding 200 DMA exit
back improves the strategy.

Variants (all else equal — Nifty 250 biweekly, 50/50→0/100 tilt, NIFTY 100
regime, lookback 252, top-25/buf-20, return filter on, no ATR stop):
  A) use_dma_exit=False (current locked-in baseline)
  B) use_dma_exit=True  (200 DMA cut-out re-enabled)
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from scripts._clean_engine import (
    run_strategy,
    fridays, biweekly_fridays, monthly_first_trading_day,
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


def run_one(use_dma_exit: bool, label: str):
    print(f"\n{'='*60}\n{label}  (use_dma_exit={use_dma_exit})\n{'='*60}")
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

    res = run_strategy(
        close_panel=close_panel, trade_panel=trade_panel,
        calendar=calendar, benchmark_aligned=benchmark_aligned,
        entry_signal_dates=entry_dates,
        weekly_signal_dates=weekly_filt,
        signal_function=score_fn, signal_function_args={},
        sma_200_panel=sma_200, atr_20_panel=atr_20,
        top_n=25, exit_buffer=20,
        atr_mult=0.0, atr_min_floor=0.0,
        max_weight=0.075, slippage=0.002,
        use_trailing_stop=False, use_dma_exit=use_dma_exit,
        regime_panel=None, bear_exposure=0.0,
    )

    eq = res["equity"]
    trades = res["trades"]
    exits = res["exits"]

    win_eval = evaluate_all_windows(eq)
    ok, _ = passes_criteria(win_eval)

    print(f"\nTrades: {len(trades)}  (BUY {(trades['side']=='BUY').sum()} / SELL {(trades['side']=='SELL').sum()})")
    print(f"Exits: {len(exits)}")
    print(f"\nExit reasons:")
    if "reason" in exits.columns:
        rc = exits["reason"].value_counts()
        for r, n in rc.items():
            print(f"  {r:>10}: {n:>4} ({n/len(exits)*100:.1f}%)")
        print(f"\nAvg PnL by reason:")
        grp = exits.groupby("reason").agg(
            count=("pnl_pct", "count"),
            avg_pnl=("pnl_pct", "mean"),
            median_pnl=("pnl_pct", "median"),
            hit_rate=("pnl_pct", lambda s: (s > 0).mean()),
            avg_hold=("hold_days", "mean"),
        ).round(3)
        print(grp.to_string())

    print(f"\n=== Per-window metrics ===")
    print(win_eval.to_string(index=False))
    print(f"\nPASS: {ok}")
    return eq, trades, exits, win_eval


# Run both variants
eqA, trA, exA, wA = run_one(False, "A) Locked-in (no DMA exit)")
eqB, trB, exB, wB = run_one(True,  "B) With 200 DMA exit ON")

# Summary comparison
print(f"\n{'='*70}")
print("COMPARISON (OOS_full)")
print(f"{'='*70}")
def grab(w, key):
    r = w[w["window"] == "OOS_full"].iloc[0]
    return r.get(key)

print(f"  Variant A (no DMA):   CAGR {grab(wA,'cagr_pct'):>5}%  Sharpe {grab(wA,'sharpe'):>4}  DD {grab(wA,'max_dd_pct'):>5}%  Exits {len(exA)}")
print(f"  Variant B (DMA on):   CAGR {grab(wB,'cagr_pct'):>5}%  Sharpe {grab(wB,'sharpe'):>4}  DD {grab(wB,'max_dd_pct'):>5}%  Exits {len(exB)}")
print(f"  Δ B-A:                CAGR {grab(wB,'cagr_pct')-grab(wA,'cagr_pct'):+5.2f}pp  Sharpe {grab(wB,'sharpe')-grab(wA,'sharpe'):+5.2f}  DD {grab(wB,'max_dd_pct')-grab(wA,'max_dd_pct'):+5.2f}pp")

# Save
out = ROOT / "tasks/oos_retune_2026/winner_artifacts"
exB.to_csv(out / "om25_with_dma_exits.csv", index=False)
trB.to_csv(out / "om25_with_dma_trades.csv", index=False)
print(f"\n[wrote] B variant trades & exits to {out}/")
