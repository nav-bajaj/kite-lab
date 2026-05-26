"""Phase 2 advanced — refine S4 with:
  - Continuous (signal-strength) position sizing
  - DD-aware long boost (lean in when Nifty in drawdown + VIX rising)
  - Multi-signal short specificity (3 conditions must align)
  - VIX rate-of-change conditioning
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from backtest import BacktestConfig, run_backtest
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


# ---- Signal D1: Continuous "stress index" ----
def stress_index(panel: pd.DataFrame, idx: pd.Index) -> pd.Series:
    """Return a continuous stress index in [-1, +1]:
       +1 = max bullish stress (panic = strong long signal)
       -1 = max bearish stress (deterioration + complacency breaking = short signal)
    """
    p = panel.reindex(idx).ffill()
    # Bullish stress components (high = buy)
    vix_z = p["vix_zscore_252d"].fillna(0).clip(-3, 3) / 3.0  # [-1, 1]
    new_lows = p["new_52w_lows_pct"].fillna(0)
    # Normalize new_lows by its rolling 252d max (capped at 0.5 for sanity)
    new_lows_norm = (new_lows / 0.3).clip(0, 1)  # 30% of stocks at 52w lows = max stress
    cum_ad_roc = p["cumulative_ad"].diff(20).fillna(0)
    cum_ad_panic = (-cum_ad_roc / 10.0).clip(0, 1)  # rapid AD decline = panic

    bull_score = (0.5 * vix_z.clip(0) + 0.3 * new_lows_norm + 0.2 * cum_ad_panic).clip(0, 1)

    # Bearish stress (deterioration warning signs)
    pct200 = p["pct_above_200dma"].fillna(0.5)
    pct200_roc = (pct200 - pct200.shift(20)).fillna(0)
    bearish_breadth = (-pct200_roc / 0.3).clip(0, 1)  # 30 pp decline in 20d = max bear
    vix_rising = ((p["vix_zscore_252d"] - p["vix_zscore_252d"].shift(10)).fillna(0) / 1.0).clip(0, 1)
    sector_div = p["sector_breadth_st_lt"].fillna(0)  # < 0 = ST sector breadth lagging LT
    sector_signal = (-sector_div / 0.3).clip(0, 1)

    # All 3 bear components must align (multiplicative, not additive)
    bear_score = (bearish_breadth * vix_rising * sector_signal).clip(0, 1)
    bear_score = bear_score ** (1/3)  # cube root to soften the multiplicative compression

    stress = bull_score - 0.6 * bear_score  # weighted; bear gets smaller weight
    return stress


# ---- D1: Long-bias + signal-tilted ----
def d1_continuous_stress(nifty: pd.Series, panel: pd.DataFrame) -> pd.Series:
    """Continuous: 1.0 default + 0.0 to +0.0 (capped); during bear stress, scale down.

    Mapping:  stress in [-1, +1] → position in [-0.3, +1.0]
      stress=+1.0: position=1.0 (max long, market panic)
      stress=0.0:  position=1.0 (default long)
      stress=-0.5: position=0.5 (cut on warning)
      stress=-1.0: position=-0.3 (short on confirmed deterioration)
    """
    s = stress_index(panel, nifty.index)
    pos = pd.Series(1.0, index=nifty.index)
    # Bear adjustment kicks in only when s < 0
    bear_mask = s < 0
    pos[bear_mask] = 1.0 + 1.3 * s[bear_mask]  # at s=-1, position = -0.3
    return pos.clip(-0.5, 1.0)


# ---- D2: D1 + DD-aware long boost ----
def d2_dd_boost(nifty: pd.Series, panel: pd.DataFrame) -> pd.Series:
    """D1, but when Nifty in 8%+ drawdown, set position to 1.0 unconditionally
    (override any bearish stress). This captures the 'don't be flat at the bottom' idea."""
    pos = d1_continuous_stress(nifty, panel)
    rolling_peak = nifty.rolling(252, min_periods=60).max()
    dd = (nifty / rolling_peak - 1.0)
    deep_dd = dd < -0.08
    pos = pos.where(~deep_dd, 1.0)
    return pos


# ---- D3: D2 + 200-DMA gate (long only when above OR in panic) ----
def d3_dd_boost_gated(nifty: pd.Series, panel: pd.DataFrame) -> pd.Series:
    """D2 + extra rule: if Nifty < 200-DMA AND not in panic territory, cut to 0.3."""
    pos = d2_dd_boost(nifty, panel)
    nifty_200dma = nifty.rolling(200, min_periods=200).mean()
    below_200 = nifty < nifty_200dma
    p = panel.reindex(nifty.index).ffill()
    in_panic = p["vix_zscore_252d"] > 1.0
    cut_mask = below_200 & (~in_panic)
    pos[cut_mask] = pos[cut_mask].clip(upper=0.3)
    return pos


