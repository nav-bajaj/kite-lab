"""OM25 v3: conditional stop, and swapping the score's regime-tilt signal.

Two questions crossed with the overlay:

  STOP     always20   20% per-stock trailing stop at all times (production)
           off        no stop
           riskoff20  [NEW] stop ARMED ONLY while the market signal says
                      risk-off, disarmed in risk-on. Keeps the tail insurance
                      for the state where tails happen, drops the drag the
                      rest of the time.

  TILT     N100_MA    NIFTY 100 vs 100-DMA, 3-day confirm (production). Decides
                      whether the SCORE weights UC/CR 50-50 (bull) or CR-only
                      (bear).
           N500_ROC31 [NEW] NIFTY 500 31-session ROC > 0, 3-day confirm — the
                      same signal shape that won the overlay study.

  OVERLAY  none, or ROC31 NIFTY 500 at 75% bear exposure.

The engine takes a date-indexed mapping for `atr_min_floor`, so the
conditional stop needs no engine change. Risk-on passes a 999% floor rather
than 0 — with atr_mult=0 a floor of 0 would make `op < -0` fire on any
position below its peak.

Usage:
  python tasks/portfolio_risk_2026/om25_stop_and_tilt.py
"""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts._clean_engine import run_strategy, fridays, biweekly_fridays
from scripts.backtest_momentum import load_price_panels, load_benchmark
from scripts.om25_v3 import LOCKED, make_om25_tilt_score
from scripts.universe_membership import resolve_universe

HERE = Path(__file__).resolve().parent
OUT = HERE / "runs" / "om25_stop_tilt"
sys.path.insert(0, str(HERE))
from rolling_returns import underwater_stats, rolling_stats  # noqa: E402
from regime_experiment import build_regime                    # noqa: E402

