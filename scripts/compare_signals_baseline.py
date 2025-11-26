import argparse
from pathlib import Path

import pandas as pd


def load_signals(path: Path, top_n: int) -> pd.DataFrame:
    df = pd.read_csv(path, parse_dates=["date"])
    df = df[df["rank"] <= top_n]
    return df[["date", "symbol", "rank"]]


def compare(baseline: pd.DataFrame, candidate: pd.DataFrame, top_n: int):
    dates = sorted(set(baseline["date"]) & set(candidate["date"]))
    if not dates:
        raise SystemExit("No overlapping dates between baseline and candidate signals")

    rows = []
    for dt in dates:
        base_slice = baseline[baseline["date"] == dt]
        cand_slice = candidate[candidate["date"] == dt]
        base_set = set(base_slice["symbol"])
        cand_set = set(cand_slice["symbol"])
        overlap = base_set & cand_set
        overlap_ratio = len(overlap) / top_n if top_n else 0

        rank_diff = []
        base_rank_map = dict(zip(base_slice["symbol"], base_slice["rank"]))
        cand_rank_map = dict(zip(cand_slice["symbol"], cand_slice["rank"]))
        for sym in overlap:
            rank_diff.append(abs(base_rank_map.get(sym, top_n + 1) - cand_rank_map.get(sym, top_n + 1)))
        avg_rank_diff = sum(rank_diff) / len(rank_diff) if rank_diff else None

        rows.append(
            {
                "date": dt,
                "overlap": len(overlap),
                "overlap_ratio": overlap_ratio,
                "base_only": len(base_set - cand_set),
                "cand_only": len(cand_set - base_set),
                "avg_rank_diff": avg_rank_diff,
            }
        )
    return pd.DataFrame(rows)


def main():
    parser = argparse.ArgumentParser(description="Compare a candidate L6 signal file against a frozen baseline snapshot")
    parser.add_argument("--baseline", type=Path, default=Path("data/momentum/signals_L6_noskip.csv"))
    parser.add_argument("--candidate", type=Path, default=Path("data/momentum/top25_signals.csv"))
    parser.add_argument("--top-n", type=int, default=25)
    parser.add_argument("--output", type=Path, help="Optional CSV to write detailed comparison results")
    args = parser.parse_args()

    baseline = load_signals(args.baseline, args.top_n)
    candidate = load_signals(args.candidate, args.top_n)
    report = compare(baseline, candidate, args.top_n)

    summary = {
        "dates_compared": len(report),
        "avg_overlap": report["overlap_ratio"].mean(),
        "median_overlap": report["overlap_ratio"].median(),
        "avg_rank_diff": report["avg_rank_diff"].mean(),
    }
    print("Summary vs baseline:")
    for k, v in summary.items():
        print(f"- {k}: {v}")

    drift_dates = report[report["overlap_ratio"] < 0.8]
    if not drift_dates.empty:
        print("\nDates with <80% overlap:")
        print(drift_dates[["date", "overlap_ratio", "base_only", "cand_only"]].to_string(index=False))

    if args.output:
        report.to_csv(args.output, index=False)
        print(f"\nDetailed report written to {args.output}")


if __name__ == "__main__":
    main()
