import argparse
from pathlib import Path

import pandas as pd


def main():
    parser = argparse.ArgumentParser(description="Validate momentum rankings file")
    parser.add_argument("--signals", type=Path, default=Path("data/momentum/top25_signals.csv"))
    parser.add_argument("--top-n", type=int, default=25)
    args = parser.parse_args()

    if not args.signals.exists():
        raise SystemError(f"Signals file {args.signals} not found")

    df = pd.read_csv(args.signals, parse_dates=["date"])
    errors = []
    warnings = []

    grouped = df.groupby("date")
    for date, group in grouped:
        if len(group) > args.top_n:
            errors.append(f"{date.date()}: has {len(group)} entries > top_n")
        if group["symbol"].duplicated().any():
            errors.append(f"{date.date()}: duplicate symbols detected")
        missing_scores = group[["score_12m", "score_6m", "score_3m"]].isna().sum().sum()
        if missing_scores:
            warnings.append(f"{date.date()}: {missing_scores} score cells missing")

    if errors:
        print("Errors:")
        for err in errors:
            print(" -", err)
    else:
        print("No critical errors detected.")

    if warnings:
        print("Warnings:")
        for warn in warnings:
            print(" -", warn)

    if errors:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
