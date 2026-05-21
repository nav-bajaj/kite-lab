"""T2 — Calendar-year breakdown of A_PROD vs D_BREADTH (post-fix).

Slices the full equity curves into calendar years and reports per-year
CAGR, Sharpe, MaxDD for each variant. Identifies the years where D
materially over- or under-performs.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

RUN_DIR = ROOT / "tasks/breadth_atlas/combo_3state/runs/combo_breadth_20260521_205838"


def load_equity(p: Path) -> pd.Series:
    df = pd.read_csv(p, parse_dates=["date"]).set_index("date")
    return df["pv"].astype(float)


def year_metrics(pv: pd.Series) -> pd.DataFrame:
    rows = []
    for year, seg in pv.groupby(pv.index.year):
        if len(seg) < 60:
            continue
        rets = seg.pct_change().dropna()
        ann_ret = (seg.iloc[-1] / seg.iloc[0] - 1) * 100
        vol = rets.std() * math.sqrt(252) * 100
        sharpe = ((ann_ret - 5) / vol) if vol > 0 else 0.0
        dd = (seg / seg.cummax() - 1).min() * 100
        rows.append({"year": year, "n_days": len(seg),
                     "annual_ret_pct": round(ann_ret, 2),
                     "vol_pct": round(vol, 2),
                     "sharpe": round(sharpe, 3),
                     "intra_year_dd_pct": round(dd, 2)})
    return pd.DataFrame(rows).set_index("year")


def main():
    print(f"[load] equity from {RUN_DIR.relative_to(ROOT)}")
    a = load_equity(RUN_DIR / "A_PROD_equity.csv")
    d = load_equity(RUN_DIR / "D_BREADTH_equity.csv")

    a_year = year_metrics(a)
    d_year = year_metrics(d)

    merged = a_year.join(d_year, lsuffix="_a", rsuffix="_d")
    merged["ret_spread"] = (merged["annual_ret_pct_d"] - merged["annual_ret_pct_a"]).round(2)
    merged["sharpe_spread"] = (merged["sharpe_d"] - merged["sharpe_a"]).round(3)
    merged["dd_spread"] = (merged["intra_year_dd_pct_d"] - merged["intra_year_dd_pct_a"]).round(2)

    show = ["annual_ret_pct_a", "annual_ret_pct_d", "ret_spread",
            "sharpe_a", "sharpe_d", "sharpe_spread",
            "intra_year_dd_pct_a", "intra_year_dd_pct_d", "dd_spread"]

    print("=== Calendar-year metrics: A_PROD vs D_BREADTH ===\n")
    print(merged[show].to_string())
    print()

    # Summary
    n = len(merged)
    d_ret_wins = (merged["ret_spread"] > 0).sum()
    d_sharpe_wins = (merged["sharpe_spread"] > 0).sum()
    d_dd_wins = (merged["dd_spread"] > 0).sum()
    print(f"=== Year-count win rates (n={n} years) ===")
    print(f"  D return    > A : {d_ret_wins}/{n} ({d_ret_wins/n*100:.0f}%)")
    print(f"  D Sharpe    > A : {d_sharpe_wins}/{n} ({d_sharpe_wins/n*100:.0f}%)")
    print(f"  D MaxDD     > A : {d_dd_wins}/{n} ({d_dd_wins/n*100:.0f}%)")
    print()

    # Best / worst for D
    print(f"=== Best 3 years for D (Sharpe spread) ===")
    print(merged.nlargest(3, "sharpe_spread")[show].to_string())
    print()
    print(f"=== Worst 3 years for D (Sharpe spread) ===")
    print(merged.nsmallest(3, "sharpe_spread")[show].to_string())

    merged[show].to_csv(RUN_DIR / "yearly_a_vs_d.csv")


if __name__ == "__main__":
    main()
