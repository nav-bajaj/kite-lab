"""Walk-forward stress test for L6 DD-reduction candidates.

Tests 4 candidate configs across 13 rolling 1-year OOS windows (matching
walk_forward/PLAN.md):
  1. L6 standalone (current production baseline)
  2. L6 + Regime (100-DMA, 3-conf, bear=50%)
  3. 50-50 COMBO L6+OM25 (L6 priority)
  4. 50-50 COMBO + Regime

For each (config, window) pair, computes Sharpe / CAGR / DD on the OOS year.
Reports pass-rate per config (Sharpe ≥ 0.7), worst-window DD, mean OOS metrics,
and Sharpe stability across regimes.

This is a robustness check on FIXED configs — not a re-tune. We want to know
which candidate holds up most consistently across the 13 different regimes
(pre-Modi, Modi rally, demonetization, COVID, mega rally, inflation,
smallcap mania, 2025 correction, etc).
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts._clean_engine import run_strategy, thursdays
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


# 13 rolling 3y-IS / 1y-OOS windows (matches tasks/walk_forward/PLAN.md)
WINDOWS = {
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


def make_combined_score_fn(score_fns_in_priority_order, n_per: int = 12):
    def score_fn(signal_date, **_):
        picked = set()
        rows = []
        for label, sf in score_fns_in_priority_order:
            scores = sf(signal_date)
            if scores is None or scores.empty:
                continue
            ranked = scores.dropna().sort_values(ascending=False)
            taken = 0
            for sym in ranked.index:
                if sym in picked: continue
                picked.add(sym)
                rows.append(sym)
                taken += 1
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


def run_full_backtest(score_fn, ctx, top_n, regime_panel=None, bear_exposure=0.0):
    """Run config once across the full panel; return equity DataFrame."""
    entry_thu = thursdays(ctx["calendar"])
    weekly_thu = entry_thu  # DD-check day = Thursday
    s_ts = pd.Timestamp("2009-09-01"); e_ts = pd.Timestamp("2026-05-08")
    entry_dates = entry_thu[(entry_thu >= s_ts) & (entry_thu <= e_ts)]
    weekly_filt = weekly_thu[(weekly_thu >= s_ts) & (weekly_thu <= e_ts)]

    res = run_strategy(
        close_panel=ctx["close_panel"], trade_panel=ctx["trade_panel"],
        calendar=ctx["calendar"], benchmark_aligned=ctx["benchmark_aligned"],
        entry_signal_dates=entry_dates, weekly_signal_dates=weekly_filt,
        signal_function=score_fn, signal_function_args={},
        sma_200_panel=ctx["sma_200"], atr_20_panel=ctx["atr_20"],
        top_n=top_n, exit_buffer=0,
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
        "sortino": round(_sortino(eq, start, end), 2)
                    if _sortino(eq, start, end) is not None else None,
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

    # L6 score
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

    # OM25 score
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

    # Regime panel for overlay (100-DMA, 3-conf)
    regime_overlay = build_regime_panel_confirmed(
        ROOT / "indices_data_historical/NIFTY_100.csv", 100, 3, calendar=calendar,
    )

    combo_l6_om25 = make_combined_score_fn(
        [("L6", l6_score), ("OM25", om25_score)], n_per=12,
    )

    ctx = dict(close_panel=close_panel, trade_panel=trade_panel,
                calendar=calendar, benchmark_aligned=benchmark_aligned,
                sma_200=sma_200, atr_20=atr_20)

    # === Run each config ONCE on full panel ===
    print("\n[run] 4 candidate configs across full panel (2009-09 → 2026-05) ...")
    configs = [
        ("L6 standalone", l6_score, None, 0.0),
        ("L6 + Regime", l6_score, regime_overlay, 0.5),
        ("COMBO 50-50", combo_l6_om25, None, 0.0),
        ("COMBO + Regime", combo_l6_om25, regime_overlay, 0.5),
    ]
    equities = {}
    for label, sfn, reg, bear in configs:
        print(f"  {label} ...")
        eq = run_full_backtest(sfn, ctx, top_n=24,
                                  regime_panel=reg, bear_exposure=bear)
        equities[label] = eq

    # === Slice equity into 13 walk-forward OOS windows ===
    print("\n[slice] 13 OOS windows per config ...")
    rows = []
    for w_id, (is_start, is_end, oos_start, oos_end) in WINDOWS.items():
        for label, _, _, _ in configs:
            eq = equities[label]
            is_m = slice_metrics(eq, is_start, is_end)
            oos_m = slice_metrics(eq, oos_start, oos_end)
            rows.append({
                "window": w_id,
                "config": label,
                "oos_start": oos_start, "oos_end": oos_end,
                "is_sharpe": is_m["sharpe"],
                "is_cagr_pct": is_m["cagr_pct"],
                "is_max_dd_pct": is_m["max_dd_pct"],
                "oos_sharpe": oos_m["sharpe"],
                "oos_cagr_pct": oos_m["cagr_pct"],
                "oos_max_dd_pct": oos_m["max_dd_pct"],
                "oos_calmar": oos_m["calmar"],
                "oos_pass": (oos_m["sharpe"] is not None
                             and oos_m["sharpe"] >= 0.7),
            })

    df = pd.DataFrame(rows)
    out_dir = ROOT / "tasks/MM-tuning"
    df.to_csv(out_dir / "walk_forward.csv", index=False)

    # === Per-config summary ===
    print(f"\n{'=' * 110}")
    print("WALK-FORWARD — pass rate per config (OOS Sharpe ≥ 0.7)")
    print(f"{'=' * 110}")
    summary = (df.groupby("config")
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

    print(f"\n{'=' * 110}")
    print("PER-WINDOW OOS SHARPE (color: PASS Sharpe ≥ 0.7)")
    print(f"{'=' * 110}")
    pivot_sharpe = df.pivot(index="window", columns="config",
                              values="oos_sharpe").reindex(WINDOWS.keys())
    pivot_sharpe = pivot_sharpe[["L6 standalone", "L6 + Regime",
                                   "COMBO 50-50", "COMBO + Regime"]]
    print(pivot_sharpe.round(2).to_string())

    print(f"\n{'=' * 110}")
    print("PER-WINDOW OOS DD (more negative = deeper)")
    print(f"{'=' * 110}")
    pivot_dd = df.pivot(index="window", columns="config",
                          values="oos_max_dd_pct").reindex(WINDOWS.keys())
    pivot_dd = pivot_dd[["L6 standalone", "L6 + Regime",
                          "COMBO 50-50", "COMBO + Regime"]]
    print(pivot_dd.round(2).to_string())

    print(f"\n[wrote] {out_dir / 'walk_forward.csv'}")


if __name__ == "__main__":
    main()
