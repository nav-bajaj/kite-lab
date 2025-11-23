import argparse
import subprocess
import sys
from pathlib import Path
import pandas as pd


def run(cmd):
    print("Command:", " ".join(str(c) for c in cmd))
    result = subprocess.run(cmd)
    if result.returncode != 0:
        raise SystemExit(result.returncode)


def sample_universe(source: Path, size: int, seed: int, dest: Path):
    df = pd.read_csv(source)
    if "Symbol" not in df.columns:
        raise SystemExit(f"Source file {source} must contain a Symbol column")
    sampled = df.sample(n=size, random_state=seed)
    dest.parent.mkdir(parents=True, exist_ok=True)
    sampled.to_csv(dest, index=False)
    print(f"Saved sample universe ({len(sampled)} symbols) to {dest}")
    return dest


def main():
    parser = argparse.ArgumentParser(description="Run baseline vs hysteresis backtests in one go")
    parser.add_argument("--prices-dir", type=Path, default=Path("nse500_data"))
    parser.add_argument("--benchmark", type=Path, default=Path("data/benchmarks/nifty100.csv"))
    parser.add_argument("--universe-file", type=Path, default=Path("data/static/nse500_universe.csv"))
    parser.add_argument("--sample-size", type=int, default=250, help="Sample size from universe for this run")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--signals-dir", type=Path, default=Path("data/momentum"))
    parser.add_argument("--runs-dir", type=Path, default=Path("data/backtests"))
    parser.add_argument("--label", default="l6_sample")
    parser.add_argument("--lookbacks", nargs="+", default=["6"])
    parser.add_argument("--skip-days", type=int, default=0)
    parser.add_argument("--top-n", type=int, default=25)
    parser.add_argument("--exit-buffer", type=int, default=10)
    parser.add_argument("--pnl-hold-threshold", type=float, default=0.05)
    args = parser.parse_args()

    signals_dir = args.signals_dir
    runs_dir = args.runs_dir
    signals_dir.mkdir(parents=True, exist_ok=True)
    runs_dir.mkdir(parents=True, exist_ok=True)

    sample_path = signals_dir / f"{args.label}_universe.csv"
    sample_universe(args.universe_file, args.sample_size, args.seed, sample_path)

    signal_path = signals_dir / f"{args.label}_signals.csv"
    build_top_n = args.top_n + args.exit_buffer
    run([
        sys.executable,
        "scripts/build_momentum_signals.py",
        "--prices-dir",
        str(args.prices_dir),
        "--output",
        str(signal_path),
        "--skip-days",
        str(args.skip_days),
        "--lookbacks",
        *args.lookbacks,
        "--top-n",
        str(build_top_n),
        "--universe-file",
        str(sample_path),
    ])

    scenarios = [
        ("l6_baseline", 0, None),
        ("l6_hyst", args.exit_buffer, None),
        ("l6_hyst_pnl", args.exit_buffer, args.pnl_hold_threshold),
    ]

    run_paths = []
    for name, exit_buffer, pnl_threshold in scenarios:
        run_dir = runs_dir / name
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
            "--top-n",
            str(args.top_n),
            "--scenario",
            "baseline",
            "--exit-buffer",
            str(exit_buffer),
        ]
        if pnl_threshold is not None:
            cmd += ["--pnl-hold-threshold", str(pnl_threshold)]
        run(cmd)
        run_paths.append(str(run_dir))

    report_path = runs_dir / "report.html"
    run([
        sys.executable,
        "scripts/report_backtests.py",
        "--runs",
        *run_paths,
        "--output",
        str(report_path),
    ])
    print(f"Finished. Report: {report_path}")


if __name__ == "__main__":
    main()
