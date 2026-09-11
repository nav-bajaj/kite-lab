"""Multi-window OOS evaluation utility.

Slices an equity curve into multiple sub-windows and computes per-window
metrics (CAGR, Sharpe, Vol, Max DD). Used by the OOS retune harnesses
(tasks/{om25,trend_leaders}/experiments/_*_oos_retune.py) to evaluate
strategy candidates against pre-committed pass criteria.

Default windows reflect the OOS retune 2026 plan:
  - IS:        2009-09-01 -> 2016-12-31
  - OOS-A:     2017-01-01 -> 2019-12-31  (sideways/quality-value)
  - OOS-B:     2020-01-01 -> 2022-12-31  (COVID + rally + inflation)
  - OOS-C:     2023-01-01 -> 2026-05-08  (smallcap mania + 2025 correction)
  - OOS-full:  2017-01-01 -> 2026-05-08

Pass criteria (per tasks/oos_retune_2026/PLAN.md):
  IS Sharpe >= 1.0
  OOS-full Sharpe >= 1.0
  OOS-A Sharpe >= 0.7
  OOS-B Sharpe >= 0.7
  OOS-C Sharpe >= 0.7
  OOS-full Max DD >= -45%

Equity DataFrames may have either 'portfolio_value' (production scripts)
or 'pv' (_clean_engine.run_strategy) as the value column — both are
handled.

CLI:
    python scripts/multi_window_oos_eval.py <path_to_equity.csv>
"""
from __future__ import annotations

import argparse
import math
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

import pandas as pd


# Default windows for the OOS retune 2026 plan
DEFAULT_WINDOWS: List[Tuple[str, str, str]] = [
    ("IS",       "2009-09-01", "2016-12-31"),
    ("OOS_A",    "2017-01-01", "2019-12-31"),
    ("OOS_B",    "2020-01-01", "2022-12-31"),
    ("OOS_C",    "2023-01-01", "2026-05-08"),
    ("OOS_full", "2017-01-01", "2026-05-08"),
]


@dataclass
class PassCriteria:
    is_sharpe_min: float = 1.0
    oos_full_sharpe_min: float = 1.0
    oos_subwindow_sharpe_min: float = 0.7
    oos_full_max_dd_min: float = -0.45  # i.e., shallower than -45%


def _value_column(eq: pd.DataFrame) -> str:
    """Return whichever value column is present: portfolio_value or pv."""
    for col in ("portfolio_value", "pv"):
        if col in eq.columns:
            return col
    raise ValueError(f"equity CSV must contain 'portfolio_value' or 'pv' "
                     f"column; got {list(eq.columns)}")


def period_metrics(eq: pd.DataFrame, label: str, start, end) -> dict:
    """Slice equity to [start, end] and compute metrics. Empty slice -> NaNs."""
    if eq.empty:
        return {"window": label, "rows": 0}
    valcol = _value_column(eq)
    df = eq.copy()
    df["date"] = pd.to_datetime(df["date"])
    s = pd.Timestamp(start)
    e = pd.Timestamp(end)
    sub = df[(df["date"] >= s) & (df["date"] <= e)]
    if sub.empty:
        return {"window": label, "rows": 0,
                "start": s.date(), "end": e.date(),
                "cagr_pct": float("nan"), "sharpe": float("nan"),
                "vol_pct": float("nan"), "max_dd_pct": float("nan")}

    pv = sub.set_index("date")[valcol].astype(float)
    rets = pv.pct_change().dropna()

    days = (pv.index[-1] - pv.index[0]).days
    yrs = max(days / 365.25, 1e-9)
    if pv.iloc[0] <= 0 or rets.empty:
        return {"window": label, "rows": int(len(pv)),
                "start": pv.index[0].date(), "end": pv.index[-1].date(),
                "yrs": round(yrs, 2),
                "cagr_pct": float("nan"), "sharpe": float("nan"),
                "vol_pct": float("nan"), "max_dd_pct": float("nan")}

    cagr = (pv.iloc[-1] / pv.iloc[0]) ** (1 / yrs) - 1
    vol = rets.std() * math.sqrt(252)
    sharpe = (rets.mean() * 252) / vol if vol > 0 else float("nan")
    cum = pv / pv.cummax()
    max_dd = (cum.min() - 1) * 100

    return {
        "window": label,
        "start": pv.index[0].date(),
        "end": pv.index[-1].date(),
        "yrs": round(yrs, 2),
        "rows": int(len(pv)),
        "start_value": round(float(pv.iloc[0]), 2),
        "end_value": round(float(pv.iloc[-1]), 2),
        "cagr_pct": round(cagr * 100, 2),
        "vol_pct": round(vol * 100, 2),
        "sharpe": round(sharpe, 2),
        "max_dd_pct": round(max_dd, 2),
    }


