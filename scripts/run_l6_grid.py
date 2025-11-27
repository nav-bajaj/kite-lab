import argparse
import itertools
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd


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
    turnover_path = run_dir / "momentum_turnover.csv"

    df = pd.read_csv(equity_path, parse_dates=["date"])
    total_return = df["portfolio_value"].iloc[-1] / df["portfolio_value"].iloc[0] - 1
    start_date = df["date"].iloc[0]
    end_date = df["date"].iloc[-1]
    years = max((end_date - start_date).days / 365.25, 1e-6)
    cagr = (1 + total_return) ** (1 / years) - 1
    benchmark_return = df["benchmark"].iloc[-1] / df["benchmark"].iloc[0] - 1
    drawdown = df["portfolio_value"].div(df["portfolio_value"].cummax()) - 1
    max_dd = drawdown.min()

    turnover_stats = {"avg_turnover_pct": None, "max_turnover_pct": None}
    if turnover_path.exists():
        tdf = pd.read_csv(turnover_path, parse_dates=["date"])
        if not tdf.empty:
            turnover_stats["avg_turnover_pct"] = tdf["turnover_pct"].mean()
            turnover_stats["max_turnover_pct"] = tdf["turnover_pct"].max()

    return {
        "total_return": total_return,
        "cagr": cagr,
        "benchmark_return": benchmark_return,
        "max_drawdown": max_dd,
        **turnover_stats,
        "start": start_date.date(),
        "end": end_date.date(),
    }


def main():
    parser = argparse.ArgumentParser(description="Grid search for L6 momentum hyperparameters")
    parser.add_argument("--skip-days", nargs="+", type=int, default=[21, 10, 0])
    parser.add_argument("--vol-floor", nargs="+", type=float, default=[0.0005, 0.001])
    parser.add_argument("--top-n", nargs="+", type=int, default=[25, 20])
    parser.add_argument("--exit-buffer", nargs="+", type=int, default=[0, 5])
    parser.add_argument("--scenarios", nargs="+", choices=list(SCENARIOS.keys()), default=["baseline", "cooldown"])
    parser.add_argument("--prices-dir", type=Path, default=Path("nse500_data"))
    parser.add_argument("--benchmark", type=Path, default=Path("data/benchmarks/nifty100.csv"))
    parser.add_argument("--universe-file", type=Path)
    parser.add_argument("--output-root", type=Path, default=Path("experiments"))
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, help="Cap the number of runs (evaluated in listed order)")
    args = parser.parse_args()

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    exp_dir = args.output_root / f"l6_grid_{timestamp}"
    signals_dir = exp_dir / "signals"
    runs_dir = exp_dir / "backtests"
    exp_dir.mkdir(parents=True, exist_ok=True)
    signals_dir.mkdir(parents=True, exist_ok=True)
    runs_dir.mkdir(parents=True, exist_ok=True)

    grid = itertools.product(args.skip_days, args.vol_floor, args.top_n, args.exit_buffer, args.scenarios)

    summary_rows = []
    run_paths = []
    for idx, (skip_days, vol_floor, top_n, exit_buf, scenario) in enumerate(grid, start=1):
        if args.limit and idx > args.limit:
            break
        label = f"l6_sd{skip_days}_vf{vol_floor}_top{top_n}_buf{exit_buf}_{scenario}"

        signal_path = signals_dir / f"{label}.csv"
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
            str(top_n),
            "--vol-floor",
            str(vol_floor),
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
            "--exit-buffer",
            str(exit_buf),
        ] + SCENARIOS[scenario]
        run(cmd, args.dry_run)
        run_paths.append(str(run_dir))

        if not args.dry_run:
            metrics = analyze_backtest(run_dir)
            metrics.update(
                {
                    "label": label,
                    "skip_days": skip_days,
                    "vol_floor": vol_floor,
                    "top_n": top_n,
                    "exit_buffer": exit_buf,
                    "scenario": scenario,
                }
            )
            summary_rows.append(metrics)

    if summary_rows:
        summary_path = exp_dir / "summary.csv"
        pd.DataFrame(summary_rows).to_csv(summary_path, index=False)
        print(f"Saved summary to {summary_path}")

    if run_paths:
        report_path = exp_dir / "report.html"
        run(
            [
                sys.executable,
                "scripts/report_backtests.py",
                "--runs",
                *run_paths,
                "--output",
                str(report_path),
            ],
            args.dry_run,
        )
        print(f"Saved report to {report_path}")

    print(f"Experiment directory: {exp_dir}")


if __name__ == "__main__":
    main()
