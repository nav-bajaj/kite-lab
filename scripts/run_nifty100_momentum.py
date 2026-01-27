"""
Run Nifty 100 momentum portfolio with same parameters as final portfolio

This script generates momentum signals and backtests for the Nifty 100 universe only.
Uses identical parameters to the NSE 500 final portfolio for direct comparison.

Usage:
    python scripts/run_nifty100_momentum.py
    python scripts/run_nifty100_momentum.py --dry-run
"""

import argparse
import subprocess
import sys
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))


def run_command(cmd, dry_run=False):
    """Execute a command and return success status"""
    print("Command:", " ".join(cmd))
    if dry_run:
        print("[dry-run] skipped")
        return True

    result = subprocess.run(cmd)
    return result.returncode == 0


def main():
    parser = argparse.ArgumentParser(description="Nifty 100 momentum portfolio generator")
    parser.add_argument("--prices-dir", type=Path, default=Path("nse500_data"))
    parser.add_argument("--benchmark", type=Path, default=Path("data/benchmarks/nifty100.csv"))
    parser.add_argument("--universe-file", type=Path, default=Path("data/static/nifty100_universe.csv"))
    parser.add_argument("--output-root", type=Path, default=Path("nifty_100_tests"))

    # Portfolio parameters (same as final portfolio)
    parser.add_argument("--top-n", type=int, default=24)
    parser.add_argument("--lookback-months", type=int, default=6)
    parser.add_argument("--skip-days", type=int, default=0)
    parser.add_argument("--rebalance-weeks", type=int, default=1)
    parser.add_argument("--vol-floor", type=float, default=0.05)
    parser.add_argument("--vol-power", type=float, default=1.0)

    # Backtest parameters
    parser.add_argument("--initial-capital", type=float, default=1_000_000)
    parser.add_argument("--slippage", type=float, default=0.002)
    parser.add_argument("--scenario", type=str, default="baseline")
    parser.add_argument("--exit-buffer", type=int, default=0)

    parser.add_argument("--dry-run", action="store_true")

    args = parser.parse_args()

    # Create timestamped output directory
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    output_dir = args.output_root / f"nifty100_portfolio_{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=True)

    signals_dir = output_dir / "signals"
    backtests_dir = output_dir / "backtests" / args.scenario
    signals_dir.mkdir(parents=True, exist_ok=True)
    backtests_dir.mkdir(parents=True, exist_ok=True)

    signals_path = signals_dir / "nifty100_signals.csv"

    print(f"\n{'='*80}")
    print(f"NIFTY 100 MOMENTUM PORTFOLIO")
    print(f"{'='*80}\n")
    print(f"Universe: Nifty 100 (100 stocks)")
    print(f"Output: {output_dir}")
    print(f"Parameters:")
    print(f"  - Top-N: {args.top_n}")
    print(f"  - Lookback: {args.lookback_months} months")
    print(f"  - Skip days: {args.skip_days}")
    print(f"  - Rebalance: {args.rebalance_weeks} week(s)")
    print(f"  - Vol floor: {args.vol_floor}")
    print(f"  - Initial capital: ₹{args.initial_capital:,.0f}")
    print(f"  - Scenario: {args.scenario}")
    print()

    # Step 1: Generate signals
    print(f"{'='*80}")
    print("STEP 1: Generate Momentum Signals")
    print(f"{'='*80}\n")

    signal_cmd = [
        sys.executable,
        "scripts/build_momentum_signals_flexible.py",
        "--prices-dir", str(args.prices_dir),
        "--output", str(signals_path),
        "--skip-days", str(args.skip_days),
        "--lookback-months", str(args.lookback_months),
        "--rebalance-weeks", str(args.rebalance_weeks),
        "--top-n", str(args.top_n),
        "--vol-floor", str(args.vol_floor),
        "--vol-power", str(args.vol_power),
        "--universe-file", str(args.universe_file),
    ]

    if not run_command(signal_cmd, args.dry_run):
        print("Signal generation failed")
        return 1

    if args.dry_run:
        return 0

    # Step 2: Run backtest
    print(f"\n{'='*80}")
    print("STEP 2: Run Backtest")
    print(f"{'='*80}\n")

    backtest_cmd = [
        sys.executable,
        "scripts/backtest_momentum.py",
        "--prices-dir", str(args.prices_dir),
        "--signals", str(signals_path),
        "--benchmark", str(args.benchmark),
        "--output-dir", str(backtests_dir),
        "--initial-capital", str(args.initial_capital),
        "--top-n", str(args.top_n),
        "--slippage", str(args.slippage),
        "--scenario", args.scenario,
        "--exit-buffer", str(args.exit_buffer),
    ]

    if not run_command(backtest_cmd, args.dry_run):
        print("Backtest failed")
        return 1

    # Step 3: Generate report
    print(f"\n{'='*80}")
    print("STEP 3: Generate Report")
    print(f"{'='*80}\n")

    report_path = output_dir / "report.html"

    report_cmd = [
        sys.executable,
        "scripts/report_backtests.py",
        "--runs", str(backtests_dir),
        "--output", str(report_path),
    ]

    if not run_command(report_cmd, args.dry_run):
        print("Report generation failed")
        return 1

    print(f"\n{'='*80}")
    print("COMPLETED")
    print(f"{'='*80}\n")
    print(f"Output directory: {output_dir}")
    print(f"Signals: {signals_path}")
    print(f"Backtest: {backtests_dir}")
    print(f"Report: {report_path}")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
