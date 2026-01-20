#!/usr/bin/env python3
"""
Score threshold grid search for momentum portfolio

Tests all combinations of entry and exit score thresholds to find
the optimal hysteresis configuration.
"""

import argparse
import subprocess
import sys
from pathlib import Path
from datetime import datetime
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def run_command(cmd, description):
    """Run a command and handle errors"""
    print(f"\n{'=' * 80}")
    print(f"{description}")
    print(f"{'=' * 80}")
    print(f"Command: {' '.join(map(str, cmd))}\n")

    result = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"ERROR: {description} failed with exit code {result.returncode}")
        print(f"STDERR: {result.stderr}")
        sys.exit(result.returncode)
    return result


def extract_metrics(backtest_dir):
    """Extract key metrics from a backtest run"""
    metrics_file = backtest_dir / "momentum_metrics.csv"
    if not metrics_file.exists():
        return None

    df = pd.read_csv(metrics_file)
    if df.empty:
        return None

    return {
        "cagr": df["cagr"].iloc[0],
        "total_return": df["total_return"].iloc[0],
        "max_drawdown": df["max_drawdown"].iloc[0],
        "max_dd_duration": df["max_drawdown_duration_days"].iloc[0],
        "avg_turnover": df["avg_turnover_pct"].iloc[0],
        "total_trades": df["trades_total"].iloc[0],
        "hit_rate": df["hit_rate_overall"].iloc[0],
        "avg_holding_days": df["avg_holding_days"].iloc[0],
    }


