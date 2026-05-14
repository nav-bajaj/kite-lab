"""Comprehensive regime design sweep — exploit the ALT 1 insight.

The COMBO Defensive's protective value comes from the CASH allocation, not
from stock selection during bear (per the bear_entries comparison). This
means the layered/aggressive variants we tested before were partly
handicapped by the skip-entries rule. Re-test them with ALT 1 (allow
entries at bear-scaled size).

(b) Layered regime with ALT 1 behavior:
    - Layered 100-DMA→75%, 200-DMA→50% (binary's smoother sibling)
    - Layered 100-DMA→50%, 200-DMA→25% (more aggressive)
    - Layered 100-DMA→75%, 200-DMA→25% (mild start, deep deepening)

(c) Even more aggressive cash on binary 100-DMA:
    - 50%, 40%, 35%, 30%, 25% bear exposure

Base config: Friday biweekly L6→OM25 COMBO (locked Defensive candidate).

Reports OOS_full + Prod window + walk-forward pass rate + holdings count.
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
from scripts.combo_defensive import LOCKED, make_combo_score_fn
from scripts.momentum_layered_regime import build_layered_regime
from scripts.backtest_momentum import load_price_panels, load_benchmark
from scripts.build_om25_signals import load_universe
from scripts.multi_window_oos_eval import period_metrics


AGG_WINDOWS = [
    ("OOS_full",    "2017-01-01", "2026-05-08"),
    ("Prod window", "2020-07-10", "2026-05-08"),
    ("OOS_B (COVID)", "2020-01-01", "2022-12-31"),
    ("OOS_C (recent)", "2023-01-01", "2026-05-08"),
]

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


def run_combo(score_fn, ctx, regime_panel, bear_exposure, bear_skips_entries):
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
        top_n=LOCKED["top_n"], exit_buffer=LOCKED["exit_buffer"],
        max_weight=LOCKED["max_weight"], slippage=LOCKED["slippage"],
        atr_mult=0.0, atr_min_floor=0.0,
        use_trailing_stop=False, use_dma_exit=False,
        weekly_rank_check=False,
        regime_panel=regime_panel, bear_exposure=bear_exposure,
        bear_skips_entries=bear_skips_entries,
        min_hold_days=LOCKED["min_hold_days"], initial_capital=1_000_000,
    )
    return res["equity"]


def main():
    print("[load] panels ...")
    close_panel, trade_panel = load_price_panels(ROOT / "nse500_data_merged")
    calendar = close_panel.index
    benchmark = load_benchmark(ROOT / "data/benchmarks/nifty100.csv")
    benchmark_aligned = benchmark.reindex(calendar).ffill()
    sma_200 = close_panel.rolling(200, min_periods=200).mean()
    atr_20 = close_panel.pct_change().rolling(20).std()

    nse500_uni = load_universe(ROOT / LOCKED["l6_universe_csv"])
    nse500_cols = [s for s in close_panel.columns if s in nse500_uni]
    l6_panels = build_momentum_panels(
        close_panel[nse500_cols],
        lookback_days=lookback_months_to_days(LOCKED["l6_lookback_months"]),
        skip_days=LOCKED["l6_skip_days"],
    )
    l6_score = make_momentum_score(
        l6_panels, vol_floor=LOCKED["l6_vol_floor"],
        vol_power=LOCKED["l6_vol_power"], cross_sectional_zscore=True,
    )
    nifty250_uni = load_universe(ROOT / LOCKED["om25_universe_csv"])
    nifty250_cols = [s for s in close_panel.columns if s in nifty250_uni]
    om25_returns = close_panel[nifty250_cols].pct_change()
    om25_regime_for_score = build_regime_panel_confirmed(
        ROOT / LOCKED["regime_index_path"],
        OM25_LOCKED["regime_ma_window"], OM25_LOCKED["regime_confirm_days"],
        calendar=calendar,
    )
    om25_score = make_om25_tilt_score(
        om25_returns, om25_regime_for_score,
        bull_w_uc=LOCKED["om25_bull_w_uc"], bull_w_cr=LOCKED["om25_bull_w_cr"],
        bear_w_uc=LOCKED["om25_bear_w_uc"], bear_w_cr=LOCKED["om25_bear_w_cr"],
        return_filter=LOCKED["om25_return_filter"],
        lookback=LOCKED["om25_lookback"], min_obs=LOCKED["om25_min_obs"],
    )

    # Regime panels
    print("[build] regime panels ...")
    binary_100 = build_regime_panel_confirmed(
        ROOT / LOCKED["regime_index_path"], 100, 3, calendar=calendar,
    )
    layered_75_50 = build_layered_regime(
        ROOT / LOCKED["regime_index_path"], calendar,
        confirm_days=3, ma_short=100, ma_long=200,
        mild_bear_target=0.75, deep_bear_target=0.50,
    )
    layered_50_25 = build_layered_regime(
        ROOT / LOCKED["regime_index_path"], calendar,
        confirm_days=3, ma_short=100, ma_long=200,
        mild_bear_target=0.50, deep_bear_target=0.25,
    )
    layered_75_25 = build_layered_regime(
        ROOT / LOCKED["regime_index_path"], calendar,
        confirm_days=3, ma_short=100, ma_long=200,
        mild_bear_target=0.75, deep_bear_target=0.25,
    )

    ctx = dict(close_panel=close_panel, trade_panel=trade_panel,
                calendar=calendar, benchmark_aligned=benchmark_aligned,
                sma_200=sma_200, atr_20=atr_20)
    combo = make_combo_score_fn(
        [("L6", l6_score), ("OM25", om25_score)],
        n_per=LOCKED["n_per_strategy"],
    )

    # === Configs ===
    configs = [
        # (label, regime, bear_exp, skip_entries)
        # Reference: production candidate as currently locked
        ("REFERENCE: Binary 100/50% + skip_entries=True (locked)", binary_100, 0.5, True),
        ("REFERENCE: Binary 100/50% + ALT 1", binary_100, 0.5, False),
        # (c) Binary aggressive cash levels — all with ALT 1
        ("Binary 100/40% + ALT 1", binary_100, 0.40, False),
        ("Binary 100/35% + ALT 1", binary_100, 0.35, False),
        ("Binary 100/30% + ALT 1", binary_100, 0.30, False),
        ("Binary 100/25% + ALT 1", binary_100, 0.25, False),
        # (b) Layered regime variants — all with ALT 1
        ("Layered 100→75%, 200→50% + ALT 1", layered_75_50, 0.0, False),
        ("Layered 100→50%, 200→25% + ALT 1", layered_50_25, 0.0, False),
        ("Layered 100→75%, 200→25% + ALT 1 (mild→deep)", layered_75_25, 0.0, False),
    ]

    equities = {}
    for label, reg, be, skip in configs:
        print(f"[run] {label} ...", flush=True)
        equities[label] = run_combo(combo, ctx, reg, be, skip)

    # === Aggregate metrics ===
    print(f"\n{'=' * 130}")
    print("AGGREGATE METRICS")
    print(f"{'=' * 130}")
    agg_rows = []
    for label, _, _, _ in configs:
        eq = equities[label]
        for w_id, s, e in AGG_WINDOWS:
            m = slice_metrics(eq, s, e)
            agg_rows.append({"config": label, "window": w_id, **m})
    agg = pd.DataFrame(agg_rows)
    for w in ["OOS_full", "Prod window", "OOS_B (COVID)", "OOS_C (recent)"]:
        sub = agg[agg["window"] == w]
        if sub.empty: continue
        print(f"\n--- {w} ---")
        cols = ["config", "cagr_pct", "sharpe", "sortino", "calmar", "max_dd_pct"]
        print(sub[cols].to_string(index=False))

    # === Walk-forward pass rates + holdings count ===
    print(f"\n{'=' * 130}")
    print("WALK-FORWARD (13 windows, OOS Sharpe ≥ 0.7) + Avg holdings (Prod window)")
    print(f"{'=' * 130}")
    wf_rows = []
    holdings_rows = []
    for label, _, _, _ in configs:
        eq = equities[label]
        for w_id, (is_s, is_e, oos_s, oos_e) in WF_WINDOWS.items():
            oos_m = slice_metrics(eq, oos_s, oos_e)
            wf_rows.append({
                "window": w_id, "config": label,
                "oos_sharpe": oos_m["sharpe"],
                "oos_cagr_pct": oos_m["cagr_pct"],
                "oos_max_dd_pct": oos_m["max_dd_pct"],
                "oos_pass": (oos_m["sharpe"] is not None and oos_m["sharpe"] >= 0.7),
            })
        # Holdings count over prod window
        ec = eq.copy(); ec["date"] = pd.to_datetime(ec["date"])
        s = pd.Timestamp("2020-07-10"); e = pd.Timestamp("2026-05-08")
        sub_eq = ec[(ec["date"] >= s) & (ec["date"] <= e)]
        if not sub_eq.empty and "holdings" in sub_eq.columns:
            holdings_rows.append({
                "config": label,
                "avg_holdings": round(sub_eq["holdings"].mean(), 1),
                "min_holdings": int(sub_eq["holdings"].min()),
            })

    wf_df = pd.DataFrame(wf_rows)
    summary = (wf_df.groupby("config")
                  .agg(n_pass=("oos_pass", "sum"),
                       mean_oos_sharpe=("oos_sharpe", "mean"),
                       median_oos_sharpe=("oos_sharpe", "median"),
                       min_oos_sharpe=("oos_sharpe", "min"),
                       mean_oos_cagr=("oos_cagr_pct", "mean"),
                       worst_oos_dd=("oos_max_dd_pct", "min"))
                  .round(2))
    summary["pass_rate_pct"] = (summary["n_pass"] / 13 * 100).round(0)
    holdings_df = pd.DataFrame(holdings_rows).set_index("config")
    summary = summary.join(holdings_df)
    print(summary.to_string())

    out = ROOT / "tasks/MM-tuning/combo_regime_design_sweep.csv"
    agg.to_csv(out, index=False)
    wf_df.to_csv(ROOT / "tasks/MM-tuning/combo_regime_design_sweep_wf.csv", index=False)
    print(f"\n[wrote] {out}")


if __name__ == "__main__":
    main()
