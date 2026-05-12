"""Walk-forward Phase 4a — re-rank existing IS sweep results by alternative metrics.

Loads `is_sweep.csv` from every (strategy, universe, window) and computes
which config would have been picked under each candidate metric:

  - Sharpe (current default)
  - Calmar (CAGR / |MaxDD|)
  - Multi-criteria filter: Sharpe ≥ floor1 AND Calmar ≥ floor2 AND trades ≥ floor3,
    then rank by Sharpe among survivors
  - Composite: 0.5 × normalized(Sharpe) + 0.5 × normalized(Calmar)

For each metric and each window, identifies whether the new top-1 happens to
be one of {challenger, baseline, worst} for which we already have OOS metrics.
Reports overlap and computes available OOS comparisons.

Output: tasks/walk_forward/results/alt_metrics/
  - per_window_alt_picks.csv (one row per (strategy, universe, window, metric))
  - overlap_summary.csv (how often alt-metric picks overlap with existing OOS data)
  - alt_vs_sharpe.csv (when overlap allows, OOS Sharpe of alt-metric pick vs current)
  - missing_configs.csv (configs we'd need to re-run for full comparison)
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


# Locked v3 baseline IDs (matching scripts/run_walk_forward.py)
TL25_BASELINE_ID = "P0.40_D0.20_M0.40_S20"
OM25_BASELINE_ID = "UC0.5_CR0.5_B"


def _baseline_id(strategy: str) -> str:
    return TL25_BASELINE_ID if strategy == "tl25_v3" else OM25_BASELINE_ID


def calmar(row) -> float:
    """Calmar from is_sweep row. CAGR / |MaxDD|."""
    if row.get("is_max_dd_pct") is None or pd.isna(row["is_max_dd_pct"]):
        return float("nan")
    if abs(row["is_max_dd_pct"]) < 1e-6:
        return float("nan")
    return row["is_cagr_pct"] / abs(row["is_max_dd_pct"])


def normalize(series: pd.Series) -> pd.Series:
    """Min-max normalize a series within a window."""
    lo, hi = series.min(), series.max()
    if hi - lo < 1e-9:
        return pd.Series([0.5] * len(series), index=series.index)
    return (series - lo) / (hi - lo)


def rank_by_metric(df: pd.DataFrame, metric: str,
                    sharpe_floor: float = 0.0,
                    calmar_floor: float = 0.0,
                    trades_floor: int = 40) -> str | None:
    """Return the config_id of the top-1 pick under the given metric, or None."""
    elig = df[
        (df["ok"] == True)  # noqa: E712
        & (df["is_max_dd_pct"] > -45)
        & (df["n_trades"] >= trades_floor)
    ].copy()
    if elig.empty:
        return None
    elig["calmar"] = elig.apply(calmar, axis=1)

    if metric == "sharpe":
        elig = elig.sort_values(["is_sharpe", "n_trades"], ascending=[False, True])
    elif metric == "calmar":
        elig = elig.sort_values(["calmar", "is_sharpe"], ascending=[False, False])
    elif metric == "multi":
        # Filter on a moderate quality bar then pick by Sharpe
        elig = elig[(elig["is_sharpe"] >= sharpe_floor) & (elig["calmar"] >= calmar_floor)]
        if elig.empty:
            return None
        elig = elig.sort_values(["is_sharpe", "calmar"], ascending=[False, False])
    elif metric == "composite":
        elig["norm_sharpe"] = normalize(elig["is_sharpe"])
        elig["norm_calmar"] = normalize(elig["calmar"])
        elig["composite"] = 0.5 * elig["norm_sharpe"] + 0.5 * elig["norm_calmar"]
        elig = elig.sort_values(["composite", "is_sharpe"], ascending=[False, False])
    else:
        raise ValueError(f"unknown metric {metric!r}")

    return elig.iloc[0]["config_id"]


def collect_alt_picks(input_dir: Path) -> pd.DataFrame:
    """For each window's is_sweep.csv, compute IS-top-1 under each metric."""
    rows = []
    for strat_uni_dir in sorted(input_dir.glob("*_*/")):
        # strat_uni_dir like 'tl25_v3_nse500' or 'om25_v3_nifty250'
        parts = strat_uni_dir.name.rsplit("_", 1)
        if len(parts) != 2:
            continue
        strategy, universe = parts
        if strategy not in ("tl25_v3", "om25_v3"):
            continue
        for window_dir in sorted(strat_uni_dir.glob("W*/")):
            window_id = window_dir.name
            is_path = window_dir / "is_sweep.csv"
            if not is_path.exists():
                continue
            df = pd.read_csv(is_path)
            picks = {
                "strategy": strategy, "universe": universe, "window_id": window_id,
                "sharpe_pick":    rank_by_metric(df, "sharpe"),
                "calmar_pick":    rank_by_metric(df, "calmar"),
                "multi_pick":     rank_by_metric(df, "multi",
                                                  sharpe_floor=1.0, calmar_floor=1.0),
                "composite_pick": rank_by_metric(df, "composite"),
                "baseline_id": _baseline_id(strategy),
            }
            rows.append(picks)
    return pd.DataFrame(rows)


