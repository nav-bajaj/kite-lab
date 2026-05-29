"""Phase 2 baseline — VIX-led stress-buyer strategy.

Rules:
  - VIX z-score (252d) ≥ +1.0  → long 100% (panic / capitulation)
  - VIX z-score ≤ -1.0 AND sector breadth (200dma) > 80% → short 50% (extreme complacency)
  - Otherwise cash

Adds an "OOS check" by running the same config IS-only (2010-2018) and OOS-only
(2019-2026) separately. If OOS Sharpe collapses, the signal is suspect.

This is INTENTIONALLY simple. Phase 3 will add costs; Phase 4 will explore
multi-signal combinations.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from backtest import BacktestConfig, print_summary, run_backtest
from breadth_signals import build_or_load as load_breadth
from macro_signals import build_or_load as load_macro

INDICES_DIR = Path("/Users/navdeep/Documents/stock_data/indices_data_full")
IS_START = pd.Timestamp("2010-01-04")
IS_END = pd.Timestamp("2018-12-31")
OOS_START = pd.Timestamp("2019-01-01")
OOS_END = pd.Timestamp("2026-05-12")


def load_nifty() -> pd.Series:
    df = pd.read_csv(INDICES_DIR / "NIFTY_50.csv", parse_dates=["date"])
    return df.set_index("date")["close"].sort_index()


def build_feature_panel() -> pd.DataFrame:
    breadth = load_breadth()
    macro = load_macro()
    panel = pd.concat([breadth, macro], axis=1)
    return panel


def vix_stress_signal(nifty: pd.Series, panel: pd.DataFrame,
                       long_z: float = 1.0,
                       short_z: float = -1.0,
                       short_breadth: float = 0.80,
                       long_size: float = 1.0,
                       short_size: float = -0.5) -> pd.Series:
    """Continuous position based on VIX z-score + sector breadth filter."""
    aligned = panel.reindex(nifty.index).ffill()
    vix_z = aligned["vix_zscore_252d"]
    sector_above = aligned["sector_pct_above_200dma"]

    long_mask = vix_z >= long_z
    short_mask = (vix_z <= short_z) & (sector_above >= short_breadth)

    pos = pd.Series(0.0, index=nifty.index)
    pos[long_mask] = long_size
    pos[short_mask] = short_size
    return pos


def main() -> None:
    nifty = load_nifty()
    panel = build_feature_panel()

    print(f"Phase 2 baseline — VIX stress-buyer\n")

    # Full window — no costs first
    cfg_full = BacktestConfig(
        explicit_cost_bps_per_rt=0,
        roll_cost_bps_per_month=0,
        apply_roll_cost=False,
        name="VIX stress (full, no cost)",
    )
    nifty_full = nifty.loc["2010-01-04":"2026-05-12"]
    res_full = run_backtest(nifty_full, vix_stress_signal, panel, cfg_full)
    print_summary(res_full, header="Full window, zero cost (sanity)")

    # IS window
    cfg_is = BacktestConfig(
        explicit_cost_bps_per_rt=0,
        roll_cost_bps_per_month=0,
        apply_roll_cost=False,
        name="VIX stress (IS, no cost)",
    )
    nifty_is = nifty.loc[IS_START:IS_END]
    res_is = run_backtest(nifty_is, vix_stress_signal, panel, cfg_is)
    print_summary(res_is, header="IS 2010-2018, zero cost")

    # OOS window
    nifty_oos = nifty.loc[OOS_START:OOS_END]
    res_oos = run_backtest(nifty_oos, vix_stress_signal, panel, cfg_is)
    print_summary(res_oos, header="OOS 2019-2026, zero cost")

    # Full with realistic costs (5 bps RT, 10 bps roll)
    cfg_cost = BacktestConfig(name="VIX stress (full, with costs)")
    res_cost = run_backtest(nifty_full, vix_stress_signal, panel, cfg_cost)
    print_summary(res_cost, header="Full window, with 5bp explicit + 10bp/mo roll")

    # Quick parameter sensitivity
    print("\n\n=== Parameter sensitivity (Full window, no costs) ===")
    print(f"  {'long_z':<8} {'short_z':<9} {'long_size':<11} {'short_size':<12}"
          f"{'CAGR':>8} {'Sharpe':>8} {'MaxDD':>8} {'Time-long':>10} {'Time-short':>11}")
    grid = [
        (0.5, -0.5, 1.0, -0.5),
        (1.0, -1.0, 1.0, -0.5),
        (1.5, -1.5, 1.0, -0.5),
        (1.0, -1.0, 1.0,  0.0),  # long-only variant
        (1.0, -1.0, 0.5, -0.25),
    ]
    for lz, sz, ls, ss in grid:
        sig = lambda n, p, lz=lz, sz=sz, ls=ls, ss=ss: vix_stress_signal(n, p, lz, sz, 0.8, ls, ss)
        r = run_backtest(nifty_full, sig, panel, cfg_full)
        tip = r.time_in_position
        print(f"  {lz:<8} {sz:<9} {ls:<11} {ss:<12}"
              f"{r.cagr*100:>7.2f}% {r.sharpe:>8.2f} {r.max_drawdown*100:>7.2f}% "
              f"{tip['long']*100:>9.1f}% {tip['short']*100:>10.1f}%")


if __name__ == "__main__":
    main()