START = "2015-07-01"
NEVER = 9.99   # 999% trailing floor == stop disarmed


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tilts", nargs="+", default=["N100_MA", "N100_ROC31", "N500_ROC31"])
    ap.add_argument("--overlays", nargs="+", default=["none", "roc31@75"])
    ap.add_argument("--stops", nargs="+", default=["always20", "off"])
    ap.add_argument("--start", default=START)
    ap.add_argument("--tag", default="")
    args = ap.parse_args()
    global OUT
    OUT = OUT.parent / (OUT.name + args.tag)
    OUT.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    print("[load] panels ...", flush=True)
    cp, tp = load_price_panels(ROOT / "nse500_data_merged")
    cal = cp.index
    bm = load_benchmark(ROOT / "data/benchmarks/nifty100.csv").reindex(cal).ffill()
    sma = cp.rolling(200, min_periods=200).mean()
    atr = cp.pct_change().rolling(20).std()
    s, end = pd.Timestamp(args.start), cal[-1]

    ALL_TILTS = {
        "N100_MA":    ("NIFTY_100", "ma", 100),
        "N100_ROC31": ("NIFTY_100", "roc", 31),
        "N500_ROC31": ("NIFTY_500", "roc", 31),
    }
    TILTS = {k: build_regime(*ALL_TILTS[k], calendar=cal, confirm_days=3)
             for k in args.tilts}
    risk = build_regime("NIFTY_500", "roc", 31, calendar=cal, confirm_days=3)
    # 20% floor while risk-off, disarmed while risk-on.
    cond_stop = pd.Series(np.where(risk.values, NEVER, 0.20), index=cal)

    uni, mem, cand = resolve_universe(
        ROOT / "data/static/nifty250_membership.csv", ROOT / LOCKED["universe_csv"])
    ru = cp[[c for c in cp.columns if c in uni]].pct_change()

    scores = {}
    for tname, treg in TILTS.items():
        raw = make_om25_tilt_score(
            ru, treg, bull_w_uc=LOCKED["bull_w_uc"], bull_w_cr=LOCKED["bull_w_cr"],
            bear_w_uc=LOCKED["bear_w_uc"], bear_w_cr=LOCKED["bear_w_cr"],
            return_filter=LOCKED["return_filter"], lookback=LOCKED["lookback"],
            min_obs=LOCKED["min_obs"], candidate_fn=cand)
        cache = {}
        def mk(raw=raw, cache=cache):
            def f(signal_date, **_):
                if signal_date not in cache:
                    cache[signal_date] = raw(signal_date)
                return cache[signal_date].copy()
            return f
        scores[tname] = mk()

    ed = biweekly_fridays(cal); ed = ed[(ed >= s) & (ed <= end)]
    wf = fridays(cal); wf = wf[(wf >= s) & (wf <= end)]

    ALL_STOPS = {"always20": 0.20, "off": NEVER, "riskoff20": cond_stop}
    ALL_OVERLAYS = {"none": None, "roc31@75": 0.75}
    STOPS = {k: ALL_STOPS[k] for k in args.stops}
    OVERLAYS = {k: ALL_OVERLAYS[k] for k in args.overlays}

    rows = []
    for tname in TILTS:
        for oname, bexp in OVERLAYS.items():
            for sname, stop in STOPS.items():
                t = time.time()
                res = run_strategy(
                    close_panel=cp, trade_panel=tp, calendar=cal,
                    benchmark_aligned=bm, entry_signal_dates=ed,
                    weekly_signal_dates=wf, signal_function=scores[tname],
                    signal_function_args={}, sma_200_panel=sma, atr_20_panel=atr,
                    top_n=LOCKED["top_n"], exit_buffer=LOCKED["exit_buffer"],
                    max_weight=LOCKED["max_weight"], slippage=LOCKED["slippage"],
                    atr_mult=0.0, atr_min_floor=stop, use_trailing_stop=True,
                    use_dma_exit=False, weekly_rank_check=False,
                    regime_panel=(risk if bexp is not None else None),
                    bear_exposure=(bexp if bexp is not None else 0.0),
                    membership_fn=mem, initial_capital=1_000_000)
                eq = res["equity"].copy(); eq["date"] = pd.to_datetime(eq["date"])
                ex = res["exits"].copy()
                label = f"{tname} | {oname} | stop:{sname}"
                eq.to_csv(OUT / f"{tname}_{oname.replace('@','')}_{sname}_equity.csv", index=False)
                pv = eq.set_index("date")["pv"].astype(float)

                def st(a, b):
                    x = pv.loc[a:b]
                    y = (x.index[-1] - x.index[0]).days / 365.25
                    r = x.pct_change().dropna(); v = r.std() * np.sqrt(252)
                    c = (x.iloc[-1] / x.iloc[0]) ** (1 / y) - 1
                    return round(c * 100, 2), round(c / v, 2), round((x / x.cummax() - 1).min() * 100, 2)

                u = underwater_stats(pv); r12 = rolling_stats(pv, 252)
                cg, sh, dd = st(args.start, str(end.date()))
                b18 = st("2018-01-15", "2019-12-31"); cov = st("2020-01-01", "2020-12-31")
                nstop = int((ex["reason"] == "atr_stop").sum()) if "reason" in ex.columns else 0
                rows.append({"config": label, "cagr_pct": cg, "sharpe": sh,
                             "max_dd_pct": dd, "calmar": round(cg / abs(dd), 2),
                             "ulcer": u["ulcer_index"],
                             "pct_days_dd_gt_20": u["pct_days_dd_gt_20"],
                             "pct_12m_neg": r12["pct_negative"],
                             "worst_12m": r12["min"], "median_12m": r12["median"],
                             "stop_exits": nstop, "n_exits": len(ex),
                             "bear18_cagr": b18[0], "bear18_dd": b18[2],
                             "covid_cagr": cov[0], "covid_dd": cov[2]})
                print(f"  {label:<44} ({time.time()-t:.0f}s)", flush=True)

    df = pd.DataFrame(rows)
    df.to_csv(OUT / "stop_and_tilt.csv", index=False)
    print(f"\n=== EVAL {args.start} -> {end.date()} ===")
    print(df[["config", "cagr_pct", "sharpe", "max_dd_pct", "calmar", "ulcer",
              "pct_days_dd_gt_20", "pct_12m_neg", "worst_12m", "median_12m",
              "stop_exits", "n_exits"]].to_string(index=False))
    print(f"\n=== episodes (CAGR / maxDD) ===")
    print(df[["config", "bear18_cagr", "bear18_dd", "covid_cagr", "covid_dd"]].to_string(index=False))
    print(f"\n[total] {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
