"""3-state regime overlay — Bull / Bear / Value-Zone.

The thesis: a bear from MA crossover correctly de-risks, BUT extreme
oversold conditions are mean-reversion opportunities, not stay-in-cash
moments. Redeploy capital when the market stretches far below MA.

States (target gross exposure):
  BULL  (price > MA + 3-day confirm)       → 100% invested
  BEAR  (price < MA, not extreme)          → bear_exposure (30% by default)
  VALUE (price < MA AND oversold extreme)  → 100% invested (deploy)

Transitions:
  BULL → BEAR: price < MA for 3 consecutive days
  BEAR → VALUE: oversold trigger fires (price < MA - N×σ, or breadth crashes)
  BEAR → BULL: price > MA for 3 consecutive days (recovery)
  VALUE → BULL: price > MA for 3 consecutive days (recovery from extreme)
  VALUE → BEAR: never directly — once in value, stay deployed until MA recovery

VARIANTS TESTED:
  V1: Stddev value zone at -2σ (price < MA - 2 × rolling_std)
  V2: Stddev value zone at -2.5σ (tighter — only deepest events)
  V3: Stddev value zone at -1.5σ (looser — more frequent value triggers)
  BV1: Breadth value zone at <10% (very low breadth = extreme)
  BV2: Breadth value zone at <15%
  BV3: Breadth value zone at <20% (most generous)
  F: Reference binary 100-DMA (no value zone)

All tested on COMBO 50/50 Friday biweekly + ALT 1 + bear=30%.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
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


def build_3state_stddev_regime(
    idx_path, calendar, *,
    bear_ma=100, bear_confirm=3,
    value_stddev_threshold=2.0,    # price < MA - this many σ → value zone
    stddev_window=252,
    bear_exposure=0.30,
):
    """3-state regime (bull/bear/value) based on price's stddev distance from MA.

    Returns a float panel where each date has the target gross exposure:
      1.0 = bull or value (full invested)
      bear_exposure = bear (de-risked)
    """
    idx = pd.read_csv(idx_path, parse_dates=["date"])
    idx["date"] = pd.to_datetime(idx["date"]).dt.tz_localize(None).dt.normalize()
    idx = idx.sort_values("date").set_index("date")["close"].astype(float)

    sma = idx.rolling(bear_ma, min_periods=bear_ma).mean()
    pct_dev = (idx - sma) / sma
    rolling_std = pct_dev.rolling(stddev_window, min_periods=stddev_window).std()

    state = []   # "BULL", "BEAR", "VALUE"
    exposure = []
    current = "BULL"
    bear_consec = 0
    bull_consec = 0  # consecutive bull-trigger days while in bear/value
    for d in idx.index:
        price = idx[d]; ma = sma.get(d); std = rolling_std.get(d)
        if pd.isna(price) or pd.isna(ma):
            state.append(current)
            exposure.append(1.0 if current != "BEAR" else bear_exposure)
            continue
        below_ma = price < ma
        extreme = False
        if not pd.isna(std):
            extreme = pct_dev[d] < -value_stddev_threshold * std

        if current == "BULL":
            if below_ma:
                bear_consec += 1
                if bear_consec >= bear_confirm:
                    current = "BEAR"
                    bear_consec = 0
                    bull_consec = 0
            else:
                bear_consec = 0
        elif current == "BEAR":
            bear_consec = 0
            # Check value trigger first (extreme oversold)
            if extreme:
                current = "VALUE"
                bull_consec = 0
            else:
                # Check bull recovery
                if not below_ma:
                    bull_consec += 1
                    if bull_consec >= bear_confirm:
                        current = "BULL"
                        bull_consec = 0
                else:
                    bull_consec = 0
        elif current == "VALUE":
            # In value zone — stay deployed until price > MA for confirm days
            if not below_ma:
                bull_consec += 1
                if bull_consec >= bear_confirm:
                    current = "BULL"
                    bull_consec = 0
            else:
                bull_consec = 0
            # NOTE: value zone is "sticky" — even if oversold becomes less
            # extreme, we don't fall back to bear; only MA recovery exits.

        state.append(current)
        exposure.append(bear_exposure if current == "BEAR" else 1.0)

    out_state = pd.Series(index=idx.index, data=state)
    out_exp = pd.Series(index=idx.index, data=exposure, dtype=float)
    out_exp = out_exp.shift(1).fillna(1.0)  # 1-day lag for no-lookahead
    if calendar is not None:
        out_exp = out_exp.reindex(calendar).ffill().fillna(1.0)
    return out_exp, out_state


def build_3state_breadth_regime(
    close_panel, universe_cols, calendar, *,
    bear_ma=100, bear_confirm=3,
    breadth_sma_window=200,
    bear_breadth_pct=0.30,    # below this breadth → bear trigger candidate
    value_breadth_pct=0.10,   # below this breadth → value zone (extreme low)
    bear_exposure=0.30,
    idx_path=None,
):
    """3-state regime using BOTH price-vs-MA (for bear/bull) AND breadth
    (for value zone).

    Transitions:
      BULL → BEAR: NIFTY 100 < bear_ma for bear_confirm days
      BEAR → VALUE: breadth < value_breadth_pct (extreme low)
      BEAR → BULL: NIFTY 100 > bear_ma for bear_confirm days
      VALUE → BULL: NIFTY 100 > bear_ma for bear_confirm days
    """
    # NIFTY 100 for MA trigger
    idx = pd.read_csv(idx_path, parse_dates=["date"])
    idx["date"] = pd.to_datetime(idx["date"]).dt.tz_localize(None).dt.normalize()
    idx = idx.sort_values("date").set_index("date")["close"].astype(float)
    sma = idx.rolling(bear_ma, min_periods=bear_ma).mean()

    # Breadth on NSE 500
    uni_panel = close_panel[universe_cols]
    breadth_sma = uni_panel.rolling(breadth_sma_window, min_periods=breadth_sma_window).mean()
    above = uni_panel > breadth_sma
    valid = uni_panel.notna() & breadth_sma.notna()
    breadth = (above & valid).sum(axis=1) / valid.sum(axis=1).clip(lower=1)
    breadth = breadth.reindex(idx.index).ffill().bfill()

    state = []
    exposure = []
    current = "BULL"
    bear_consec = 0
    bull_consec = 0
    for d in idx.index:
        price = idx[d]; ma = sma.get(d); br = breadth.get(d)
        if pd.isna(price) or pd.isna(ma) or pd.isna(br):
            state.append(current)
            exposure.append(1.0 if current != "BEAR" else bear_exposure)
            continue
        below_ma = price < ma
        extreme = br < value_breadth_pct

        if current == "BULL":
            if below_ma:
                bear_consec += 1
                if bear_consec >= bear_confirm:
                    current = "BEAR"
                    bear_consec = 0; bull_consec = 0
            else:
                bear_consec = 0
        elif current == "BEAR":
            bear_consec = 0
            if extreme:
                current = "VALUE"; bull_consec = 0
            else:
                if not below_ma:
                    bull_consec += 1
                    if bull_consec >= bear_confirm:
                        current = "BULL"; bull_consec = 0
                else:
                    bull_consec = 0
        elif current == "VALUE":
            if not below_ma:
                bull_consec += 1
                if bull_consec >= bear_confirm:
                    current = "BULL"; bull_consec = 0
            else:
                bull_consec = 0

        state.append(current)
        exposure.append(bear_exposure if current == "BEAR" else 1.0)

    out_state = pd.Series(index=idx.index, data=state)
    out_exp = pd.Series(index=idx.index, data=exposure, dtype=float)
    out_exp = out_exp.shift(1).fillna(1.0)
    if calendar is not None:
        out_exp = out_exp.reindex(calendar).ffill().fillna(1.0)
    return out_exp, out_state, breadth


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

    BEAR_EXPOSURE = 0.30

    # Build all variant regime panels (float)
    regimes = {}

    # Reference: binary 100-DMA, no value zone
    bin_ref = build_regime_panel_confirmed(idx_path, 100, 3, calendar=calendar)
    # Convert bool to float panel for consistency
    regimes["F. reference 100-DMA (no value zone)"] = pd.Series(
        [1.0 if v else BEAR_EXPOSURE for v in bin_ref], index=bin_ref.index,
    )

    # Stddev value zone variants
    for label, threshold in [("V1: stddev value @ -2σ", 2.0),
                              ("V2: stddev value @ -2.5σ", 2.5),
                              ("V3: stddev value @ -1.5σ", 1.5)]:
        panel, _ = build_3state_stddev_regime(
            idx_path, calendar,
            bear_ma=100, bear_confirm=3,
            value_stddev_threshold=threshold,
            bear_exposure=BEAR_EXPOSURE,
        )
        regimes[label] = panel

    # Breadth value zone variants
    for label, br_thresh in [("BV1: breadth value @ <10%", 0.10),
                              ("BV2: breadth value @ <15%", 0.15),
                              ("BV3: breadth value @ <20%", 0.20)]:
        panel, _, _ = build_3state_breadth_regime(
            close_panel, nse500_cols, calendar,
            bear_ma=100, bear_confirm=3,
            value_breadth_pct=br_thresh,
            bear_exposure=BEAR_EXPOSURE,
            idx_path=idx_path,
        )
        regimes[label] = panel

    # Diagnostic: count of days in each state for each variant
    print(f"\n{'=' * 110}")
    print("DIAGNOSTIC: days at each exposure level (full history 2009-2026)")
    print(f"{'=' * 110}")
    for label, panel in regimes.items():
        bull_days = (panel >= 0.95).sum()
        value_days = ((panel >= 0.95) & (panel < 1.0)).sum()
        bear_days = (panel < 0.95).sum()
        total = len(panel)
        # For 3-state, "bull" and "value" both = 1.0 so we can't distinguish
        # without the state series. Just count days at full vs bear.
        full_days = (panel >= 0.95).sum()
        print(f"  {label:45s}: full={full_days} ({100*full_days/total:.0f}%), "
              f"bear={bear_days} ({100*bear_days/total:.0f}%)")

    # Run backtests
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
            regime_panel=regime, bear_exposure=BEAR_EXPOSURE,
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

    # === Aggregate ===
    print(f"\n{'=' * 110}")
    print("AGGREGATE METRICS")
    print(f"{'=' * 110}")
    agg_rows = []
    for label, eq in equities.items():
        for w_id, s, e in [("OOS_full", "2017-01-01", "2026-05-08"),
                            ("Prod window", "2020-07-10", "2026-05-08"),
                            ("OOS_B (COVID)", "2020-01-01", "2022-12-31")]:
            agg_rows.append({"variant": label, "window": w_id, **slice_metrics(eq, s, e)})
    agg = pd.DataFrame(agg_rows)
    for w in ["OOS_full", "Prod window", "OOS_B (COVID)"]:
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
                       median_oos_sharpe=("oos_sharpe", "median"))
                  .round(2))
    summary["pass_rate_pct"] = (summary["n_pass"] / 13 * 100).round(0)
    print(summary.to_string())

    pd.DataFrame(rows).to_csv(ROOT / "tasks/MM-tuning/three_state_trailing.csv", index=False)
    agg.to_csv(ROOT / "tasks/MM-tuning/three_state_agg.csv", index=False)
    wf_df.to_csv(ROOT / "tasks/MM-tuning/three_state_wf.csv", index=False)


if __name__ == "__main__":
    main()
