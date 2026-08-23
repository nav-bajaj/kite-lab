"""Apply demerger / vendor-splice factors (demerger_factors.json) to both
price dirs, and trim VEDL's corrupt first weeks of Kite 2005 data.

Factors multiply OHLC (and divide volume) for all rows strictly before
ex_date. Idempotent: skips a factor whose step is already gone (adjacent
ratio at ex_date within 12% of 1). Dry-run by default; --apply writes.

Run:  .venv/bin/python tasks/corporate_actions_fix/apply_factors.py [--apply]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
DIRS = [ROOT / "nse500_data", ROOT / "nse500_data_merged"]
PRICE_COLS = ["open", "high", "low", "close"]
VEDL_TRIM_BEFORE = "2005-02-01"


def step_ratio(df: pd.DataFrame, ex_date: str) -> float | None:
    """Close-to-close step across ex_date (reporting)."""
    pre = df[df.date < ex_date]
    post = df[df.date >= ex_date]
    if pre.empty or post.empty:
        return None
    return float(post.iloc[0].close / pre.iloc[-1].close)


def step_ratio_open(df: pd.DataFrame, ex_date: str) -> float | None:
    """Prev-close to ex-day-open step (the continuity the factor targets;
    immune to large real intraday moves on the ex-day itself)."""
    pre = df[df.date < ex_date]
    post = df[df.date >= ex_date]
    if pre.empty or post.empty:
        return None
    return float(post.iloc[0].open / pre.iloc[-1].close)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    factors = json.loads((HERE / "demerger_factors.json").read_text())
    for f in factors:
        sym, ex, fac = f["symbol"], f["ex_date"], f["factor"]
        for d in DIRS:
            p = d / f"{sym}_day.csv"
            if not p.exists():
                continue
            df = pd.read_csv(p, parse_dates=["date"]).sort_values("date")
            df["date"] = df["date"].dt.strftime("%Y-%m-%d")
            r = step_ratio(df, ex)
            ro = step_ratio_open(df, ex)
            if r is None:
                print(f"  {sym:10s} {d.name:20s} no rows straddle {ex} — skip")
                continue
            matches = (abs(r / fac - 1) <= 0.12
                       or (ro is not None and abs(ro / fac - 1) <= 0.12))
            if not matches:
                verdict = ("already adjusted" if abs(r - 1) < 0.12
                           else f"step close {r:.4f} / open {ro:.4f} != factor {fac} — REFUSING")
                print(f"  {sym:10s} {d.name:20s} {verdict}")
                continue
            mask = df.date < ex
            if args.apply:
                for col in PRICE_COLS:
                    df.loc[mask, col] = df.loc[mask, col] * fac
                if "volume" in df.columns:
                    df.loc[mask, "volume"] = (df.loc[mask, "volume"] / fac).round().astype("int64")
                df.to_csv(p, index=False)
            post_r = None if not args.apply else step_ratio(
                pd.read_csv(p, parse_dates=["date"]).assign(
                    date=lambda x: x.date.dt.strftime("%Y-%m-%d")), ex)
            print(f"  {sym:10s} {d.name:20s} step {r:.4f} -> factor {fac} applied "
                  f"to {int(mask.sum())} rows"
                  + (f"; residual step {post_r:.4f}" if post_r else "")
                  + ("" if args.apply else " [dry-run]"))

    # VEDL 2005 boundary junk
    for d in DIRS:
        p = d / "VEDL_day.csv"
        if not p.exists():
            continue
        df = pd.read_csv(p, parse_dates=["date"]).sort_values("date")
        n_trim = int((df.date < VEDL_TRIM_BEFORE).sum())
        if n_trim and args.apply:
            df = df[df.date >= VEDL_TRIM_BEFORE]
            df["date"] = df["date"].dt.strftime("%Y-%m-%d")
            df.to_csv(p, index=False)
        print(f"  VEDL       {d.name:20s} trim {n_trim} rows before "
              f"{VEDL_TRIM_BEFORE}" + ("" if args.apply else " [dry-run]"))


if __name__ == "__main__":
    main()
