"""OM25 v3: is the ROC overlay a REPLACEMENT for the 20% drawdown stop?

The overlay study ran the regime overlay *alongside* OM25's locked 20%
trailing stop. Both are drawdown controls, so they may be largely redundant
and the stop may be costing CAGR the overlay already earns. This crosses
dd_stop {20%, off} with overlay {none, ROC31@75/50/25} and also reports
calendar-year returns and current drawdown state.

Usage:
  python tasks/portfolio_risk_2026/om25_stop_vs_overlay.py
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

from scripts._clean_engine import run_strategy, fridays, biweekly_fridays
from scripts.backtest_momentum import load_price_panels, load_benchmark
from scripts.om25_v3 import LOCKED, make_om25_tilt_score
from scripts.universe_membership import resolve_universe

HERE = Path(__file__).resolve().parent
OUT = HERE / "runs" / "om25_stop"
sys.path.insert(0, str(HERE))
from rolling_returns import underwater_stats, rolling_stats  # noqa: E402
from regime_experiment import build_regime                    # noqa: E402

START = "2015-07-01"
STOPS = [("stop20", 0.20), ("nostop", 0.00)]
OVERLAYS = [("none", None), ("roc31_75", 0.75), ("roc31_50", 0.50), ("roc31_25", 0.25)]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    print("[load] panels ...", flush=True)
    cp, tp = load_price_panels(ROOT / "nse500_data_merged")
    cal = cp.index
    bm = load_benchmark(ROOT / "data/benchmarks/nifty100.csv").reindex(cal).ffill()
    sma = cp.rolling(200, min_periods=200).mean()
    atr = cp.pct_change().rolling(20).std()

    tilt_regime = build_regime("NIFTY_100", "ma", 100, calendar=cal, confirm_days=3)
    overlay_regime = build_regime("NIFTY_500", "roc", 31, calendar=cal, confirm_days=3)

    uni, mem, cand = resolve_universe(
        ROOT / "data/static/nifty250_membership.csv", ROOT / LOCKED["universe_csv"])
    ru = cp[[c for c in cp.columns if c in uni]].pct_change()
    score = make_om25_tilt_score(
        ru, tilt_regime, bull_w_uc=LOCKED["bull_w_uc"], bull_w_cr=LOCKED["bull_w_cr"],
        bear_w_uc=LOCKED["bear_w_uc"], bear_w_cr=LOCKED["bear_w_cr"],
        return_filter=LOCKED["return_filter"], lookback=LOCKED["lookback"],
        min_obs=LOCKED["min_obs"], candidate_fn=cand)

    s, e = pd.Timestamp(START), cal[-1]
    ed = biweekly_fridays(cal); ed = ed[(ed >= s) & (ed <= e)]
    wf = fridays(cal); wf = wf[(wf >= s) & (wf <= e)]

    curves = {}
    for slabel, stop in STOPS:
        for olabel, bexp in OVERLAYS:
            name = f"{slabel}_{olabel}"
            t = time.time()
            res = run_strategy(
                close_panel=cp, trade_panel=tp, calendar=cal, benchmark_aligned=bm,
                entry_signal_dates=ed, weekly_signal_dates=wf,
                signal_function=score, signal_function_args={},
                sma_200_panel=sma, atr_20_panel=atr,
                top_n=LOCKED["top_n"], exit_buffer=LOCKED["exit_buffer"],
                max_weight=LOCKED["max_weight"], slippage=LOCKED["slippage"],
                atr_mult=0.0, atr_min_floor=stop, use_trailing_stop=stop > 0,
                use_dma_exit=False, weekly_rank_check=False,
                regime_panel=(overlay_regime if bexp is not None else None),
                bear_exposure=(bexp if bexp is not None else 0.0),
                membership_fn=mem, initial_capital=1_000_000)
            eq = res["equity"].copy(); eq["date"] = pd.to_datetime(eq["date"])
            eq.to_csv(OUT / f"{name}_equity.csv", index=False)
            curves[name] = eq.set_index("date")["pv"].astype(float)
            print(f"  {name:<20} ({time.time()-t:.0f}s)", flush=True)

    def stats(pv, a=None, b=None):
        x = pv.loc[a:b] if (a or b) else pv
        if len(x) < 3:
            return {}
        y = (x.index[-1] - x.index[0]).days / 365.25
        r = x.pct_change().dropna()
        c = (x.iloc[-1] / x.iloc[0]) ** (1 / y) - 1
        vol = r.std() * np.sqrt(252)
        return {"cagr_pct": round(c * 100, 2), "sharpe": round(c / vol, 2) if vol else np.nan,
                "max_dd_pct": round((x / x.cummax() - 1).min() * 100, 2)}

    rows = []
    for n, pv in curves.items():
        u = underwater_stats(pv); r12 = rolling_stats(pv, 252)
        dd = pv / pv.cummax() - 1
        peak = pv[pv == pv.cummax()].index[-1]
        rows.append({"config": n, **stats(pv),
                     "calmar": round(stats(pv)["cagr_pct"] / abs(stats(pv)["max_dd_pct"]), 2),
                     "ulcer": u["ulcer_index"], "pct_days_dd_gt_20": u["pct_days_dd_gt_20"],
                     "pct_12m_neg": r12["pct_negative"], "median_12m": r12["median"],
                     "cur_dd_pct": round(dd.iloc[-1] * 100, 1),
                     "days_since_high": (pv.index[-1] - peak).days})
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "stop_vs_overlay.csv", index=False)
    print(f"\n=== EVAL {START} -> {e.date()} ===")
    print(df.to_string(index=False))

    print(f"\n=== Recent windows (CAGR % / max DD %) ===")
    recent = [("2021-01-01", None, "2021 ->"), ("2023-01-01", None, "2023 ->"),
              ("2024-01-01", None, "2024 ->"), ("2025-01-01", None, "2025 ->")]
    rr = []
    for n, pv in curves.items():
        row = {"config": n}
        for a, b, lbl in recent:
            st = stats(pv, a, b)
            row[lbl] = f"{st.get('cagr_pct')} / {st.get('max_dd_pct')}"
        rr.append(row)
    print(pd.DataFrame(rr).to_string(index=False))

    print(f"\n=== Calendar-year total return % ===")
    yr = {}
    for n, pv in curves.items():
        y = pv.resample("YE").last()
        y = pd.concat([pd.Series([pv.iloc[0]], index=[pv.index[0]]), y]).pct_change().dropna() * 100
        yr[n] = y.round(1)
    ydf = pd.DataFrame(yr); ydf.index = ydf.index.year
    print(ydf.to_string())
    ydf.to_csv(OUT / "yearly.csv")
    print(f"\n[total] {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
