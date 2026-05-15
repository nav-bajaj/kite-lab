import argparse
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed


# Pre-fetch step: instruments cache (required for symbol resolution)
INSTRUMENTS_STEP = ("Cache instruments list", [sys.executable, "scripts/cache_instruments.py"])

# Steps that can run in parallel (data fetching)
PARALLEL_FETCH_STEPS = [
    ("Refresh NSE 500 data", [sys.executable, "scripts/fetch_nse500_history.py"]),
    ("Fetch indices data", [sys.executable, "scripts/fetch_indices_history.py"]),
]

# Steps that must run sequentially (depend on fetched data)
SEQUENTIAL_STEPS = [
    ("Apply corporate actions", [sys.executable, "scripts/apply_corporate_actions.py"]),
    ("Update Nifty 100 benchmark", [sys.executable, "scripts/compute_benchmark.py"]),
    # NOTE: scripts/build_momentum_signals.py was removed from the daily pipeline
    # on 2026-05-15 (pipeline-improvements branch). Its output
    # data/momentum/top25_signals.csv had no downstream consumers in the
    # daily pipeline — only ad-hoc research tools (validate_signals,
    # compare_signals_baseline, backtest_momentum, run_rebalance_sensitivity)
    # read it. Run it standalone when those tools need fresh signals.
    # See tasks/pipeline_improvements/PLAN.md.
    # OM25 v3 production run — locked-in May 2026 OOS retune stack.
    # Uses live Kite data (nse500_data) and live NIFTY 100 index for regime.
    # See tasks/oos_retune_2026/RESULTS.md for the strategy spec.
    ("Build OM25 v3 portfolio", [
        sys.executable, "scripts/run_om25_v3_portfolio.py",
        "--prices-dir", "nse500_data",
        "--regime-index", "indices_data/NIFTY_100.csv",
        "--start", "2020-01-01",
    ]),
    # TL25 v3 production run — locked-in May 2026 OOS retune stack.
    # Pure trend-following on NSE 500; complements OM25 v3 (different signal).
    # See tasks/oos_retune_2026/RESULTS.md for the strategy spec.
    ("Build TL25 v3 portfolio", [
        sys.executable, "scripts/run_tl25_v3_portfolio.py",
        "--prices-dir", "nse500_data",
        "--start", "2020-01-01",
    ]),
    # L6 v2 parallel run — same L6 momentum config but via the new
    # _momentum_engine. Runs alongside the legacy L6 path during the
    # parallel-run verification window (5-7 trading days). After clean
    # diffs, dashboard cuts over to v2 and the legacy path is retired.
    # See tasks/MM-tuning/PRODUCTIONIZATION.md.
    ("Build L6 v2 portfolio (parallel-run)", [
        sys.executable, "scripts/run_l6_v2_portfolio.py",
        "--prices-dir", "nse500_data",
        "--start", "2020-01-01",
    ]),
    # COMBO Defensive — new product (50-50 L6 + OM25, regime-overlaid).
    # Biweekly Fri → Mon cadence. Operates on same nse500_data.
    # See tasks/MM-tuning/DD_REDUCTION_RESEARCH.md for the full spec.
    ("Build COMBO Defensive portfolio", [
        sys.executable, "scripts/run_combo_defensive_portfolio.py",
        "--prices-dir", "nse500_data",
        "--start", "2020-01-01",
    ]),
    ("Sync data to database", [sys.executable, "scripts/sync_to_database.py"]),
    ("Backup data to external location", [sys.executable, "scripts/sync_data_backup.py"]),
]


def run_command(name, command, dry_run=False):
    """Run a single command and return (name, success, duration)."""
    print(f"\n>>> {name}")
    print("Command:", " ".join(command))
    if dry_run:
        print("[dry-run] skipped")
        return name, True, 0

    start = time.time()
    result = subprocess.run(command)
    duration = time.time() - start

    if result.returncode != 0:
        print(f"Step '{name}' failed with code {result.returncode}")
        return name, False, duration
    return name, True, duration


def run_parallel_steps(steps, dry_run=False):
    """Run multiple steps in parallel and wait for all to complete."""
    if dry_run:
        for name, cmd in steps:
            run_command(name, cmd, dry_run=True)
        return True

    print(f"\n{'='*60}")
    print(f"Running {len(steps)} data fetch steps in parallel...")
    print(f"{'='*60}")

    start = time.time()
    results = {}

    with ThreadPoolExecutor(max_workers=len(steps)) as executor:
        futures = {
            executor.submit(run_command, name, cmd, dry_run): name
            for name, cmd in steps
        }

        for future in as_completed(futures):
            name, success, duration = future.result()
            results[name] = (success, duration)
            status = "completed" if success else "FAILED"
            print(f"\n[{status}] {name} ({duration:.1f}s)")

    total_duration = time.time() - start
    all_success = all(success for success, _ in results.values())

    print(f"\n{'='*60}")
    print(f"Parallel fetch completed in {total_duration:.1f}s")
    for name, (success, duration) in results.items():
        status = "OK" if success else "FAILED"
        print(f"  - {name}: {status} ({duration:.1f}s)")
    print(f"{'='*60}")

    return all_success


def main():
    parser = argparse.ArgumentParser(description="Run the daily momentum data pipeline")
    parser.add_argument("--with-login", action="store_true", help="Run login script before data updates")
    parser.add_argument("--headless", action="store_true", help="Use automated login (no browser needed)")
    parser.add_argument("--dry-run", action="store_true", help="Print commands without executing")
    parser.add_argument("--sequential", action="store_true", help="Disable parallel execution (for debugging)")
    args = parser.parse_args()

    start_time = time.time()

    if args.with_login:
        login_cmd = [sys.executable, "scripts/login_and_save_token.py"]
        if args.headless:
            login_cmd.append("--headless")
        name, success, _ = run_command("Login to Kite", login_cmd, dry_run=args.dry_run)
        if not success:
            sys.exit(1)

    # Token-expiry preflight — fail fast (<1s) if the access token is
    # missing or expired, before any data-fetch step runs. Cheap kite.profile()
    # call. If --with-login just ran, this also confirms the new token works.
    preflight_cmd = [sys.executable, "scripts/preflight_token.py"]
    name, success, _ = run_command("Preflight: Kite token check", preflight_cmd,
                                    dry_run=args.dry_run)
    if not success:
        print("\nToken preflight failed. Re-run with --with-login.")
        sys.exit(1)

    # Cache instruments (needed for symbol resolution in stock fetches)
    name, success, _ = run_command(*INSTRUMENTS_STEP, dry_run=args.dry_run)
    if not success:
        print("\nFailed to cache instruments. Stock fetches will fail without it.")
        sys.exit(1)

    # Run data fetch steps
    if args.sequential:
        # Sequential mode (original behavior)
        for name, cmd in PARALLEL_FETCH_STEPS:
            _, success, _ = run_command(name, cmd, dry_run=args.dry_run)
            if not success:
                sys.exit(1)
    else:
        # Parallel mode (default)
        if not run_parallel_steps(PARALLEL_FETCH_STEPS, dry_run=args.dry_run):
            print("\nParallel fetch failed. Exiting.")
            sys.exit(1)

    # Run sequential steps
    for name, cmd in SEQUENTIAL_STEPS:
        _, success, _ = run_command(name, cmd, dry_run=args.dry_run)
        if not success:
            sys.exit(1)

    total_time = time.time() - start_time
    print(f"\nDaily pipeline completed successfully in {total_time:.1f}s")


if __name__ == "__main__":
    main()
