import argparse
import csv
import subprocess
import sys
from datetime import date, datetime, timedelta
from pathlib import Path


WEEKDAYS = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


def run_command(command, dry_run=False):
    print("Command:", " ".join(str(c) for c in command))
    if dry_run:
        print("[dry-run] skipped")
        return 0
    result = subprocess.run(command)
    if result.returncode != 0:
        raise SystemExit(result.returncode)
    return result.returncode


def parse_latest_signals(signals_path: Path):
    max_date = None
    rows = []
    with signals_path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            signal_date = row.get("date")
            if not signal_date:
                continue
            if max_date is None or signal_date > max_date:
                max_date = signal_date
                rows = [row]
            elif signal_date == max_date:
                rows.append(row)
    if not rows:
        raise SystemExit(f"No rows found in {signals_path}")
    rows.sort(key=lambda r: int(r["rank"]))
    return max_date, rows


def last_completed_week_end(today: date, week_end_weekday: int) -> date:
    """
    Return the last completed week-end boundary for a weekly period ending on `week_end_weekday`.

    This mirrors the behavior of resampling with e.g. `W-THU`, but avoids including the in-progress
    (partial) current week when `today` is before the week end.
    """
    if week_end_weekday < 0 or week_end_weekday > 6:
        raise ValueError(f"Invalid weekday: {week_end_weekday}")
    days_to_end = (week_end_weekday - today.weekday()) % 7
    period_end = today + timedelta(days=days_to_end)
    if today < period_end:
        return period_end - timedelta(days=7)
    return period_end


def filter_signals_to_completed_periods(signals_path: Path, output_path: Path, today: date) -> Path:
    """
    Drop any signals that fall into the current in-progress weekly period (W-THU),
    which would otherwise produce an early rebalance/trade when run mid-week (e.g. Monday).
    """
    cutoff = last_completed_week_end(today, WEEKDAYS["thursday"]).isoformat()
    with signals_path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = reader.fieldnames
        if not fieldnames:
            raise SystemExit(f"Signals file missing header: {signals_path}")
        rows = [row for row in reader if row.get("date") and row["date"] <= cutoff]
    if not rows:
        raise SystemExit(
            f"No completed-period signals found in {signals_path} with cutoff {cutoff}; "
            "check price data coverage and signal generation."
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return output_path


def next_trading_day(signal_date: date, calendar_dates) -> date:
    """
    Pick the next available trading day strictly after `signal_date`.
    Falls back to `signal_date` if no later date exists in the calendar.
    """
    for d in calendar_dates:
        if d > signal_date:
            return d
    return signal_date


def load_trading_calendar_from_benchmark(benchmark_path: Path):
    dates = []
    with benchmark_path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            d = row.get("date")
            if not d:
                continue
            try:
                dates.append(datetime.strptime(d, "%Y-%m-%d").date())
            except ValueError:
                continue
    dates = sorted(set(dates))
    if not dates:
        raise SystemExit(f"No dates found in benchmark file: {benchmark_path}")
    return dates


def write_snapshot(rows, snapshot_path: Path):
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    with snapshot_path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["date", "signal_date", "rank", "symbol", "score"])
        for row in rows:
            writer.writerow([row.get("_as_of_date", row["date"]), row["date"], row["rank"], row["symbol"], row.get("score", "")])


