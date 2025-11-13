import argparse
import subprocess
import sys
from pathlib import Path
from datetime import datetime


LOOKBACK_CONFIGS = {
    "L3": ["3"],
    "L6": ["6"],
    "L12": ["12"],
}

SKIP_CONFIGS = {
    "noskip": 0,
}

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


def main():
    parser = argparse.ArgumentParser(description="Run multiple momentum backtest scenarios")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--universe-file", type=Path, help="Optional CSV with Symbol column")
    parser.add_argument("--signals-dir", type=Path, default=Path("data/momentum"))
    parser.add_argument("--output-root", type=Path, default=Path("data/backtests"))
    parser.add_argument("--label-prefix", default="")
    args = parser.parse_args()

    runs = []

    for lb_label, lb_values in LOOKBACK_CONFIGS.items():
        for skip_label, skip_days in SKIP_CONFIGS.items():
            name_prefix = f"{args.label_prefix}{lb_label}_{skip_label}"
            signal_name = f"signals_{name_prefix}.csv"
            signal_path = args.signals_dir / signal_name
            signal_path.parent.mkdir(parents=True, exist_ok=True)
            # Build signals
            cmd = [
                sys.executable,
                "scripts/build_momentum_signals.py",
                "--prices-dir",
                "nse500_data",
                "--output",
                str(signal_path),
                "--skip-days",
                str(skip_days),
                "--lookbacks",
                *lb_values,
            ]
            if args.universe_file:
                cmd += ["--universe-file", str(args.universe_file)]
            run(cmd, args.dry_run)

            run([
                sys.executable,
                "scripts/validate_signals.py",
                "--signals",
                str(signal_path),
            ], args.dry_run)

            for scenario, scenario_flags in SCENARIOS.items():
                run_dir = args.output_root / f"{name_prefix}_{scenario}"
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
                    "25",
                    "--slippage",
                    "0.002",
                ] + scenario_flags
                run(cmd, args.dry_run)
                runs.append(str(run_dir))

    # Generate comparison report
    if runs:
        report_path = args.output_root / "report.html"
        run([
            sys.executable,
            "scripts/report_backtests.py",
            "--runs",
            *runs,
            "--output",
            str(report_path),
        ], args.dry_run)


if __name__ == "__main__":
    main()
