"""OM25 regime filter test — does an index 200-DMA on/off filter help OOS DD?

Post-hoc approximation: take an existing OM25 equity curve, apply a
regime mask derived from index Close vs 200-DMA. On bear days (index
below 200-DMA on the prior trading day), replace strategy daily return
with 0 (cash). Compute regime-filtered equity and re-evaluate per-window.

This isn't a perfect simulation — it doesn't capture re-entry friction
or the stocks the strategy would have rotated into during bear regime.
But it bounds the upside of "what if the strategy went to cash on bear
regime days?" If the answer is "doesn't help much," skip the in-engine
version. If it materially reduces DD, then we go properly.

Usage:
    python tasks/om25/experiments/_om25_regime_filter_test.py
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from scripts.multi_window_oos_eval import (
    evaluate_all_windows, passes_criteria,
)


# Existing equity curves to test (from oos_universes_oos run)
RUN_DIR = ROOT / "experiments/oos_retune/20260509175217_om25_universes_oos"
EQUITIES = [
    ("Nifty_250_monthly", RUN_DIR / "Nifty_250_monthly_equity.csv"),
    ("Nifty_250_biweekly", RUN_DIR / "Nifty_250_biweekly_equity.csv"),
    ("NSE_500_monthly", RUN_DIR / "NSE_500_monthly_equity.csv"),
    ("NSE_500_biweekly", RUN_DIR / "NSE_500_biweekly_equity.csv"),
]

INDEX_FILES = {
    "NIFTY_50":  ROOT / "indices_data_historical/NIFTY_50.csv",
    "NIFTY_100": ROOT / "indices_data_historical/NIFTY_100.csv",
    "NIFTY_500": ROOT / "indices_data_historical/NIFTY_500.csv",
}


def load_index_with_regime(path: Path, ma_window: int = 200) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["date"])
    df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None).dt.normalize()
    df = df.sort_values("date").reset_index(drop=True)
    df["ma"] = df["close"].rolling(ma_window, min_periods=ma_window).mean()
    df["bull"] = df["close"] > df["ma"]
    return df[["date", "close", "ma", "bull"]]


def apply_regime_filter(eq: pd.DataFrame, regime: pd.DataFrame,
                        max_exposure_bear: float = 0.0) -> pd.DataFrame:
    """Apply post-hoc regime filter to an equity curve.

    On each day t, if the regime at t-1 was bear, today's return is
    blended toward 0 (cash) by `(1 - max_exposure_bear)`. So
    max_exposure_bear=0 means full cash on bear days; 0.5 means half
    exposure during bear; 1.0 means no filter (passes through).
    """
    e = eq.copy()
    e["date"] = pd.to_datetime(e["date"]).dt.tz_localize(None).dt.normalize()
    valcol = "pv" if "pv" in e.columns else "portfolio_value"
    e = e.sort_values("date").reset_index(drop=True)
    e["raw_ret"] = e[valcol].pct_change()

    # Lag regime by 1 day (yesterday's close determines today's exposure)
    r = regime[["date", "bull"]].copy()
    r["bull_lagged"] = r["bull"].shift(1)
    e = e.merge(r[["date", "bull_lagged"]], on="date", how="left")
    # If we don't have regime data for a date (early in panel), assume bull
    e["bull_lagged"] = e["bull_lagged"].fillna(True)

    # Effective return: bull → strategy return; bear → max_exposure_bear * strategy_return
    e["eff_ret"] = e.apply(
        lambda row: row["raw_ret"] * (1.0 if row["bull_lagged"] else max_exposure_bear),
        axis=1,
    )
    e["eff_ret"] = e["eff_ret"].fillna(0)

    # Build new equity curve from initial PV
    init_pv = e[valcol].iloc[0]
    e["filtered_pv"] = init_pv * (1 + e["eff_ret"]).cumprod()
    # Set first row to init_pv (cumprod gives 1 at first row but we have an initial offset)
    e.loc[0, "filtered_pv"] = init_pv

    out = e[["date", "filtered_pv"]].rename(columns={"filtered_pv": "pv"})
    return out


def main():
    rows = []
    for eq_label, eq_path in EQUITIES:
        eq = pd.read_csv(eq_path, parse_dates=["date"])
        # Baseline metrics
        win_eval = evaluate_all_windows(eq)
        ok, _ = passes_criteria(win_eval)
        for _, w in win_eval.iterrows():
            rows.append({
                "config": eq_label, "regime": "NONE", "exposure_bear": "—",
                "window": w["window"],
                "cagr_pct": w["cagr_pct"], "sharpe": w["sharpe"],
                "max_dd_pct": w["max_dd_pct"],
                "passes": ok if w["window"] == "OOS_full" else None,
            })

        for idx_name, idx_path in INDEX_FILES.items():
            regime = load_index_with_regime(idx_path)
            for exp_bear in (0.0, 0.25, 0.5):
                filt = apply_regime_filter(eq, regime, max_exposure_bear=exp_bear)
                fwin = evaluate_all_windows(filt)
                fok, _ = passes_criteria(fwin)
                for _, w in fwin.iterrows():
                    rows.append({
                        "config": eq_label, "regime": idx_name,
                        "exposure_bear": exp_bear,
                        "window": w["window"],
                        "cagr_pct": w["cagr_pct"], "sharpe": w["sharpe"],
                        "max_dd_pct": w["max_dd_pct"],
                        "passes": fok if w["window"] == "OOS_full" else None,
                    })

    df = pd.DataFrame(rows)

    # Compact OOS_full view
    oos = df[df["window"] == "OOS_full"][
        ["config", "regime", "exposure_bear", "cagr_pct", "sharpe", "max_dd_pct", "passes"]
    ]
    print("\n=== OOS_full results across regime filters ===")
    print(oos.to_string(index=False))

    # Save full results
    out = ROOT / f"experiments/oos_retune/regime_filter_{pd.Timestamp.now().strftime('%Y%m%d%H%M%S')}.csv"
    df.to_csv(out, index=False)
    print(f"\n[wrote] {out}")


if __name__ == "__main__":
    main()
