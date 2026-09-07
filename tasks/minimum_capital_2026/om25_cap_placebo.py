"""Placebo control for the OM25 price-cap study.

The cap sweep is non-monotonic (Rs 2,000 beats baseline, Rs 6,000 trails
it), which suggests the spread is path-dependence rather than a price
effect: dropping any one name changes cash, entries and every subsequent
rebalance, and those differences compound over 5.6 years.

This runs the same machinery but excludes a RANDOM subset of the
universe of the same size the real cap excludes, over many seeds. If the
price-cap arms land inside the random distribution, the cap carries no
information -- which is the result that makes a cap safe to adopt for
operational reasons.

Usage:
    python tasks/minimum_capital_2026/om25_cap_placebo.py --n-seeds 40 --cap 4000
"""
from __future__ import annotations

import argparse
import json
import math
import random
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts._clean_engine import run_strategy, fridays, biweekly_fridays
from data_pipeline.loaders import load_price_panels, load_benchmark
from scripts.om25_v3 import (
    LOCKED, build_regime_panel_confirmed, make_om25_tilt_score,
)
from scripts.universe_membership import resolve_universe

OUT = Path(__file__).resolve().parent / "runs"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n-seeds", type=int, default=40)
    ap.add_argument("--cap", type=float, default=4000)
    ap.add_argument("--start", default="2020-01-01")
    args = ap.parse_args()

    close_panel, trade_panel = load_price_panels(ROOT / "nse500_data")
    benchmark = load_benchmark(ROOT / "data/benchmarks/nifty100.csv")
    calendar = close_panel.index
    benchmark_aligned = benchmark.reindex(calendar).ffill()
    sma_200 = close_panel.rolling(200, min_periods=200).mean()
    atr_20 = close_panel.pct_change().rolling(20).std()

    weekly_fri = fridays(calendar)
    entry_all = biweekly_fridays(calendar)
    start_ts, end_ts = pd.Timestamp(args.start), calendar[-1]
    weekly_filt = weekly_fri[(weekly_fri >= start_ts) & (weekly_fri <= end_ts)]
    entry_dates = entry_all[(entry_all >= start_ts) & (entry_all <= end_ts)]

    universe, membership_fn, candidate_fn = resolve_universe(
        ROOT / "data/static/nifty250_membership.csv",
        ROOT / LOCKED["universe_csv"])
    cols = [s for s in close_panel.columns if s in universe]
    returns_uni = close_panel[cols].pct_change()

    regime = build_regime_panel_confirmed(
        args.regime_index if hasattr(args, "regime_index")
        else ROOT / "indices_data/NIFTY_100.csv",
        LOCKED["regime_ma_window"], LOCKED["regime_confirm_days"],
        calendar=calendar)

    score_fn = make_om25_tilt_score(
        returns_uni, regime,
        bull_w_uc=LOCKED["bull_w_uc"], bull_w_cr=LOCKED["bull_w_cr"],
        bear_w_uc=LOCKED["bear_w_uc"], bear_w_cr=LOCKED["bear_w_cr"],
        return_filter=LOCKED["return_filter"],
        lookback=LOCKED["lookback"], min_obs=LOCKED["min_obs"],
        candidate_fn=candidate_fn)

    def run(mem_fn):
        res = run_strategy(
            close_panel=close_panel, trade_panel=trade_panel, calendar=calendar,
            benchmark_aligned=benchmark_aligned,
            entry_signal_dates=entry_dates, weekly_signal_dates=weekly_filt,
            signal_function=score_fn, signal_function_args={},
            sma_200_panel=sma_200, atr_20_panel=atr_20,
            top_n=LOCKED["top_n"], exit_buffer=LOCKED["exit_buffer"],
            max_weight=LOCKED["max_weight"], slippage=LOCKED["slippage"],
            atr_mult=0.0, atr_min_floor=LOCKED["drawdown_stop_pct"],
            use_trailing_stop=True, use_dma_exit=False,
            regime_panel=None, bear_exposure=0.0,
            membership_fn=mem_fn, initial_capital=1_000_000)
        eq = res["equity"].copy(); eq["date"] = pd.to_datetime(eq["date"])
        pv = eq.set_index("date")["pv"].astype(float)
        yrs = max((pv.index[-1] - pv.index[0]).days / 365.25, 1e-9)
        cagr = (pv.iloc[-1] / pv.iloc[0]) ** (1 / yrs) - 1
        vol = pv.pct_change().dropna().std() * math.sqrt(252)
        mdd = (pv / pv.cummax()).min() - 1
        return cagr * 100, (cagr - 0.05) / vol * 100 / 100, mdd * 100

    # How many distinct names does the real cap actually block over the run?
    blocked = set()
    for d in entry_dates:
        row = close_panel.loc[d] if d in close_panel.index else None
        if row is None:
            continue
        blocked |= set(row.index[(row > args.cap) & row.notna()]) & set(cols)
    n_blocked = len(blocked)
    print(f"[info] Rs {args.cap:,.0f} cap blocks {n_blocked} distinct names "
          f"at some point ({n_blocked/len(cols)*100:.0f}% of the {len(cols)}-name universe)")

    rows = []
    for seed in range(args.n_seeds):
        rnd = random.Random(seed)
        drop = frozenset(rnd.sample(cols, n_blocked))
        keep = frozenset(c for c in cols if c not in drop)

        def mem(date, _keep=keep):
            base = (frozenset(membership_fn(date)) if membership_fn is not None
                    else frozenset(cols))
            return base & _keep

        c, s, m = run(mem)
        rows.append({"seed": seed, "cagr_pct": round(c, 2),
                     "sharpe": round(s, 2), "max_dd_pct": round(m, 2)})
        print(f"  seed {seed:3d}: CAGR {c:6.2f}%  Sharpe {s:5.2f}  MaxDD {m:7.2f}%")

    df = pd.DataFrame(rows)
    df.to_csv(OUT / f"om25_placebo_cap{int(args.cap)}.csv", index=False)
    q = df["cagr_pct"].quantile([0.05, 0.25, 0.5, 0.75, 0.95])
    print(f"\n[placebo] random-exclusion of {n_blocked} names, {args.n_seeds} seeds")
    print(f"  CAGR  mean {df['cagr_pct'].mean():.2f}%  sd {df['cagr_pct'].std():.2f}pp"
          f"  min {df['cagr_pct'].min():.2f}%  max {df['cagr_pct'].max():.2f}%")
    print("  percentiles: " + "  ".join(f"p{int(k*100)} {v:.2f}%" for k, v in q.items()))
    (OUT / f"om25_placebo_cap{int(args.cap)}_summary.json").write_text(json.dumps({
        "n_blocked": n_blocked, "n_seeds": args.n_seeds,
        "mean": round(df["cagr_pct"].mean(), 2),
        "sd": round(df["cagr_pct"].std(), 2),
        "min": round(df["cagr_pct"].min(), 2),
        "max": round(df["cagr_pct"].max(), 2),
        "pct": {f"p{int(k*100)}": round(v, 2) for k, v in q.items()},
    }, indent=2))


if __name__ == "__main__":
    main()
