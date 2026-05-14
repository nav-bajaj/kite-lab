"""A2: Trade-ledger diff between new and legacy engines on identical config.

After the Thursday-signal fix, the new engine produces ~54.86% CAGR vs
legacy's ~52.82% on production-config over 2020-07 → 2026-05. The new
engine is now ~2pp HIGHER than legacy (was 10pp lower before Thursday fix).

This script compares trade counts, total notional traded, average position
sizes, and cash/exposure profiles to identify where the 2pp comes from.
Most likely: position sizing logic — legacy uses incremental rebalance
(only new entrants get cash), new engine uses two-pass fair-share.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _summarize_trades(trades, eq, side_col="side"):
    by = trades.groupby(side_col)
    rows = {}
    for side, g in by:
        rows[side] = {
            "n_trades": len(g),
            "total_notional": g.get("notional", pd.Series([0])).sum() if "notional" in g.columns else 0,
            "avg_shares": g.get("shares", pd.Series([0])).mean(),
            "avg_price": g.get("price", pd.Series([0])).mean(),
        }
    return rows


def main():
    print("=== A2: Trade-ledger comparison (new vs legacy, production config) ===\n")

    # Legacy: existing run at /tmp/mm_legacy/bt_PRODUCTION/
    legacy_eq = pd.read_csv("/tmp/mm_legacy/bt_PRODUCTION/momentum_equity.csv",
                             parse_dates=["date"])
    legacy_trades = pd.read_csv("/tmp/mm_legacy/bt_PRODUCTION/momentum_trades.csv",
                                  parse_dates=["date"])
    legacy_holdings = pd.read_csv("/tmp/mm_legacy/bt_PRODUCTION/momentum_holdings.csv")

    print("Legacy backtest (incremental rebalance mode, Thursday signals):")
    print(f"  Start: {legacy_eq['date'].iloc[0].date()}  End: {legacy_eq['date'].iloc[-1].date()}")
    print(f"  Start PV: ₹{legacy_eq['portfolio_value'].iloc[0]:,.0f}  "
          f"End PV: ₹{legacy_eq['portfolio_value'].iloc[-1]:,.0f}")
    days = (legacy_eq['date'].iloc[-1] - legacy_eq['date'].iloc[0]).days
    yrs = days / 365.25
    cagr = (legacy_eq['portfolio_value'].iloc[-1] / legacy_eq['portfolio_value'].iloc[0]) ** (1/yrs) - 1
    print(f"  CAGR: {cagr*100:.2f}%   Years: {yrs:.2f}")
    print(f"  Total trades: {len(legacy_trades)}")
    print(f"  Final holdings count: {len(legacy_holdings) if not legacy_holdings.empty else 0}")
    legacy_summary = _summarize_trades(legacy_trades, legacy_eq)
    for side, m in legacy_summary.items():
        print(f"    {side}: n={m['n_trades']}, total notional=₹{m['total_notional']:,.0f}, "
              f"avg shares={m['avg_shares']:.0f}, avg price=₹{m['avg_price']:.2f}")

    # Run NEW engine on production config (Thursday signals) to compare
    from scripts._momentum_engine import (
        BASELINE, build_momentum_panels, run_momentum,
        lookback_months_to_days,
    )
    from scripts.backtest_momentum import load_price_panels, load_benchmark
    from scripts.build_om25_signals import load_universe

    print("\n[new engine] running production config on same window ...")
    close_panel, trade_panel = load_price_panels(ROOT / "nse500_data")
    calendar = close_panel.index
    benchmark = load_benchmark(ROOT / "data/benchmarks/nifty100.csv")
    benchmark_aligned = benchmark.reindex(calendar).ffill()
    sma_200 = close_panel.rolling(200, min_periods=200).mean()
    atr_20 = close_panel.pct_change().rolling(20).std()
    universe = load_universe(ROOT / BASELINE["universe_csv"])
    cols = [s for s in close_panel.columns if s in universe]
    close_uni = close_panel[cols]
    panels = build_momentum_panels(
        close_uni,
        lookback_days=lookback_months_to_days(BASELINE["lookback_months"]),
        skip_days=BASELINE["skip_days"],
    )
    res = run_momentum(
        close_panel=close_panel, trade_panel=trade_panel,
        calendar=calendar, benchmark_aligned=benchmark_aligned,
        panels=panels, sma_200_panel=sma_200, atr_20_panel=atr_20,
        start="2020-07-10", end="2026-05-12", config={},
    )
    new_eq = res["equity"]
    new_trades = res["trades"]

    print(f"\nNew engine backtest (two-pass fair-share allocation, Thursday signals):")
    print(f"  Start: {pd.to_datetime(new_eq['date'].iloc[0]).date()}  End: {pd.to_datetime(new_eq['date'].iloc[-1]).date()}")
    print(f"  Start PV: ₹{new_eq['pv'].iloc[0]:,.0f}  End PV: ₹{new_eq['pv'].iloc[-1]:,.0f}")
    days = (pd.to_datetime(new_eq['date'].iloc[-1]) - pd.to_datetime(new_eq['date'].iloc[0])).days
    yrs = days / 365.25
    cagr_new = (new_eq['pv'].iloc[-1] / new_eq['pv'].iloc[0]) ** (1/yrs) - 1
    print(f"  CAGR: {cagr_new*100:.2f}%   Years: {yrs:.2f}")
    print(f"  Total trades: {len(new_trades)}")
    new_summary = _summarize_trades(new_trades, new_eq)
    for side, m in new_summary.items():
        print(f"    {side}: n={m['n_trades']}, total notional=₹{m['total_notional']:,.0f}, "
              f"avg shares={m['avg_shares']:.0f}, avg price=₹{m['avg_price']:.2f}")

    # === Diff analysis ===
    print(f"\n=== DIFF ANALYSIS ===")
    # 1. Cash drag — average cash as % of PV through time
    legacy_eq["cash_pct"] = legacy_eq["cash"] / legacy_eq["portfolio_value"] * 100
    new_eq_full = pd.read_csv(StringIO(new_eq.to_csv(index=False)),
                                parse_dates=["date"]) if False else new_eq.copy()
    new_eq_full["date"] = pd.to_datetime(new_eq_full["date"])
    if "cash" in new_eq_full.columns and "pv" in new_eq_full.columns:
        new_eq_full["cash_pct"] = new_eq_full["cash"] / new_eq_full["pv"] * 100
        print(f"\n  Avg cash %:")
        print(f"    Legacy: {legacy_eq['cash_pct'].mean():.2f}% (max={legacy_eq['cash_pct'].max():.1f}%)")
        print(f"    New:    {new_eq_full['cash_pct'].mean():.2f}% (max={new_eq_full['cash_pct'].max():.1f}%)")

    # 2. Average holdings count per day
    if "holdings" in new_eq_full.columns:
        # legacy doesn't have holdings count in equity CSV; estimate from trade ledger
        pass

    # 3. Compare end PVs
    print(f"\n  Final portfolio value (₹1M start):")
    print(f"    Legacy: ₹{legacy_eq['portfolio_value'].iloc[-1]:,.0f}  "
          f"({legacy_eq['portfolio_value'].iloc[-1]/legacy_eq['portfolio_value'].iloc[0]:.2f}×)")
    print(f"    New:    ₹{new_eq['pv'].iloc[-1]:,.0f}  "
          f"({new_eq['pv'].iloc[-1]/new_eq['pv'].iloc[0]:.2f}×)")
    print(f"    Gap: ₹{new_eq['pv'].iloc[-1] - legacy_eq['portfolio_value'].iloc[-1]:,.0f}")

    # 4. Trade-count comparison
    print(f"\n  Trade counts:")
    print(f"    Legacy BUYs/SELLs:  {len(legacy_trades[legacy_trades['side']=='BUY']):>5d} / {len(legacy_trades[legacy_trades['side']=='SELL']):>5d}")
    print(f"    New BUYs/SELLs:     {len(new_trades[new_trades['side']=='BUY']):>5d} / {len(new_trades[new_trades['side']=='SELL']):>5d}")

    # 5. Avg notional per trade
    if "notional" in legacy_trades.columns and "notional" in new_trades.columns:
        print(f"\n  Avg notional per trade:")
        print(f"    Legacy: ₹{legacy_trades['notional'].mean():,.0f}")
        print(f"    New:    ₹{new_trades['notional'].mean():,.0f}")


from io import StringIO


if __name__ == "__main__":
    main()
