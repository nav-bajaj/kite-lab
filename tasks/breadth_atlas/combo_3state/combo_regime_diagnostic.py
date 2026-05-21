"""COMBO Defensive regime-behaviour diagnostic.

Compares three configurations of the COMBO portfolio differing only in how
they handle the NIFTY-100 close-vs-100dma 2-state regime:

  A. PROD          — production: bear_skips_entries=True, bear_exposure=0.5.
                     In bear, sells down to 50% pro-rata and refuses new
                     entries — holdings dwindle over extended bears (the
                     '5 positions live' problem).

  B. BEAR_ENTRIES  — fix candidate: bear_skips_entries=False, bear_exposure=0.5.
                     In bear, maintains the 24-stock structure but each
                     position is at half-weight (2.1% instead of 4.2%);
                     ~50% cash held across the 24 names.

  C. ALWAYS_100PCT — no portfolio-level regime overlay (regime_panel=None).
                     OM25's INTERNAL regime tilt (UC/CR weights) still
                     fires inside the OM25 component score. Portfolio stays
                     100% deployed regardless of the NIFTY-100 gate.

For each variant: a single 2009-09 → 2026-05 backtest, then metrics sliced
per window (IS + OOS A/B/C + 2021+). Holdings-count stats computed by
regime state.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts._clean_engine import run_strategy, fridays, biweekly_fridays  # noqa: E402
from scripts._momentum_engine import (  # noqa: E402
    build_momentum_panels, make_momentum_score, lookback_months_to_days,
)
from scripts.om25_v3 import (  # noqa: E402
    LOCKED as OM25_LOCKED, build_regime_panel_confirmed, make_om25_tilt_score,
)
from scripts.combo_defensive import LOCKED as COMBO_LOCKED, make_combo_score_fn  # noqa: E402
from scripts.backtest_momentum import load_price_panels, load_benchmark  # noqa: E402
from scripts.build_om25_signals import load_universe  # noqa: E402


WINDOWS = {
    "IS":     ("2009-09-01", "2016-12-31"),
    "OOS-A":  ("2017-01-01", "2019-12-31"),
    "OOS-B":  ("2020-01-01", "2022-12-31"),
    "OOS-C":  ("2023-01-01", "2026-05-08"),
    "2021+":  ("2021-01-01", "2026-05-08"),
    "FULL":   ("2009-09-01", "2026-05-08"),
}


def build_combo_score(close_panel, calendar, regime_index_path):
    """Construct the standard COMBO composite score (L6 + OM25 with priority dedup).
    OM25's internal regime tilt fires inside this score regardless of the
    portfolio-level regime overlay used downstream.
    """
    nse500 = load_universe(ROOT / COMBO_LOCKED["l6_universe_csv"])
    nse500_cols = [s for s in close_panel.columns if s in nse500]
    l6_panels = build_momentum_panels(
        close_panel[nse500_cols],
        lookback_days=lookback_months_to_days(COMBO_LOCKED["l6_lookback_months"]),
        skip_days=COMBO_LOCKED["l6_skip_days"],
    )
    l6_score = make_momentum_score(
        l6_panels, vol_floor=COMBO_LOCKED["l6_vol_floor"],
        vol_power=COMBO_LOCKED["l6_vol_power"], cross_sectional_zscore=True,
    )

    nifty250 = load_universe(ROOT / COMBO_LOCKED["om25_universe_csv"])
    nifty250_cols = [s for s in close_panel.columns if s in nifty250]
    om25_returns = close_panel[nifty250_cols].pct_change()
    om25_internal_regime = build_regime_panel_confirmed(
        regime_index_path,
        OM25_LOCKED["regime_ma_window"], OM25_LOCKED["regime_confirm_days"],
        calendar=calendar,
    )
    om25_score = make_om25_tilt_score(
        om25_returns, om25_internal_regime,
        bull_w_uc=COMBO_LOCKED["om25_bull_w_uc"], bull_w_cr=COMBO_LOCKED["om25_bull_w_cr"],
        bear_w_uc=COMBO_LOCKED["om25_bear_w_uc"], bear_w_cr=COMBO_LOCKED["om25_bear_w_cr"],
        return_filter=COMBO_LOCKED["om25_return_filter"],
        lookback=COMBO_LOCKED["om25_lookback"], min_obs=COMBO_LOCKED["om25_min_obs"],
    )
    return make_combo_score_fn(
        [("L6", l6_score), ("OM25", om25_score)],
        n_per=COMBO_LOCKED["n_per_strategy"],
    )


def run_variant(*, label, close_panel, trade_panel, calendar, benchmark_aligned,
                sma_200, atr_20, entry_dates, weekly_dates, combo_score,
                portfolio_regime, bear_exposure, bear_skips_entries,
                args, out_dir):
    print(f"[run] {label}  "
          f"regime_panel={'YES' if portfolio_regime is not None else 'None'}  "
          f"bear_exposure={bear_exposure}  "
          f"bear_skips_entries={bear_skips_entries}")
    res = run_strategy(
        close_panel=close_panel, trade_panel=trade_panel,
        calendar=calendar, benchmark_aligned=benchmark_aligned,
        entry_signal_dates=entry_dates, weekly_signal_dates=weekly_dates,
        signal_function=combo_score, signal_function_args={},
        sma_200_panel=sma_200, atr_20_panel=atr_20,
        top_n=COMBO_LOCKED["top_n"], exit_buffer=COMBO_LOCKED["exit_buffer"],
        max_weight=COMBO_LOCKED["max_weight"], slippage=COMBO_LOCKED["slippage"],
        atr_mult=0.0, atr_min_floor=0.0,
        use_trailing_stop=False, use_dma_exit=False, weekly_rank_check=False,
        regime_panel=portfolio_regime,
        bear_exposure=bear_exposure,
        bear_skips_entries=bear_skips_entries,
        min_hold_days=COMBO_LOCKED["min_hold_days"],
        initial_capital=args.initial_capital,
    )
    if res is None:
        return None
    eq = res["equity"].copy()
    eq["date"] = pd.to_datetime(eq["date"])
    eq.to_csv(out_dir / f"{label}_equity.csv", index=False)
    res["trades"].to_csv(out_dir / f"{label}_trades.csv", index=False)
    res["exits"].to_csv(out_dir / f"{label}_exits.csv", index=False)
    return res


def window_metrics(pv: pd.Series, start: pd.Timestamp, end: pd.Timestamp) -> dict:
    pv = pv.loc[(pv.index >= start) & (pv.index <= end)]
    if len(pv) < 2:
        return {}
    rets = pv.pct_change().dropna()
    years = max((pv.index[-1] - pv.index[0]).days / 365.25, 1e-9)
    cagr = (pv.iloc[-1] / pv.iloc[0]) ** (1 / years) - 1
    vol = rets.std() * math.sqrt(252)
    sharpe = (cagr - 0.05) / vol if vol > 0 else 0.0
    dd = (pv / pv.cummax() - 1).min()
    calmar = cagr / abs(dd) if dd < 0 else np.nan
    return {
        "cagr_pct": round(cagr * 100, 2),
        "sharpe": round(sharpe, 3),
        "vol_pct": round(vol * 100, 2),
        "max_dd_pct": round(dd * 100, 2),
        "calmar": round(float(calmar), 3) if not pd.isna(calmar) else None,
        "years": round(years, 2),
    }


def holdings_stats(eq: pd.DataFrame, regime: pd.Series,
                   start: pd.Timestamp, end: pd.Timestamp) -> dict:
    sub = eq.loc[(eq["date"] >= start) & (eq["date"] <= end)]
    if len(sub) == 0:
        return {}
    reg_aligned = regime.reindex(sub["date"]).ffill()
    bull_mask = reg_aligned.values == True  # noqa: E712
    bear_mask = ~bull_mask
    bull_h = sub.loc[bull_mask, "holdings"]
    bear_h = sub.loc[bear_mask, "holdings"]
    cash_pct = sub["cash_pct"] if "cash_pct" in sub.columns else None
    return {
        "n_days": len(sub),
        "n_bull_days": int(bull_mask.sum()),
        "n_bear_days": int(bear_mask.sum()),
        "bull_holdings_mean": round(float(bull_h.mean()), 1) if len(bull_h) else None,
        "bull_holdings_min": int(bull_h.min()) if len(bull_h) else None,
        "bear_holdings_mean": round(float(bear_h.mean()), 1) if len(bear_h) else None,
        "bear_holdings_min": int(bear_h.min()) if len(bear_h) else None,
        "overall_holdings_mean": round(float(sub["holdings"].mean()), 1),
        "overall_holdings_min": int(sub["holdings"].min()),
        "end_holdings": int(sub["holdings"].iloc[-1]),
        "end_cash_pct": round(float(cash_pct.iloc[-1]) * 100, 2) if cash_pct is not None else None,
    }


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument("--prices-dir", type=Path, default=ROOT / "nse500_data_merged")
    ap.add_argument("--benchmark", type=Path, default=ROOT / "data/benchmarks/nifty100.csv")
    ap.add_argument("--regime-index", type=Path, default=ROOT / COMBO_LOCKED["regime_index_path"])
    ap.add_argument("--initial-capital", type=float, default=1_000_000)
    ap.add_argument("--output-dir", type=Path, default=None)
    return ap.parse_args()


def main():
    args = parse_args()
    ts = pd.Timestamp.now().strftime("%Y%m%d_%H%M%S")
    out_dir = args.output_dir or ROOT / "tasks/breadth_atlas/combo_3state/runs" / f"combo_diag_{ts}"
    out_dir.mkdir(parents=True, exist_ok=True)

    print("[load] price panels")
    close_panel, trade_panel = load_price_panels(args.prices_dir)
    calendar = close_panel.index
    benchmark = load_benchmark(args.benchmark).reindex(calendar).ffill()
    sma_200 = close_panel.rolling(200, min_periods=200).mean()
    atr_20 = close_panel.pct_change().rolling(20).std()

    combo_score = build_combo_score(close_panel, calendar, args.regime_index)

    portfolio_regime = build_regime_panel_confirmed(
        args.regime_index,
        COMBO_LOCKED["regime_ma_window"], COMBO_LOCKED["regime_confirm_days"],
        calendar=calendar,
    )

    full_start = pd.Timestamp(WINDOWS["FULL"][0])
    full_end = pd.Timestamp(WINDOWS["FULL"][1])
    entry_dates = biweekly_fridays(calendar)
    entry_dates = entry_dates[(entry_dates >= full_start) & (entry_dates <= full_end)]
    weekly = fridays(calendar)
    weekly_dates = weekly[(weekly >= full_start) & (weekly <= full_end)]

    variants = [
        # (label, regime_panel, bear_exposure, bear_skips_entries)
        ("A_PROD",         portfolio_regime, 0.5, True),
        ("B_BEAR_ENTRIES", portfolio_regime, 0.5, False),
        ("C_ALWAYS_100",   None,             0.0, False),
    ]

    eqs = {}
    for label, reg, be, bse in variants:
        res = run_variant(
            label=label, close_panel=close_panel, trade_panel=trade_panel,
            calendar=calendar, benchmark_aligned=benchmark,
            sma_200=sma_200, atr_20=atr_20,
            entry_dates=entry_dates, weekly_dates=weekly_dates,
            combo_score=combo_score,
            portfolio_regime=reg, bear_exposure=be, bear_skips_entries=bse,
            args=args, out_dir=out_dir,
        )
        if res is None:
            print(f"  [{label}] empty result")
            continue
        eq = res["equity"].copy()
        eq["date"] = pd.to_datetime(eq["date"])
        eqs[label] = eq

    # ===== Per-window metrics =====
    print("\n=== Per-window metrics ===\n")
    rows = []
    for label, eq in eqs.items():
        pv = eq.set_index("date")["pv"].astype(float)
        for window_name, (start_s, end_s) in WINDOWS.items():
            s, e = pd.Timestamp(start_s), pd.Timestamp(end_s)
            m = window_metrics(pv, s, e)
            if not m:
                continue
            rows.append({"variant": label, "window": window_name, **m})
    metrics_df = pd.DataFrame(rows)
    metrics_df.to_csv(out_dir / "metrics_by_window.csv", index=False)

    show_cols = ["variant", "window", "cagr_pct", "sharpe", "max_dd_pct", "calmar", "years"]
    for window_name in WINDOWS:
        sub = metrics_df[metrics_df["window"] == window_name]
        if sub.empty:
            continue
        print(f"--- {window_name} ---")
        print(sub[show_cols].to_string(index=False))
        print()

    # ===== Holdings stats per variant per window =====
    print("\n=== Holdings stats by variant × window ===\n")
    h_rows = []
    for label, eq in eqs.items():
        for window_name, (start_s, end_s) in WINDOWS.items():
            s, e = pd.Timestamp(start_s), pd.Timestamp(end_s)
            stats = holdings_stats(eq, portfolio_regime, s, e)
            if not stats:
                continue
            h_rows.append({"variant": label, "window": window_name, **stats})
    h_df = pd.DataFrame(h_rows)
    h_df.to_csv(out_dir / "holdings_by_window.csv", index=False)

    show_h = ["variant", "window", "n_bull_days", "n_bear_days",
              "bull_holdings_mean", "bear_holdings_mean", "bear_holdings_min",
              "end_holdings", "end_cash_pct"]
    for window_name in WINDOWS:
        sub = h_df[h_df["window"] == window_name]
        if sub.empty:
            continue
        print(f"--- {window_name} ---")
        print(sub[show_h].to_string(index=False))
        print()

    # ===== Config dump =====
    (out_dir / "config.json").write_text(json.dumps({
        "variants": [{
            "label": "A_PROD",
            "description": "production current: bear_skips_entries=True, bear_exposure=0.5",
        }, {
            "label": "B_BEAR_ENTRIES",
            "description": "fix candidate: bear_skips_entries=False, bear_exposure=0.5 (maintain 24-stock structure during bear)",
        }, {
            "label": "C_ALWAYS_100",
            "description": "no portfolio-level regime overlay; OM25 internal regime tilt still active inside score",
        }],
        "windows": WINDOWS,
        "combo_locked": {k: v for k, v in COMBO_LOCKED.items()},
    }, indent=2, default=str))
    print(f"[wrote] {out_dir.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
