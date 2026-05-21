"""Detailed comparison: NSE500 3-state(avg_dist) winner vs production OM25 v3 baseline.

For each calendar year and each window:
  - Annual return, max drawdown, Sharpe
  - Regime-state distribution (bull/bear/deep days for the 3-state)
  - Aggregate OOS metrics

Reads the equity CSVs written by om25_three_state_experiment.py.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tasks.breadth_atlas.experiments.om25_three_state_experiment import (  # noqa: E402
    METRIC_THRESHOLDS, WINDOWS, build_three_state_regime, load_breadth_panel,
)


RUN_DIR = ROOT / "tasks/breadth_atlas/experiments/runs_3state/20260521_144908"
WINNER_METRIC = "avg_dist_from_200dma"

# Override via CLI: --winner-universe NSE500|Nifty250
import argparse
_ap = argparse.ArgumentParser()
_ap.add_argument("--winner-universe", default="NSE500", choices=["NSE500", "Nifty250"])
_ap.add_argument("--winner-metric", default=WINNER_METRIC)
_args, _ = _ap.parse_known_args()
WINNER_UNIVERSE = _args.winner_universe
WINNER_METRIC = _args.winner_metric


def load_equity(path: Path) -> pd.Series:
    df = pd.read_csv(path, parse_dates=["date"]).set_index("date")
    return df["pv"].astype(float)


def window_metrics(pv: pd.Series, start: pd.Timestamp, end: pd.Timestamp) -> dict:
    pv = pv.loc[(pv.index >= start) & (pv.index <= end)]
    if len(pv) < 2:
        return {"start": str(start.date()), "end": str(end.date()), "n_days": 0}
    rets = pv.pct_change().dropna()
    years = max((pv.index[-1] - pv.index[0]).days / 365.25, 1e-9)
    cagr = (pv.iloc[-1] / pv.iloc[0]) ** (1 / years) - 1
    vol = rets.std() * math.sqrt(252)
    sharpe = (cagr - 0.05) / vol if vol > 0 else 0.0
    dd = (pv / pv.cummax() - 1).min()
    calmar = cagr / abs(dd) if dd < 0 else np.nan
    return {
        "start": str(pv.index[0].date()),
        "end": str(pv.index[-1].date()),
        "n_days": len(pv),
        "start_pv": float(pv.iloc[0]),
        "end_pv": float(pv.iloc[-1]),
        "cagr_pct": round(cagr * 100, 2),
        "sharpe": round(sharpe, 3),
        "vol_pct": round(vol * 100, 2),
        "max_dd_pct": round(dd * 100, 2),
        "calmar": round(float(calmar), 3) if not pd.isna(calmar) else None,
    }


def annual_metrics(pv: pd.Series) -> pd.DataFrame:
    rows = []
    for year, segment in pv.groupby(pv.index.year):
        if len(segment) < 2:
            continue
        rets = segment.pct_change().dropna()
        annual_ret = (segment.iloc[-1] / segment.iloc[0] - 1) * 100
        vol = rets.std() * math.sqrt(252) * 100
        sharpe = ((annual_ret - 5) / vol) if vol > 0 else 0.0
        intra_dd = (segment / segment.cummax() - 1).min() * 100
        rows.append({
            "year": year,
            "n_days": len(segment),
            "annual_ret_pct": round(annual_ret, 2),
            "vol_pct": round(vol, 2),
            "sharpe": round(sharpe, 3),
            "intra_year_dd_pct": round(intra_dd, 2),
        })
    return pd.DataFrame(rows)


def regime_yearly_breakdown(regime: pd.Series, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    reg = regime.loc[(regime.index >= start) & (regime.index <= end)]
    rows = []
    for year, segment in reg.groupby(reg.index.year):
        if len(segment) == 0:
            continue
        rows.append({
            "year": year,
            "days_bull": int((segment == "bull").sum()),
            "days_bear": int((segment == "bear").sum()),
            "days_deep": int((segment == "deep").sum()),
            "deep_visits": int(((segment == "deep") & (segment.shift(1) != "deep")).sum()),
        })
    return pd.DataFrame(rows)


def stitch_equity(window_files: dict[str, Path]) -> pd.Series:
    """Concatenate per-window equity curves into one continuous PV series,
    rebasing each subsequent window to start at the prior window's end value."""
    pieces = []
    base = None
    for win in ["IS", "OOS-A", "OOS-B", "OOS-C"]:
        if win not in window_files:
            continue
        pv = load_equity(window_files[win])
        start, end = pd.Timestamp(WINDOWS[win][0]), pd.Timestamp(WINDOWS[win][1])
        pv = pv.loc[(pv.index >= start) & (pv.index <= end)]
        if base is not None:
            scale = base / pv.iloc[0]
            pv = pv * scale
        pieces.append(pv)
        base = pv.iloc[-1]
    return pd.concat(pieces)


