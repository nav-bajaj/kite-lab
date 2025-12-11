"""
Run experiments comparing baseline L6 momentum vs TA-filtered variants

Tests whether technical analysis filters improve risk-adjusted returns.

Usage:
    python scripts/run_ta_filter_experiments.py --runs 10 --sample-size 250
"""

import argparse
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd


def run(cmd, dry_run=False):
    print("Command:", " ".join(str(c) for c in cmd))
    if dry_run:
        return 0
    result = subprocess.run(cmd)
    if result.returncode != 0:
        raise SystemExit(result.returncode)
    return result.returncode


def sample_universe(source: Path, size: int, seed: int, dest: Path):
    """Sample a subset of the universe"""
    df = pd.read_csv(source)
    if "Symbol" not in df.columns:
        raise SystemExit(f"Source file {source} must contain a Symbol column")
    sampled = df.sample(n=size, random_state=seed)
    dest.parent.mkdir(parents=True, exist_ok=True)
    sampled.to_csv(dest, index=False)
    print(f"Saved sample universe ({len(sampled)} symbols) to {dest}")
    return dest


def load_metrics(metrics_path: Path) -> dict:
    """Load backtest metrics from CSV"""
    if not metrics_path.exists():
        return {}
    df = pd.read_csv(metrics_path)
    if df.empty:
        return {}
    return df.iloc[0].to_dict()


def main():
    parser = argparse.ArgumentParser(
        description="Test TA filters against baseline L6 momentum"
    )
    parser.add_argument("--runs", type=int, default=10, help="Number of runs per filter")
    parser.add_argument("--prices-dir", type=Path, default=Path("nse500_data"))
    parser.add_argument("--benchmark", type=Path, default=Path("data/benchmarks/nifty100.csv"))
    parser.add_argument("--universe-file", type=Path, default=Path("data/static/nse500_universe.csv"))
    parser.add_argument("--sample-size", type=int, default=250)
    parser.add_argument("--output-root", type=Path, default=Path("experiments"))
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    exp_dir = args.output_root / f"ta_filters_{timestamp}"
    signals_dir = exp_dir / "signals"
    runs_dir = exp_dir / "backtests"
    exp_dir.mkdir(parents=True, exist_ok=True)
    signals_dir.mkdir(parents=True, exist_ok=True)
    runs_dir.mkdir(parents=True, exist_ok=True)

    # Define filters to test
    ta_filters = [
        "none",                      # Baseline
        "rsi_neutral",               # Exclude extremes
        "rsi_bullish",               # Bullish only
        "trend_ema20",               # Short-term trend
        "trend_ema50",               # Medium-term trend
        "adx_trending",              # Strong trends only
        "macd_positive",             # Momentum confirmation
        "combined_conservative",     # Multi-filter conservative
        "combined_aggressive",       # Multi-filter aggressive
    ]

    summary_rows = []
    all_run_dirs = []

    # Single universe sample for all runs
    universe_sample_path = signals_dir / "fixed_universe.csv"
    sample_universe(args.universe_file, args.sample_size, args.seed, universe_sample_path)

    for run_num in range(1, args.runs + 1):
        print(f"\n{'='*60}")
        print(f"Run {run_num}/{args.runs}")
        print(f"{'='*60}\n")

        for ta_filter in ta_filters:
            label = f"run{run_num:03d}_filter_{ta_filter}"
            signal_path = signals_dir / f"{label}_signals.csv"

            # Build signals with TA filter
            cmd = [
                sys.executable,
                "scripts/build_momentum_signals_with_ta.py",
                "--prices-dir",
                str(args.prices_dir),
                "--output",
                str(signal_path),
                "--skip-days",
                "21",
                "--lookback-months",
                "6",
                "--top-n",
                "25",
                "--vol-floor",
                "0.0005",
                "--ta-filter",
                ta_filter,
                "--universe-file",
                str(universe_sample_path),
            ]
            run(cmd, args.dry_run)

            # Run backtest (baseline scenario, no exit buffer)
            run_dir = runs_dir / label
            run_dir.mkdir(parents=True, exist_ok=True)
            cmd = [
                sys.executable,
                "scripts/backtest_momentum.py",
                "--prices-dir",
                str(args.prices_dir),
                "--signals",
                str(signal_path),
                "--benchmark",
                str(args.benchmark),
                "--output-dir",
                str(run_dir),
                "--initial-capital",
                "1000000",
                "--top-n",
                "25",
                "--slippage",
                "0.002",
                "--scenario",
                "baseline",
                "--exit-buffer",
                "0",
            ]
            run(cmd, args.dry_run)
            all_run_dirs.append(str(run_dir))

            # Collect metrics
            if not args.dry_run:
                metrics = load_metrics(run_dir / "momentum_metrics.csv")
                metrics.update({
                    "label": label,
                    "run": run_num,
                    "ta_filter": ta_filter,
                    "sample_size": args.sample_size,
                })
                summary_rows.append(metrics)

    # Save summary
    if summary_rows:
        summary_path = exp_dir / "summary.csv"
        summary_df = pd.DataFrame(summary_rows)

        # Calculate averages by filter
        avg_by_filter = summary_df.groupby("ta_filter").agg({
            "cagr": "mean",
            "max_drawdown": "mean",
            "avg_turnover_pct": "mean",
            "hit_rate_overall": "mean",
            "avg_holding_days": "mean",
        }).round(4)

        print("\n" + "="*60)
        print("Average Performance by TA Filter")
        print("="*60)
        print(avg_by_filter.to_string())

        # Sort full results by CAGR
        if "cagr" in summary_df.columns:
            summary_df.sort_values("cagr", ascending=False, inplace=True)
            summary_df.insert(0, "rank_cagr", range(1, len(summary_df) + 1))

        summary_df.to_csv(summary_path, index=False)
        print(f"\nSaved full summary to {summary_path}")

        # Save averages
        avg_path = exp_dir / "summary_by_filter.csv"
        avg_by_filter.to_csv(avg_path)
        print(f"Saved filter averages to {avg_path}")

    # Generate HTML report
    if all_run_dirs:
        report_path = exp_dir / "report.html"
        run(
            [
                sys.executable,
                "scripts/report_backtests.py",
                "--runs",
                *all_run_dirs,
                "--output",
                str(report_path),
            ],
            args.dry_run,
        )
        print(f"\nSaved report to {report_path}")

    print(f"\nExperiment directory: {exp_dir}")


if __name__ == "__main__":
    main()
