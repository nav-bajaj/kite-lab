"""Walk-forward test of the OM25 v3 + ROC overlay candidate.

ROC lookback 31 / confirm 3 was chosen by looking at the whole 2015-2026
window. This asks the honest version: if the parameters had been re-chosen
periodically using only data available at the time, how would it have done?

Method
  - Grid: ROC lookback {10,15,21,31,42,52,63} x confirm {1,2,3,5,8} on
    NIFTY 500, all at 75% bear exposure with OM25's 20% stop removed.
    Exposure is a policy choice, not a fitted parameter, so it is held fixed.
  - Rolling 3-year train, 1-year test, stepped annually. At each boundary the
    config with the best TRAIN Sharpe is selected (house discipline: select on
    Sharpe, not CAGR) and applied to the following year, unseen.
  - The selected per-fold signals are spliced into ONE regime series and a
    single backtest is run on it. So this is a true walk-forward curve with
    real handover between parameter regimes, not stitched sub-backtests.
  - Selection uses constant-config backtests sliced to the train window —
    which is what you would actually have run at that decision point.

Usage:
  python tasks/portfolio_risk_2026/om25_walkforward.py
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
OUT = HERE / "runs" / "om25_wf"
sys.path.insert(0, str(HERE))
from rolling_returns import underwater_stats, rolling_stats  # noqa: E402
from regime_experiment import build_regime                    # noqa: E402

START = "2015-07-01"
LOOKBACKS = [10, 15, 21, 31, 42, 52, 63]
CONFIRMS = [1, 2, 3, 5, 8]
BEAR_EXP = 0.75
TRAIN_YEARS = 3
FIRST_TEST = "2018-07-01"


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--index", default="NIFTY_500",
                    help="index the ROC overlay reads (NIFTY_100 unlocks 2010+)")
    ap.add_argument("--start", default=START)
    ap.add_argument("--first-test", default=FIRST_TEST)
    ap.add_argument("--bear-exp", type=float, default=BEAR_EXP)
    ap.add_argument("--tag", default="")
    return ap.parse_args()


def main():
    args = parse_args()
    global OUT, START, FIRST_TEST, BEAR_EXP
    START, FIRST_TEST, BEAR_EXP = args.start, args.first_test, args.bear_exp
    OUT = OUT.parent / (OUT.name + args.tag)
    OUT.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    print("[load] panels ...", flush=True)
    cp, tp = load_price_panels(ROOT / "nse500_data_merged")
    cal = cp.index
    bm = load_benchmark(ROOT / "data/benchmarks/nifty100.csv").reindex(cal).ffill()
    sma = cp.rolling(200, min_periods=200).mean()
    atr = cp.pct_change().rolling(20).std()
    s, end = pd.Timestamp(START), cal[-1]

    tilt = build_regime("NIFTY_100", "ma", 100, calendar=cal, confirm_days=3)
    uni, mem, cand = resolve_universe(
        ROOT / "data/static/nifty250_membership.csv", ROOT / LOCKED["universe_csv"])
    ru = cp[[c for c in cp.columns if c in uni]].pct_change()
    raw_score = make_om25_tilt_score(
        ru, tilt, bull_w_uc=LOCKED["bull_w_uc"], bull_w_cr=LOCKED["bull_w_cr"],
        bear_w_uc=LOCKED["bear_w_uc"], bear_w_cr=LOCKED["bear_w_cr"],
        return_filter=LOCKED["return_filter"], lookback=LOCKED["lookback"],
        min_obs=LOCKED["min_obs"], candidate_fn=cand)

    # The score depends only on signal_date — identical across every overlay
    # config — so memoise it once and reuse across all 35 backtests.
    _cache = {}
    def score(signal_date, **_):
        if signal_date not in _cache:
            _cache[signal_date] = raw_score(signal_date)
        return _cache[signal_date].copy()

    ed = biweekly_fridays(cal); ed = ed[(ed >= s) & (ed <= end)]
    wf = fridays(cal); wf = wf[(wf >= s) & (wf <= end)]

    def backtest(regime, bear_exp, stop=0.0):
        res = run_strategy(
            close_panel=cp, trade_panel=tp, calendar=cal, benchmark_aligned=bm,
            entry_signal_dates=ed, weekly_signal_dates=wf,
            signal_function=score, signal_function_args={},
            sma_200_panel=sma, atr_20_panel=atr,
            top_n=LOCKED["top_n"], exit_buffer=LOCKED["exit_buffer"],
            max_weight=LOCKED["max_weight"], slippage=LOCKED["slippage"],
            atr_mult=0.0, atr_min_floor=stop, use_trailing_stop=stop > 0,
            use_dma_exit=False, weekly_rank_check=False,
            regime_panel=regime, bear_exposure=bear_exp,
            membership_fn=mem, initial_capital=1_000_000)
        eq = res["equity"].copy(); eq["date"] = pd.to_datetime(eq["date"])
        return eq.set_index("date")["pv"].astype(float)

    # --- constant-config grid, used only for train-window selection ---
    regimes, curves = {}, {}
    for lb in LOOKBACKS:
        for cd in CONFIRMS:
            k = (lb, cd)
            regimes[k] = build_regime(args.index, "roc", lb, calendar=cal, confirm_days=cd)
            curves[k] = backtest(regimes[k], BEAR_EXP)
    print(f"  grid of {len(curves)} configs in {time.time()-t0:.0f}s", flush=True)

    def sharpe(pv, a, b):
        x = pv.loc[a:b]
        if len(x) < 60:
            return -np.inf
        y = (x.index[-1] - x.index[0]).days / 365.25
        r = x.pct_change().dropna()
        v = r.std() * np.sqrt(252)
        if v <= 0:
            return -np.inf
        return ((x.iloc[-1] / x.iloc[0]) ** (1 / y) - 1) / v

    # --- folds ---
    folds, t = [], pd.Timestamp(FIRST_TEST)
    while t < end:
        te = min(t + pd.DateOffset(years=1) - pd.Timedelta(days=1), end)
        folds.append((t - pd.DateOffset(years=TRAIN_YEARS), t - pd.Timedelta(days=1), t, te))
        t = t + pd.DateOffset(years=1)

    picks = []
    composite = pd.Series(True, index=cal, dtype=bool)
    for tr_s, tr_e, te_s, te_e in folds:
        best = max(curves, key=lambda k: sharpe(curves[k], tr_s, tr_e))
        mask = (cal >= te_s) & (cal <= te_e)
        composite[mask] = regimes[best][mask]
        picks.append({"train": f"{tr_s.date()}..{tr_e.date()}",
                      "test": f"{te_s.date()}..{te_e.date()}",
                      "picked_lookback": best[0], "picked_confirm": best[1],
                      "train_sharpe": round(sharpe(curves[best], tr_s, tr_e), 2)})
    print("\n=== fold selections ===")
    print(pd.DataFrame(picks).to_string(index=False))

    # --- true walk-forward run on the spliced signal ---
    wf_pv = backtest(composite, BEAR_EXP)
    wf_pv.to_frame("pv").to_csv(OUT / "walkforward_equity.csv")

    ref = {
        f"WALK-FORWARD {args.index} (re-picked yearly)": wf_pv,
        f"FIXED {args.index} ROC31/c3 @75": curves[(31, 3)],
        "production OM25 (stop20, no overlay)": backtest(None, 0.0, stop=0.20),
        "no stop, no overlay": backtest(None, 0.0, stop=0.0),
    }
    a, b = pd.Timestamp(FIRST_TEST), end
    rows = []
    for name, pv in ref.items():
        x = pv.loc[a:b]
        y = (x.index[-1] - x.index[0]).days / 365.25
        r = x.pct_change().dropna(); v = r.std() * np.sqrt(252)
        c = (x.iloc[-1] / x.iloc[0]) ** (1 / y) - 1
        u = underwater_stats(x); r12 = rolling_stats(x, 252)
        rows.append({"config": name, "cagr_pct": round(c * 100, 2),
                     "sharpe": round(c / v, 2), "max_dd_pct": u["max_dd_pct"],
                     "calmar": round(c * 100 / abs(u["max_dd_pct"]), 2),
                     "ulcer": u["ulcer_index"],
                     "pct_days_dd_gt_20": u["pct_days_dd_gt_20"],
                     "pct_12m_neg": r12["pct_negative"],
                     "worst_12m": r12["min"], "median_12m": r12["median"]})
    df = pd.DataFrame(rows)
    df.to_csv(OUT / "walkforward_summary.csv", index=False)
    print(f"\n=== WALK-FORWARD TEST PERIOD {a.date()} -> {b.date()} "
          f"({(b-a).days/365.25:.1f}y, out-of-sample by construction) ===")
    print(df.to_string(index=False))
    print(f"\n[total] {time.time()-t0:.0f}s")


if __name__ == "__main__":
    main()
