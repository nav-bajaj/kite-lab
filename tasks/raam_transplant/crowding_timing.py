"""Crowding as a timing signal + a proprietary indicator.

Three product angles, one crowding series:

  1. MOMENTUM CROWDING INDEX — a single daily series: the average residual
     pairwise correlation of the top momentum decile (how much the momentum
     leaders are secretly the same bet). Characterised with an expanding
     percentile (lookahead-safe) so "today = 88th pct of history" is a live,
     honest readout. This is the publishable indicator.

  2. STRATEGY LEVER — throttle L6's gross exposure when the index is in an
     extreme percentile (crowding weakly predicts near-term drawdown). Grid
     threshold/floor on IS, evaluate OOS vs bare L6. Fed through the engine's
     float regime_panel.

  3. WHAT IT MEANS — forward 20/60d L6 (momentum) return conditioned on the
     index decile, for a subscriber-facing "when crowding is extreme,
     momentum's next N days historically looked like X" (descriptive; any
     published forward claim must clear the insight validity gate).

Run:  python tasks/raam_transplant/crowding_timing.py
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
from residuals import build_residual_panel, avg_pairwise_corr  # noqa: E402
from e1_l6div import load_index_close, NSE500_UNIVERSE_CSV, NIFTY100_INDEX  # noqa: E402

INDEX_TOPK = 50          # momentum decile of the ~500 universe
CROWD_WINDOW = 63
FWD = [20, 60]
IS = ("2009-09-01", "2016-12-31")
OOS = [("OOS-A", "2017-01-01", "2019-12-31"), ("OOS-B", "2020-01-01", "2022-12-31"),
       ("OOS-C", "2023-01-01", "2026-07-20")]
FULL = ("2009-09-01", "2026-07-20")
# lever grid: (percentile threshold, floor exposure)
LEVER = [(0.80, 0.7), (0.80, 0.5), (0.90, 0.7), (0.90, 0.5), (0.85, 0.6)]


def perf(pv):
    rets = pv.pct_change().dropna()
    years = max((pv.index[-1] - pv.index[0]).days / 365.25, 1e-9)
    cagr = (pv.iloc[-1] / pv.iloc[0]) ** (1 / years) - 1
    vol = rets.std() * math.sqrt(252)
    dd = (pv / pv.cummax() - 1).min()
    return {"cagr": round(cagr * 100, 2), "vol": round(vol * 100, 2), "dd": round(dd * 100, 2),
            "sharpe": round((cagr - 0.05) / vol, 3) if vol > 0 else None,
            "calmar": round(cagr / abs(dd), 3) if dd < 0 else None}


def pv_of(res, s, e):
    eq = res["equity"].copy(); eq["date"] = pd.to_datetime(eq["date"])
    pv = eq.set_index("date")["pv"].astype(float)
    return pv.loc[(pv.index >= pd.Timestamp(s)) & (pv.index <= pd.Timestamp(e))]


def main():
    ts = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
    out_dir = ROOT / "tasks/raam_transplant/runs" / f"crowding_timing_{ts}"
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
    resid = build_residual_panel(close_panel[cols], nifty100)["residual"]

    # ---- 1. Momentum Crowding Index (weekly) ----
    print("[1] building Momentum Crowding Index")
    rebal = thursdays(calendar); rebal = rebal[(rebal >= pd.Timestamp("2010-01-01")) & (rebal <= pd.Timestamp(FULL[1]))]
    idx = {}
    for d in rebal:
        mrow = momentum.loc[d].dropna() if d in momentum.index else pd.Series(dtype=float)
        top = mrow.sort_values(ascending=False).head(INDEX_TOPK).index
        win = resid.loc[:d].tail(CROWD_WINDOW)[[t for t in top if t in resid.columns]]
        idx[d] = avg_pairwise_corr(win)
    index = pd.Series(idx).dropna()
    # expanding percentile (lookahead-safe): where does today sit vs all history so far
    exp_pct = pd.Series({d: float((index.loc[:d] <= index.loc[d]).mean()) for d in index.index})
    index_df = pd.DataFrame({"crowding": index, "exp_pctile": exp_pct})
    index_df.to_csv(out_dir / "momentum_crowding_index.csv")

    desc = index.describe(percentiles=[.1, .25, .5, .75, .9]).round(4).to_dict()
    # top-10 most-crowded weeks (full-sample) — the episodes
    episodes = index.sort_values(ascending=False).head(10)
    episodes_list = [{"date": str(d.date()), "crowding": round(float(v), 4)} for d, v in episodes.items()]

    # ---- 2. Strategy lever ----
    print("[2] crowding exposure lever")
    exp_pct_daily = exp_pct.reindex(calendar).ffill().shift(1)  # known-yesterday, lookahead-safe

    def exposure_panel(thresh, floor):
        e = pd.Series(1.0, index=calendar)
        e[exp_pct_daily > thresh] = floor
        return e

    def run(regime=None):
        ed = thursdays(calendar)
        def _run(s, e):
            edw = ed[(ed >= pd.Timestamp(s)) & (ed <= pd.Timestamp(e))]
            return run_strategy(
                close_panel=close_panel[cols], trade_panel=trade_panel[cols], calendar=calendar,
                benchmark_aligned=benchmark, entry_signal_dates=edw, weekly_signal_dates=edw,
                signal_function=l6_score, signal_function_args={}, sma_200_panel=sma_200[cols], atr_20_panel=atr_20[cols],
                top_n=24, exit_buffer=0, max_weight=0.075, slippage=0.002, atr_mult=0.0, atr_min_floor=0.0,
                use_trailing_stop=False, use_dma_exit=False, weekly_rank_check=False,
                regime_panel=regime, bear_exposure=0.0, bear_skips_entries=False,
                regime_redeploy_on_increase=True, min_hold_days=8, initial_capital=1_000_000)
        return _run

    base_run = run(None)
    base_pv = {w: pv_of(base_run(s, e), s, e) for w, s, e in ([("IS",) + IS] + OOS)}

    lever_rows = []
    for thresh, floor in LEVER:
        rp = run(exposure_panel(thresh, floor))
        rec = {"thresh": thresh, "floor": floor}
        for w, s, e in ([("IS",) + IS] + OOS):
            pv = pv_of(rp(s, e), s, e); m = perf(pv); b = perf(base_pv[w])
            rec[f"{w}_dCAGR"] = round(m["cagr"] - b["cagr"], 2)
            rec[f"{w}_dCalmar"] = round((m["calmar"] or 0) - (b["calmar"] or 0), 3)
            rec[f"{w}_dDD"] = round(m["dd"] - b["dd"], 2)  # +ve = shallower
        oos = ["OOS-A", "OOS-B", "OOS-C"]
        rec["OOS_mean_dCAGR"] = round(np.mean([rec[f"{w}_dCAGR"] for w in oos]), 2)
        rec["OOS_calmar_wins"] = int(sum(rec[f"{w}_dCalmar"] > 0 for w in oos))
        lever_rows.append(rec)
    lever_df = pd.DataFrame(lever_rows); lever_df.to_csv(out_dir / "lever_grid.csv", index=False)

    # ---- 3. What it means: forward L6 return by index decile ----
    print("[3] conditional forward momentum returns by crowding decile")
    l6_full = pv_of(base_run(*FULL), *FULL)
    cond = []
    dec = pd.qcut(exp_pct.rank(method="first"), 5, labels=[1, 2, 3, 4, 5])  # quintiles of the index
    for d in index.index:
        if d not in l6_full.index:
            pos = l6_full.index.searchsorted(d)
            if pos >= len(l6_full.index):
                continue
            d2 = l6_full.index[pos]
        else:
            d2 = d
        i = l6_full.index.get_loc(d2)
        row = {"quintile": int(dec.loc[d])}
        for n in FWD:
            fwd = l6_full.iloc[i:i + n + 1]
            if len(fwd) >= n + 1:
                row[f"fwd{n}"] = float(fwd.iloc[-1] / fwd.iloc[0] - 1)
        cond.append(row)
    cond_df = pd.DataFrame(cond)
    by_q = cond_df.groupby("quintile").agg(
        n=("quintile", "size"),
        fwd20_mean=("fwd20", lambda x: round(x.mean() * 100, 2)),
        fwd20_hit=("fwd20", lambda x: round((x > 0).mean() * 100, 1)),
        fwd60_mean=("fwd60", lambda x: round(x.mean() * 100, 2)),
        fwd60_hit=("fwd60", lambda x: round((x > 0).mean() * 100, 1)),
    ).reset_index()
    by_q.to_csv(out_dir / "conditional_forward.csv", index=False)

    report = {"index_describe": desc, "current": {"date": str(index.index[-1].date()),
              "crowding": round(float(index.iloc[-1]), 4), "exp_pctile": round(float(exp_pct.iloc[-1]), 3)},
              "episodes": episodes_list, "lever": lever_rows, "conditional": by_q.to_dict("records")}
    (out_dir / "report.json").write_text(json.dumps(report, indent=2, default=str))

    pd.set_option("display.width", 200, "display.max_columns", 30)
    print("\n" + "=" * 76)
    print("MOMENTUM CROWDING INDEX — timing signal / indicator")
    print("=" * 76)
    print(f"\n[1] Index distribution (residual crowding of top-{INDEX_TOPK} momentum):")
    print(f"    {desc}")
    print(f"    CURRENT ({index.index[-1].date()}): crowding={index.iloc[-1]:.4f}  expanding-pctile={exp_pct.iloc[-1]:.2f}")
    print("    Most-crowded weeks (episodes):")
    for e in episodes_list[:6]:
        print(f"      {e['date']}  {e['crowding']}")
    print("\n[2] Exposure lever (Δ vs bare L6; +dDD = shallower drawdown):")
    show = ["thresh", "floor", "OOS-A_dCAGR", "OOS-B_dCAGR", "OOS-C_dCAGR", "OOS_mean_dCAGR", "OOS_calmar_wins"]
    print(lever_df[show].to_string(index=False))
    print("\n[3] Forward L6 (momentum) return by crowding quintile (1=calm .. 5=crowded):")
    print(by_q.to_string(index=False))
    print(f"\nwrote {out_dir}")


if __name__ == "__main__":
    main()
