"""(b) + (c) combined: walk-forward the new Defensive candidate, AND test
50-DMA-based regime variants for faster bear detection.

The candidate: Friday biweekly L6→OM25 + Binary 100-DMA + 3-conf + bear=50%

Two sub-investigations:

(b) Walk-forward stress test: run the candidate across 13 rolling 1-year
    OOS windows (same framework as momentum_walk_forward.py) to verify
    the DD reduction is structurally consistent on the new cadence.

(c) 50-DMA variants: 50-DMA is faster than 100-DMA (catches bear sooner
    but more whipsaw-prone). Test:
      - 50-DMA + 3 conf + bear=50%
      - 50-DMA + 5 conf + bear=50% (longer confirm for noise filter)
      - 50-DMA + 3 conf + bear=75% (lighter de-risk since 50-DMA fires more often)
    Compare to the current 100-DMA + 3 conf + bear=50%.
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
from scripts.backtest_momentum import load_price_panels, load_benchmark
from scripts.build_om25_signals import load_universe
from scripts.multi_window_oos_eval import period_metrics


# 13 walk-forward OOS windows (matches walk_forward/PLAN.md)
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

# Aggregate windows
AGG_WINDOWS = [
    ("IS",          "2009-09-01", "2016-12-31"),
    ("OOS_A",       "2017-01-01", "2019-12-31"),
    ("OOS_B",       "2020-01-01", "2022-12-31"),
    ("OOS_C",       "2023-01-01", "2026-05-08"),
    ("OOS_full",    "2017-01-01", "2026-05-08"),
    ("Prod window", "2020-07-10", "2026-05-08"),
]


def make_combined(score_fns_in_priority_order, n_per=12):
    def score_fn(signal_date, **_):
        picked = set(); rows = []
        for _, sf in score_fns_in_priority_order:
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


def _sortino(eq, s, e):
    s = pd.Timestamp(s); e = pd.Timestamp(e)
    sub = eq[(eq["date"] >= s) & (eq["date"] <= e)]
    if len(sub) < 5: return None
    rets = sub["pv"].astype(float).pct_change().dropna()
    if rets.empty: return None
    downside = rets[rets < 0]
    if downside.empty or downside.std() == 0: return None
    excess = rets.mean() * 252 - 0.05
    return excess / (downside.std() * math.sqrt(252))


def run_full(score_fn, ctx, regime_panel, bear_exposure):
    entry_all = biweekly_fridays(ctx["calendar"])
    weekly_all = fridays(ctx["calendar"])
    s = pd.Timestamp("2009-09-01"); e = pd.Timestamp("2026-05-08")
    entry_dates = entry_all[(entry_all >= s) & (entry_all <= e)]
    weekly_filt = weekly_all[(weekly_all >= s) & (weekly_all <= e)]
    res = run_strategy(
        close_panel=ctx["close_panel"], trade_panel=ctx["trade_panel"],
        calendar=ctx["calendar"], benchmark_aligned=ctx["benchmark_aligned"],
        entry_signal_dates=entry_dates, weekly_signal_dates=weekly_filt,
        signal_function=score_fn, signal_function_args={},
        sma_200_panel=ctx["sma_200"], atr_20_panel=ctx["atr_20"],
        top_n=24, exit_buffer=0,
        max_weight=0.075, slippage=0.002,
        atr_mult=0.0, atr_min_floor=0.0,
        use_trailing_stop=False, use_dma_exit=False,
        weekly_rank_check=False,
        regime_panel=regime_panel, bear_exposure=bear_exposure,
        min_hold_days=8, initial_capital=1_000_000,
    )
    return res["equity"]


def slice_metrics(eq, start, end):
    m = period_metrics(eq, "x", start, end)
    cagr = m.get("cagr_pct"); dd = m.get("max_dd_pct"); sh = m.get("sharpe")
    return {
        "cagr_pct": round(cagr, 2) if cagr is not None else None,
        "sharpe": round(sh, 2) if sh is not None else None,
        "sortino": round(_sortino(eq, start, end), 2) if _sortino(eq, start, end) is not None else None,
        "calmar": round(_calmar(cagr, dd), 2) if _calmar(cagr, dd) is not None else None,
        "max_dd_pct": round(dd, 2) if dd is not None else None,
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
        ROOT / "indices_data_historical/NIFTY_100.csv",
        OM25_LOCKED["regime_ma_window"], OM25_LOCKED["regime_confirm_days"],
        calendar=calendar,
    )
    om25_score = make_om25_tilt_score(
        om25_returns, om25_regime_for_score,
        bull_w_uc=OM25_LOCKED["bull_w_uc"], bull_w_cr=OM25_LOCKED["bull_w_cr"],
        bear_w_uc=OM25_LOCKED["bear_w_uc"], bear_w_cr=OM25_LOCKED["bear_w_cr"],
        return_filter=OM25_LOCKED["return_filter"],
        lookback=OM25_LOCKED["lookback"], min_obs=OM25_LOCKED["min_obs"],
    )

    ctx = dict(close_panel=close_panel, trade_panel=trade_panel,
                calendar=calendar, benchmark_aligned=benchmark_aligned,
                sma_200=sma_200, atr_20=atr_20)
    combo = make_combined([("L6", l6_score), ("OM25", om25_score)], n_per=12)

    print("[build] regime panels for comparison ...")
    # Current candidate's regime
    regime_100_3 = build_regime_panel_confirmed(
        ROOT / "indices_data_historical/NIFTY_100.csv", 100, 3, calendar=calendar,
    )
    # 50-DMA variants
    regime_50_3 = build_regime_panel_confirmed(
        ROOT / "indices_data_historical/NIFTY_100.csv", 50, 3, calendar=calendar,
    )
    regime_50_5 = build_regime_panel_confirmed(
        ROOT / "indices_data_historical/NIFTY_100.csv", 50, 5, calendar=calendar,
    )

    # === Configs ===
    configs = [
        # (label, score_fn, regime, bear_exposure)
        ("L6 standalone (production, Thu wkly)", l6_score, None, 0.0),
        ("Combo no regime (Fri biwkly L6→OM25)", combo, None, 0.0),
        ("Combo + 100-DMA/3conf/50% (current Defensive)", combo, regime_100_3, 0.5),
        ("Combo + 50-DMA/3conf/50% (faster)", combo, regime_50_3, 0.5),
        ("Combo + 50-DMA/5conf/50% (faster but more confirm)", combo, regime_50_5, 0.5),
        ("Combo + 50-DMA/3conf/75% (lighter de-risk)", combo, regime_50_3, 0.75),
    ]

    # Run all configs once; reuse equity for both walk-forward and aggregate windows
    print("[run] all configs ...")
    equities = {}
    for label, sfn, reg, be in configs:
        print(f"  {label}", flush=True)
        # L6 standalone uses Thursday weekly (production native) — run that separately
        if label.startswith("L6 standalone"):
            from scripts._momentum_engine import run_momentum
            res = run_momentum(
                close_panel=close_panel, trade_panel=trade_panel,
                calendar=calendar, benchmark_aligned=benchmark_aligned,
                panels=l6_panels, sma_200_panel=sma_200, atr_20_panel=atr_20,
                start="2009-09-01", end="2026-05-08", config={},
            )
            equities[label] = res["equity"]
        else:
            equities[label] = run_full(sfn, ctx, reg, be)

    # === Aggregate-window summary (IS / OOS_A/B/C/full / Prod) ===
    print("\n[slice] aggregate windows ...")
    agg_rows = []
    for label, _, _, _ in configs:
        eq = equities[label]
        for w_id, s, e in AGG_WINDOWS:
            m = slice_metrics(eq, s, e)
            agg_rows.append({"config": label, "window": w_id, **m})
    agg_df = pd.DataFrame(agg_rows)
    agg_df.to_csv(ROOT / "tasks/MM-tuning/defensive_validation_agg.csv", index=False)

    print(f"\n{'=' * 130}")
    print("DEFENSIVE candidate variants — aggregate window summary")
    print(f"{'=' * 130}")
    for w in ["OOS_full", "Prod window", "OOS_B", "OOS_C"]:
        sub = agg_df[agg_df["window"] == w]
        if sub.empty: continue
        print(f"\n--- {w} ---")
        cols = ["config", "cagr_pct", "sharpe", "sortino", "calmar", "max_dd_pct"]
        print(sub[cols].to_string(index=False))

    # === Walk-forward per-window ===
    print(f"\n[slice] 13 walk-forward windows ...")
    wf_rows = []
    for w_id, (is_s, is_e, oos_s, oos_e) in WF_WINDOWS.items():
        for label, _, _, _ in configs:
            eq = equities[label]
            oos_m = slice_metrics(eq, oos_s, oos_e)
            wf_rows.append({
                "window": w_id, "config": label,
                "oos_start": oos_s, "oos_end": oos_e,
                "oos_sharpe": oos_m["sharpe"],
                "oos_cagr_pct": oos_m["cagr_pct"],
                "oos_max_dd_pct": oos_m["max_dd_pct"],
                "oos_calmar": oos_m["calmar"],
                "oos_pass": (oos_m["sharpe"] is not None and oos_m["sharpe"] >= 0.7),
            })
    wf_df = pd.DataFrame(wf_rows)
    wf_df.to_csv(ROOT / "tasks/MM-tuning/defensive_validation_wf.csv", index=False)

    print(f"\n{'=' * 130}")
    print("WALK-FORWARD pass rates (OOS Sharpe ≥ 0.7)")
    print(f"{'=' * 130}")
    summary = (wf_df.groupby("config")
                  .agg(n_windows=("oos_pass", "count"),
                       n_pass=("oos_pass", "sum"),
                       mean_oos_sharpe=("oos_sharpe", "mean"),
                       median_oos_sharpe=("oos_sharpe", "median"),
                       min_oos_sharpe=("oos_sharpe", "min"),
                       mean_oos_cagr=("oos_cagr_pct", "mean"),
                       worst_oos_dd=("oos_max_dd_pct", "min"))
                  .round(2))
    summary["pass_rate_pct"] = (summary["n_pass"] / summary["n_windows"] * 100).round(0)
    print(summary[["n_windows", "n_pass", "pass_rate_pct",
                    "mean_oos_sharpe", "median_oos_sharpe", "min_oos_sharpe",
                    "mean_oos_cagr", "worst_oos_dd"]].to_string())

    print(f"\n{'=' * 130}")
    print("PER-WINDOW OOS Sharpe (passes Sharpe ≥ 0.7?)")
    print(f"{'=' * 130}")
    pivot = wf_df.pivot(index="window", columns="config",
                          values="oos_sharpe").reindex(WF_WINDOWS.keys())
    print(pivot.round(2).to_string())

    print(f"\n{'=' * 130}")
    print("PER-WINDOW OOS Max DD")
    print(f"{'=' * 130}")
    pivot_dd = wf_df.pivot(index="window", columns="config",
                             values="oos_max_dd_pct").reindex(WF_WINDOWS.keys())
    print(pivot_dd.round(2).to_string())


if __name__ == "__main__":
    main()
