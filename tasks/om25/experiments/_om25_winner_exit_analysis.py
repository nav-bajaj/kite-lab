"""Re-run the OM25 winner config and analyze exit reasons.

User question: how many exits come from rank vs 200 DMA?
Concern: 200 DMA may not be firing at all given the current
use_trailing_stop=False setting.
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
from tasks.om25.experiments._om25_regime_100dma_3conf import (
    build_regime_panel_confirmed,
)
from tasks.om25.experiments._om25_regime_weight_tilt import make_om25_tilt_score


PRICES_DIR = ROOT / "nse500_data_merged"
BENCHMARK = ROOT / "data/benchmarks/nifty100.csv"

# Locked-in winner config
LOCKED_CFG = dict(
    universe=ROOT / "data/static/nifty250_universe.csv",
    cadence="biweekly",
    regime_index=ROOT / "indices_data_historical/NIFTY_100.csv",
    bull_uc=0.5, bull_cr=0.5,
    bear_uc=0.0, bear_cr=1.0,
    lookback=252, min_obs=220,
    top_n=25, exit_buffer=20,
    return_filter=True,
    use_trailing_stop=False,
)


def main():
    print("[load] panels...")
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

    universe = load_universe(LOCKED_CFG["universe"])
    cols = [s for s in close_panel.columns if s in universe]
    returns_uni = close_panel[cols].pct_change()

    regime = build_regime_panel_confirmed(
        LOCKED_CFG["regime_index"], 100, 3, calendar=calendar
    )
    score_fn = make_om25_tilt_score(
        returns_uni, regime,
        bull_uc=LOCKED_CFG["bull_uc"], bull_cr=LOCKED_CFG["bull_cr"],
        bear_uc=LOCKED_CFG["bear_uc"], bear_cr=LOCKED_CFG["bear_cr"],
        return_filter=LOCKED_CFG["return_filter"],
        lookback=LOCKED_CFG["lookback"], min_obs=LOCKED_CFG["min_obs"],
    )

    print(f"[run] use_trailing_stop={LOCKED_CFG['use_trailing_stop']}")
    res = run_strategy(
        close_panel=close_panel, trade_panel=trade_panel,
        calendar=calendar, benchmark_aligned=benchmark_aligned,
        entry_signal_dates=entry_dates,
        weekly_signal_dates=weekly_filt,
        signal_function=score_fn, signal_function_args={},
        sma_200_panel=sma_200, atr_20_panel=atr_20,
        top_n=LOCKED_CFG["top_n"], exit_buffer=LOCKED_CFG["exit_buffer"],
        atr_mult=0.0, atr_min_floor=0.0,
        max_weight=0.075, slippage=0.002,
        use_trailing_stop=LOCKED_CFG["use_trailing_stop"],
        regime_panel=None, bear_exposure=0.0,
    )

    trades = res["trades"]
    exits = res["exits"]
    print(f"\nTotal trades: {len(trades)}")
    print(f"  BUY:  {(trades['side'] == 'BUY').sum()}")
    print(f"  SELL: {(trades['side'] == 'SELL').sum()}")
    print(f"\nExit records: {len(exits)}")

    print("\n=== SELL trades by reason ===")
    sells = trades[trades["side"] == "SELL"]
    if "reason" in sells.columns:
        reason_counts = sells["reason"].value_counts()
        print(reason_counts)
        print(f"\n  Total sells: {len(sells)}")
        for reason, n in reason_counts.items():
            print(f"  {reason:>20}: {n:>4} ({n/len(sells)*100:.1f}%)")

    print("\n=== Exit records by reason ===")
    if "reason" in exits.columns:
        exit_reason_counts = exits["reason"].value_counts()
        print(exit_reason_counts)
        # PnL by reason
        print("\n=== Avg PnL% by exit reason ===")
        if "pnl_pct" in exits.columns:
            grouped = exits.groupby("reason").agg(
                count=("pnl_pct", "count"),
                avg_pnl=("pnl_pct", "mean"),
                median_pnl=("pnl_pct", "median"),
                hit_rate=("pnl_pct", lambda s: (s > 0).mean()),
                avg_hold=("hold_days", "mean") if "hold_days" in exits.columns else ("pnl_pct", "count"),
            )
            print(grouped.round(3).to_string())

    # Save for inspection
    out = ROOT / "tasks/oos_retune_2026/winner_artifacts"
    trades.to_csv(out / "om25_winner_trades.csv", index=False)
    exits.to_csv(out / "om25_winner_exits.csv", index=False)
    print(f"\n[wrote] {out}/om25_winner_trades.csv")
    print(f"[wrote] {out}/om25_winner_exits.csv")


if __name__ == "__main__":
    main()
