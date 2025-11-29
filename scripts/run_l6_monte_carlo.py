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
    df = pd.read_csv(source)
    if "Symbol" not in df.columns:
        raise SystemExit(f"Source file {source} must contain a Symbol column")
    sampled = df.sample(n=size, random_state=seed)
    dest.parent.mkdir(parents=True, exist_ok=True)
    sampled.to_csv(dest, index=False)
    print(f"Saved sample universe ({len(sampled)} symbols) to {dest}")
    return dest


def load_metrics(metrics_path: Path) -> dict:
    if not metrics_path.exists():
        return {}
    df = pd.read_csv(metrics_path)
    if df.empty:
        return {}
    return df.iloc[0].to_dict()


def main():
    parser = argparse.ArgumentParser(description="Monte Carlo for L6 momentum (baseline, hysteresis, PnL-hold)")
    parser.add_argument("--runs", type=int, default=20)
    parser.add_argument("--prices-dir", type=Path, default=Path("nse500_data"))
    parser.add_argument("--benchmark", type=Path, default=Path("data/benchmarks/nifty100.csv"))
    parser.add_argument("--universe-file", type=Path, default=Path("data/static/nse500_universe.csv"))
    parser.add_argument("--sample-size", type=int, default=250)
    parser.add_argument("--topn-min", type=int, default=20)
    parser.add_argument("--topn-max", type=int, default=30)
    parser.add_argument("--skip-days", nargs="+", type=int, default=[0])
    parser.add_argument("--exit-buffers", nargs="+", type=int, default=[0, 5, 10])
    parser.add_argument("--pnl-hold", nargs="+", type=float, default=[0.05, 0.1])
    parser.add_argument("--vol-floor", nargs="+", type=float, default=[0.0005, 0.001])
    parser.add_argument("--output-root", type=Path, default=Path("experiments"))
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    random.seed(args.seed)
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    exp_dir = args.output_root / f"l6_mc_{timestamp}"
    signals_dir = exp_dir / "signals"
    runs_dir = exp_dir / "backtests"
    exp_dir.mkdir(parents=True, exist_ok=True)
    signals_dir.mkdir(parents=True, exist_ok=True)
    runs_dir.mkdir(parents=True, exist_ok=True)

    summary_rows = []
    all_run_dirs = []

    for i in range(1, args.runs + 1):
        top_n = random.randint(args.topn_min, args.topn_max)
        skip_days = random.choice(args.skip_days)
        exit_buffer = random.choice(args.exit_buffers)
        pnl_hold = random.choice(args.pnl_hold)
        vol_floor = random.choice(args.vol_floor)
        sample_seed = args.seed + i

        label = f"run{i:03d}_sd{skip_days}_buf{exit_buffer}_pnl{pnl_hold}_top{top_n}"
        universe_sample_path = signals_dir / f"{label}_universe.csv"
        sample_universe(args.universe_file, args.sample_size, sample_seed, universe_sample_path)

        signal_path = signals_dir / f"{label}_signals.csv"
        build_top_n = top_n + exit_buffer
        cmd = [
            sys.executable,
            "scripts/build_momentum_signals.py",
            "--prices-dir",
            str(args.prices_dir),
            "--output",
            str(signal_path),
            "--skip-days",
            str(skip_days),
            "--lookbacks",
            "6",
            "--top-n",
            str(build_top_n),
            "--vol-floor",
            str(vol_floor),
            "--universe-file",
            str(universe_sample_path),
        ]
        run(cmd, args.dry_run)
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

        scenarios = [
            ("baseline", 0, None),
            ("hyst", exit_buffer, None),
            ("pnl_hold", exit_buffer, pnl_hold),
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

            if not args.dry_run:
                metrics = load_metrics(run_dir / "momentum_metrics.csv")
                metrics.update(
                    {
                        "label": f"{label}_{scenario_label}",
                        "scenario": scenario_label,
                        "top_n": top_n,
                        "skip_days": skip_days,
                        "exit_buffer": scenario_exit_buf,
                        "pnl_hold": pnl_threshold,
                        "vol_floor": vol_floor,
                        "sample_size": args.sample_size,
                    }
                )
                summary_rows.append(metrics)

    if summary_rows:
        summary_path = exp_dir / "summary.csv"
        summary_df = pd.DataFrame(summary_rows)
        if "cagr" in summary_df.columns:
            summary_df.sort_values("cagr", ascending=False, inplace=True)
            summary_df.insert(0, "rank_cagr", range(1, len(summary_df) + 1))
        summary_df.to_csv(summary_path, index=False)
        print(f"Saved summary to {summary_path}")

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
        print(f"Saved report to {report_path}")

    print(f"Experiment directory: {exp_dir}")


if __name__ == "__main__":
    main()
