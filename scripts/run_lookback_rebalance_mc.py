"""
Monte Carlo experiments for lookback period and rebalance frequency optimization

Tests combinations of:
- Lookback periods: 6, 9, 12 months
- Rebalance frequencies: 1, 2, 3, 4 weeks
- Exit buffers: 0, 5, 10
- PnL-hold thresholds: 0, 0.05, 0.1

Usage:
    python scripts/run_lookback_rebalance_mc.py --runs 20 --sample-size 250
"""

import argparse
import random
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
        description="Monte Carlo for lookback period and rebalance frequency optimization"
    )
    parser.add_argument("--runs", type=int, default=20, help="Number of Monte Carlo runs")
    parser.add_argument("--prices-dir", type=Path, default=Path("nse500_data"))
    parser.add_argument("--benchmark", type=Path, default=Path("data/benchmarks/nifty100.csv"))
    parser.add_argument("--universe-file", type=Path, default=Path("data/static/nse500_universe.csv"))
    parser.add_argument("--sample-size", type=int, default=250)
    parser.add_argument("--topn-min", type=int, default=20)
    parser.add_argument("--topn-max", type=int, default=30)
    parser.add_argument(
        "--lookback-months",
        nargs="+",
        type=int,
        default=[6, 9, 12],
        help="Lookback periods to test (months, 1-12)"
    )
    parser.add_argument(
        "--rebalance-weeks",
        nargs="+",
        type=int,
        default=[1, 2, 3, 4],
        help="Rebalance frequencies to test (weeks, 1-12)"
    )
    parser.add_argument("--skip-days", type=int, default=21, help="Skip window (fixed)")
    parser.add_argument("--exit-buffers", nargs="+", type=int, default=[0, 5, 10])
    parser.add_argument("--pnl-hold", nargs="+", type=float, default=[0, 0.05, 0.1])
    parser.add_argument("--vol-floor", type=float, default=0.0005, help="Fixed vol-floor")
    parser.add_argument("--output-root", type=Path, default=Path("experiments"))
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    random.seed(args.seed)
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    exp_dir = args.output_root / f"lookback_rebal_mc_{timestamp}"
    signals_dir = exp_dir / "signals"
    runs_dir = exp_dir / "backtests"
    exp_dir.mkdir(parents=True, exist_ok=True)
    signals_dir.mkdir(parents=True, exist_ok=True)
    runs_dir.mkdir(parents=True, exist_ok=True)

    summary_rows = []
    all_run_dirs = []

    # Single universe sample for all runs
    universe_sample_path = signals_dir / "fixed_universe.csv"
    sample_universe(args.universe_file, args.sample_size, args.seed, universe_sample_path)

    for i in range(1, args.runs + 1):
        print(f"\n{'='*70}")
        print(f"Run {i}/{args.runs}")
        print(f"{'='*70}\n")

        # Sample parameters
        top_n = random.randint(args.topn_min, args.topn_max)
        lookback_months = random.choice(args.lookback_months)
        rebalance_weeks = random.choice(args.rebalance_weeks)
        exit_buffer = random.choice(args.exit_buffers)
        pnl_hold = random.choice(args.pnl_hold)

        label = f"run{i:03d}_L{lookback_months}_R{rebalance_weeks}w_buf{exit_buffer}_pnl{pnl_hold}_top{top_n}"

        # Build signals
        signal_path = signals_dir / f"{label}_signals.csv"
        build_top_n = top_n + exit_buffer
        cmd = [
            sys.executable,
            "scripts/build_momentum_signals_flexible.py",
            "--prices-dir",
            str(args.prices_dir),
            "--output",
            str(signal_path),
            "--skip-days",
            str(args.skip_days),
            "--lookback-months",
            str(lookback_months),
            "--rebalance-weeks",
            str(rebalance_weeks),
            "--top-n",
            str(build_top_n),
            "--vol-floor",
            str(args.vol_floor),
            "--universe-file",
            str(universe_sample_path),
        ]
        run(cmd, args.dry_run)

        # Validate signals
        run(
            [
                sys.executable,
                "scripts/validate_signals.py",
                "--signals",
                str(signal_path),
                "--top-n",
                str(build_top_n),
            ],
            args.dry_run,
        )

        # Run three scenarios: baseline, hysteresis, pnl_hold
        scenarios = [
            ("baseline", 0, None),
            ("hyst", exit_buffer, None),
            ("pnl_hold", exit_buffer, pnl_hold if pnl_hold > 0 else None),
        ]

        for scenario_label, scenario_exit_buf, pnl_threshold in scenarios:
            run_dir = runs_dir / f"{label}_{scenario_label}"
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
                str(top_n),
                "--slippage",
                "0.002",
                "--scenario",
                "baseline",
                "--exit-buffer",
                str(scenario_exit_buf),
            ]
            if pnl_threshold is not None:
                cmd += ["--pnl-hold-threshold", str(pnl_threshold)]
            run(cmd, args.dry_run)
            all_run_dirs.append(str(run_dir))

            # Collect metrics
            if not args.dry_run:
                metrics = load_metrics(run_dir / "momentum_metrics.csv")
                metrics.update({
                    "label": f"{label}_{scenario_label}",
                    "scenario": scenario_label,
                    "run": i,
                    "top_n": top_n,
                    "lookback_months": lookback_months,
                    "rebalance_weeks": rebalance_weeks,
                    "skip_days": args.skip_days,
                    "exit_buffer": scenario_exit_buf,
                    "pnl_hold": pnl_threshold if pnl_threshold is not None else 0,
                    "vol_floor": args.vol_floor,
                    "sample_size": args.sample_size,
                })
                summary_rows.append(metrics)

    # Save summary
    if summary_rows:
        summary_path = exp_dir / "summary.csv"
        summary_df = pd.DataFrame(summary_rows)

        # Sort by CAGR
        if "cagr" in summary_df.columns:
            summary_df.sort_values("cagr", ascending=False, inplace=True)
            summary_df.insert(0, "rank_cagr", range(1, len(summary_df) + 1))

        summary_df.to_csv(summary_path, index=False)
        print(f"\n{'='*70}")
        print(f"Saved summary to {summary_path}")

        # Generate aggregated analysis
        print(f"\n{'='*70}")
        print("Average Performance by Configuration")
        print(f"{'='*70}")

        # By lookback period
        if "lookback_months" in summary_df.columns:
            avg_by_lookback = summary_df.groupby("lookback_months").agg({
                "cagr": "mean",
                "max_drawdown": "mean",
                "avg_turnover_pct": "mean",
                "hit_rate_overall": "mean",
            }).round(4)
            print("\nBy Lookback Period:")
            print(avg_by_lookback.to_string())

        # By rebalance frequency
        if "rebalance_weeks" in summary_df.columns:
            avg_by_rebal = summary_df.groupby("rebalance_weeks").agg({
                "cagr": "mean",
                "max_drawdown": "mean",
                "avg_turnover_pct": "mean",
                "hit_rate_overall": "mean",
            }).round(4)
            print("\nBy Rebalance Frequency (weeks):")
            print(avg_by_rebal.to_string())

        # By lookback + rebalance combination
        if "lookback_months" in summary_df.columns and "rebalance_weeks" in summary_df.columns:
            avg_by_combo = summary_df.groupby(["lookback_months", "rebalance_weeks"]).agg({
                "cagr": "mean",
                "max_drawdown": "mean",
            }).round(4)
            print("\nBy Lookback × Rebalance Combination:")
            print(avg_by_combo.to_string())

            # Save aggregated stats
            combo_path = exp_dir / "summary_by_config.csv"
            avg_by_combo.to_csv(combo_path)
            print(f"\nSaved config summary to {combo_path}")

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
