"""E-LV robustness — is the low-vol sleeve a real product or a lucky config?

Stress the LV_TREND result along the axes that decide a conservative
product:
  A. Cadence x size — does the edge survive lower churn (weekly/biweekly/
     monthly) and more diversification (top 24/30/40)? Conservative sleeves
     churn less; the edge must not depend on weekly trading.
  B. Ingredient sensitivity — vol estimator (EWMA vs realized 252d) and
     trend gate (both / 200-DMA only / momentum only / none). Confirms the
     edge isn't cherry-picked on one knob.
  C. Calendar-year returns vs NIFTY 100 and L6 — consistency, and exactly
     when it lags (the recent high-beta caveat).
  D. Rolling 1-year win-rate vs NIFTY 100 — beats the index across windows,
     not just full-period.
  E. Conservative benchmark — LV_TREND vs a 60/40 (NIFTY 100 / 10y gilt),
     2017+ (bond series starts 2017-06).

Reference config for C/D/E: LV_TREND, EWMA vol, both-gate, weekly, top-24
(the validated one). Run:  python tasks/raam_transplant/lv_robustness.py
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
from scripts._clean_engine import (  # noqa: E402
    run_strategy, thursdays, biweekly_thursdays, monthly_first_trading_day,
)
from scripts._momentum_engine import (  # noqa: E402
    BASELINE as L6, build_momentum_panels, make_momentum_score, lookback_months_to_days,
)
from lv_revisit import ewma_vol_panel, make_lv_score, VOL_MIN_OBS  # noqa: E402
from e1_l6div import load_index_close, NSE500_UNIVERSE_CSV, NIFTY100_INDEX  # noqa: E402

FULL = ("2009-09-01", "2026-07-20")
BOND_INDEX = "indices_data_historical/NIFTY_GS_10YR.csv"


def full_metrics(res, s, e) -> dict:
    eq = res["equity"].copy(); eq["date"] = pd.to_datetime(eq["date"])
    pv = eq.set_index("date")["pv"].astype(float)
    pv = pv.loc[(pv.index >= pd.Timestamp(s)) & (pv.index <= pd.Timestamp(e))]
    rets = pv.pct_change().dropna()
    years = max((pv.index[-1] - pv.index[0]).days / 365.25, 1e-9)
    cagr = (pv.iloc[-1] / pv.iloc[0]) ** (1 / years) - 1
    vol = rets.std() * math.sqrt(252)
    dd = (pv / pv.cummax() - 1).min()
    tr = res.get("trades")
    cost = None
    if tr is not None and not tr.empty and "slippage" in tr.columns:
        inw = tr[(pd.to_datetime(tr["date"]) >= pd.Timestamp(s)) & (pd.to_datetime(tr["date"]) <= pd.Timestamp(e))]
        cost = round(inw["slippage"].sum() / pv.mean() / years * 100, 2)  # vs avg capital
    return {"cagr": round(cagr * 100, 2), "vol": round(vol * 100, 2),
            "dd": round(dd * 100, 2), "sharpe": round((cagr - 0.05) / vol, 3) if vol > 0 else None,
            "calmar": round(cagr / abs(dd), 3) if dd < 0 else None, "cost_yr": cost}


def main():
    ts = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
    out_dir = ROOT / "tasks/raam_transplant/runs" / f"lv_robust_{ts}"
    out_dir.mkdir(parents=True, exist_ok=True)

    print("[load] panels")
    close_panel, trade_panel = load_price_panels(ROOT / "nse500_data_merged")
    calendar = close_panel.index
    benchmark = load_benchmark(ROOT / "data/benchmarks/nifty100.csv").reindex(calendar).ffill()
    sma_200 = close_panel.rolling(200, min_periods=200).mean()
    atr_20 = close_panel.pct_change().rolling(20).std()
    nse500 = load_universe(ROOT / NSE500_UNIVERSE_CSV)
    cols = [s for s in close_panel.columns if s in nse500]

    returns = close_panel[cols].pct_change()
    ewma_vol = ewma_vol_panel(returns)
    realized_vol = returns.rolling(252, min_periods=VOL_MIN_OBS).std() * math.sqrt(252)
    ret_252 = close_panel[cols] / close_panel[cols].shift(252) - 1.0
    mom_126 = close_panel[cols] / close_panel[cols].shift(126) - 1.0
    sma200_c = sma_200[cols]
    nifty100 = load_index_close(ROOT / NIFTY100_INDEX).reindex(calendar).ffill()

    def gate_both(d):
        up = (close_panel[cols].loc[d] > sma200_c.loc[d]) & (mom_126.loc[d] > 0)
        return set(up[up].index)

    def gate_dma(d):
        up = close_panel[cols].loc[d] > sma200_c.loc[d]
        return set(up[up].index)

    def gate_mom(d):
        up = mom_126.loc[d] > 0
        return set(up[up].index)

    def entry_dates(cadence, s, e):
        base = {"weekly": thursdays, "biweekly": biweekly_thursdays,
                "monthly": monthly_first_trading_day}[cadence](calendar)
        return base[(base >= pd.Timestamp(s)) & (base <= pd.Timestamp(e))]

    def run(score_fn, cadence, top_n, s, e, dd_stop=0.0):
        ed = entry_dates(cadence, s, e)
        if len(ed) == 0:
            return None
        return run_strategy(
            close_panel=close_panel[cols], trade_panel=trade_panel[cols], calendar=calendar,
            benchmark_aligned=benchmark, entry_signal_dates=ed, weekly_signal_dates=ed,
            signal_function=score_fn, signal_function_args={},
            sma_200_panel=sma_200[cols], atr_20_panel=atr_20[cols],
            top_n=top_n, exit_buffer=0, max_weight=1.0 / top_n * 1.8, slippage=0.002,
            atr_mult=0.0, atr_min_floor=dd_stop, use_trailing_stop=dd_stop > 0,
            use_dma_exit=False, weekly_rank_check=False, regime_panel=None,
            bear_exposure=0.0, bear_skips_entries=False, min_hold_days=8, initial_capital=1_000_000)

    ref_score = make_lv_score(ewma_vol, ret_252, trend_gate=gate_both)

    # ---- A. cadence x size ----
    print("[A] cadence x size")
    A = []
    for cad in ["weekly", "biweekly", "monthly"]:
        for n in [24, 30, 40]:
            res = run(ref_score, cad, n, *FULL)
            if res:
                A.append({"cadence": cad, "top_n": n, **full_metrics(res, *FULL)})
    A_df = pd.DataFrame(A); A_df.to_csv(out_dir / "A_cadence_size.csv", index=False)

    # ---- B. ingredient sensitivity (weekly, 24) ----
    print("[B] ingredient sensitivity")
    B = []
    for vlabel, vpanel in [("EWMA", ewma_vol), ("realized252", realized_vol)]:
        for glabel, g in [("both", gate_both), ("dma_only", gate_dma), ("mom_only", gate_mom), ("none", None)]:
            sfn = make_lv_score(vpanel, ret_252, trend_gate=g)
            res = run(sfn, "weekly", 24, *FULL)
            if res:
                B.append({"vol_est": vlabel, "gate": glabel, **full_metrics(res, *FULL)})
    B_df = pd.DataFrame(B); B_df.to_csv(out_dir / "B_ingredients.csv", index=False)

    # reference PV for C/D/E
    ref_res = run(ref_score, "weekly", 24, *FULL)
    reqp = ref_res["equity"].copy(); reqp["date"] = pd.to_datetime(reqp["date"])
    lv_pv = reqp.set_index("date")["pv"].astype(float)
    l6_panels = build_momentum_panels(close_panel[cols], lookback_days=lookback_months_to_days(L6["lookback_months"]), skip_days=L6["skip_days"])
    l6_score = make_momentum_score(l6_panels, vol_floor=L6["vol_floor"], vol_power=L6["vol_power"], cross_sectional_zscore=L6["cross_sectional_zscore"])
    l6_res = run(l6_score, "weekly", 24, *FULL)
    l6q = l6_res["equity"].copy(); l6q["date"] = pd.to_datetime(l6q["date"])
    l6_pv = l6q.set_index("date")["pv"].astype(float)
    idx_pv = nifty100.loc[(nifty100.index >= pd.Timestamp(FULL[0])) & (nifty100.index <= pd.Timestamp(FULL[1]))].dropna()

    # ---- C. calendar-year returns ----
    def yearly(pv):
        return pv.resample("YE").last().pct_change().dropna() * 100
    C = pd.DataFrame({"LV_TREND": yearly(lv_pv), "NIFTY100": yearly(idx_pv), "L6": yearly(l6_pv)}).round(1)
    C.index = C.index.year
    C.to_csv(out_dir / "C_calendar.csv")

    # ---- D. rolling 1y win-rate vs NIFTY100 ----
    common = lv_pv.index.intersection(idx_pv.index)
    lvc, ixc = lv_pv.reindex(common).ffill(), idx_pv.reindex(common).ffill()
    lv_1y = lvc / lvc.shift(252) - 1
    ix_1y = ixc / ixc.shift(252) - 1
    both = pd.DataFrame({"lv": lv_1y, "ix": ix_1y}).dropna()
    ret_winrate = round(float((both["lv"] > both["ix"]).mean()) * 100, 1)
    # rolling 1y max drawdown
    def roll_dd(pv, w=252):
        out = {}
        for i in range(w, len(pv)):
            seg = pv.iloc[i - w:i]
            out[pv.index[i]] = (seg / seg.cummax() - 1).min()
        return pd.Series(out)
    lv_dd, ix_dd = roll_dd(lvc), roll_dd(ixc)
    ddc = pd.DataFrame({"lv": lv_dd, "ix": ix_dd}).dropna()
    dd_winrate = round(float((ddc["lv"] > ddc["ix"]).mean()) * 100, 1)  # shallower (less negative)

    # ---- E. 60/40 benchmark (2017+) ----
    bond = load_index_close(ROOT / BOND_INDEX).reindex(calendar).ffill()
    start6040 = "2017-06-01"
    m = pd.DataFrame({"eq": nifty100.pct_change(), "bd": bond.pct_change()}).dropna()
    m = m.loc[m.index >= pd.Timestamp(start6040)]
    blend_ret = 0.6 * m["eq"] + 0.4 * m["bd"]
    blend_pv = (1 + blend_ret).cumprod()
    lv6040 = lv_pv.loc[lv_pv.index >= pd.Timestamp(start6040)]
    E = {"LV_TREND": full_metrics_from_pv(lv6040), "60_40": full_metrics_from_pv(blend_pv),
         "NIFTY100": full_metrics_from_pv(idx_pv.loc[idx_pv.index >= pd.Timestamp(start6040)])}
    pd.DataFrame(E).T.to_csv(out_dir / "E_6040.csv")

    report = {"A": A, "B": B, "D": {"return_winrate_pct": ret_winrate, "dd_winrate_pct": dd_winrate},
              "E_from": start6040, "E": E}
    (out_dir / "report.json").write_text(json.dumps(report, indent=2, default=str))

    pd.set_option("display.width", 200, "display.max_columns", 30)
    print("\n" + "=" * 80)
    print("E-LV ROBUSTNESS")
    print("=" * 80)
    print("\n[A] Cadence x size (LV_TREND, FULL 2009-2026):")
    print(A_df.to_string(index=False))
    print("\n[B] Ingredient sensitivity (weekly, top-24, FULL):")
    print(B_df.to_string(index=False))
    print("\n[C] Calendar-year returns (%):")
    print(C.to_string())
    print(f"\n[D] Rolling 1-year win-rate vs NIFTY100:  return {ret_winrate}%   shallower-drawdown {dd_winrate}%")
    print(f"\n[E] vs 60/40 (NIFTY100/10y gilt), from {start6040}:")
    print(pd.DataFrame(E).T.to_string())
    print(f"\nwrote {out_dir}")


def full_metrics_from_pv(pv):
    pv = pv.dropna()
    rets = pv.pct_change().dropna()
    years = max((pv.index[-1] - pv.index[0]).days / 365.25, 1e-9)
    cagr = (pv.iloc[-1] / pv.iloc[0]) ** (1 / years) - 1
    vol = rets.std() * math.sqrt(252)
    dd = (pv / pv.cummax() - 1).min()
    return {"cagr": round(cagr * 100, 2), "vol": round(vol * 100, 2), "dd": round(dd * 100, 2),
            "sharpe": round((cagr - 0.05) / vol, 3) if vol > 0 else None}


if __name__ == "__main__":
    main()
