import argparse
import itertools
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


def load_metrics(metrics_path: Path) -> dict:
    if not metrics_path.exists():
        return {}
    df = pd.read_csv(metrics_path)
    if df.empty:
        return {}
    return df.iloc[0].to_dict()


def main():
    parser = argparse.ArgumentParser(description="Rebalance sensitivity sweep (exit buffer, PnL-hold, cooldown, vol-trigger)")
    parser.add_argument("--prices-dir", type=Path, default=Path("nse500_data"))
    parser.add_argument("--signals", type=Path, default=Path("data/momentum/top25_signals.csv"))
    parser.add_argument("--benchmark", type=Path, default=Path("data/benchmarks/nifty100.csv"))
    parser.add_argument("--top-n", type=int, default=25)
    parser.add_argument("--exit-buffers", nargs="+", type=int, default=[0, 5, 10])
    parser.add_argument("--pnl-hold", nargs="+", type=float, default=[0.05, 0.1])
    parser.add_argument("--cooldown-weeks", nargs="+", type=int, default=[1, 2])
    parser.add_argument("--staged-steps", nargs="+", type=float, default=[0.25, 0.5])
    parser.add_argument("--vol-targets", nargs="+", type=float, default=[0.15, 0.2])
    parser.add_argument("--vol-lookbacks", nargs="+", type=int, default=[63])
    parser.add_argument("--scenarios", nargs="+", choices=["baseline", "cooldown", "vol_trigger"], default=["baseline", "cooldown", "vol_trigger"])
    parser.add_argument("--output-root", type=Path, default=Path("experiments"))
    parser.add_argument("--limit", type=int, help="Optional cap on number of runs")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    exp_dir = args.output_root / f"rebalance_{timestamp}"
    runs_dir = exp_dir / "backtests"
    runs_dir.mkdir(parents=True, exist_ok=True)

    summary_rows = []
    all_runs = []

    combos = itertools.product(args.exit_buffers, args.pnl_hold)
    cooldown_combos = list(itertools.product(args.cooldown_weeks, args.staged_steps))
    vol_combos = list(itertools.product(args.vol_targets, args.vol_lookbacks))

    count = 0
    for exit_buffer, pnl_hold in combos:
        for scenario in args.scenarios:
            if args.limit and count >= args.limit:
                break
            if scenario == "cooldown":
                scenario_params = cooldown_combos
            elif scenario == "vol_trigger":
                scenario_params = vol_combos
            else:
                scenario_params = [(None, None)]

            for p1, p2 in scenario_params:
                if args.limit and count >= args.limit:
                    break
                label = f"{scenario}_buf{exit_buffer}_pnl{pnl_hold}"
                if scenario == "cooldown":
                    cooldown_weeks, staged_step = p1, p2
                    label += f"_cd{cooldown_weeks}_step{staged_step}"
                elif scenario == "vol_trigger":
                    vol_target, vol_lookback = p1, p2
                    label += f"_vt{vol_target}_vl{vol_lookback}"

                run_dir = runs_dir / label
                run_dir.mkdir(parents=True, exist_ok=True)
                cmd = [
                    sys.executable,
                    "scripts/backtest_momentum.py",
                    "--prices-dir",
                    str(args.prices_dir),
                    "--signals",
                    str(args.signals),
                    "--benchmark",
                    str(args.benchmark),
                    "--output-dir",
                    str(run_dir),
                    "--top-n",
                    str(args.top_n),
                    "--exit-buffer",
                    str(exit_buffer),
                    "--scenario",
                    scenario,
                ]
                if pnl_hold is not None:
                    cmd += ["--pnl-hold-threshold", str(pnl_hold)]
                if scenario == "cooldown":
                    cmd += ["--cooldown-weeks", str(cooldown_weeks), "--staged-step", str(staged_step)]
                if scenario == "vol_trigger":
                    cmd += ["--vol-lookback", str(vol_lookback), "--target-vol", str(vol_target)]

                run(cmd, args.dry_run)
                all_runs.append(str(run_dir))
                count += 1

                if not args.dry_run:
                    metrics = load_metrics(run_dir / "momentum_metrics.csv")
                    metrics.update(
                        {
                            "label": label,
                            "scenario": scenario,
                            "exit_buffer": exit_buffer,
                            "pnl_hold": pnl_hold,
                        }
                    )
                    if scenario == "cooldown":
                        metrics.update({"cooldown_weeks": cooldown_weeks, "staged_step": staged_step})
                    if scenario == "vol_trigger":
                        metrics.update({"vol_target": vol_target, "vol_lookback": vol_lookback})
                    summary_rows.append(metrics)

    if summary_rows:
        summary_df = pd.DataFrame(summary_rows)
        if "cagr" in summary_df.columns:
            summary_df.sort_values("cagr", ascending=False, inplace=True)
            summary_df.insert(0, "rank_cagr", range(1, len(summary_df) + 1))
        summary_path = exp_dir / "summary.csv"
        summary_df.to_csv(summary_path, index=False)
        print(f"Saved summary to {summary_path}")

    if all_runs:
        report_path = exp_dir / "report.html"
        run(
            [
                sys.executable,
                "scripts/report_backtests.py",
                "--runs",
                *all_runs,
                "--output",
                str(report_path),
            ],
            args.dry_run,
        )
        print(f"Saved report to {report_path}")

    print(f"Experiment directory: {exp_dir}")


if __name__ == "__main__":
    main()
