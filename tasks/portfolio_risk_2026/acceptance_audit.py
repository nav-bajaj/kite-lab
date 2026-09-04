"""Re-score the production portfolios against the bar they were accepted on.

The OM25/TL25 OOS validation window closed 2026-05-08. This re-runs the
original `oos_retune_2026` pass criteria on today's data, extends OOS to the
panel end, isolates the forward stub since the validation closed, and adds a
product-grade bar for comparison.

Builds TL25 v3 (no curve on disk); reuses the L6 / OM25 / COMBO curves already
produced in this task folder.

Usage:
  python tasks/portfolio_risk_2026/acceptance_audit.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts._clean_engine import run_strategy, fridays, biweekly_fridays
from scripts.backtest_momentum import load_price_panels, load_benchmark
from scripts.tl25_v3 import V3_LOCKED, build_tl25_panels, make_tl25_score
from scripts.universe_membership import resolve_universe

HERE = Path(__file__).resolve().parent
RUNS = HERE / "runs"
sys.path.insert(0, str(HERE))
from rolling_returns import underwater_stats, rolling_stats  # noqa: E402

# Original oos_retune_2026 split, with OOS-C and OOS-full extended to the
# panel end so today's data is included.
SUBWINDOWS = [("OOS-A", "2017-01-01", "2019-12-31"),
              ("OOS-B", "2020-01-01", "2022-12-31"),
              ("OOS-C+", "2023-01-01", None)]
OOS_FULL = ("2017-01-01", None)
FORWARD = ("2026-05-09", None)   # since the validation window closed


def build_tl25():
    out = RUNS / "tl25_v3_equity.csv"
    if out.exists():
        return pd.read_csv(out, parse_dates=["date"]).set_index("date")["pv"].astype(float)
    print("[build] TL25 v3 ...", flush=True)
    cp, tp = load_price_panels(ROOT / "nse500_data_merged")
    cal = cp.index
    bm = load_benchmark(ROOT / "data/benchmarks/nifty100.csv").reindex(cal).ffill()
    sma = cp.rolling(200, min_periods=200).mean()
    atr = cp.pct_change().rolling(20).std()
    uni, mem, cand = resolve_universe(
        ROOT / "data/static/nse500_membership.csv", ROOT / V3_LOCKED["universe_csv"])
    panels = build_tl25_panels(
        cp[[c for c in cp.columns if c in uni]],
        dma_short=V3_LOCKED["dma_short"], dma_long=V3_LOCKED["dma_long"],
        dma_persist_ref=V3_LOCKED["dma_persist_ref"],
        persistence_window=V3_LOCKED["persistence_window"],
        drawdown_window=V3_LOCKED["drawdown_window"],
        drawdown_concavity=V3_LOCKED["drawdown_concavity"],
        momentum_window=V3_LOCKED["momentum_window"])
    score = make_tl25_score(panels, w_persistence=V3_LOCKED["w_persistence"],
                            w_drawdown=V3_LOCKED["w_drawdown"],
                            w_momentum=V3_LOCKED["w_momentum"], candidate_fn=cand)
    s, e = pd.Timestamp("2010-07-01"), cal[-1]
    ed = biweekly_fridays(cal); ed = ed[(ed >= s) & (ed <= e)]
    wf = fridays(cal); wf = wf[(wf >= s) & (wf <= e)]
    res = run_strategy(
        close_panel=cp, trade_panel=tp, calendar=cal, benchmark_aligned=bm,
        entry_signal_dates=ed, weekly_signal_dates=wf,
        signal_function=score, signal_function_args={},
        sma_200_panel=sma, atr_20_panel=atr,
        top_n=V3_LOCKED["top_n"], exit_buffer=V3_LOCKED["exit_buffer"],
        max_weight=V3_LOCKED["max_weight"], slippage=V3_LOCKED["slippage"],
        atr_mult=0.0, atr_min_floor=V3_LOCKED["atr_min_floor"],
        use_trailing_stop=True, use_dma_exit=False,
        weekly_rank_check=V3_LOCKED["weekly_rank_check"],
        regime_panel=None, bear_exposure=0.0,
        membership_fn=mem, initial_capital=1_000_000)
    eq = res["equity"].copy(); eq["date"] = pd.to_datetime(eq["date"])
    eq.to_csv(out, index=False)
    return eq.set_index("date")["pv"].astype(float)


def stats(pv, a=None, b=None):
    x = pv.loc[a:b] if (a or b) else pv
    if len(x) < 5:
        return None
    y = (x.index[-1] - x.index[0]).days / 365.25
    r = x.pct_change().dropna()
    c = (x.iloc[-1] / x.iloc[0]) ** (1 / y) - 1
    v = r.std() * np.sqrt(252)
    return {"yrs": round(y, 2), "cagr_pct": round(c * 100, 2),
            "sharpe": round(c / v, 2) if v else np.nan,
            "max_dd_pct": round((x / x.cummax() - 1).min() * 100, 2)}


def load(f):
    pv = pd.read_csv(RUNS / f, parse_dates=["date"]).set_index("date")["pv"].astype(float)
    return pv[~pv.index.duplicated()]


def main():
    curves = {
        "L6 v2": load("buf00_equity.csv"),
        "OM25 v3": load("om25_stop/stop20_none_equity.csv"),
        "TL25 v3": build_tl25(),
        "COMBO": load("combo_buf00_equity.csv"),
        "OM25 + ROC31@75, no stop": load("om25_stop/nostop_roc31_75_equity.csv"),
        "COMBO + ROC31@75 + buf20": None,
    }
    p = RUNS / "regime_buf20" / "roc42_NIFTY_500_equity.csv"
    curves.pop("COMBO + ROC31@75 + buf20")

    print("=" * 96)
    print("ORIGINAL PASS CRITERIA, re-scored on today's data")
    print("  OOS agg Sharpe >= 1.0 | every sub-window Sharpe >= 0.7 | OOS max DD >= -45%")
    print("=" * 96)
    rows = []
    for name, pv in curves.items():
        row = {"portfolio": name}
        full = stats(pv, *OOS_FULL)
        row["OOS yrs"] = full["yrs"]; row["OOS CAGR"] = full["cagr_pct"]
        row["OOS Sharpe"] = full["sharpe"]; row["OOS maxDD"] = full["max_dd_pct"]
        ok = full["sharpe"] >= 1.0 and full["max_dd_pct"] >= -45
        for lbl, a, b in SUBWINDOWS:
            st = stats(pv, a, b)
            row[lbl] = st["sharpe"]
            ok = ok and st["sharpe"] >= 0.7
        row["PASS"] = "PASS" if ok else "FAIL"
        rows.append(row)
    print(pd.DataFrame(rows).to_string(index=False))

    print("\n" + "=" * 96)
    print(f"FORWARD STUB since the OOS window closed: {FORWARD[0]} -> panel end")
    print("=" * 96)
    fr = []
    for name, pv in curves.items():
        st = stats(pv, *FORWARD)
        if st:
            fr.append({"portfolio": name, **st})
    print(pd.DataFrame(fr).to_string(index=False))

    print("\n" + "=" * 96)
    print("PRODUCT-GRADE BAR — what a subscriber actually lives through (OOS 2017 ->)")
    print("=" * 96)
    pr = []
    for name, pv in curves.items():
        x = pv.loc[OOS_FULL[0]:]
        u = underwater_stats(x); r12 = rolling_stats(x, 252)
        peak = x[x == x.cummax()].index[-1]
        pr.append({"portfolio": name, "max_dd_pct": u["max_dd_pct"],
                   "pct_days_dd_gt_20": u["pct_days_dd_gt_20"],
                   "longest_uw_months": round(u["longest_uw_days"] / 30.44, 1),
                   "ulcer": u["ulcer_index"],
                   "pct_12m_neg": r12["pct_negative"],
                   "worst_12m": r12["min"], "median_12m": r12["median"],
                   "days_since_high": (x.index[-1] - peak).days})
    print(pd.DataFrame(pr).to_string(index=False))


if __name__ == "__main__":
    main()
