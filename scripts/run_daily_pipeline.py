import argparse
import atexit
import os
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor, as_completed


# Pre-fetch step: instruments cache (required for symbol resolution)
INSTRUMENTS_STEP = ("Cache instruments list", [sys.executable, "scripts/cache_instruments.py"])

# Steps that can run in parallel (data fetching)
PARALLEL_FETCH_STEPS = [
    ("Refresh NSE 500 data", [sys.executable, "scripts/fetch_nse500_history.py"]),
    ("Fetch indices data", [sys.executable, "scripts/fetch_indices_history.py"]),
    # Phase 4.5 — cross-asset series (USDINR / Gold / Crude via Kite Connect
    # continuous front-month futures). Incremental: only fetches new dates
    # since the last file timestamp.
    ("Fetch cross-asset data", [sys.executable, "scripts/fetch_cross_asset_history.py", "--incremental"]),
]

# Pre-portfolio sequential steps (depend on fetched data, run before shared
# state is built)
PRE_PORTFOLIO_STEPS = [
    ("Apply corporate actions", [sys.executable, "scripts/apply_corporate_actions.py"]),
    ("Update Nifty 100 benchmark", [sys.executable, "scripts/compute_benchmark.py"]),
    # NOTE: scripts/build_momentum_signals.py was removed from the daily pipeline
    # on 2026-05-15 (pipeline-improvements branch). Its output
    # data/momentum/top25_signals.csv had no downstream consumers in the
    # daily pipeline — only ad-hoc research tools (validate_signals,
    # compare_signals_baseline, backtest_momentum, run_rebalance_sensitivity)
    # read it. Run it standalone when those tools need fresh signals.
    # See tasks/pipeline_improvements/PLAN.md.
]


# Portfolio builds + DB sync are delegated to update_all_portfolios.py so the
# legacy nse500/nifty100/nifty250 portfolios refresh on every cron run too.
# Without this, the dashboard's default nse500 view stayed frozen between
# manual "Update Portfolios" clicks even though the cron itself was healthy.
def update_portfolios_step(shared_state_file):
    cmd = [
        sys.executable, "scripts/update_all_portfolios.py",
        "--skip-fetch",              # already fetched above
        "--skip-corporate-actions",  # already applied above
    ]
    if shared_state_file:
        cmd += ["--shared-state-file", str(shared_state_file)]
    return ("Build all portfolios + sync DB", cmd)


POST_PORTFOLIO_STEPS = [
    # Insight-engine freshness. sync_insights_panels appends the day's new EOD
    # rows (from nse500_data / indices_data, populated + corporate-action
    # adjusted earlier this run) onto the long-history panels the engine reads.
    # Append-only and idempotent, so it is safe this late in the run. The clear
    # step then drops the on-disk insight pkl caches so the next read rebuilds
    # from the freshened panels. To refresh a live API worker's in-memory cache
    # without a redeploy, POST /api/insights/cache/clear (admin) — see
    # tasks/insights_v2/RUNBOOK_admin_launch.md.
    ("Sync insight panels", [sys.executable, "scripts/sync_insights_panels.py"]),
    ("Clear insight caches", [
        sys.executable, "-c",
        "import sys; sys.path.insert(0, 'kite-api'); "
        "from app.insights.reading import clear_all_caches; clear_all_caches()",
    ]),
    ("Backup data to external location", [sys.executable, "scripts/sync_data_backup.py"]),
]


def run_command(name, command, dry_run=False, timings=None):
    """Run a single command and return (name, success, duration)."""
    print(f"\n>>> {name}")
    print("Command:", " ".join(command))
    if dry_run:
        print("[dry-run] skipped")
        if timings is not None:
            timings.append((name, 0.0, True))
        return name, True, 0

    start = time.time()
    result = subprocess.run(command)
    duration = time.time() - start

    if timings is not None:
        timings.append((name, duration, result.returncode == 0))

    if result.returncode != 0:
        print(f"Step '{name}' failed with code {result.returncode}")
        return name, False, duration
    return name, True, duration


def run_parallel_steps(steps, dry_run=False, timings=None):
    """Run multiple steps in parallel and wait for all to complete."""
    if dry_run:
        for name, cmd in steps:
            run_command(name, cmd, dry_run=True, timings=timings)
        return True

    print(f"\n{'='*60}")
    print(f"Running {len(steps)} data fetch steps in parallel...")
    print(f"{'='*60}")

    start = time.time()
    results = {}

    with ThreadPoolExecutor(max_workers=len(steps)) as executor:
        futures = {
            executor.submit(run_command, name, cmd, dry_run, None): name
            for name, cmd in steps
        }

        for future in as_completed(futures):
            name, success, duration = future.result()
            results[name] = (success, duration)
            status = "completed" if success else "FAILED"
            print(f"\n[{status}] {name} ({duration:.1f}s)")
            if timings is not None:
                timings.append((name, duration, success))

    total_duration = time.time() - start
    all_success = all(success for success, _ in results.values())

    print(f"\n{'='*60}")
    print(f"Parallel fetch completed in {total_duration:.1f}s")
    for name, (success, duration) in results.items():
        status = "OK" if success else "FAILED"
        print(f"  - {name}: {status} ({duration:.1f}s)")
    print(f"{'='*60}")

    return all_success


def print_timing_summary(timings, total_time):
    """End-of-run table of per-step durations."""
    print(f"\n{'='*60}")
    print(f"Pipeline timing summary")
    print(f"{'='*60}")
    width = max((len(name) for name, _, _ in timings), default=20)
    for name, duration, success in timings:
        status = "OK  " if success else "FAIL"
        print(f"  {status}  {name:<{width}}  {duration:6.1f}s")
    print(f"  {'-'*(width+16)}")
    print(f"        {'TOTAL':<{width}}  {total_time:6.1f}s")
    print(f"{'='*60}")


