import argparse
import random
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd


DEFAULT_LOOKBACK_SETS = [
    ["3"],
    ["6"],
    ["12"],
    ["6", "3"],
    ["12", "6"],
    ["12", "6", "3"],
]

SCENARIOS = {
    "baseline": [],
    "cooldown": ["--scenario", "cooldown", "--cooldown-weeks", "1", "--staged-step", "0.25"],
    "voltrigger": ["--scenario", "vol_trigger", "--vol-lookback", "63", "--target-vol", "0.15"],
}


def run(cmd, dry_run=False):
    print("Command:", " ".join(str(c) for c in cmd))
    if dry_run:
        return 0
    result = subprocess.run(cmd)
    if result.returncode != 0:
        raise SystemExit(result.returncode)
    return result.returncode


def analyze_backtest(run_dir: Path) -> dict:
    equity_path = run_dir / "momentum_equity.csv"
    df = pd.read_csv(equity_path, parse_dates=["date"])
    total_return = df["portfolio_value"].iloc[-1] / df["portfolio_value"].iloc[0] - 1
    benchmark_return = df["benchmark"].iloc[-1] / df["benchmark"].iloc[0] - 1
    drawdown = df["portfolio_value"].div(df["portfolio_value"].cummax()) - 1
    max_dd = drawdown.min()
    return {
        "total_return": total_return,
        "benchmark_return": benchmark_return,
        "max_drawdown": max_dd,
        "start": df["date"].iloc[0].date(),
        "end": df["date"].iloc[-1].date(),
    }


def main():
    parser = argparse.ArgumentParser(description="Monte Carlo parameter search for momentum backtests")
    parser.add_argument("--runs", type=int, default=10)
    parser.add_argument("--topn-min", type=int, default=15)
    parser.add_argument("--topn-max", type=int, default=30)
    parser.add_argument("--lookback-sets", nargs="*", default=None, help="Override lookback sets (comma-separated, e.g., 12,6,3)")
    parser.add_argument("--scenarios", nargs="*", choices=list(SCENARIOS.keys()), default=list(SCENARIOS.keys()))
    parser.add_argument("--universe-file", type=Path)
    parser.add_argument("--output-root", type=Path, default=Path("experiments"))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    random.seed(args.seed)
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    exp_dir = args.output_root / f"monte_{timestamp}"
    signals_dir = exp_dir / "signals"
    runs_dir = exp_dir / "backtests"
    exp_dir.mkdir(parents=True, exist_ok=True)
    signals_dir.mkdir(parents=True, exist_ok=True)
    runs_dir.mkdir(parents=True, exist_ok=True)

    lookback_sets = DEFAULT_LOOKBACK_SETS
    if args.lookback_sets:
        parsed = []
        for item in args.lookback_sets:
            parsed.append(item.split(","))
        lookback_sets = parsed

    summary_rows = []

    for i in range(1, args.runs + 1):
        lookbacks = random.choice(lookback_sets)
        top_n = random.randint(args.topn_min, args.topn_max)
        scenario = random.choice(args.scenarios)
        label = f"run{i:03d}_{'_'.join(lookbacks)}_{scenario}_top{top_n}"

        signal_path = signals_dir / f"{label}.csv"
        cmd = [
            sys.executable,
            "scripts/build_momentum_signals.py",
            "--prices-dir",
            "nse500_data",
            "--output",
            str(signal_path),
            "--skip-days",
            "0",
            "--lookbacks",
            *lookbacks,
            "--top-n",
            str(top_n),
        ]
        if args.universe_file:
            cmd += ["--universe-file", str(args.universe_file)]
        run(cmd, args.dry_run)

        run([
            sys.executable,
            "scripts/validate_signals.py",
            "--signals",
            str(signal_path),
            "--top-n",
            str(top_n),
        ], args.dry_run)

        run_dir = runs_dir / label
        run_dir.mkdir(parents=True, exist_ok=True)
        cmd = [
            sys.executable,
            "scripts/backtest_momentum.py",
            "--prices-dir",
            "nse500_data",
            "--signals",
            str(signal_path),
            "--benchmark",
            "data/benchmarks/nifty100.csv",
            "--output-dir",
            str(run_dir),
            "--initial-capital",
            "1000000",
            "--top-n",
            str(top_n),
            "--slippage",
            "0.002",
        ] + SCENARIOS[scenario]
        if args.universe_file:
            cmd += ["--universe-file", str(args.universe_file)]
        run(cmd, args.dry_run)

        if not args.dry_run:
            metrics = analyze_backtest(run_dir)
            metrics.update(
                {
                    "label": label,
                    "lookbacks": ",".join(lookbacks),
                    "top_n": top_n,
                    "scenario": scenario,
                }
            )
            summary_rows.append(metrics)

    if summary_rows:
        pd.DataFrame(summary_rows).to_csv(exp_dir / "summary.csv", index=False)
        run([
            sys.executable,
            "scripts/report_backtests.py",
            "--runs",
            *(str(runs_dir / row["label"]) for row in summary_rows),
            "--output",
            str(exp_dir / "report.html"),
        ], args.dry_run)

    print(f"Experiment directory: {exp_dir}")


if __name__ == "__main__":
    main()
