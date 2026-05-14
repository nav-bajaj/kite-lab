"""Layered regime overlay for COMBO 50-50 — Friday biweekly L6→OM25.

Tests progressive de-risking using TWO MAs:
  100-DMA (faster, early warning) + 200-DMA (slower, deep-bear confirmation)

Three target-exposure states:
  Bull (both above):        100% invested
  Early warning (100-DMA down only): 75% invested / 25% cash
  Confirmed bear (both below):       50% invested / 50% cash

Variants tested on Friday biweekly L6→OM25 base:
  - No regime
  - Binary 100-DMA + bear=50% (current Defensive candidate)
  - Binary 200-DMA + bear=50%
  - LAYERED 100-DMA→75%, 200-DMA→50%   (user's request)
  - LAYERED 100-DMA→50%, 200-DMA→25%   (more aggressive de-risk)

The layered approach should give smoother transitions and avoid binary
whipsaws while still protecting against deep bears.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts._clean_engine import run_strategy, biweekly_fridays, fridays
from scripts._momentum_engine import (
    BASELINE as MM_BASELINE, build_momentum_panels, make_momentum_score,
    lookback_months_to_days,
)
from scripts.om25_v3 import (
    LOCKED as OM25_LOCKED, build_regime_panel_confirmed, make_om25_tilt_score,
)
from scripts.backtest_momentum import load_price_panels, load_benchmark
from scripts.build_om25_signals import load_universe
from scripts.multi_window_oos_eval import period_metrics


WINDOWS = [
    ("IS",          "2009-09-01", "2016-12-31"),
    ("OOS_A",       "2017-01-01", "2019-12-31"),
    ("OOS_B",       "2020-01-01", "2022-12-31"),
    ("OOS_C",       "2023-01-01", "2026-05-08"),
    ("OOS_full",    "2017-01-01", "2026-05-08"),
    ("Prod window", "2020-07-10", "2026-05-08"),
]


def build_layered_regime(idx_path: Path, calendar, *, confirm_days=3,
                          ma_short=100, ma_long=200,
                          mild_bear_target=0.75, deep_bear_target=0.50):
    """Build a float regime panel where each date carries the target gross exposure.

    Uses two MAs (short + long) on the NIFTY 100 index. Three states:
      - Bull (price > both MAs):        target = 1.0
      - Mild bear (price < short MA only):     target = mild_bear_target
      - Deep bear (price < both MAs):          target = deep_bear_target

    Each MA crossover state is confirmed by `confirm_days` consecutive days
    to avoid whipsaws. Output is lagged 1 day to ensure no lookahead.
    """
    idx = pd.read_csv(idx_path, parse_dates=["date"])
    idx["date"] = pd.to_datetime(idx["date"]).dt.tz_localize(None).dt.normalize()
    idx = idx.sort_values("date").set_index("date")["close"].astype(float)

    sma_short = idx.rolling(ma_short, min_periods=ma_short).mean()
    sma_long = idx.rolling(ma_long, min_periods=ma_long).mean()

    # Daily booleans: price above each MA?
    above_short = idx > sma_short
    above_long = idx > sma_long

    # Confirm: state must persist for confirm_days consecutive
    # We track the "confirmed" state per MA separately.
    def _confirm(series: pd.Series, conf: int) -> pd.Series:
        if conf <= 0:
            return series.copy().astype(bool)
        rolled_above = series.rolling(conf).sum() >= conf  # conf consecutive trues
        rolled_below = (~series).rolling(conf).sum() >= conf  # conf consecutive falses
        out = pd.Series(index=series.index, data=True, dtype=bool)
        prev = True  # start bull
        for d in series.index:
            if rolled_below.get(d, False):
                out[d] = False; prev = False
            elif rolled_above.get(d, False):
                out[d] = True; prev = True
            else:
                out[d] = prev
        return out

    confirmed_short = _confirm(above_short.fillna(False), confirm_days)
    confirmed_long = _confirm(above_long.fillna(False), confirm_days)

    # Target exposure per date
    def _target(s_ok, l_ok):
        if s_ok and l_ok:
            return 1.0
        if l_ok and not s_ok:
            return mild_bear_target
        return deep_bear_target  # both down (or unusual short-up/long-down)

    target = pd.Series(index=idx.index,
                       data=[_target(s, l) for s, l in zip(confirmed_short, confirmed_long)],
                       dtype=float)
    # Lag 1 day for no-lookahead, then reindex to calendar
    target = target.shift(1)
    if calendar is not None:
        target = target.reindex(calendar).ffill().fillna(1.0)
    return target


def make_combined(score_fns_in_priority_order, n_per=12):
    def score_fn(signal_date, **_):
        picked = set()
        rows = []
        for _, sf in score_fns_in_priority_order:
            scores = sf(signal_date)
            if scores is None or scores.empty: continue
            ranked = scores.dropna().sort_values(ascending=False)
            taken = 0
            for sym in ranked.index:
                if sym in picked: continue
                picked.add(sym); rows.append(sym); taken += 1
                if taken >= n_per: break
        if not rows: return pd.Series(dtype=float)
        n = len(rows)
        return pd.Series({sym: float(n - i) for i, sym in enumerate(rows)})
    return score_fn


def _calmar(c, d):
    if d is None or pd.isna(d) or abs(d) < 1e-6: return None
    return c / abs(d)


def _sortino(eq, s, e):
    s = pd.Timestamp(s); e = pd.Timestamp(e)
    sub = eq[(eq["date"] >= s) & (eq["date"] <= e)]
    if len(sub) < 5: return None
    rets = sub["pv"].astype(float).pct_change().dropna()
    if rets.empty: return None
    downside = rets[rets < 0]
    if downside.empty or downside.std() == 0: return None
    excess = rets.mean() * 252 - 0.05
    return excess / (downside.std() * math.sqrt(252))


def run_one(label, score_fn, ctx, regime_panel, bear_exposure):
    entry_all = biweekly_fridays(ctx["calendar"])
    weekly_all = fridays(ctx["calendar"])
    s = pd.Timestamp("2009-09-01"); e = pd.Timestamp("2026-05-08")
    entry_dates = entry_all[(entry_all >= s) & (entry_all <= e)]
    weekly_filt = weekly_all[(weekly_all >= s) & (weekly_all <= e)]
    res = run_strategy(
        close_panel=ctx["close_panel"], trade_panel=ctx["trade_panel"],
        calendar=ctx["calendar"], benchmark_aligned=ctx["benchmark_aligned"],
        entry_signal_dates=entry_dates, weekly_signal_dates=weekly_filt,
        signal_function=score_fn, signal_function_args={},
        sma_200_panel=ctx["sma_200"], atr_20_panel=ctx["atr_20"],
        top_n=24, exit_buffer=0,
        max_weight=0.075, slippage=0.002,
        atr_mult=0.0, atr_min_floor=0.0,
        use_trailing_stop=False, use_dma_exit=False,
        weekly_rank_check=False,
        regime_panel=regime_panel, bear_exposure=bear_exposure,
        min_hold_days=8, initial_capital=1_000_000,
    )
    eq = res["equity"]
    rows = []
    for w_id, ws, we in WINDOWS:
        m = period_metrics(eq, w_id, ws, we)
        cagr = m.get("cagr_pct"); dd = m.get("max_dd_pct"); sh = m.get("sharpe")
        rows.append({
            "config": label, "window": w_id,
            "cagr_pct": round(cagr, 2) if cagr is not None else None,
            "sharpe": round(sh, 2) if sh is not None else None,
            "sortino": round(_sortino(eq, ws, we), 2) if _sortino(eq, ws, we) is not None else None,
            "calmar": round(_calmar(cagr, dd), 2) if _calmar(cagr, dd) is not None else None,
            "max_dd_pct": round(dd, 2) if dd is not None else None,
        })
    return rows


def main():
    print("[load] panels ...")
    close_panel, trade_panel = load_price_panels(ROOT / "nse500_data_merged")
    calendar = close_panel.index
    benchmark = load_benchmark(ROOT / "data/benchmarks/nifty100.csv")
    benchmark_aligned = benchmark.reindex(calendar).ffill()
    sma_200 = close_panel.rolling(200, min_periods=200).mean()
    atr_20 = close_panel.pct_change().rolling(20).std()

    nse500_uni = load_universe(ROOT / "data/static/nse500_universe.csv")
    nse500_cols = [s for s in close_panel.columns if s in nse500_uni]
    l6_panels = build_momentum_panels(
        close_panel[nse500_cols],
        lookback_days=lookback_months_to_days(MM_BASELINE["lookback_months"]),
        skip_days=MM_BASELINE["skip_days"],
    )
    l6_score = make_momentum_score(
        l6_panels, vol_floor=MM_BASELINE["vol_floor"],
        vol_power=MM_BASELINE["vol_power"], cross_sectional_zscore=True,
    )
    nifty250_uni = load_universe(ROOT / "data/static/nifty250_universe.csv")
    nifty250_cols = [s for s in close_panel.columns if s in nifty250_uni]
    om25_returns = close_panel[nifty250_cols].pct_change()
    om25_regime = build_regime_panel_confirmed(
        ROOT / "indices_data_historical/NIFTY_100.csv",
        OM25_LOCKED["regime_ma_window"], OM25_LOCKED["regime_confirm_days"],
        calendar=calendar,
    )
    om25_score = make_om25_tilt_score(
        om25_returns, om25_regime,
        bull_w_uc=OM25_LOCKED["bull_w_uc"], bull_w_cr=OM25_LOCKED["bull_w_cr"],
        bear_w_uc=OM25_LOCKED["bear_w_uc"], bear_w_cr=OM25_LOCKED["bear_w_cr"],
        return_filter=OM25_LOCKED["return_filter"],
        lookback=OM25_LOCKED["lookback"], min_obs=OM25_LOCKED["min_obs"],
    )

    ctx = dict(close_panel=close_panel, trade_panel=trade_panel,
                calendar=calendar, benchmark_aligned=benchmark_aligned,
                sma_200=sma_200, atr_20=atr_20)
    combo = make_combined([("L6", l6_score), ("OM25", om25_score)], n_per=12)

    # Build regime panels
    print("[build] regime panels ...")
    binary_100 = build_regime_panel_confirmed(
        ROOT / "indices_data_historical/NIFTY_100.csv", 100, 3, calendar=calendar,
    )
    binary_200 = build_regime_panel_confirmed(
        ROOT / "indices_data_historical/NIFTY_100.csv", 200, 3, calendar=calendar,
    )
    layered_75_50 = build_layered_regime(
        ROOT / "indices_data_historical/NIFTY_100.csv", calendar,
        confirm_days=3, ma_short=100, ma_long=200,
        mild_bear_target=0.75, deep_bear_target=0.50,
    )
    layered_50_25 = build_layered_regime(
        ROOT / "indices_data_historical/NIFTY_100.csv", calendar,
        confirm_days=3, ma_short=100, ma_long=200,
        mild_bear_target=0.50, deep_bear_target=0.25,
    )

    # Diagnostic: how many days in each state for layered_75_50?
    print(f"\n[diagnostic] layered_75_50 state distribution:")
    counts = layered_75_50.value_counts().sort_index()
    total = len(layered_75_50.dropna())
    for v, n in counts.items():
        print(f"  exposure={v:.2f}: {n} days ({100*n/total:.1f}%)")

    # === Run all variants ===
    variants = [
        ("No regime", None, 0.0),
        ("Binary 100-DMA + 50% bear (current)", binary_100, 0.5),
        ("Binary 200-DMA + 50% bear", binary_200, 0.5),
        ("LAYERED 100→75%, 200→50%", layered_75_50, 0.0),  # bear_exposure ignored for float panel
        ("LAYERED 100→50%, 200→25% (aggressive)", layered_50_25, 0.0),
    ]
    all_rows = []
    for label, reg, be in variants:
        print(f"\n[run] {label} ...")
        all_rows.extend(run_one(label, combo, ctx, reg, be))

    df = pd.DataFrame(all_rows)
    out = ROOT / "tasks/MM-tuning/layered_regime.csv"
    df.to_csv(out, index=False)

    print(f"\n{'=' * 130}")
    print("COMBO 50-50 (Fri biweekly L6→OM25) + regime overlay variants")
    print(f"{'=' * 130}")
    for w in ["OOS_full", "Prod window", "OOS_B", "OOS_C"]:
        sub = df[df["window"] == w]
        if sub.empty: continue
        print(f"\n--- {w} ---")
        cols = ["config", "cagr_pct", "sharpe", "sortino", "calmar", "max_dd_pct"]
        print(sub[cols].to_string(index=False))
    print(f"\n[wrote] {out}")


if __name__ == "__main__":
    main()
