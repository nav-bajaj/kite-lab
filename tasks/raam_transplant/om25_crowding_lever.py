"""Apply the crowding-index EXPOSURE lever to Quality Momentum (OM25 v3).

The market Momentum Crowding Index (residual correlation of the top-50
momentum names) throttled L6's exposure and failed. Does it time OM25 —
a different momentum-family strategy (Nifty 250, capture-ratio scoring,
bull/bear score tilt, 20% drawdown stop) — any differently?

Setup mirrors production OM25 exactly: biweekly Friday, top-25, exit-buffer
20, 20%-from-peak trailing stop, regime SCORE tilt (bull 0.5/0.5, bear pure
CR). The engine's exposure slot (regime_panel) is free in OM25, so the
crowding lever goes there: when the index sits above a percentile, cut gross
exposure to a floor; redeploy when it eases.

Run:  python tasks/raam_transplant/om25_crowding_lever.py
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
from scripts._clean_engine import run_strategy, thursdays, biweekly_fridays, fridays  # noqa: E402
from scripts._momentum_engine import build_momentum_panels, make_momentum_score, lookback_months_to_days, BASELINE as L6  # noqa: E402
from scripts.om25_v3 import LOCKED as OM, build_regime_panel_confirmed, make_om25_tilt_score  # noqa: E402
from residuals import build_residual_panel, avg_pairwise_corr  # noqa: E402
from e1_l6div import load_index_close, NSE500_UNIVERSE_CSV, NIFTY100_INDEX  # noqa: E402

INDEX_TOPK = 50
CROWD_WINDOW = 63
WINDOWS = [("IS", "2009-09-01", "2016-12-31"), ("OOS-A", "2017-01-01", "2019-12-31"),
           ("OOS-B", "2020-01-01", "2022-12-31"), ("OOS-C", "2023-01-01", "2026-07-20")]
LEVER = [(0.80, 0.7), (0.80, 0.5), (0.90, 0.7), (0.90, 0.5), (0.85, 0.6)]


def perf(res, s, e):
    eq = res["equity"].copy(); eq["date"] = pd.to_datetime(eq["date"])
    pv = eq.set_index("date")["pv"].astype(float)
    pv = pv.loc[(pv.index >= pd.Timestamp(s)) & (pv.index <= pd.Timestamp(e))]
    if len(pv) < 2:
        return {}
    rets = pv.pct_change().dropna()
    years = max((pv.index[-1] - pv.index[0]).days / 365.25, 1e-9)
    cagr = (pv.iloc[-1] / pv.iloc[0]) ** (1 / years) - 1
    vol = rets.std() * math.sqrt(252)
    dd = (pv / pv.cummax() - 1).min()
    return {"cagr": round(cagr * 100, 2), "dd": round(dd * 100, 2),
            "sharpe": round((cagr - 0.05) / vol, 3) if vol > 0 else None,
            "calmar": round(cagr / abs(dd), 3) if dd < 0 else None}


def main():
    ts = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
    out_dir = ROOT / "tasks/raam_transplant/runs" / f"om25_lever_{ts}"
    out_dir.mkdir(parents=True, exist_ok=True)

    print("[load] panels")
    close_panel, trade_panel = load_price_panels(ROOT / "nse500_data_merged")
    calendar = close_panel.index
    benchmark = load_benchmark(ROOT / "data/benchmarks/nifty100.csv").reindex(calendar).ffill()
    sma_200 = close_panel.rolling(200, min_periods=200).mean()
    atr_20 = close_panel.pct_change().rolling(20).std()
    nse500 = load_universe(ROOT / NSE500_UNIVERSE_CSV)
    nifty250 = load_universe(ROOT / "data/static/nifty250_universe.csv")
    cols500 = [s for s in close_panel.columns if s in nse500]
    cols250 = [s for s in close_panel.columns if s in nifty250]
    nifty100 = load_index_close(ROOT / NIFTY100_INDEX).reindex(calendar).ffill()

    # --- market crowding index (NSE500 top-50 momentum) -> exposure panel ---
    print("[index] building crowding index")
    l6_panels = build_momentum_panels(close_panel[cols500], lookback_days=lookback_months_to_days(L6["lookback_months"]), skip_days=0)
    momentum = l6_panels["momentum"]
    resid = build_residual_panel(close_panel[cols500], nifty100)["residual"]
    rebal = thursdays(calendar); rebal = rebal[(rebal >= pd.Timestamp("2010-01-01"))]
    idx = {}
    for d in rebal:
        mrow = momentum.loc[d].dropna() if d in momentum.index else pd.Series(dtype=float)
        top = mrow.sort_values(ascending=False).head(INDEX_TOPK).index
        win = resid.loc[:d].tail(CROWD_WINDOW)[[t for t in top if t in resid.columns]]
        idx[d] = avg_pairwise_corr(win)
    index = pd.Series(idx).dropna()
    exp_pct = pd.Series({d: float((index.loc[:d] <= index.loc[d]).mean()) for d in index.index})
    exp_pct_daily = exp_pct.reindex(calendar).ffill().shift(1)

    def exposure_panel(thresh, floor):
        e = pd.Series(1.0, index=calendar); e[exp_pct_daily > thresh] = floor
        return e

    # --- OM25 score (regime tilt in the score; memoised over dates) ---
    print("[om25] building score")
    score_regime = build_regime_panel_confirmed(ROOT / "indices_data_historical/NIFTY_100.csv",
                                                 OM["regime_ma_window"], OM["regime_confirm_days"], calendar=calendar)
    nifty250_ret = close_panel[cols250].pct_change()
    raw = make_om25_tilt_score(nifty250_ret, score_regime, bull_w_uc=OM["bull_w_uc"], bull_w_cr=OM["bull_w_cr"],
                               bear_w_uc=OM["bear_w_uc"], bear_w_cr=OM["bear_w_cr"], return_filter=OM["return_filter"],
                               lookback=OM["lookback"], min_obs=OM["min_obs"])
    _cache = {}
    def om25_score(d, **_):
        if d not in _cache:
            _cache[d] = raw(d)
        return _cache[d]

    def run(regime, s, e):
        ed = biweekly_fridays(calendar); ed = ed[(ed >= pd.Timestamp(s)) & (ed <= pd.Timestamp(e))]
        wk = fridays(calendar); wk = wk[(wk >= pd.Timestamp(s)) & (wk <= pd.Timestamp(e))]
        if len(ed) == 0:
            return None
        return run_strategy(
            close_panel=close_panel[cols250], trade_panel=trade_panel[cols250], calendar=calendar,
            benchmark_aligned=benchmark, entry_signal_dates=ed, weekly_signal_dates=wk,
            signal_function=om25_score, signal_function_args={}, sma_200_panel=sma_200[cols250], atr_20_panel=atr_20[cols250],
            top_n=OM["top_n"], exit_buffer=OM["exit_buffer"], max_weight=OM["max_weight"], slippage=OM["slippage"],
            atr_mult=0.0, atr_min_floor=OM["drawdown_stop_pct"], use_trailing_stop=True, use_dma_exit=False,
            regime_panel=regime, bear_exposure=0.0, bear_skips_entries=False,
            regime_redeploy_on_increase=(regime is not None), initial_capital=1_000_000)

    print("[run] baseline + lever grid")
    base = {}
    for wn, s, e in WINDOWS:
        base[wn] = perf(run(None, s, e), s, e)

    rows = [{"variant": "OM25 (baseline)", **{f"{wn}_{k}": base[wn].get(k) for wn, _, _ in WINDOWS for k in ["cagr", "dd", "sharpe"]}}]
    lever_rows = []
    for thresh, floor in LEVER:
        rec = {"thresh": thresh, "floor": floor}
        drow = {"variant": f"lever {int(thresh*100)}/{int(floor*100)}"}
        for wn, s, e in WINDOWS:
            m = perf(run(exposure_panel(thresh, floor), s, e), s, e)
            drow[f"{wn}_cagr"] = m.get("cagr"); drow[f"{wn}_dd"] = m.get("dd"); drow[f"{wn}_sharpe"] = m.get("sharpe")
            rec[f"{wn}_dCAGR"] = round((m.get("cagr") or 0) - (base[wn].get("cagr") or 0), 2)
            rec[f"{wn}_dCalmar"] = round((m.get("calmar") or 0) - (base[wn].get("calmar") or 0), 3)
        oos = ["OOS-A", "OOS-B", "OOS-C"]
        rec["OOS_mean_dCAGR"] = round(np.mean([rec[f"{w}_dCAGR"] for w in oos]), 2)
        rec["OOS_calmar_wins"] = int(sum(rec[f"{w}_dCalmar"] > 0 for w in oos))
        lever_rows.append(rec); rows.append(drow)

    summ = pd.DataFrame(rows); summ.to_csv(out_dir / "summary.csv", index=False)
    lev = pd.DataFrame(lever_rows); lev.to_csv(out_dir / "lever_deltas.csv", index=False)
    (out_dir / "report.json").write_text(json.dumps({"baseline": base, "lever": lever_rows}, indent=2, default=str))

    pd.set_option("display.width", 200, "display.max_columns", 40)
    print("\n" + "=" * 80)
    print("CROWDING EXPOSURE LEVER ON QUALITY MOMENTUM (OM25 v3)")
    print("=" * 80)
    print("\nCAGR / MaxDD / Sharpe per window:")
    cols = ["variant"] + [f"{wn}_{k}" for wn, _, _ in WINDOWS for k in ["cagr", "dd", "sharpe"]]
    print(summ[cols].to_string(index=False))
    print("\nLever Δ vs baseline OM25:")
    print(lev[["thresh", "floor", "OOS-A_dCAGR", "OOS-B_dCAGR", "OOS-C_dCAGR", "OOS_mean_dCAGR", "OOS_calmar_wins"]].to_string(index=False))
    print(f"\nwrote {out_dir}")


if __name__ == "__main__":
    main()
