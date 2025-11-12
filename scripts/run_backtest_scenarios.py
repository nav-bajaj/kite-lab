import argparse
import subprocess
import sys
from pathlib import Path


LOOKBACK_CONFIGS = {
    "L3": ["3"],
    "L6": ["6"],
    "L12": ["12"],
}

SKIP_CONFIGS = {
    "skip": 21,
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
    args = parser.parse_args()

    runs = []

    for lb_label, lb_values in LOOKBACK_CONFIGS.items():
        for skip_label, skip_days in SKIP_CONFIGS.items():
            signal_name = f"signals_{lb_label}_{skip_label}.csv"
            signal_path = Path("data/momentum") / signal_name
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
            run(cmd, args.dry_run)

            run([
                sys.executable,
                "scripts/validate_signals.py",
                "--signals",
                str(signal_path),
            ], args.dry_run)

            for scenario, scenario_flags in SCENARIOS.items():
                run_dir = Path("data/backtests") / f"{lb_label}_{skip_label}_{scenario}"
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
    run([
        sys.executable,
        "scripts/report_backtests.py",
        "--runs",
        *runs,
        "--output",
        "data/backtests/report.html",
    ], args.dry_run)


if __name__ == "__main__":
    main()
