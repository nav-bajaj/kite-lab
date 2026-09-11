"""Has any already-published rebalance been rewritten by a later run?

Every portfolio run writes a full recomputed history to
data/<portfolio>_portfolios/<name>_portfolio_<ts>/. If the engine is
deterministic and its inputs never change, the trades a run produces for a
past date must match what an earlier run produced for that same date. Where
they differ, a decision that was already published has been silently
restated.

Compares by hashing each trade DATE's block independently. Row-positional
comparison is not safe here: the backtest start date has been shortened at
least once, which shifts every row and reports the whole history as changed.
A key-merge is not safe either - a symbol can trade twice on one date and the
join duplicates - which produced a false "drift reaches back 2203 days".
Per-date hashing is immune to both.
"""
from __future__ import annotations

import argparse, glob, hashlib, os
import pandas as pd

from data_pipeline.master_store import ROOT as REPO  # noqa: E402
PORTFOLIOS = {
    "om25_v3": ("om25_v3_portfolios", "om25_trades.csv"),
    "tl25_v3": ("tl25_v3_portfolios", "tl25_trades.csv"),
    "l6_v2": ("l6_v2_portfolios", "l6_trades.csv"),
    "combo_defensive": ("combo_defensive_portfolios", "combo_trades.csv"),
}
# The run date from which each strategy's recomputed history stops changing.
# Established by bisecting every stored run against the latest one; see
# RESULTS.md. Before these dates the engine itself still changed, so their
# history is backtest under an earlier strategy version, not a live record.
LOCKED_FROM = {
    "om25_v3": "20260606",
    "tl25_v3": "20260606",
    "l6_v2": "20260514",
    "combo_defensive": "20260514",
}


def run_dirs(dirname: str) -> list[str]:
    p = os.path.join(REPO, "data", dirname)
    return sorted(d for d in glob.glob(f"{p}/*_portfolio_*") if os.path.isdir(d))


def run_date(path: str) -> str:
    return os.path.basename(path).split("_")[-2]


def per_date_hash(df: pd.DataFrame) -> dict:
    df = df.sort_values(list(df.columns))
    return {k: hashlib.md5(g.to_csv(index=False).encode()).hexdigest()
            for k, g in df.groupby(df["date"].dt.date)}


def audit(name: str, dirname: str, trades_file: str) -> list[tuple]:
    runs = [d for d in run_dirs(dirname) if run_date(d) >= LOCKED_FROM[name]]
    if len(runs) < 2:
        return []
    latest = pd.read_csv(os.path.join(runs[-1], trades_file))
    latest["date"] = pd.to_datetime(latest["date"])
    ref = per_date_hash(latest)

    findings = []
    for d in runs[:-1]:
        df = pd.read_csv(os.path.join(d, trades_file))
        df["date"] = pd.to_datetime(df["date"])
        cut = pd.Timestamp(run_date(d)).date()
        for day, h in per_date_hash(df).items():
            # only dates the run had already decided count as published
            if day < cut and (day not in ref or ref[day] != h):
                findings.append((name, os.path.basename(d), day, (cut - day).days))
    return findings


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--strict", action="store_true",
                    help="exit non-zero if any published rebalance was restated")
    a = ap.parse_args()

    all_findings = []
    for name, (dirname, tf) in PORTFOLIOS.items():
        f = audit(name, dirname, tf)
        all_findings += f
        runs = [d for d in run_dirs(dirname) if run_date(d) >= LOCKED_FROM[name]]
        print(f"{name:18s} locked from {LOCKED_FROM[name]}  runs audited {len(runs):2d}  "
              f"restated trade-dates: {len(f)}")
        for _, run, day, lag in f:
            print(f"      run {run[-15:]} restated {day} ({lag} days earlier)")

    if all_findings:
        lags = [x[3] for x in all_findings]
        print(f"\n{len(all_findings)} restatements, reaching back {min(lags)}-{max(lags)} days.")
        print("All within the 15-day refetch window means nothing older than the "
              "window has ever moved; a restatement beyond it is a different bug.")
    else:
        print("\nNo published rebalance has been restated.")
    return 1 if (a.strict and all_findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