def evaluate_all_windows(eq: pd.DataFrame,
                         windows: Optional[List[Tuple[str, str, str]]] = None
                         ) -> pd.DataFrame:
    """Apply period_metrics across each window and return a DataFrame."""
    if windows is None:
        windows = DEFAULT_WINDOWS
    rows = [period_metrics(eq, label, s, e) for label, s, e in windows]
    return pd.DataFrame(rows)


def passes_criteria(window_df: pd.DataFrame,
                    criteria: Optional[PassCriteria] = None
                    ) -> Tuple[bool, List[str]]:
    """Check pass/fail vs criteria. Returns (passed, list_of_reasons).

    Each reason in the list is a short string describing a check
    (PASS or FAIL). If `passed` is False, at least one reason starts with FAIL.
    """
    crit = criteria or PassCriteria()
    df = window_df.set_index("window")
    reasons: List[str] = []
    ok = True

    def check(label: str, condition: bool, detail: str):
        nonlocal ok
        prefix = "PASS" if condition else "FAIL"
        reasons.append(f"{prefix}: {label} ({detail})")
        if not condition:
            ok = False

    if "IS" in df.index:
        is_sh = df.loc["IS", "sharpe"]
        check("IS Sharpe >= {:.2f}".format(crit.is_sharpe_min),
              pd.notna(is_sh) and is_sh >= crit.is_sharpe_min,
              f"got {is_sh}")

    if "OOS_full" in df.index:
        ofull_sh = df.loc["OOS_full", "sharpe"]
        check("OOS_full Sharpe >= {:.2f}".format(crit.oos_full_sharpe_min),
              pd.notna(ofull_sh) and ofull_sh >= crit.oos_full_sharpe_min,
              f"got {ofull_sh}")
        ofull_dd = df.loc["OOS_full", "max_dd_pct"]
        check("OOS_full Max DD >= {:.0f}%".format(crit.oos_full_max_dd_min * 100),
              pd.notna(ofull_dd) and ofull_dd >= crit.oos_full_max_dd_min * 100,
              f"got {ofull_dd}%")

    for sw in ("OOS_A", "OOS_B", "OOS_C"):
        if sw not in df.index:
            continue
        sh = df.loc[sw, "sharpe"]
        check("{} Sharpe >= {:.2f}".format(sw, crit.oos_subwindow_sharpe_min),
              pd.notna(sh) and sh >= crit.oos_subwindow_sharpe_min,
              f"got {sh}")

    return ok, reasons


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("equity_csv", type=Path)
    ap.add_argument("--summary-out", type=Path, default=None,
                    help="Optional CSV to save the per-window metrics table")
    args = ap.parse_args()

    if not args.equity_csv.exists():
        print(f"ERROR: {args.equity_csv} not found", file=sys.stderr)
        sys.exit(1)

    eq = pd.read_csv(args.equity_csv, parse_dates=["date"])
    df = evaluate_all_windows(eq)

    print("\n=== Per-window metrics ===")
    print(df.to_string(index=False))

    ok, reasons = passes_criteria(df)
    print("\n=== Pass criteria ===")
    for r in reasons:
        print(f"  {r}")
    print(f"\nOverall: {'PASS' if ok else 'FAIL'}")

    if args.summary_out:
        df.to_csv(args.summary_out, index=False)
        print(f"\n[wrote] {args.summary_out}")


if __name__ == "__main__":
    main()
