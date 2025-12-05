import argparse
from datetime import datetime
from pathlib import Path

import pandas as pd


def main():
    parser = argparse.ArgumentParser(description="Top 25 momentum snapshot (L6, default settings)")
    parser.add_argument("--signals", type=Path, default=Path("data/momentum/top25_signals.csv"))
    parser.add_argument("--top-n", type=int, default=25)
    parser.add_argument("--output-root", type=Path, default=Path("experiments"))
    args = parser.parse_args()

    if not args.signals.exists():
        raise SystemExit(f"Signals file not found: {args.signals}")

    df = pd.read_csv(args.signals, parse_dates=["date"])
    if df.empty:
        raise SystemExit(f"No data in signals file: {args.signals}")

    latest_date = df["date"].max()
    latest = df[df["date"] == latest_date].sort_values("rank")
    latest_top = latest.head(args.top_n)

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    out_dir = args.output_root / f"top25_snapshot_{timestamp}"
    out_dir.mkdir(parents=True, exist_ok=True)

    latest_top.to_csv(out_dir / "top25_snapshot.csv", index=False)
    latest.to_csv(out_dir / "full_snapshot.csv", index=False)

    print(f"Latest rebalance date: {latest_date.date()}")
    print(f"Saved top {args.top_n} snapshot to {out_dir / 'top25_snapshot.csv'}")


if __name__ == "__main__":
    main()
