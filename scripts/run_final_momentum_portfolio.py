import argparse
import csv
import subprocess
import sys
from datetime import date, datetime
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


def write_snapshot(rows, snapshot_path: Path):
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    with snapshot_path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["date", "rank", "symbol", "score"])
        for row in rows:
            writer.writerow([row["date"], row["rank"], row["symbol"], row.get("score", "")])


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
    parser.add_argument("--universe-file", type=Path, default=Path("data/static/nse500_universe.csv"))
    parser.add_argument("--signals-output", type=Path, default=Path("data/static/final_top24_signals.csv"))
    parser.add_argument("--latest-output", type=Path, default=Path("data/static/final_portfolio_24.csv"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/daily/final_portfolio"))
    parser.add_argument("--lookback-months", type=int, default=6)
    parser.add_argument("--rebalance-weeks", type=int, default=1)
    parser.add_argument("--skip-days", type=int, default=0)
    parser.add_argument("--top-n", type=int, default=24)
    parser.add_argument("--vol-floor", type=float, default=0.2)
    parser.add_argument("--vol-power", type=float, default=1.0)
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
        str(args.signals_output),
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

    latest_date, latest_rows = parse_latest_signals(args.signals_output)
    snapshot_dir = args.output_dir / "snapshots"
    snapshot_path = snapshot_dir / f"portfolio_{latest_date}.csv"
    write_snapshot(latest_rows, snapshot_path)
    write_snapshot(latest_rows, args.latest_output)
    print(f"Saved latest portfolio snapshot to {snapshot_path}")
    print(f"Updated latest holdings to {args.latest_output}")

    latest_holdings = {row["symbol"]: int(row["rank"]) for row in latest_rows}
    prior_snapshot = find_previous_snapshot(snapshot_dir, snapshot_path)

    if prior_snapshot:
        prior_holdings = load_snapshot(prior_snapshot)
    else:
        prior_holdings = {}

    is_rebalance_day = today.weekday() == WEEKDAYS[args.rebalance_weekday.lower()]
    if is_rebalance_day:
        changes = compute_changes(prior_holdings, latest_holdings)
        changes_dir = args.output_dir / "rebalance"
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
        changes_dir = args.output_dir / "rebalance"
        latest_change = find_latest_change(changes_dir)
        if not latest_change:
            print("No rebalance changes found for order day.")
            return
        orders_dir = args.output_dir / "orders"
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