def load_snapshot(snapshot_path: Path):
    holdings = {}
    with snapshot_path.open(newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            symbol = row.get("symbol")
            if not symbol:
                continue
            holdings[symbol] = int(row["rank"])
    return holdings


def find_latest_snapshot(snapshot_dir: Path):
    if not snapshot_dir.exists():
        return None
    candidates = []
    for path in snapshot_dir.glob("portfolio_*.csv"):
        try:
            date_str = path.stem.replace("portfolio_", "")
            snapshot_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            continue
        candidates.append((snapshot_date, path))
    if not candidates:
        return None
    candidates.sort()
    return candidates[-1][1]


def find_previous_snapshot(snapshot_dir: Path, current_path: Path):
    if not snapshot_dir.exists():
        return None
    candidates = []
    for path in snapshot_dir.glob("portfolio_*.csv"):
        if path == current_path:
            continue
        try:
            date_str = path.stem.replace("portfolio_", "")
            snapshot_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            continue
        candidates.append((snapshot_date, path))
    if not candidates:
        return None
    candidates.sort()
    return candidates[-1][1]


def compute_changes(old_holdings, new_holdings):
    old_symbols = set(old_holdings)
    new_symbols = set(new_holdings)
    additions = sorted(new_symbols - old_symbols, key=lambda s: new_holdings[s])
    removals = sorted(old_symbols - new_symbols, key=lambda s: old_holdings[s])
    rank_changes = [
        (sym, old_holdings[sym], new_holdings[sym])
        for sym in sorted(old_symbols & new_symbols, key=lambda s: new_holdings[s])
        if old_holdings[sym] != new_holdings[sym]
    ]
    return additions, removals, rank_changes


def write_changes_report(report_path: Path, changes, prior_path, current_path, as_of_date, new_holdings):
    additions, removals, rank_changes = changes
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with report_path.open("w") as handle:
        handle.write("# Final momentum portfolio changes\n\n")
        handle.write(f"- As of: {as_of_date}\n")
        handle.write(f"- Previous snapshot: {prior_path.name if prior_path else 'none'}\n")
        handle.write(f"- Current snapshot: {current_path.name}\n\n")
        handle.write(f"Additions: {len(additions)}\n")
        handle.write(f"Removals: {len(removals)}\n")
        handle.write(f"Rank changes: {len(rank_changes)}\n\n")

        if additions:
            handle.write("## Additions\n")
            for symbol in additions:
                handle.write(f"- {symbol} (rank {new_holdings.get(symbol)})\n")
            handle.write("\n")

        if removals:
            handle.write("## Removals\n")
            for symbol in removals:
                handle.write(f"- {symbol}\n")
            handle.write("\n")

        if rank_changes:
            handle.write("## Rank changes\n")
            for symbol, old_rank, new_rank in rank_changes:
                handle.write(f"- {symbol}: {old_rank} -> {new_rank}\n")
            handle.write("\n")


def write_changes_csv(output_path: Path, changes, old_holdings, new_holdings):
    additions, removals, rank_changes = changes
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["action", "symbol", "old_rank", "new_rank"])
        for symbol in additions:
            writer.writerow(["add", symbol, "", new_holdings.get(symbol)])
        for symbol in removals:
            writer.writerow(["remove", symbol, old_holdings.get(symbol), ""])
        for symbol, old_rank, new_rank in rank_changes:
            writer.writerow(["rank_change", symbol, old_rank, new_rank])


def find_latest_change(changes_dir: Path):
    if not changes_dir.exists():
        return None
    candidates = []
    for path in changes_dir.glob("changes_*.csv"):
        try:
            date_str = path.stem.replace("changes_", "")
            change_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            continue
        candidates.append((change_date, path))
    if not candidates:
        return None
    candidates.sort()
    return candidates[-1][1]