def main():
    parser = argparse.ArgumentParser(description="Run the daily momentum data pipeline")
    parser.add_argument("--with-login", action="store_true", help="Run login script before data updates")
    parser.add_argument("--headless", action="store_true", help="Use automated login (no browser needed)")
    parser.add_argument("--dry-run", action="store_true", help="Print commands without executing")
    parser.add_argument("--sequential", action="store_true", help="Disable parallel execution (for debugging)")
    parser.add_argument("--no-shared-state", action="store_true",
                        help="Disable the Phase 2 shared-state cache (portfolios load panels independently)")
    parser.add_argument("--fetch-only", action="store_true",
                        help="Stop after login + data fetch + corporate actions "
                             "+ benchmark; skip the shared-state cache, the "
                             "all-7-portfolio build, and the backup. Used by the "
                             "16:00 EOD producer, which only needs today's "
                             "adjusted closes (it re-runs each strategy itself), "
                             "so a second full portfolio build every signal day "
                             "is pure waste.")
    args = parser.parse_args()

    start_time = time.time()
    timings = []

    if args.with_login:
        login_cmd = [sys.executable, "scripts/login_and_save_token.py"]
        if args.headless:
            login_cmd.append("--headless")
        name, success, _ = run_command("Login to Kite", login_cmd,
                                        dry_run=args.dry_run, timings=timings)
        if not success:
            sys.exit(1)

    # Token-expiry preflight — fail fast (<1s) if the access token is
    # missing or expired, before any data-fetch step runs. Cheap kite.profile()
    # call. If --with-login just ran, this also confirms the new token works.
    preflight_cmd = [sys.executable, "scripts/preflight_token.py"]
    name, success, _ = run_command("Preflight: Kite token check", preflight_cmd,
                                    dry_run=args.dry_run, timings=timings)
    if not success:
        print("\nToken preflight failed. Re-run with --with-login.")
        sys.exit(1)

    # Cache instruments (needed for symbol resolution in stock fetches)
    name, success, _ = run_command(*INSTRUMENTS_STEP, dry_run=args.dry_run,
                                    timings=timings)
    if not success:
        print("\nFailed to cache instruments. Stock fetches will fail without it.")
        sys.exit(1)

    # Run data fetch steps
    if args.sequential:
        for name, cmd in PARALLEL_FETCH_STEPS:
            _, success, _ = run_command(name, cmd, dry_run=args.dry_run,
                                         timings=timings)
            if not success:
                sys.exit(1)
    else:
        if not run_parallel_steps(PARALLEL_FETCH_STEPS, dry_run=args.dry_run,
                                   timings=timings):
            print("\nParallel fetch failed. Exiting.")
            sys.exit(1)

    # Pre-portfolio sequential steps (corporate actions, benchmark)
    for name, cmd in PRE_PORTFOLIO_STEPS:
        _, success, _ = run_command(name, cmd, dry_run=args.dry_run,
                                     timings=timings)
        if not success:
            sys.exit(1)

    # The EOD producer only needs fresh adjusted closes + benchmark + indices
    # (all produced above); it rebuilds each strategy itself. Stop here to avoid
    # a second full all-7-portfolio build every signal day.
    if args.fetch_only:
        total_time = time.time() - start_time
        print(f"\nFetch-only pipeline completed in {total_time:.1f}s "
              f"(skipped shared-state cache, portfolio builds, backup).")
        print_timing_summary(timings, total_time)
        return

    # Phase 2: build shared-state cache once, pass to each portfolio.
    shared_state_file = None
    if not args.no_shared_state:
        ts_tag = time.strftime("%Y%m%d_%H%M%S")
        shared_state_file = os.path.join(
            tempfile.gettempdir(), f"pipeline_state_{ts_tag}.pkl",
        )
        # Cleanup on exit so stray cache files don't accumulate in /tmp.
        atexit.register(lambda p=shared_state_file: _cleanup_cache(p))

        prep_cmd = [
            sys.executable, "scripts/pipeline_core.py",
            "--prices-dir", "nse500_data",
            "--benchmark", "data/benchmarks/nifty100.csv",
            "--regime-index", "indices_data/NIFTY_100.csv",
            "--output", shared_state_file,
        ]
        _, success, _ = run_command(
            "Prepare shared-state cache", prep_cmd,
            dry_run=args.dry_run, timings=timings,
        )
        if not success:
            print("\nShared-state cache build failed. "
                  "Re-run with --no-shared-state to fall back to per-portfolio loads.")
            sys.exit(1)

    # All 7 portfolios + DB sync — single subprocess call to keep this
    # orchestrator and the manual "Update Portfolios" button in lock-step.
    name, cmd = update_portfolios_step(shared_state_file)
    _, success, _ = run_command(name, cmd, dry_run=args.dry_run,
                                 timings=timings)
    if not success:
        sys.exit(1)

    # Post-portfolio: external-dir backup.
    for name, cmd in POST_PORTFOLIO_STEPS:
        _, success, _ = run_command(name, cmd, dry_run=args.dry_run,
                                     timings=timings)
        if not success:
            sys.exit(1)

    total_time = time.time() - start_time
    print(f"\nDaily pipeline completed successfully in {total_time:.1f}s")
    print_timing_summary(timings, total_time)


def _cleanup_cache(path):
    try:
        if os.path.exists(path):
            os.remove(path)
    except OSError:
        pass


if __name__ == "__main__":
    main()
