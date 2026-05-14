"""Alternative regime signals — drawdown-based and breadth-based.

Tests fundamentally different regime triggers vs the reference 100-DMA:

DRAWDOWN-BASED (NIFTY 100 drawdown from trailing peak):
  DD1: bear < -10% from 100-day peak; bull when recovered to within -5%
  DD2: bear < -15% from 100-day peak; bull when recovered to within -5%
  DD3: bear < -10%; bull within -3% (tighter recovery — more rally-eager)

BREADTH-BASED (% of NSE 500 stocks above their own 200-DMA):
  BR1: bear when breadth < 30%; bull when > 50%
  BR2: bear when breadth < 25%; bull when > 55% (more conservative)
  BR3: bear when breadth < 30%; bull when > 40% (looser bull — eager re-entry)

Reference: F. symmetric_100_3 (current).

All tested on COMBO 50/50 Friday biweekly + ALT 1 + bear=30%.
Reports trailing returns, OOS_full, walk-forward pass rate, regime flips.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts._clean_engine import run_strategy, biweekly_fridays, fridays
from scripts._momentum_engine import (
    BASELINE as MM_BASELINE, build_momentum_panels, make_momentum_score,
    lookback_months_to_days,
)
from scripts.om25_v3 import (
    LOCKED as OM25_LOCKED, build_regime_panel_confirmed, make_om25_tilt_score,
)
from scripts.combo_defensive import LOCKED as COMBO_LOCKED, make_combo_score_fn
from scripts.backtest_momentum import load_price_panels, load_benchmark
from scripts.build_om25_signals import load_universe
from scripts.multi_window_oos_eval import period_metrics


END_DATE = "2026-05-12"


def build_drawdown_regime(
    idx_path, calendar, *,
    peak_window=100,
    bear_threshold=-0.10,    # bear when DD from peak < this (e.g., -0.10 = -10%)
    bull_threshold=-0.05,    # bull when DD recovers to > this (e.g., -0.05 = -5%)
):
    """Bull/bear based on NIFTY 100 drawdown from rolling peak.

    State machine:
      - Start bull
      - In bull: switch to bear when drawdown < bear_threshold
      - In bear: switch to bull when drawdown >= bull_threshold (i.e., closer to peak)
    """
    idx = pd.read_csv(idx_path, parse_dates=["date"])
    idx["date"] = pd.to_datetime(idx["date"]).dt.tz_localize(None).dt.normalize()
    idx = idx.sort_values("date").set_index("date")["close"].astype(float)
    rolling_peak = idx.rolling(peak_window, min_periods=1).max()
    drawdown = (idx / rolling_peak) - 1.0

    state = []
    current = True
    for d in idx.index:
        dd = drawdown.get(d)
        if dd is None or pd.isna(dd):
            state.append(current); continue
        if current:
            if dd < bear_threshold:
                current = False
        else:
            if dd > bull_threshold:
                current = True
        state.append(current)
    out = pd.Series(index=idx.index, data=state, dtype=bool)
    out = out.shift(1).fillna(True)
    if calendar is not None:
        out = out.reindex(calendar).ffill().fillna(True).astype(bool)
    return out


def build_breadth_regime(
    close_panel, universe_cols, calendar, *,
    sma_window=200,
    bear_pct=0.30,    # bear when breadth (% above 200-DMA) < this
    bull_pct=0.50,    # bull when breadth > this
):
    """Bull/bear based on % of universe stocks above their own 200-DMA.

    State machine:
      - Start bull
      - In bull: switch to bear when breadth_pct < bear_pct
      - In bear: switch to bull when breadth_pct > bull_pct
    """
    uni_panel = close_panel[universe_cols]
    sma = uni_panel.rolling(sma_window, min_periods=sma_window).mean()
    above = uni_panel > sma
    # Use only days where each stock has enough data
    valid = uni_panel.notna() & sma.notna()
    breadth = (above & valid).sum(axis=1) / valid.sum(axis=1).clip(lower=1)

    state = []
    current = True
    for d in breadth.index:
        b = breadth.get(d)
        if b is None or pd.isna(b):
            state.append(current); continue
        if current:
            if b < bear_pct:
                current = False
        else:
            if b > bull_pct:
                current = True
        state.append(current)
    out = pd.Series(index=breadth.index, data=state, dtype=bool)
    out = out.shift(1).fillna(True)
    if calendar is not None:
        out = out.reindex(calendar).ffill().fillna(True).astype(bool)
    return out, breadth


def make_combo(score_fns, n_per=12):
    def score_fn(signal_date, **_):
        picked = set(); rows = []
        for _, sf in score_fns:
            scores = sf(signal_date)
            if scores is None or scores.empty: continue
            ranked = scores.dropna().sort_values(ascending=False)
            taken = 0
            for sym in ranked.index:
                if sym in picked: continue
                picked.add(sym); rows.append(sym); taken += 1
                if taken >= n_per: break
        if not rows: return pd.Series(dtype=float)
        n = len(rows)
        return pd.Series({sym: float(n - i) for i, sym in enumerate(rows)})
    return score_fn


def _calmar(c, d):
    if d is None or pd.isna(d) or abs(d) < 1e-6: return None
    return c / abs(d)


def slice_metrics(eq, start, end):
    m = period_metrics(eq, "x", start, end)
    cagr = m.get("cagr_pct"); dd = m.get("max_dd_pct"); sh = m.get("sharpe")
    return {
        "cagr_pct": round(cagr, 2) if cagr is not None else None,
        "sharpe": round(sh, 2) if sh is not None else None,
        "calmar": round(_calmar(cagr, dd), 2) if _calmar(cagr, dd) is not None else None,
        "max_dd_pct": round(dd, 2) if dd is not None else None,
    }


def trailing(eq, end_date):
    pv = eq.set_index("date")["pv"].astype(float)
    pv.index = pd.to_datetime(pv.index)
    pv = pv[pv.index <= pd.Timestamp(end_date)]
    if pv.empty: return {}
    out = {}
    for days, label in [(21, "1mo"), (63, "3mo"), (126, "6mo")]:
        if len(pv) > days:
            out[label] = round((pv.iloc[-1] / pv.iloc[-days - 1] - 1) * 100, 2)
    ytd = pv[pv.index >= pd.Timestamp("2026-01-01")]
    if not ytd.empty:
        out["YTD_2026"] = round((ytd.iloc[-1] / ytd.iloc[0] - 1) * 100, 2)
    return out


def regime_flips_recent(panel, end_date, days_back=180):
    end_ts = pd.Timestamp(end_date)
    start = end_ts - pd.Timedelta(days=days_back)
    sub = panel[(panel.index >= start) & (panel.index <= end_ts)]
    flips = []
    prev = None
    for d, v in sub.items():
        if prev is not None and v != prev:
            flips.append((d.date(), "BULL" if v else "BEAR"))
        prev = v
    return flips


WF_WINDOWS = {
    "W01": ("2010-09-01", "2013-08-31", "2013-09-01", "2014-08-31"),
    "W02": ("2011-09-01", "2014-08-31", "2014-09-01", "2015-08-31"),
    "W03": ("2012-09-01", "2015-08-31", "2015-09-01", "2016-08-31"),
    "W04": ("2013-09-01", "2016-08-31", "2016-09-01", "2017-08-31"),
    "W05": ("2014-09-01", "2017-08-31", "2017-09-01", "2018-08-31"),
    "W06": ("2015-09-01", "2018-08-31", "2018-09-01", "2019-08-31"),
    "W07": ("2016-09-01", "2019-08-31", "2019-09-01", "2020-08-31"),
    "W08": ("2017-09-01", "2020-08-31", "2020-09-01", "2021-08-31"),
    "W09": ("2018-09-01", "2021-08-31", "2021-09-01", "2022-08-31"),
    "W10": ("2019-09-01", "2022-08-31", "2022-09-01", "2023-08-31"),
    "W11": ("2020-09-01", "2023-08-31", "2023-09-01", "2024-08-31"),
    "W12": ("2021-09-01", "2024-08-31", "2024-09-01", "2025-08-31"),
    "W13": ("2022-09-01", "2025-08-31", "2025-09-01", "2026-05-08"),
}


def main():
    print("[load] panels ...")
    close_panel, trade_panel = load_price_panels(ROOT / "nse500_data_merged")
    calendar = close_panel.index
    benchmark = load_benchmark(ROOT / "data/benchmarks/nifty100.csv")
    benchmark_aligned = benchmark.reindex(calendar).ffill()
    sma_200 = close_panel.rolling(200, min_periods=200).mean()
    atr_20 = close_panel.pct_change().rolling(20).std()

    nse500_uni = load_universe(ROOT / "data/static/nse500_universe.csv")
    nse500_cols = [s for s in close_panel.columns if s in nse500_uni]
    l6_panels = build_momentum_panels(
        close_panel[nse500_cols],
        lookback_days=lookback_months_to_days(MM_BASELINE["lookback_months"]),
        skip_days=MM_BASELINE["skip_days"],
    )
    l6_score = make_momentum_score(
        l6_panels, vol_floor=MM_BASELINE["vol_floor"],
        vol_power=MM_BASELINE["vol_power"], cross_sectional_zscore=True,
    )
    nifty250_uni = load_universe(ROOT / "data/static/nifty250_universe.csv")
    nifty250_cols = [s for s in close_panel.columns if s in nifty250_uni]
    om25_returns = close_panel[nifty250_cols].pct_change()
    om25_regime_for_score = build_regime_panel_confirmed(
        ROOT / "indices_data_historical/NIFTY_100.csv", 100, 3, calendar=calendar,
    )
    om25_score = make_om25_tilt_score(
        om25_returns, om25_regime_for_score,
        bull_w_uc=OM25_LOCKED["bull_w_uc"], bull_w_cr=OM25_LOCKED["bull_w_cr"],
        bear_w_uc=OM25_LOCKED["bear_w_uc"], bear_w_cr=OM25_LOCKED["bear_w_cr"],
        return_filter=OM25_LOCKED["return_filter"],
        lookback=OM25_LOCKED["lookback"], min_obs=OM25_LOCKED["min_obs"],
    )
    combo = make_combo([("L6", l6_score), ("OM25", om25_score)], n_per=12)

    print("[build] regime panels ...")
    idx_path = ROOT / "indices_data_historical/NIFTY_100.csv"

    regimes = {
        "F. reference 100-DMA/3-conf": build_regime_panel_confirmed(
            idx_path, 100, 3, calendar=calendar),
        "DD1: bear<-10% peak, bull>-5%": build_drawdown_regime(
            idx_path, calendar, peak_window=100,
            bear_threshold=-0.10, bull_threshold=-0.05),
        "DD2: bear<-15% peak, bull>-5%": build_drawdown_regime(
            idx_path, calendar, peak_window=100,
            bear_threshold=-0.15, bull_threshold=-0.05),
        "DD3: bear<-10%, bull>-3% (tight)": build_drawdown_regime(
            idx_path, calendar, peak_window=100,
            bear_threshold=-0.10, bull_threshold=-0.03),
    }
    # Breadth — needs the NSE500 panel to compute
    print("[build] breadth panels (slower — computing 500-stock 200-DMA) ...")
    br1, breadth1 = build_breadth_regime(
        close_panel, nse500_cols, calendar,
        sma_window=200, bear_pct=0.30, bull_pct=0.50)
    regimes["BR1: breadth bear<30%, bull>50%"] = br1
    br2, _ = build_breadth_regime(
        close_panel, nse500_cols, calendar,
        sma_window=200, bear_pct=0.25, bull_pct=0.55)
    regimes["BR2: breadth bear<25%, bull>55%"] = br2
    br3, _ = build_breadth_regime(
        close_panel, nse500_cols, calendar,
        sma_window=200, bear_pct=0.30, bull_pct=0.40)
    regimes["BR3: breadth bear<30%, bull>40%"] = br3

    # === Recent flip patterns ===
    print(f"\n{'=' * 110}")
    print("RECENT REGIME FLIPS (last 6 months)")
    print(f"{'=' * 110}")
    for label, panel in regimes.items():
        flips = regime_flips_recent(panel, END_DATE, days_back=180)
        end_state = "BULL" if panel.iloc[-1] else "BEAR"
        print(f"\n[{label}] today: {end_state}")
        if not flips:
            print(f"  (no flips in last 6mo)")
        else:
            for d, s in flips:
                print(f"  {d}: → {s}")

    # Show current breadth value for context
    end_ts = pd.Timestamp(END_DATE)
    nearest = breadth1.index[breadth1.index <= end_ts][-1]
    print(f"\nCurrent breadth (% NSE 500 > 200-DMA on {nearest.date()}): "
          f"{breadth1.loc[nearest]*100:.1f}%")

    # === Run backtests ===
    print(f"\n[run] backtests ...")
    equities = {}
    entry_all = biweekly_fridays(calendar)
    weekly_all = fridays(calendar)
    s_ts = pd.Timestamp("2009-09-01"); e_ts = pd.Timestamp(END_DATE)
    entry_dates = entry_all[(entry_all >= s_ts) & (entry_all <= e_ts)]
    weekly_filt = weekly_all[(weekly_all >= s_ts) & (weekly_all <= e_ts)]

    for label, regime in regimes.items():
        res = run_strategy(
            close_panel=close_panel, trade_panel=trade_panel,
            calendar=calendar, benchmark_aligned=benchmark_aligned,
            entry_signal_dates=entry_dates, weekly_signal_dates=weekly_filt,
            signal_function=combo, signal_function_args={},
            sma_200_panel=sma_200, atr_20_panel=atr_20,
            top_n=24, exit_buffer=0, max_weight=0.075, slippage=0.002,
            atr_mult=0.0, atr_min_floor=0.0,
            use_trailing_stop=False, use_dma_exit=False,
            weekly_rank_check=False,
            regime_panel=regime, bear_exposure=0.30,
            bear_skips_entries=False,
            min_hold_days=8, initial_capital=1_000_000,
        )
        equities[label] = res["equity"]
        print(f"  {label}", flush=True)

    # === Trailing returns ===
    print(f"\n{'=' * 110}")
    print("TRAILING RETURNS through 2026-05-12")
    print(f"{'=' * 110}")
    rows = []
    for label, eq in equities.items():
        rows.append({"variant": label, **trailing(eq, END_DATE)})
    print(pd.DataFrame(rows).to_string(index=False))

    # === Aggregate metrics ===
    print(f"\n{'=' * 110}")
    print("AGGREGATE METRICS")
    print(f"{'=' * 110}")
    agg_rows = []
    for label, eq in equities.items():
        for w_id, s, e in [("OOS_full", "2017-01-01", "2026-05-08"),
                            ("Prod window", "2020-07-10", "2026-05-08")]:
            agg_rows.append({"variant": label, "window": w_id, **slice_metrics(eq, s, e)})
    agg = pd.DataFrame(agg_rows)
    for w in ["OOS_full", "Prod window"]:
        sub = agg[agg["window"] == w]
        print(f"\n--- {w} ---")
        cols = ["variant", "cagr_pct", "sharpe", "calmar", "max_dd_pct"]
        print(sub[cols].to_string(index=False))

    # === Walk-forward ===
    print(f"\n{'=' * 110}")
    print("WALK-FORWARD (13 windows)")
    print(f"{'=' * 110}")
    wf_rows = []
    for w_id, (_, _, oos_s, oos_e) in WF_WINDOWS.items():
        for label, eq in equities.items():
            m = slice_metrics(eq, oos_s, oos_e)
            wf_rows.append({"window": w_id, "variant": label,
                              "oos_sharpe": m["sharpe"],
                              "oos_pass": (m["sharpe"] is not None and m["sharpe"] >= 0.7)})
    wf_df = pd.DataFrame(wf_rows)
    summary = (wf_df.groupby("variant")
                  .agg(n_pass=("oos_pass", "sum"),
                       mean_oos_sharpe=("oos_sharpe", "mean"),
                       median_oos_sharpe=("oos_sharpe", "median"),
                       min_oos_sharpe=("oos_sharpe", "min"))
                  .round(2))
    summary["pass_rate_pct"] = (summary["n_pass"] / 13 * 100).round(0)
    print(summary.to_string())

    pd.DataFrame(rows).to_csv(ROOT / "tasks/MM-tuning/alt_regime_trailing.csv", index=False)
    agg.to_csv(ROOT / "tasks/MM-tuning/alt_regime_agg.csv", index=False)
    wf_df.to_csv(ROOT / "tasks/MM-tuning/alt_regime_wf.csv", index=False)


if __name__ == "__main__":
    main()