def main():
    parser = argparse.ArgumentParser(description="Grid search for score entry/exit thresholds")
    parser.add_argument("--entry-thresholds", nargs="+", type=float, default=[2.0, 2.5, 3.0],
                        help="Entry score thresholds to test (default: 2.0 2.5 3.0)")
    parser.add_argument("--exit-thresholds", nargs="+", type=float, default=[1.0, 1.5, 2.0],
                        help="Exit score thresholds to test (default: 1.0 1.5 2.0)")
    parser.add_argument("--signals", type=Path, default=None,
                        help="Signals file (default: data/final_portfolio/final_top24_signals.csv)")
    parser.add_argument("--prices-dir", type=Path, default=Path("nse500_data"),
                        help="Price data directory")
    parser.add_argument("--benchmark", type=Path, default=Path("data/benchmarks/nifty100.csv"),
                        help="Benchmark file")
    parser.add_argument("--top-n", type=int, default=24,
                        help="Number of top positions")
    parser.add_argument("--initial-capital", type=float, default=1000000,
                        help="Initial capital")
    parser.add_argument("--slippage", type=float, default=0.002,
                        help="Slippage (default: 0.002 = 20 bps)")
    parser.add_argument("--include-baseline", action="store_true",
                        help="Include baseline (no filter) for comparison")
    parser.add_argument("--output-dir", type=Path, default=None,
                        help="Output directory (default: experiments/score_grid_TIMESTAMP)")

    args = parser.parse_args()

    # Default signals path
    if args.signals is None:
        signals_path = ROOT / "data" / "final_portfolio" / "final_top24_signals.csv"
        if not signals_path.exists():
            # Fall back to experiments folder
            latest_runs = sorted((ROOT / "experiments" / "final_portfolio").glob("final_portfolio_*"))
            if latest_runs:
                signals_path = latest_runs[-1] / "signals" / "final_top24_signals.csv"
    else:
        signals_path = ROOT / args.signals

    if not signals_path.exists():
        print(f"ERROR: Signals file not found: {signals_path}")
        sys.exit(1)

    # Create output directory
    if args.output_dir is None:
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        experiment_dir = ROOT / "experiments" / f"score_grid_{timestamp}"
    else:
        experiment_dir = ROOT / args.output_dir

    experiment_dir.mkdir(parents=True, exist_ok=True)

    prices_dir = ROOT / args.prices_dir
    benchmark_path = ROOT / args.benchmark

    print(f"\nScore Threshold Grid Search")
    print(f"{'=' * 80}")
    print(f"Output directory: {experiment_dir}")
    print(f"Signals: {signals_path}")
    print(f"Entry thresholds: {args.entry_thresholds}")
    print(f"Exit thresholds: {args.exit_thresholds}")
    print(f"Total combinations: {len(args.entry_thresholds) * len(args.exit_thresholds)}")
    if args.include_baseline:
        print(f"Including baseline (no filter)")

    results = []
    backtest_dirs = []

    # Run baseline if requested
    if args.include_baseline:
        baseline_dir = experiment_dir / "baseline_no_filter"
        baseline_dir.mkdir(parents=True, exist_ok=True)
        backtest_dirs.append(baseline_dir)

        run_command([
            sys.executable,
            "scripts/backtest_momentum.py",
            "--prices-dir", str(prices_dir),
            "--signals", str(signals_path),
            "--benchmark", str(benchmark_path),
            "--output-dir", str(baseline_dir),
            "--initial-capital", str(args.initial_capital),
            "--top-n", str(args.top_n),
            "--slippage", str(args.slippage),
            "--scenario", "baseline",
        ], "Baseline (no score filter)")

        metrics = extract_metrics(baseline_dir)
        if metrics:
            results.append({
                "config": "baseline",
                "entry_threshold": None,
                "exit_threshold": None,
                "output_dir": baseline_dir.name,
                **metrics,
            })

    # Run grid search
    total_runs = len(args.entry_thresholds) * len(args.exit_thresholds)
    current_run = 0

    for entry_threshold in args.entry_thresholds:
        for exit_threshold in args.exit_thresholds:
            current_run += 1

            # Skip invalid combinations (exit should be <= entry)
            if exit_threshold > entry_threshold:
                print(f"\nSkipping invalid combination: entry={entry_threshold}, exit={exit_threshold} (exit > entry)")
                continue

            config_name = f"entry{entry_threshold:.1f}_exit{exit_threshold:.1f}".replace(".", "")
            config_dir = experiment_dir / config_name
            config_dir.mkdir(parents=True, exist_ok=True)
            backtest_dirs.append(config_dir)

            print(f"\n[{current_run}/{total_runs}] Testing: entry={entry_threshold}, exit={exit_threshold}")

            run_command([
                sys.executable,
                "scripts/backtest_momentum.py",
                "--prices-dir", str(prices_dir),
                "--signals", str(signals_path),
                "--benchmark", str(benchmark_path),
                "--output-dir", str(config_dir),
                "--initial-capital", str(args.initial_capital),
                "--top-n", str(args.top_n),
                "--slippage", str(args.slippage),
                "--scenario", "baseline",
                "--min-entry-score", str(entry_threshold),
                "--min-exit-score", str(exit_threshold),
                "--score-rebalance-mode", "incremental",
            ], f"Entry={entry_threshold}, Exit={exit_threshold}")

            metrics = extract_metrics(config_dir)
            if metrics:
                results.append({
                    "config": config_name,
                    "entry_threshold": entry_threshold,
                    "exit_threshold": exit_threshold,
                    "hysteresis_gap": entry_threshold - exit_threshold,
                    "output_dir": config_dir.name,
                    **metrics,
                })

    # Create summary CSV
    if results:
        summary_df = pd.DataFrame(results)
        summary_df = summary_df.sort_values("cagr", ascending=False)
        summary_path = experiment_dir / "summary.csv"
        summary_df.to_csv(summary_path, index=False)
        print(f"\n{'=' * 80}")
        print(f"Summary saved to: {summary_path}")
        print(f"{'=' * 80}\n")

        # Display top 5 configurations
        print("Top 5 configurations by CAGR:")
        print(summary_df[["config", "entry_threshold", "exit_threshold", "cagr", "max_drawdown", "total_trades"]].head(5).to_string(index=False))
        print()

    # Generate comparison report
    if len(backtest_dirs) > 0:
        print(f"\n{'=' * 80}")
        print("Generating comparison report")
        print(f"{'=' * 80}")

        run_command([
            sys.executable,
            "scripts/report_backtests.py",
            "--runs"] + [str(d) for d in backtest_dirs] + [
            "--output", str(experiment_dir / "comparison_report.html"),
        ], "Comparison report")

    print(f"\n{'=' * 80}")
    print("GRID SEARCH COMPLETE")
    print(f"{'=' * 80}")
    print(f"\nResults saved to: {experiment_dir}")
    print(f"Summary CSV: {experiment_dir / 'summary.csv'}")
    print(f"Report: {experiment_dir / 'comparison_report.html'}")

    if results:
        best = summary_df.iloc[0]
        print(f"\nBest configuration (by CAGR):")
        print(f"  Entry threshold: {best['entry_threshold']}")
        print(f"  Exit threshold: {best['exit_threshold']}")
        print(f"  Hysteresis gap: {best['hysteresis_gap']}")
        print(f"  CAGR: {best['cagr']*100:.2f}%")
        print(f"  Max Drawdown: {best['max_drawdown']*100:.2f}%")
        print(f"  Total Trades: {int(best['total_trades'])}")


if __name__ == "__main__":
    main()
