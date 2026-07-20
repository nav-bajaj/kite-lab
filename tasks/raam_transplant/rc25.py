"""Phase 3 — E3: RC25, the paper's full ranked composite as a standalone book.

RAAM's Ranking Model ranks each name on several factors, weight-combines the
RANKS, holds the top slice, and drops negative-momentum slots to cash. Built
here with what raam_transplant learned:
  M  126d vol-adjusted momentum (L6 base), high = good
  C  per-name average residual correlation to the candidate pool (the paper's
     "Average Relative Correlations"), LOW = good (a diversifier)
  T  distance above the 200-DMA (breakout state failed; DMA works), high = good
Total rank = wM*rank(M) + wC*rank(C) + wT*rank(T). Top-24. Per-slot cash: a
selected name with negative 126d momentum is dropped to cash.

This is the "is a 5th MOMENTUM portfolio warranted?" test. Bar (om25_alt):
daily corr to L6 < 0.7 AND holdings overlap < 25% AND Sharpe >= 1.5 AND
CAGR >= 30%. Prior is low — most momentum variants collapse into L6.

Run:  python tasks/raam_transplant/rc25.py
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from scripts.backtest_momentum import load_price_panels, load_benchmark  # noqa: E402
from scripts.build_om25_signals import load_universe  # noqa: E402
from scripts._clean_engine import run_strategy, thursdays  # noqa: E402
from scripts._momentum_engine import (  # noqa: E402
    BASELINE as L6, build_momentum_panels, make_momentum_score, lookback_months_to_days,
)
from residuals import build_residual_panel  # noqa: E402
from e1_l6div import load_index_close, holdings_overlap, NSE500_UNIVERSE_CSV, NIFTY100_INDEX  # noqa: E402

IS = ("2009-09-01", "2016-12-31")
OOS = [("OOS-A", "2017-01-01", "2019-12-31"), ("OOS-B", "2020-01-01", "2022-12-31"),
       ("OOS-C", "2023-01-01", "2026-07-20"), ("FULL", "2009-09-01", "2026-07-20")]
POOL_K = 80
CROWD_WINDOW = 63
TOP_N = 24
# (wM, wC, wT) weight combos on the rank-sum
WEIGHTS = [(0.6, 0.2, 0.2), (0.5, 0.3, 0.2), (0.5, 0.25, 0.25),
           (0.4, 0.3, 0.3), (0.7, 0.15, 0.15)]


def make_rc25_score(momentum, dma_dist, resid, wM, wC, wT, *,
                    pool_k=POOL_K, crowd_window=CROWD_WINDOW, top_n=TOP_N):
    def score_fn(d, **_):
        if d not in momentum.index:
            return pd.Series(dtype=float)
        mom = momentum.loc[d].dropna()
        mom = mom[mom > -1]  # valid
        if mom.empty:
            return mom
        pool = mom.sort_values(ascending=False).head(pool_k).index
        rM = mom.reindex(pool).rank(pct=True)
        # C: avg residual corr to pool over trailing window (low = good)
        win = resid.loc[:d].tail(crowd_window)[[p for p in pool if p in resid.columns]].dropna(axis=1, thresh=40)
        if win.shape[1] >= 3:
            cm = win.corr()
            avg_corr = (cm.sum(axis=1) - 1.0) / (cm.shape[1] - 1)
            rC = (-avg_corr.reindex(pool)).rank(pct=True)  # low corr -> high rank
        else:
            rC = pd.Series(0.5, index=pool)
        tdist = dma_dist.loc[d].reindex(pool) if d in dma_dist.index else pd.Series(0.0, index=pool)
        rT = tdist.rank(pct=True)
        total = wM * rM + wC * rC.fillna(0.5) + wT * rT.fillna(0.5)
        sel = total.sort_values(ascending=False).head(top_n)
        # per-slot cash: drop negative-momentum names
        sel = sel[mom.reindex(sel.index) > 0]
        # boost selected above all for the engine
        out = pd.Series(0.0, index=pool)
        out.loc[:] = total
        for i, name in enumerate(sel.index):
            out[name] = 1e6 + (top_n - i)
        return out
    return score_fn


def perf(res, s, e):
    eq = res["equity"].copy(); eq["date"] = pd.to_datetime(eq["date"])
    pv = eq.set_index("date")["pv"].astype(float)
    pv = pv.loc[(pv.index >= pd.Timestamp(s)) & (pv.index <= pd.Timestamp(e))]
    rets = pv.pct_change().dropna()
    years = max((pv.index[-1] - pv.index[0]).days / 365.25, 1e-9)
    cagr = (pv.iloc[-1] / pv.iloc[0]) ** (1 / years) - 1
    vol = rets.std() * math.sqrt(252)
    dd = (pv / pv.cummax() - 1).min()
    return {"pv": pv, "cagr_pct": round(cagr * 100, 2), "vol_pct": round(vol * 100, 2),
            "max_dd_pct": round(dd * 100, 2), "sharpe": round((cagr - 0.05) / vol, 3) if vol > 0 else None,
            "calmar": round(cagr / abs(dd), 3) if dd < 0 else None}


def main():
    ts = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
    out_dir = ROOT / "tasks/raam_transplant/runs" / f"rc25_{ts}"
    out_dir.mkdir(parents=True, exist_ok=True)

    print("[load] panels")
    close_panel, trade_panel = load_price_panels(ROOT / "nse500_data_merged")
    calendar = close_panel.index
    benchmark = load_benchmark(ROOT / "data/benchmarks/nifty100.csv").reindex(calendar).ffill()
    sma_200 = close_panel.rolling(200, min_periods=200).mean()
    atr_20 = close_panel.pct_change().rolling(20).std()
    nse500 = load_universe(ROOT / NSE500_UNIVERSE_CSV)
    cols = [s for s in close_panel.columns if s in nse500]
    nifty100 = load_index_close(ROOT / NIFTY100_INDEX).reindex(calendar).ffill()

    l6_panels = build_momentum_panels(close_panel[cols], lookback_days=lookback_months_to_days(L6["lookback_months"]), skip_days=L6["skip_days"])
    l6_score = make_momentum_score(l6_panels, vol_floor=L6["vol_floor"], vol_power=L6["vol_power"], cross_sectional_zscore=L6["cross_sectional_zscore"])
    momentum = l6_panels["momentum"]
    dma_dist = close_panel[cols] / sma_200[cols] - 1.0
    resid = build_residual_panel(close_panel[cols], nifty100)["residual"]

    def run(sfn, s, e):
        ed = thursdays(calendar); ed = ed[(ed >= pd.Timestamp(s)) & (ed <= pd.Timestamp(e))]
        if len(ed) == 0:
            return None
        return run_strategy(
            close_panel=close_panel[cols], trade_panel=trade_panel[cols], calendar=calendar,
            benchmark_aligned=benchmark, entry_signal_dates=ed, weekly_signal_dates=ed,
            signal_function=sfn, signal_function_args={}, sma_200_panel=sma_200[cols], atr_20_panel=atr_20[cols],
            top_n=TOP_N, exit_buffer=0, max_weight=0.075, slippage=0.002, atr_mult=0.0, atr_min_floor=0.0,
            use_trailing_stop=False, use_dma_exit=False, weekly_rank_check=False, regime_panel=None,
            bear_exposure=0.0, bear_skips_entries=False, min_hold_days=8, initial_capital=1_000_000)

    # ---- IS weight tuning ----
    print("[IS] weight grid")
    is_rows = []
    for wM, wC, wT in WEIGHTS:
        sfn = make_rc25_score(momentum, dma_dist, resid, wM, wC, wT)
        res = run(sfn, *IS)
        m = perf(res, *IS) if res else {}
        is_rows.append({"w": f"{wM}/{wC}/{wT}", **{k: v for k, v in m.items() if k != "pv"}})
        print(f"  {wM}/{wC}/{wT}: {is_rows[-1]}")
    is_df = pd.DataFrame(is_rows); is_df.to_csv(out_dir / "is_weights.csv", index=False)
    best_i = int(is_df["sharpe"].astype(float).idxmax())
    wstar = WEIGHTS[best_i]
    print(f"[IS] w* = {wstar} (best Sharpe)")

    # ---- OOS + differentiation ----
    rc_sfn = make_rc25_score(momentum, dma_dist, resid, *wstar)
    rows = []
    pvs = {}
    for wn, s, e in OOS:
        rres = run(rc_sfn, s, e); lres = run(l6_score, s, e)
        rp, lp = perf(rres, s, e), perf(lres, s, e)
        pvs[wn] = (rp["pv"], lp["pv"])
        rows.append({"window": wn, "RC25_cagr": rp["cagr_pct"], "L6_cagr": lp["cagr_pct"],
                     "RC25_dd": rp["max_dd_pct"], "L6_dd": lp["max_dd_pct"],
                     "RC25_sharpe": rp["sharpe"], "L6_sharpe": lp["sharpe"],
                     "RC25_calmar": rp["calmar"]})
    oos_df = pd.DataFrame(rows); oos_df.to_csv(out_dir / "oos.csv", index=False)

    # differentiation vs L6 (FULL)
    rp, lp = pvs["FULL"]
    rr, lr = rp.pct_change().dropna(), lp.pct_change().dropna()
    common = rr.index.intersection(lr.index)
    corr = round(float(rr.loc[common].corr(lr.loc[common])), 3)
    diag = thursdays(calendar); diag = diag[(diag >= pd.Timestamp("2010-01-01")) & (diag <= pd.Timestamp("2026-07-20"))][::2]
    ov = holdings_overlap(l6_score, rc_sfn, diag)

    full = perf(run(rc_sfn, *("2009-09-01", "2026-07-20")), "2009-09-01", "2026-07-20")
    bar = {"w_star": f"{wstar[0]}/{wstar[1]}/{wstar[2]}",
           "daily_corr_to_L6": corr, "corr_pass": corr < 0.7,
           "holdings_overlap_pct": ov, "overlap_pass": ov < 25,
           "full_cagr": full["cagr_pct"], "cagr_pass": full["cagr_pct"] >= 30,
           "full_sharpe": full["sharpe"], "sharpe_pass": (full["sharpe"] or 0) >= 1.5}
    bar["DIFFERENTIATED_PASS"] = all([bar["corr_pass"], bar["overlap_pass"], bar["cagr_pass"], bar["sharpe_pass"]])
    (out_dir / "verdict.json").write_text(json.dumps({"is": is_rows, "oos": rows, "bar": bar}, indent=2, default=str))

    pd.set_option("display.width", 200, "display.max_columns", 30)
    print("\n" + "=" * 74)
    print(f"RC25 — full composite (w*={wstar})")
    print("=" * 74)
    print(oos_df.to_string(index=False))
    print("\nDifferentiation bar (om25_alt):")
    print(json.dumps(bar, indent=2, default=str))
    print(f"\nwrote {out_dir}")


if __name__ == "__main__":
    main()
