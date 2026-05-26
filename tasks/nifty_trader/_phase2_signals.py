"""Phase 2 — explore several signal designs against zero-cost benchmark.

Design choices being tested:
  S1  pure VIX-stress event driven (baseline, mostly flat — sanity check)
  S2  long-bias with low-VIX defensive cut
  S3  continuous VIX-tilted exposure (scale 0→100% by VIX percentile)
  S4  S3 + breadth deterioration short overlay
  S5  S3 + 200-DMA exit (Nifty cash > 200-DMA gate)
  S6  S5 + bear-regime short
  S7  S5 + cumulative A/D rate-of-change for sizing tilt
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable

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


def feature_panel() -> pd.DataFrame:
    return pd.concat([load_breadth(), load_macro()], axis=1)


# ---------- signal definitions ----------

def s1_vix_event(nifty, panel):
    """Pure event-driven: long when VIX z >= +1, short when VIX z <= -1 + complacent breadth."""
    p = panel.reindex(nifty.index).ffill()
    z = p["vix_zscore_252d"]
    breadth = p["sector_pct_above_200dma"]
    pos = pd.Series(0.0, index=nifty.index)
    pos[z >= 1.0] = 1.0
    pos[(z <= -1.0) & (breadth >= 0.80)] = -0.5
    return pos


def s2_long_bias_low_vix_cut(nifty, panel):
    """Default long; cut to 0.5 when VIX z < -1.5 (extreme complacency)."""
    p = panel.reindex(nifty.index).ffill()
    z = p["vix_zscore_252d"]
    pos = pd.Series(1.0, index=nifty.index)
    pos[z < -1.5] = 0.5
    return pos


def s3_vix_tilt(nifty, panel, alpha: float = 0.3, base: float = 0.7):
    """Continuous: position = base + alpha × tanh(VIX z). Range ~[0.4, 1.0]."""
    p = panel.reindex(nifty.index).ffill()
    z = p["vix_zscore_252d"].fillna(0)
    pos = base + alpha * np.tanh(z / 1.5)
    return pos.clip(0, 1)


def s4_vix_tilt_breadth_short(nifty, panel):
    """S3 + short overlay when breadth severely deteriorating AND VIX rising sharply."""
    p = panel.reindex(nifty.index).ffill()
    pos = s3_vix_tilt(nifty, panel)
    # Breadth deterioration: pct_above_200dma falling AND VIX z rising
    pct200 = p["pct_above_200dma"]
    pct200_roc_20d = pct200 - pct200.shift(20)  # 20d change
    vix_z = p["vix_zscore_252d"]
    vix_z_roc_10d = vix_z - vix_z.shift(10)

    short_mask = (pct200_roc_20d < -0.15) & (vix_z_roc_10d > 0.5) & (pct200 < 0.5)
    pos[short_mask] = -0.3
    return pos


def s5_vix_tilt_200dma_gate(nifty, panel):
    """S3 but gate to zero if Nifty < 200-DMA (the COMBO-style regime gate)."""
    p = panel.reindex(nifty.index).ffill()
    pos = s3_vix_tilt(nifty, panel)
    nifty_200dma = nifty.rolling(200, min_periods=200).mean()
    bear_regime = nifty < nifty_200dma
    pos[bear_regime] = 0.0
    return pos


def s6_vix_tilt_200dma_short_bear(nifty, panel):
    """S5 but go SHORT (modest) when Nifty firmly below 200-DMA + VIX rising."""
    p = panel.reindex(nifty.index).ffill()
    pos = s5_vix_tilt_200dma_gate(nifty, panel)
    nifty_200dma = nifty.rolling(200, min_periods=200).mean()
    nifty_pct_below_200 = (nifty / nifty_200dma) - 1.0
    deep_bear = nifty_pct_below_200 < -0.05  # 5% below 200dma
    vix_z = p["vix_zscore_252d"]
    pos[deep_bear & (vix_z > 0.5)] = -0.3
    return pos


def s7_vix_ad_compound(nifty, panel):
    """S5 + tilt position upward when cumulative_ad has been declining steeply
    (panic conditioning enhances long entry)."""
    p = panel.reindex(nifty.index).ffill()
    pos = s5_vix_tilt_200dma_gate(nifty, panel)
    cum_ad = p["cumulative_ad"]
    cum_ad_roc_20d = cum_ad - cum_ad.shift(20)
    # Boost long exposure when cum_ad has been falling AND we're in long regime
    panic_long_boost = (cum_ad_roc_20d < -5.0) & (pos > 0)
    pos = pos.where(~panic_long_boost, 1.0)
    return pos


# ---------- runner ----------

def compare(nifty: pd.Series, panel: pd.DataFrame, signals: dict, cfg: BacktestConfig):
    print(f"\n{'='*92}")
    print(f"  Configuration: {cfg.name}")
    print(f"{'='*92}")
    print(f"  {'Strategy':<8} {'Period':<25} {'CAGR':>8} {'Sharpe':>8} "
          f"{'MaxDD':>8} {'Calmar':>8} {'Time-long':>10} {'Time-flat':>10} {'Time-short':>11}")
    print("  " + "-" * 100)
    for name, fn in signals.items():
        r = run_backtest(nifty, fn, panel, cfg)
        tip = r.time_in_position
        print(f"  {name:<8} {str(r.equity.index[0].date())+' → '+str(r.equity.index[-1].date()):<25} "
              f"{r.cagr*100:>7.2f}% {r.sharpe:>8.2f} {r.max_drawdown*100:>7.2f}% "
              f"{r.calmar:>8.2f} {tip['long']*100:>9.1f}% {tip['flat']*100:>9.1f}% {tip['short']*100:>10.1f}%")
    # Benchmark
    bh_res = run_backtest(nifty, lambda n, p: pd.Series(1.0, index=n.index), panel, cfg)
    btip = bh_res.time_in_position
    print(f"  {'B&H':<8} {str(bh_res.equity.index[0].date())+' → '+str(bh_res.equity.index[-1].date()):<25} "
          f"{bh_res.cagr*100:>7.2f}% {bh_res.sharpe:>8.2f} {bh_res.max_drawdown*100:>7.2f}% "
          f"{bh_res.calmar:>8.2f} {btip['long']*100:>9.1f}% {btip['flat']*100:>9.1f}% {btip['short']*100:>10.1f}%")


def main() -> None:
    nifty = load_nifty()
    panel = feature_panel()

    signals = {
        "S1": s1_vix_event,
        "S2": s2_long_bias_low_vix_cut,
        "S3": s3_vix_tilt,
        "S4": s4_vix_tilt_breadth_short,
        "S5": s5_vix_tilt_200dma_gate,
        "S6": s6_vix_tilt_200dma_short_bear,
        "S7": s7_vix_ad_compound,
    }

    print("S1 = pure event-driven (mostly flat)")
    print("S2 = long-bias, cut to 0.5 on low-VIX")
    print("S3 = continuous VIX-tilted [0.4-1.0]")
    print("S4 = S3 + breadth-deterioration short")
    print("S5 = S3 + 200-DMA gate (flat when Nifty < 200-DMA)")
    print("S6 = S5 + modest bear-regime short")
    print("S7 = S5 + cumulative A/D panic boost on long entries")

    # Full window, zero cost
    full = nifty.loc["2010-01-04":"2026-05-12"]
    compare(full, panel, signals, BacktestConfig(
        explicit_cost_bps_per_rt=0, roll_cost_bps_per_month=0,
        apply_roll_cost=False, name="Full window, ZERO cost"))

    # Full window with realistic costs
    compare(full, panel, signals, BacktestConfig(name="Full window, 5bp explicit + 10bp/mo roll"))

    # IS / OOS split
    compare(nifty.loc[IS_START:IS_END], panel, signals,
            BacktestConfig(explicit_cost_bps_per_rt=0, roll_cost_bps_per_month=0,
                            apply_roll_cost=False, name="IS 2010-2018 zero cost"))
    compare(nifty.loc[OOS_START:OOS_END], panel, signals,
            BacktestConfig(explicit_cost_bps_per_rt=0, roll_cost_bps_per_month=0,
                            apply_roll_cost=False, name="OOS 2019-2026 zero cost"))


if __name__ == "__main__":
    main()