def main():
    # Winner
    winner_files = {
        win: RUN_DIR / f"{WINNER_UNIVERSE}_{win}_3state_{WINNER_METRIC}_equity.csv"
        for win in ["IS", "OOS-A", "OOS-B", "OOS-C"]
    }
    # Baseline (production OM25 v3 — Nifty 250 + NIFTY-100 close-vs-100dma 2-state)
    baseline_files = {
        win: RUN_DIR / f"Nifty250_{win}_baseline_2state_equity.csv"
        for win in ["IS", "OOS-A", "OOS-B", "OOS-C"]
    }

    print("=" * 100)
    print(f"WINNER:   {WINNER_UNIVERSE} + 3-state breadth ({WINNER_METRIC})")
    print("          Bull(UC/CR 50/50) / Bear(CR-only) / Deep(UC-only) ; 100% exposure ; 20% peak stop always on")
    print("BASELINE: Nifty 250 + OM25 v3 production (NIFTY-100 close-vs-100dma 2-state)")
    print("          Bull(UC/CR 50/50) / Bear(CR-only) ; 100% exposure ; 20% peak stop")
    print("=" * 100)

    # Build the regime panel for the winner (need it for state-day breakdowns)
    breadth = load_breadth_panel(ROOT / "data/breadth/breadth_daily.csv")
    bear_in, bear_out, deep_in, deep_out, higher = METRIC_THRESHOLDS[WINNER_METRIC]
    regime = build_three_state_regime(
        breadth[WINNER_METRIC],
        bear_entry=bear_in, bear_exit=bear_out,
        deep_entry=deep_in, deep_exit=deep_out,
        higher_is_bull=higher, confirm_days=3,
        calendar=breadth.index,
    )

    print("\n--- Per-window metrics ---\n")
    rows = []
    for win in ["IS", "OOS-A", "OOS-B", "OOS-C"]:
        ws, we = pd.Timestamp(WINDOWS[win][0]), pd.Timestamp(WINDOWS[win][1])
        w_pv = load_equity(winner_files[win])
        b_pv = load_equity(baseline_files[win])
        w_m = window_metrics(w_pv, ws, we)
        b_m = window_metrics(b_pv, ws, we)
        rows.append({"window": win, "variant": "winner", **w_m})
        rows.append({"window": win, "variant": "baseline", **b_m})
    df_win = pd.DataFrame(rows)
    print(df_win.to_string(index=False))

    # Stitched continuous equity for end-to-end comparison
    print("\n\n--- Stitched continuous equity (rebased at each window join) ---\n")
    w_stitched = stitch_equity(winner_files)
    b_stitched = stitch_equity(baseline_files)

    for label, pv in [("winner", w_stitched), ("baseline", b_stitched)]:
        # Full-period and OOS-only
        full = window_metrics(pv, pv.index.min(), pv.index.max())
        oos_start = pd.Timestamp("2017-01-01")
        oos_end = pd.Timestamp("2026-05-08")
        oos = window_metrics(pv, oos_start, oos_end)
        print(f"  {label:8s}  FULL  CAGR={full['cagr_pct']}%  Sharpe={full['sharpe']}  MaxDD={full['max_dd_pct']}%  Calmar={full['calmar']}  end={full['end_pv']:.0f}")
        print(f"  {label:8s}  OOS   CAGR={oos['cagr_pct']}%  Sharpe={oos['sharpe']}  MaxDD={oos['max_dd_pct']}%  Calmar={oos['calmar']}")

    # Per-year breakdown
    print("\n\n--- Year-by-year ---\n")
    w_ann = annual_metrics(w_stitched).rename(columns={
        "annual_ret_pct": "win_ret%", "vol_pct": "win_vol%",
        "sharpe": "win_sharpe", "intra_year_dd_pct": "win_dd%"
    })
    b_ann = annual_metrics(b_stitched).rename(columns={
        "annual_ret_pct": "base_ret%", "vol_pct": "base_vol%",
        "sharpe": "base_sharpe", "intra_year_dd_pct": "base_dd%"
    })[["year", "base_ret%", "base_sharpe", "base_dd%"]]
    reg_ann = regime_yearly_breakdown(regime, pd.Timestamp("2009-09-01"), pd.Timestamp("2026-05-08"))

    annual = w_ann.merge(b_ann, on="year", how="outer").merge(reg_ann, on="year", how="left")
    annual = annual.sort_values("year").reset_index(drop=True)
    annual["spread"] = (annual["win_ret%"] - annual["base_ret%"]).round(2)

    # Mark window each year belongs to
    def win_for_year(y):
        if y <= 2016: return "IS"
        if y <= 2019: return "OOS-A"
        if y <= 2022: return "OOS-B"
        return "OOS-C"
    annual["window"] = annual["year"].map(win_for_year)

    cols = ["window", "year", "win_ret%", "base_ret%", "spread",
            "win_sharpe", "base_sharpe", "win_dd%", "base_dd%",
            "days_bull", "days_bear", "days_deep", "deep_visits"]
    print(annual[cols].to_string(index=False))

    # Aggregate by window
    print("\n\n--- OOS-aggregate, equal-weighted by window ---\n")
    oos_windows = ["OOS-A", "OOS-B", "OOS-C"]
    w_sharpes = [df_win.loc[(df_win["window"]==w) & (df_win["variant"]=="winner"), "sharpe"].iloc[0] for w in oos_windows]
    b_sharpes = [df_win.loc[(df_win["window"]==w) & (df_win["variant"]=="baseline"), "sharpe"].iloc[0] for w in oos_windows]
    w_cagrs = [df_win.loc[(df_win["window"]==w) & (df_win["variant"]=="winner"), "cagr_pct"].iloc[0] for w in oos_windows]
    b_cagrs = [df_win.loc[(df_win["window"]==w) & (df_win["variant"]=="baseline"), "cagr_pct"].iloc[0] for w in oos_windows]
    w_dds = [df_win.loc[(df_win["window"]==w) & (df_win["variant"]=="winner"), "max_dd_pct"].iloc[0] for w in oos_windows]
    b_dds = [df_win.loc[(df_win["window"]==w) & (df_win["variant"]=="baseline"), "max_dd_pct"].iloc[0] for w in oos_windows]
    print(f"  Winner   avg OOS Sharpe={np.mean(w_sharpes):.3f}  CAGR={np.mean(w_cagrs):.2f}%  MaxDD={np.mean(w_dds):.2f}%")
    print(f"  Baseline avg OOS Sharpe={np.mean(b_sharpes):.3f}  CAGR={np.mean(b_cagrs):.2f}%  MaxDD={np.mean(b_dds):.2f}%")

    # Output to CSV
    out_csv = RUN_DIR / f"{WINNER_UNIVERSE}_{WINNER_METRIC}_vs_baseline_analysis.csv"
    annual.to_csv(out_csv, index=False)
    print(f"\n[wrote] {out_csv.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
