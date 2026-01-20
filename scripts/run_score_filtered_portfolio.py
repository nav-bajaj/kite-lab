#!/usr/bin/env python3
"""
Run score-filtered momentum portfolio backtests

Tests two position sizing variants:
1. Full rebalance: Equal-weight all holdings on each rebalance
2. Incremental: Keep existing positions, only allocate cash to new entrants

Both variants filter to top-24 stocks with momentum score >= 2.0
"""

import subprocess
import sys
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]


def run_command(cmd, description):
    """Run a command and handle errors"""
    print(f"\n{'=' * 80}")
    print(f"{description}")
    print(f"{'=' * 80}")
    print(f"Command: {' '.join(map(str, cmd))}\n")

    result = subprocess.run(cmd, cwd=ROOT)
    if result.returncode != 0:
        print(f"ERROR: {description} failed with exit code {result.returncode}")
        sys.exit(result.returncode)
    return result


def main():
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    experiment_dir = ROOT / "experiments" / f"score_filtered_{timestamp}"
    experiment_dir.mkdir(parents=True, exist_ok=True)

    # Use the latest final portfolio signals
    signals_path = ROOT / "data" / "final_portfolio" / "final_top24_signals.csv"
    if not signals_path.exists():
        # Fall back to experiments folder
        latest_run = sorted((ROOT / "experiments" / "final_portfolio").glob("final_portfolio_*"))[-1]
        signals_path = latest_run / "signals" / "final_top24_signals.csv"

    if not signals_path.exists():
        print(f"ERROR: Could not find signals file. Please run final portfolio first.")
        sys.exit(1)

    prices_dir = ROOT / "nse500_data"
    benchmark_path = ROOT / "data" / "benchmarks" / "nifty100.csv"

    print(f"\nScore-Filtered Portfolio Experiment")
    print(f"Timestamp: {timestamp}")
    print(f"Output directory: {experiment_dir}")
    print(f"Signals: {signals_path}")
    print(f"Min score threshold: 2.0")
    print(f"Max positions: 24")

    # Scenario 1: Baseline (no score filter) for comparison
    print("\n" + "=" * 80)
    print("Running BASELINE (no score filter)")
    print("=" * 80)
    baseline_dir = experiment_dir / "baseline_no_filter"
    baseline_dir.mkdir(parents=True, exist_ok=True)

    run_command([
        sys.executable,
        "scripts/backtest_momentum.py",
        "--prices-dir", str(prices_dir),
        "--signals", str(signals_path),
        "--benchmark", str(benchmark_path),
        "--output-dir", str(baseline_dir),
        "--initial-capital", "1000000",
        "--top-n", "24",
        "--slippage", "0.002",
        "--scenario", "baseline",
    ], "Baseline (no score filter)")

    # Scenario 2: Score filter with INCREMENTAL allocation
    print("\n" + "=" * 80)
    print("Running INCREMENTAL mode (score >= 2.0)")
    print("=" * 80)
    incremental_dir = experiment_dir / "score_filter_incremental"
    incremental_dir.mkdir(parents=True, exist_ok=True)

    run_command([
        sys.executable,
        "scripts/backtest_momentum.py",
        "--prices-dir", str(prices_dir),
        "--signals", str(signals_path),
        "--benchmark", str(benchmark_path),
        "--output-dir", str(incremental_dir),
        "--initial-capital", "1000000",
        "--top-n", "24",
        "--slippage", "0.002",
        "--scenario", "baseline",
        "--min-score", "2.0",
        "--score-rebalance-mode", "incremental",
    ], "Score filter - Incremental allocation")

    # Scenario 3: Score filter with FULL rebalance
    print("\n" + "=" * 80)
    print("Running FULL REBALANCE mode (score >= 2.0)")
    print("=" * 80)
    full_dir = experiment_dir / "score_filter_full"
    full_dir.mkdir(parents=True, exist_ok=True)

    run_command([
        sys.executable,
        "scripts/backtest_momentum.py",
        "--prices-dir", str(prices_dir),
        "--signals", str(signals_path),
        "--benchmark", str(benchmark_path),
        "--output-dir", str(full_dir),
        "--initial-capital", "1000000",
        "--top-n", "24",
        "--slippage", "0.002",
        "--scenario", "baseline",
        "--min-score", "2.0",
        "--score-rebalance-mode", "full",
    ], "Score filter - Full rebalance")

    # Generate comparison report
    print("\n" + "=" * 80)
    print("Generating comparison report")
    print("=" * 80)

    run_command([
        sys.executable,
        "scripts/report_backtests.py",
        "--runs", str(baseline_dir), str(incremental_dir), str(full_dir),
        "--output", str(experiment_dir / "comparison_report.html"),
    ], "Comparison report")

    print("\n" + "=" * 80)
    print("EXPERIMENT COMPLETE")
    print("=" * 80)
    print(f"\nResults saved to: {experiment_dir}")
    print(f"Report: {experiment_dir / 'comparison_report.html'}")
    print("\nSummary of scenarios:")
    print("1. baseline_no_filter:        Standard top-24 momentum (no score filter)")
    print("2. score_filter_incremental:  Score >= 2.0, incremental allocation")
    print("3. score_filter_full:         Score >= 2.0, full rebalance to equal-weight")


if __name__ == "__main__":
    main()
