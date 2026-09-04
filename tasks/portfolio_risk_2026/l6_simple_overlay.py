"""L6 v2 (Core Momentum): the SIMPLEST deployable overlay.

The earlier overlay study showed a daily-checked exposure cut is a bad trade
on L6 — it clips V-shaped recoveries. This asks a narrower question: if we
want an overlay anyway, which form is cheapest to run and least damaging?

Two independent axes.

HOW OFTEN YOU CHECK (fewer checks = fewer decisions, fewer surprise trades):
  daily     the regime can flip any session (what was tested before)
  weekly    sampled on L6's existing Thursday signal day — zero new
            decision points, it rides the rebalance you already do
  monthly   sampled on the first trading day of each month
  deadband  daily, but asymmetric thresholds: bear only when the NIFTY 500
            is >3% below its level 31 sessions ago, back to bull only when
            >1% above. The dead zone kills marginal flips.

WHAT YOU DO ON BEAR (fewer trades = easier execution):
  entry_gate   stop buying; never force-sell. Zero extra sell tickets — you
               simply skip the buy leg at the rebalance you already run.
  exposure_75  trim to 75% gross
  exposure_50  trim to 50% gross

Reports flips (state changes over the window) and trades/year alongside
return and risk, because those are the execution cost.

Usage:
  python tasks/portfolio_risk_2026/l6_simple_overlay.py
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts._clean_engine import (
    run_strategy, thursdays, monthly_first_trading_day,
)
from scripts._momentum_engine import (
    BASELINE, build_momentum_panels, make_momentum_score, lookback_months_to_days,
)
from scripts.backtest_momentum import load_price_panels, load_benchmark
from scripts.universe_membership import resolve_universe

HERE = Path(__file__).resolve().parent
OUT = HERE / "runs" / "l6_simple"
IDX = HERE / "runs" / "regime_idx"
sys.path.insert(0, str(HERE))
from rolling_returns import underwater_stats, rolling_stats  # noqa: E402
from regime_experiment import build_regime, _confirm          # noqa: E402

START = "2015-07-01"
LOOKBACK = 31


def deadband_regime(calendar, lookback=LOOKBACK, bear_th=-0.03, bull_th=0.01):
    """Asymmetric-threshold ROC regime. Sticky by construction: the state only
    changes when ROC clears one of the two thresholds, so drift inside the
    dead zone produces no flips at all."""
    df = pd.read_csv(IDX / "NIFTY_500.csv", parse_dates=["date"])
    df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None).dt.normalize()
    s = df.sort_values("date").set_index("date")["close"]
    roc = s / s.shift(lookback) - 1.0
    state, vals = True, []
    for v in roc.values:
        if not np.isnan(v):
            if state and v < bear_th:
                state = False
            elif not state and v > bull_th:
                state = True
        vals.append(state)
    r = pd.Series(vals, index=roc.index, dtype=bool).shift(1)
    r = r.reindex(calendar).ffill()
    return r.where(r.notna(), True).astype(bool)


def coarsen(regime, calendar, how):
    """Sample the regime only on the given decision days, then hold it."""
    if how == "daily":
        return regime
    dates = thursdays(calendar) if how == "weekly" else monthly_first_trading_day(calendar)
    r = regime.reindex(dates).reindex(calendar).ffill()
    return r.where(r.notna(), True).astype(bool)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    print("[load] panels ...", flush=True)
    cp, tp = load_price_panels(ROOT / "nse500_data_merged")
    cal = cp.index
    bm = load_benchmark(ROOT / "data/benchmarks/nifty100.csv").reindex(cal).ffill()
    sma = cp.rolling(200, min_periods=200).mean()
    atr = cp.pct_change().rolling(20).std()
    s, e = pd.Timestamp(START), cal[-1]

    uni, mem, cand = resolve_universe(
        ROOT / "data/static/nse500_membership.csv", ROOT / BASELINE["universe_csv"])
    panels = build_momentum_panels(
        cp[[c for c in cp.columns if c in uni]],
        lookback_days=lookback_months_to_days(BASELINE["lookback_months"]),
        skip_days=BASELINE["skip_days"])
    score = make_momentum_score(panels, vol_floor=BASELINE["vol_floor"],
                                vol_power=BASELINE["vol_power"],
                                cross_sectional_zscore=True, candidate_fn=cand)
    entry = thursdays(cal); entry = entry[(entry >= s) & (entry <= e)]

    base = build_regime("NIFTY_500", "roc", LOOKBACK, calendar=cal, confirm_days=3)
    TIMINGS = {
        "daily":    coarsen(base, cal, "daily"),
        "weekly":   coarsen(base, cal, "weekly"),
        "monthly":  coarsen(base, cal, "monthly"),
        "deadband": deadband_regime(cal),
    }
    ACTIONS = [("entry_gate", 0.999), ("exposure_75", 0.75), ("exposure_50", 0.50)]

    def run(label, regime, bexp):
        res = run_strategy(
            close_panel=cp, trade_panel=tp, calendar=cal, benchmark_aligned=bm,
            entry_signal_dates=entry, weekly_signal_dates=entry,
            signal_function=score, signal_function_args={},
            sma_200_panel=sma, atr_20_panel=atr,
            top_n=BASELINE["top_n"], exit_buffer=BASELINE["exit_buffer"],
            max_weight=BASELINE["max_weight"], slippage=BASELINE["slippage"],
            atr_mult=0.0, atr_min_floor=0.0, use_trailing_stop=False,
            use_dma_exit=False, weekly_rank_check=False,
            regime_panel=regime, bear_exposure=bexp,
            bear_skips_entries=True, membership_fn=mem,
            min_hold_days=BASELINE["min_hold_days"], initial_capital=1_000_000)
        eq = res["equity"].copy(); eq["date"] = pd.to_datetime(eq["date"])
        tr = res["trades"].copy(); tr["date"] = pd.to_datetime(tr["date"])
        eq.to_csv(OUT / f"{label}_equity.csv", index=False)
        return eq, tr

    rows = []
    jobs = [("production", None, 0.0, "-")]
    for tname, reg in TIMINGS.items():
        for aname, bexp in ACTIONS:
            jobs.append((f"{tname}_{aname}", reg, bexp, tname))

    for label, regime, bexp, tname in jobs:
        eq, tr = run(label, regime, bexp)
        pv = eq.set_index("date")["pv"].astype(float)
        yrs = (pv.index[-1] - pv.index[0]).days / 365.25
        r = pv.pct_change().dropna()
        cagr = (pv.iloc[-1] / pv.iloc[0]) ** (1 / yrs) - 1
        vol = r.std() * np.sqrt(252)
        u = underwater_stats(pv); r12 = rolling_stats(pv, 252)
        if regime is not None:
            seg = regime.loc[s:e]
            flips = int((seg != seg.shift(1)).iloc[1:].sum())
            bear = round(float((~seg).mean() * 100), 1)
        else:
            flips, bear = 0, 0.0
        rows.append({
            "config": label, "flips": flips, "flips_per_yr": round(flips / yrs, 1),
            "bear_pct": bear, "trades_per_yr": round(len(tr) / yrs, 0),
            "cagr_pct": round(cagr * 100, 2), "sharpe": round(cagr / vol, 2),
            "max_dd_pct": u["max_dd_pct"],
            "calmar": round(cagr * 100 / abs(u["max_dd_pct"]), 2),
            "ulcer": u["ulcer_index"], "pct_12m_neg": r12["pct_negative"],
            "median_12m": r12["median"],
            "avg_cash_pct": round(eq["cash_pct"].mean() * 100, 1)})
        print(f"  {label:<24} flips {flips:>3}  trades/yr {len(tr)/yrs:>5.0f}", flush=True)

    df = pd.DataFrame(rows)
    df.to_csv(OUT / "l6_simple_overlay.csv", index=False)
    print(f"\n=== L6 v2 overlay forms — EVAL {START} -> {e.date()} ===")
    print(df.to_string(index=False))
    print(f"\n[total] {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
