"""T3 — Differentiation of D_BREADTH and A_PROD from existing production
portfolios (L6, OM25, TL25).

Loads equity curves from prior runs and computes per-window daily-return
correlations. If D_BREADTH is too similar to L6 or OM25, the marketing
story weakens. If A_PROD is already distinct from all, swapping to D is
less urgent.

Note: TL25 equity isn't available from the prior runs in this session;
we'll skip it unless we add a separate quick backtest later.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))


COMBO_RUN = ROOT / "tasks/breadth_atlas/combo_3state/runs/combo_breadth_20260521_205838"
OM25_RUN = ROOT / "tasks/om25_alt/runs/om25d_20260521_185025"   # has L6 + OM25 baselines on the same 4 windows

WINDOWS = {
    "IS":    ("2009-09-01", "2016-12-31"),
    "OOS-A": ("2017-01-01", "2019-12-31"),
    "OOS-B": ("2020-01-01", "2022-12-31"),
    "OOS-C": ("2023-01-01", "2026-05-08"),
    "2021+": ("2021-01-01", "2026-05-08"),
}


def load_equity(p: Path) -> pd.Series:
    df = pd.read_csv(p, parse_dates=["date"]).set_index("date")
    return df["pv"].astype(float)


def daily_corr(a: pd.Series, b: pd.Series, start: str, end: str) -> tuple[float, int]:
    s, e = pd.Timestamp(start), pd.Timestamp(end)
    ra = a.loc[(a.index >= s) & (a.index <= e)].pct_change().dropna()
    rb = b.loc[(b.index >= s) & (b.index <= e)].pct_change().dropna()
    common = ra.index.intersection(rb.index)
    if len(common) < 30:
        return float("nan"), 0
    return float(ra.loc[common].corr(rb.loc[common])), len(common)


def main():
    print("[load] equity curves")
    # COMBO variants (post-fix)
    a_prod = load_equity(COMBO_RUN / "A_PROD_equity.csv")
    d_breadth = load_equity(COMBO_RUN / "D_BREADTH_equity.csv")

    # L6, OM25 baselines from prior om25_alt run (full-span equity)
    # These were per-window backtests; stitch OOS-B + OOS-C for 2021+ comparison
    refs = {}
    for win in ["IS", "OOS-A", "OOS-B", "OOS-C"]:
        for label in ["L6_NSE500", "OM25_Nifty250", "OM25_NSE500"]:
            p = OM25_RUN / f"{win}_{label}_equity.csv"
            if p.exists():
                refs.setdefault(label, {})[win] = load_equity(p)

    # For correlations we need per-window equity to align with comparison
    print("\n=== Daily-return correlations vs L6 / OM25 (per window) ===\n")
    rows = []
    for win, (sd, ed) in WINDOWS.items():
        for label, win_dict in refs.items():
            # for 2021+: stitch OOS-B + OOS-C
            if win == "2021+":
                if "OOS-B" not in win_dict or "OOS-C" not in win_dict:
                    continue
                ref = pd.concat([win_dict["OOS-B"], win_dict["OOS-C"]])
                ref = ref.loc[~ref.index.duplicated(keep="last")].sort_index()
            else:
                if win not in win_dict:
                    continue
                ref = win_dict[win]
            for var_label, var_eq in [("A_PROD", a_prod), ("D_BREADTH", d_breadth)]:
                rho, n = daily_corr(var_eq, ref, sd, ed)
                rows.append({"window": win, "variant": var_label, "vs": label,
                             "n_days": n, "daily_corr": round(rho, 3) if not np.isnan(rho) else None})

    df = pd.DataFrame(rows)
    df.to_csv(COMBO_RUN / "differentiation_corr.csv", index=False)

    pivot = df.pivot_table(index=["window", "variant"], columns="vs", values="daily_corr")
    print(pivot.to_string())
    print()

    # Cross-COMBO: A vs D
    print("=== A_PROD vs D_BREADTH (each other) — daily correlations ===")
    for win, (sd, ed) in WINDOWS.items():
        rho, n = daily_corr(a_prod, d_breadth, sd, ed)
        print(f"  {win:8s}  n={n:4d}  corr={rho:.3f}")
    print()


if __name__ == "__main__":
    main()