def annotate_with_oos(picks: pd.DataFrame, cross_summary: pd.DataFrame) -> pd.DataFrame:
    """For each (strategy, universe, window), look up OOS Sharpe for each pick
    if it matches challenger/baseline/worst we already have OOS data for.
    """
    cross = cross_summary.copy()
    cross["window_num"] = cross["window_id"].str.replace("W", "").astype(int)

    annotated = picks.copy()
    annotated["window_num"] = annotated["window_id"].str.replace("W", "").astype(int)

    out_rows = []
    for _, r in annotated.iterrows():
        key = (r["strategy"], r["universe"], r["window_id"])
        crow = cross[
            (cross["strategy"] == r["strategy"])
            & (cross["universe"] == r["universe"])
            & (cross["window_id"] == r["window_id"])
        ]
        if crow.empty:
            continue
        crow = crow.iloc[0]
        chal_id = crow["challenger_id"]
        worst_id = crow["worst_id"]
        base_id = _baseline_id(r["strategy"])

        chal_oos = crow["challenger_oos_sharpe"]
        worst_oos = crow["worst_oos_sharpe"]
        base_oos = crow["baseline_oos_sharpe"]

        def lookup_oos(pick: str) -> tuple[float | None, str]:
            if pick is None:
                return (None, "no_pick")
            if pick == chal_id:
                return (chal_oos, "challenger")
            if pick == base_id:
                return (base_oos, "baseline")
            if pick == worst_id:
                return (worst_oos, "worst")
            return (None, "missing")

        sharpe_oos, sharpe_match = lookup_oos(r["sharpe_pick"])
        calmar_oos, calmar_match = lookup_oos(r["calmar_pick"])
        multi_oos, multi_match = lookup_oos(r["multi_pick"])
        comp_oos, comp_match = lookup_oos(r["composite_pick"])

        out_rows.append({
            "strategy": r["strategy"], "universe": r["universe"],
            "window_id": r["window_id"],
            "sharpe_pick": r["sharpe_pick"],     "sharpe_oos": sharpe_oos,   "sharpe_match": sharpe_match,
            "calmar_pick": r["calmar_pick"],     "calmar_oos": calmar_oos,   "calmar_match": calmar_match,
            "multi_pick":  r["multi_pick"],      "multi_oos":  multi_oos,    "multi_match":  multi_match,
            "composite_pick": r["composite_pick"], "composite_oos": comp_oos, "composite_match": comp_match,
            "baseline_oos": base_oos,
        })
    return pd.DataFrame(out_rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path,
                    default=ROOT / "tasks/walk_forward/results/phase2")
    ap.add_argument("--output", type=Path,
                    default=ROOT / "tasks/walk_forward/results/alt_metrics")
    args = ap.parse_args()

    args.output.mkdir(parents=True, exist_ok=True)

    print(f"[load] cross_summary from {args.input}")
    cross = pd.read_csv(args.input / "cross_summary.csv")
    print(f"  {len(cross)} window-rows")

    print(f"[scan] is_sweep.csv files in {args.input}")
    picks = collect_alt_picks(args.input)
    print(f"  {len(picks)} window-picks computed")

    picks.to_csv(args.output / "per_window_alt_picks.csv", index=False)

    print("[annotate] cross-reference picks with existing OOS data")
    annotated = annotate_with_oos(picks, cross)
    annotated.to_csv(args.output / "alt_vs_sharpe.csv", index=False)

    # Overlap diagnostics — for each metric, how often is its pick something
    # we already have OOS data for (i.e., one of challenger/baseline/worst)?
    metrics = ["sharpe", "calmar", "multi", "composite"]
    overlap_rows = []
    for m in metrics:
        match_col = f"{m}_match"
        counts = annotated[match_col].value_counts().to_dict()
        n_available = sum(v for k, v in counts.items()
                          if k in ("challenger", "baseline", "worst"))
        n_missing = counts.get("missing", 0)
        n_total = len(annotated)
        overlap_rows.append({
            "metric": m,
            "n_total": n_total,
            "matches_challenger": counts.get("challenger", 0),
            "matches_baseline": counts.get("baseline", 0),
            "matches_worst": counts.get("worst", 0),
            "available_oos": n_available,
            "missing_oos": n_missing,
            "overlap_pct": round(n_available / n_total * 100, 1) if n_total else 0,
        })
    overlap_df = pd.DataFrame(overlap_rows)
    overlap_df.to_csv(args.output / "overlap_summary.csv", index=False)

    # Missing-configs list (per strategy, distinct configs we'd need to re-run)
    missing_rows = []
    for m in metrics:
        match_col = f"{m}_match"
        pick_col = f"{m}_pick"
        missing = annotated[annotated[match_col] == "missing"]
        for _, r in missing.iterrows():
            missing_rows.append({
                "strategy": r["strategy"], "universe": r["universe"],
                "window_id": r["window_id"], "metric": m, "config_id": r[pick_col],
            })
    missing_df = pd.DataFrame(missing_rows)
    missing_df.to_csv(args.output / "missing_configs.csv", index=False)

    # Compute aggregate OOS Sharpe per metric, ONLY where we have data
    agg_rows = []
    for m in metrics:
        col_oos = f"{m}_oos"
        sub = annotated[annotated[col_oos].notna()]
        agg_rows.append({
            "metric": m,
            "n_windows": len(sub),
            "mean_oos_sharpe": round(sub[col_oos].mean(), 3),
            "median_oos_sharpe": round(sub[col_oos].median(), 3),
            "pass_count": int((sub[col_oos] >= 0.7).sum()),
            "pass_rate_pct": round((sub[col_oos] >= 0.7).mean() * 100, 1),
        })
    agg_df = pd.DataFrame(agg_rows)

    # Per-strategy breakout too
    by_strat_rows = []
    for strat in ["tl25_v3", "om25_v3"]:
        ann_s = annotated[annotated["strategy"] == strat]
        for m in metrics:
            col_oos = f"{m}_oos"
            sub = ann_s[ann_s[col_oos].notna()]
            by_strat_rows.append({
                "strategy": strat,
                "metric": m,
                "n_with_oos": len(sub),
                "mean_oos_sharpe": round(sub[col_oos].mean(), 3) if len(sub) else None,
                "vs_baseline_mean": round((sub[col_oos] - sub["baseline_oos"]).mean(), 3)
                    if len(sub) else None,
                "pass_count": int((sub[col_oos] >= 0.7).sum()),
                "pass_rate_pct": round((sub[col_oos] >= 0.7).mean() * 100, 1) if len(sub) else None,
            })
    by_strat_df = pd.DataFrame(by_strat_rows)

    # === Print summary ===
    print(f"\n{'=' * 90}")
    print("Overlap with existing OOS data (chal/base/worst) per metric")
    print(f"{'=' * 90}")
    print(overlap_df.to_string(index=False))

    print(f"\n{'=' * 90}")
    print("Aggregate OOS Sharpe per IS selection metric (where data is available)")
    print(f"{'=' * 90}")
    print(agg_df.to_string(index=False))

    print(f"\n{'=' * 90}")
    print("Per-strategy breakdown")
    print(f"{'=' * 90}")
    print(by_strat_df.to_string(index=False))

    print(f"\n[wrote] {args.output}/per_window_alt_picks.csv")
    print(f"[wrote] {args.output}/overlap_summary.csv")
    print(f"[wrote] {args.output}/alt_vs_sharpe.csv")
    print(f"[wrote] {args.output}/missing_configs.csv")


if __name__ == "__main__":
    main()
