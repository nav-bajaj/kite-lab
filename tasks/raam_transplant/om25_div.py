"""OM25-DIV — the E1 selection nudge applied to Quality Momentum.

Same intervention that worked on L6 (Core Momentum): keep the strategy's own
ranking and eligibility, but select the top-25 greedily with a residual-
correlation penalty so a slightly-lower-ranked, less-crowded name can
displace a more-crowded one. Stays 100% invested — this changes WHICH names,
not exposure.

  final pick_k = argmax over pool of [ OM25_z(name) - lambda * mean_resid_corr(name, already_picked) ]

OM25 base score (capture-ratio quality-momentum tilt) is z-scored per date
so lambda has the same meaning as in E1. Engine config = production OM25
(Nifty 250, biweekly Friday, top-25, exit-buffer 20, 20% trailing stop).
Tune lambda on IS, evaluate OOS against the E1 gate + character (corr /
overlap vs plain OM25).

Run:  python tasks/raam_transplant/om25_div.py
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
from scripts._clean_engine import run_strategy, biweekly_fridays, fridays  # noqa: E402
from scripts.om25_v3 import LOCKED as OM, build_regime_panel_confirmed, make_om25_tilt_score  # noqa: E402
from residuals import build_residual_panel  # noqa: E402
from e1_l6div import make_l6div_score, holdings_overlap, load_index_close, NIFTY100_INDEX  # noqa: E402

WINDOWS = [("IS", "2009-09-01", "2016-12-31"), ("OOS-A", "2017-01-01", "2019-12-31"),
           ("OOS-B", "2020-01-01", "2022-12-31"), ("OOS-C", "2023-01-01", "2026-07-20")]
LAMBDA_GRID = [0.0, 0.5, 1.0, 2.0, 4.0]
TOP_N = 25


def perf(res, s, e):
    eq = res["equity"].copy(); eq["date"] = pd.to_datetime(eq["date"])
    pv = eq.set_index("date")["pv"].astype(float)
    pv = pv.loc[(pv.index >= pd.Timestamp(s)) & (pv.index <= pd.Timestamp(e))]
    if len(pv) < 2:
        return {}, pv
    rets = pv.pct_change().dropna()
    years = max((pv.index[-1] - pv.index[0]).days / 365.25, 1e-9)
    cagr = (pv.iloc[-1] / pv.iloc[0]) ** (1 / years) - 1
    vol = rets.std() * math.sqrt(252)
    dd = (pv / pv.cummax() - 1).min()
    return {"cagr": round(cagr * 100, 2), "vol": round(vol * 100, 2), "dd": round(dd * 100, 2),
            "sharpe": round((cagr - 0.05) / vol, 3) if vol > 0 else None,
            "calmar": round(cagr / abs(dd), 3) if dd < 0 else None}, pv


def main():
    ts = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
    out_dir = ROOT / "tasks/raam_transplant/runs" / f"om25_div_{ts}"
    out_dir.mkdir(parents=True, exist_ok=True)

    print("[load] panels")
    close_panel, trade_panel = load_price_panels(ROOT / "nse500_data_merged")
    calendar = close_panel.index
    benchmark = load_benchmark(ROOT / "data/benchmarks/nifty100.csv").reindex(calendar).ffill()
    sma_200 = close_panel.rolling(200, min_periods=200).mean()
    atr_20 = close_panel.pct_change().rolling(20).std()
    nifty250 = load_universe(ROOT / "data/static/nifty250_universe.csv")
    cols = [s for s in close_panel.columns if s in nifty250]
    nifty100 = load_index_close(ROOT / NIFTY100_INDEX).reindex(calendar).ffill()

    print("[om25] base score + residual panel")
    score_regime = build_regime_panel_confirmed(ROOT / "indices_data_historical/NIFTY_100.csv",
                                                 OM["regime_ma_window"], OM["regime_confirm_days"], calendar=calendar)
    nifty250_ret = close_panel[cols].pct_change()
    raw = make_om25_tilt_score(nifty250_ret, score_regime, bull_w_uc=OM["bull_w_uc"], bull_w_cr=OM["bull_w_cr"],
                               bear_w_uc=OM["bear_w_uc"], bear_w_cr=OM["bear_w_cr"], return_filter=OM["return_filter"],
                               lookback=OM["lookback"], min_obs=OM["min_obs"])
    _raw_cache = {}
    def om25_raw(d):
        if d not in _raw_cache:
            _raw_cache[d] = raw(d)
        return _raw_cache[d]
    def om25_z(d, **_):  # z-score so lambda is on the E1 footing
        s = om25_raw(d)
        if s is None or s.empty:
            return s
        sd = s.std()
        return (s - s.mean()) / sd if sd and sd > 0 else s * 0.0

    resid = build_residual_panel(close_panel[cols], nifty100)["residual"]

    def run(score_fn, s, e):
        ed = biweekly_fridays(calendar); ed = ed[(ed >= pd.Timestamp(s)) & (ed <= pd.Timestamp(e))]
        wk = fridays(calendar); wk = wk[(wk >= pd.Timestamp(s)) & (wk <= pd.Timestamp(e))]
        if len(ed) == 0:
            return None
        return run_strategy(
            close_panel=close_panel[cols], trade_panel=trade_panel[cols], calendar=calendar,
            benchmark_aligned=benchmark, entry_signal_dates=ed, weekly_signal_dates=wk,
            signal_function=score_fn, signal_function_args={}, sma_200_panel=sma_200[cols], atr_20_panel=atr_20[cols],
            top_n=OM["top_n"], exit_buffer=OM["exit_buffer"], max_weight=OM["max_weight"], slippage=OM["slippage"],
            atr_mult=0.0, atr_min_floor=OM["drawdown_stop_pct"], use_trailing_stop=True, use_dma_exit=False,
            regime_panel=None, bear_exposure=0.0, initial_capital=1_000_000)

    base_sfn = make_l6div_score(om25_z, resid, 0.0, top_n=TOP_N)  # plain OM25 selection

    # ---- IS lambda tuning ----
    print("[IS] lambda grid")
    is_rows = []
    for lam in LAMBDA_GRID:
        sfn = make_l6div_score(om25_z, resid, lam, top_n=TOP_N)
        m, _ = perf(run(sfn, *WINDOWS[0][1:]), *WINDOWS[0][1:])
        is_rows.append({"lambda": lam, **m})
        print(f"  λ={lam}: {m}")
    is_df = pd.DataFrame(is_rows)
    l6_is = is_rows[0]
    cand = is_df[(is_df["lambda"] > 0)].dropna(subset=["calmar"])
    cand = cand[cand["cagr"] >= (l6_is["cagr"] or 0) - 2.0]
    lam_star = float(cand.sort_values("calmar", ascending=False)["lambda"].iloc[0]) if not cand.empty else 0.0
    print(f"[IS] λ* = {lam_star}")

    # ---- OOS: baseline vs DIV(λ*) + character ----
    div_sfn = make_l6div_score(om25_z, resid, lam_star, top_n=TOP_N)
    rows = []
    pv_base_full, pv_div_full = [], []
    for wn, s, e in WINDOWS:
        mb, pvb = perf(run(base_sfn, s, e), s, e)
        md, pvd = perf(run(div_sfn, s, e), s, e)
        rows.append({"window": wn, "OM25_cagr": mb.get("cagr"), "DIV_cagr": md.get("cagr"),
                     "cagr_delta": round((md.get("cagr") or 0) - (mb.get("cagr") or 0), 2),
                     "OM25_dd": mb.get("dd"), "DIV_dd": md.get("dd"),
                     "OM25_calmar": mb.get("calmar"), "DIV_calmar": md.get("calmar"),
                     "calmar_better": (md.get("calmar") or 0) > (mb.get("calmar") or 0),
                     "OM25_sharpe": mb.get("sharpe"), "DIV_sharpe": md.get("sharpe")})
        if wn != "IS":
            pv_base_full.append(pvb); pv_div_full.append(pvd)
    oos_df = pd.DataFrame(rows)

    # character over OOS (2017+): daily corr + holdings overlap
    pb = pd.concat(pv_base_full).sort_index(); pd_ = pd.concat(pv_div_full).sort_index()
    rb, rd = pb.pct_change().dropna(), pd_.pct_change().dropna()
    common = rb.index.intersection(rd.index)
    corr = round(float(rb.loc[common].corr(rd.loc[common])), 3) if len(common) > 30 else None
    diag = biweekly_fridays(calendar); diag = diag[(diag >= pd.Timestamp("2017-01-01")) & (diag <= pd.Timestamp("2026-07-20"))]
    overlap = holdings_overlap(base_sfn, div_sfn, diag, top_n=TOP_N)

    oos3 = oos_df[oos_df["window"] != "IS"]
    gate = {"lambda_star": lam_star, "calmar_wins_of_3": int(oos3["calmar_better"].sum()),
            "calmar_gate_pass": int(oos3["calmar_better"].sum()) >= 2,
            "worst_cagr_giveup_pp": round(float(oos3["cagr_delta"].min()), 2),
            "cagr_gate_pass": float(oos3["cagr_delta"].min()) >= -3.0,
            "corr_to_OM25": corr, "overlap_to_OM25_pct": overlap}
    gate["E1STYLE_PASS"] = bool(gate["calmar_gate_pass"] and gate["cagr_gate_pass"])
    (out_dir / "verdict.json").write_text(json.dumps({"is": is_rows, "oos": rows, "gate": gate}, indent=2, default=str))
    oos_df.to_csv(out_dir / "oos.csv", index=False)

    pd.set_option("display.width", 200, "display.max_columns", 30)
    print("\n" + "=" * 78)
    print(f"OM25-DIV — selection de-crowding on Quality Momentum (λ*={lam_star})")
    print("=" * 78)
    print(oos_df.to_string(index=False))
    print("\nGate + character:", json.dumps(gate, indent=2))
    print(f"\nwrote {out_dir}")


if __name__ == "__main__":
    main()
