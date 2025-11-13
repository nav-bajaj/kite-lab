import argparse
from pathlib import Path

import pandas as pd


def main():
    parser = argparse.ArgumentParser(description="Sample a subset of the NSE 500 universe")
    parser.add_argument("--source", type=Path, default=Path("data/static/nse500_universe.csv"))
    parser.add_argument("--size", type=int, default=250)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    df = pd.read_csv(args.source)
    if "Symbol" not in df.columns:
        raise SystemExit("Source file must contain a Symbol column")
    sampled = df.sample(n=args.size, random_state=args.seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    sampled.to_csv(args.output, index=False)
    print(f"Saved {len(sampled)} symbols to {args.output}")


if __name__ == "__main__":
    main()