# ---- D4: VIX peak-rollover (enter long ONLY after VIX peaks) ----
def d4_vix_rollover(nifty: pd.Series, panel: pd.DataFrame) -> pd.Series:
    """Long when VIX has spiked AND turned over (5-day low after 20-day high).
    Hold for 60 days or until VIX z normalizes below 0."""
    p = panel.reindex(nifty.index).ffill()
    vix = p["vix_close"]
    vix_20d_high = vix.rolling(20).max()
    vix_5d_high = vix.rolling(5).max()
    was_spiking = (vix_20d_high.shift(5) > vix_20d_high.shift(5).rolling(60).quantile(0.85))
    rolling_over = (vix < vix_5d_high.shift(1)) & was_spiking

    # State machine: enter on signal, hold until VIX z < 0 OR 60 trading days elapsed
    pos = pd.Series(0.0, index=nifty.index)
    in_pos_days = 0
    holding = False
    vix_z = p["vix_zscore_252d"].fillna(0)
    for i, dt in enumerate(nifty.index):
        if holding:
            if vix_z.iloc[i] < 0 or in_pos_days > 60:
                holding = False
                pos.iloc[i] = 0.0
            else:
                pos.iloc[i] = 1.0
                in_pos_days += 1
        else:
            if rolling_over.iloc[i] and vix_z.iloc[i] > 1.0:
                holding = True
                in_pos_days = 1
                pos.iloc[i] = 1.0

    return pos


# ---- runner ----

def evaluate(name, fn, nifty, panel, cfg):
    r = run_backtest(nifty, fn, panel, cfg)
    tip = r.time_in_position
    return {
        "name": name,
        "period": f"{r.equity.index[0].date()} → {r.equity.index[-1].date()}",
        "years": r.years,
        "cagr": r.cagr * 100,
        "sharpe": r.sharpe,
        "max_dd": r.max_drawdown * 100,
        "calmar": r.calmar,
        "tlong": tip["long"] * 100,
        "tflat": tip["flat"] * 100,
        "tshort": tip["short"] * 100,
        "n_trades": r.n_trades,
    }


def print_table(rows, title):
    print(f"\n{'='*100}\n{title}\n{'='*100}")
    print(f"  {'Strategy':<8} {'CAGR':>8} {'Sharpe':>8} {'MaxDD':>8} {'Calmar':>8} "
          f"{'TimeL':>7} {'TimeF':>7} {'TimeS':>7} {'Trades':>8}")
    for r in rows:
        print(f"  {r['name']:<8} {r['cagr']:>7.2f}% {r['sharpe']:>8.2f} {r['max_dd']:>7.2f}% "
              f"{r['calmar']:>8.2f} {r['tlong']:>6.1f}% {r['tflat']:>6.1f}% {r['tshort']:>6.1f}% {r['n_trades']:>8}")


def main():
    nifty = load_nifty()
    panel = feature_panel()

    signals = {"D1": d1_continuous_stress, "D2": d2_dd_boost,
               "D3": d3_dd_boost_gated, "D4": d4_vix_rollover}

    def bh_signal(n, p):
        return pd.Series(1.0, index=n.index)

    cfg_zero = BacktestConfig(explicit_cost_bps_per_rt=0, roll_cost_bps_per_month=0,
                                apply_roll_cost=False, name="zero cost")
    cfg_full = BacktestConfig(name="5bp + 10bp/mo")

    for window_name, w_start, w_end in [
        ("Full 2010-2026", "2010-01-04", "2026-05-12"),
        ("IS 2010-2018",   IS_START, IS_END),
        ("OOS 2019-2026",  OOS_START, OOS_END),
    ]:
        n = nifty.loc[w_start:w_end]
        rows = []
        for name, fn in signals.items():
            rows.append(evaluate(name, fn, n, panel, cfg_zero))
        rows.append(evaluate("B&H", bh_signal, n, panel, cfg_zero))
        print_table(rows, f"{window_name} — ZERO cost")

        rows = []
        for name, fn in signals.items():
            rows.append(evaluate(name, fn, n, panel, cfg_full))
        rows.append(evaluate("B&H", bh_signal, n, panel, cfg_full))
        print_table(rows, f"{window_name} — WITH cost (5bp explicit + 10bp/mo roll)")


if __name__ == "__main__":
    main()