def main():
    parser = argparse.ArgumentParser(description="Daily final momentum portfolio generator")
    parser.add_argument("--prices-dir", type=Path, default=Path("nse500_data"))
    parser.add_argument("--benchmark", type=Path, default=Path("data/benchmarks/nifty100.csv"))
    parser.add_argument("--universe-file", type=Path, default=Path("data/static/nse500_universe.csv"))
    parser.add_argument("--output-root", type=Path, default=Path("experiments/final_portfolio"))
    parser.add_argument("--run-label", help="Override run folder label (default: timestamp)")
    parser.add_argument("--signals-output", type=Path, help="Override signals output path")
    parser.add_argument("--publish-signals", type=Path, default=Path("data/final_portfolio/final_top24_signals.csv"))
    parser.add_argument("--latest-output", type=Path, default=Path("data/final_portfolio/final_portfolio_24.csv"))
    parser.add_argument("--output-dir", type=Path, help="Override output folder for snapshots/reports")
    parser.add_argument("--report-output", type=Path, help="Override report output path")
    parser.add_argument("--initial-capital", type=float, default=1_000_000)
    parser.add_argument("--slippage", type=float, default=0.002)
    parser.add_argument("--lookback-months", type=int, default=6)
    parser.add_argument("--rebalance-weeks", type=int, default=1)
    parser.add_argument("--skip-days", type=int, default=0)
    parser.add_argument("--top-n", type=int, default=24)
    parser.add_argument("--vol-floor", type=float, default=0.05)
    parser.add_argument("--vol-power", type=float, default=1.0)
    parser.add_argument("--min-entry-score", type=float, default=0.0, help="Minimum momentum score for entry (default: 0.0 - no filtering)")
    parser.add_argument("--min-exit-score", type=float, default=0.0, help="Minimum momentum score to remain in position (default: 0.0 - no filtering)")
    parser.add_argument("--score-rebalance-mode", choices=["full", "incremental"], default="incremental", help="Position sizing mode when using score filtering (default: incremental)")
    parser.add_argument("--rebalance-weekday", default="thursday")
    parser.add_argument("--order-weekday", default="friday")
    parser.add_argument(
        "--with-data",
        action="store_true",
        help="Run data refresh steps (fetch NSE500 + benchmark) before building signals",
    )
    parser.add_argument(
        "--with-login",
        action="store_true",
        help="Run login before data refresh (implies --with-data)",
    )
    parser.add_argument("--today", help="Override today's date (YYYY-MM-DD)")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.rebalance_weekday.lower() not in WEEKDAYS:
        raise SystemExit(f"Invalid rebalance weekday: {args.rebalance_weekday}")
    if args.order_weekday.lower() not in WEEKDAYS:
        raise SystemExit(f"Invalid order weekday: {args.order_weekday}")

    if args.today:
        today = datetime.strptime(args.today, "%Y-%m-%d").date()
    else:
        today = date.today()

    run_label = args.run_label or datetime.now().strftime("%Y%m%d%H%M%S")
    run_dir = args.output_root / f"final_portfolio_{run_label}"
    signals_output = args.signals_output or (run_dir / "signals" / "final_top24_signals.csv")
    output_dir = args.output_dir or run_dir
    report_output = args.report_output or (run_dir / "report.html")

    run_dir.mkdir(parents=True, exist_ok=True)

    if args.with_login:
        args.with_data = True
        run_command([sys.executable, "scripts/login_and_save_token.py"], args.dry_run)
    if args.with_data:
        run_command([sys.executable, "scripts/fetch_nse500_history.py"], args.dry_run)
        run_command([sys.executable, "scripts/compute_benchmark.py"], args.dry_run)

    build_cmd = [
        sys.executable,
        "scripts/build_momentum_signals_flexible.py",
        "--prices-dir",
        str(args.prices_dir),
        "--output",
        str(signals_output),
        "--skip-days",
        str(args.skip_days),
        "--lookback-months",
        str(args.lookback_months),
        "--rebalance-weeks",
        str(args.rebalance_weeks),
        "--top-n",
        str(args.top_n),
        "--vol-floor",
        str(args.vol_floor),
        "--vol-power",
        str(args.vol_power),
        "--universe-file",
        str(args.universe_file),
    ]
    run_command(build_cmd, args.dry_run)

    if args.dry_run:
        print("[dry-run] skipped snapshot generation")
        return

    effective_signals_output = output_dir / "signals" / "final_top24_signals_completed.csv"
    effective_signals_output = filter_signals_to_completed_periods(signals_output, effective_signals_output, today)

    args.publish_signals.parent.mkdir(parents=True, exist_ok=True)
    args.publish_signals.write_text(effective_signals_output.read_text())

    signal_date_str, latest_rows = parse_latest_signals(effective_signals_output)
    signal_date = datetime.strptime(signal_date_str, "%Y-%m-%d").date()
    calendar_dates = load_trading_calendar_from_benchmark(args.benchmark)
    order_date = next_trading_day(signal_date, calendar_dates)
    as_of_date_str = order_date.isoformat()
    for row in latest_rows:
        row["_as_of_date"] = as_of_date_str

    snapshot_dir = output_dir / "snapshots"
    snapshot_path = snapshot_dir / f"portfolio_{as_of_date_str}.csv"
    write_snapshot(latest_rows, snapshot_path)
    write_snapshot(latest_rows, args.latest_output)
    print(f"Saved latest portfolio snapshot to {snapshot_path}")
    print(f"Updated latest holdings to {args.latest_output}")

    run_command(
        [
            sys.executable,
            "scripts/validate_signals.py",
            "--signals",
            str(effective_signals_output),
            "--top-n",
            str(args.top_n),
        ],
        args.dry_run,
    )

    backtest_dir = output_dir / "backtests" / "baseline"
    run_command(
        [
            sys.executable,
            "scripts/backtest_momentum.py",
            "--prices-dir",
            str(args.prices_dir),
            "--signals",
            str(effective_signals_output),
            "--benchmark",
            str(args.benchmark),
            "--output-dir",
            str(backtest_dir),
            "--initial-capital",
            str(args.initial_capital),
            "--top-n",
            str(args.top_n),
            "--slippage",
            str(args.slippage),
            "--scenario",
            "baseline",
            "--exit-buffer",
            "0",
            "--min-entry-score",
            str(args.min_entry_score),
            "--min-exit-score",
            str(args.min_exit_score),
            "--score-rebalance-mode",
            args.score_rebalance_mode,
        ],
        args.dry_run,
    )

    report_cmd = [
        sys.executable,
        "scripts/report_backtests.py",
        "--runs",
        str(backtest_dir),
        "--output",
        str(report_output),
    ]
    run_command(report_cmd, args.dry_run)
    print(f"Saved report to {report_output}")

    # Rich report generation is intentionally disabled for now; keep the backtest-style report
    # as the single source of truth for comparisons with Monte Carlo/backtests.

    latest_holdings = {row["symbol"]: int(row["rank"]) for row in latest_rows}
    prior_snapshot = find_previous_snapshot(snapshot_dir, snapshot_path)

    if prior_snapshot:
        prior_holdings = load_snapshot(prior_snapshot)
    else:
        prior_holdings = {}

    is_rebalance_day = today.weekday() == WEEKDAYS[args.rebalance_weekday.lower()]
    if is_rebalance_day:
        changes = compute_changes(prior_holdings, latest_holdings)
        changes_dir = output_dir / "rebalance"
        changes_csv = changes_dir / f"changes_{today.isoformat()}.csv"
        report_path = changes_dir / f"changes_{today.isoformat()}.md"
        write_changes_csv(changes_csv, changes, prior_holdings, latest_holdings)
        write_changes_report(
            report_path,
            changes,
            prior_snapshot,
            snapshot_path,
            today.isoformat(),
            latest_holdings,
        )
        print(f"Saved rebalance changes to {changes_csv}")
        print(f"Saved rebalance report to {report_path}")
    else:
        print("Not a rebalance day; changes report not generated.")

    is_order_day = today.weekday() == WEEKDAYS[args.order_weekday.lower()]
    if is_order_day:
        changes_dir = output_dir / "rebalance"
        latest_change = find_latest_change(changes_dir)
        if not latest_change:
            print("No rebalance changes found for order day.")
            return
        orders_dir = output_dir / "orders"
        orders_path = orders_dir / f"orders_{today.isoformat()}.csv"
        orders_dir.mkdir(parents=True, exist_ok=True)
        with latest_change.open(newline="") as handle:
            reader = csv.DictReader(handle)
            rows = list(reader)
        with orders_path.open("w", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["action", "symbol"])
            for row in rows:
                if row["action"] == "add":
                    writer.writerow(["BUY", row["symbol"]])
                elif row["action"] == "remove":
                    writer.writerow(["SELL", row["symbol"]])
        print(f"Saved order file to {orders_path}")


if __name__ == "__main__":
    main()
