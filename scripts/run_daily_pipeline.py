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


def portfolio_steps(shared_state_file):
    """Build the four portfolio commands, appending --shared-state-file to each.

    Phase 2: each portfolio script accepts --shared-state-file <path> to skip
    its own price/benchmark/regime panel loads and read the pre-built cache
    instead. Saves ~5-8s per portfolio × 4 ≈ 20-30s total wall-clock per run.
    """
    cache_args = ["--shared-state-file", str(shared_state_file)]
    return [
        # OM25 v3 production run — locked-in May 2026 OOS retune stack.
        ("Build OM25 v3 portfolio", [
            sys.executable, "scripts/run_om25_v3_portfolio.py",
            "--prices-dir", "nse500_data",
            "--regime-index", "indices_data/NIFTY_100.csv",
            "--start", "2020-01-01",
        ] + cache_args),
        # TL25 v3 production run — locked-in May 2026 OOS retune stack.
        ("Build TL25 v3 portfolio", [
            sys.executable, "scripts/run_tl25_v3_portfolio.py",
            "--prices-dir", "nse500_data",
            "--start", "2020-01-01",
        ] + cache_args),
        # L6 v2 — same L6 momentum config on the new _momentum_engine.
        ("Build L6 v2 portfolio", [
            sys.executable, "scripts/run_l6_v2_portfolio.py",
            "--prices-dir", "nse500_data",
            "--start", "2020-01-01",
        ] + cache_args),
        # COMBO Defensive — 50-50 L6 + OM25 with regime overlay.
        ("Build COMBO Defensive portfolio", [
            sys.executable, "scripts/run_combo_defensive_portfolio.py",
            "--prices-dir", "nse500_data",
            "--start", "2020-01-01",
        ] + cache_args),
    ]


POST_PORTFOLIO_STEPS = [
    ("Sync data to database", [sys.executable, "scripts/sync_to_database.py"]),
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

    # Portfolio builds — each picks up the shared state cache (if built).
    portfolio_cmds = portfolio_steps(shared_state_file) if shared_state_file \
                     else _portfolio_steps_without_cache()
    for name, cmd in portfolio_cmds:
        _, success, _ = run_command(name, cmd, dry_run=args.dry_run,
                                     timings=timings)
        if not success:
            sys.exit(1)

    # Post-portfolio: sync to DB, backup to external dir.
    for name, cmd in POST_PORTFOLIO_STEPS:
        _, success, _ = run_command(name, cmd, dry_run=args.dry_run,
                                     timings=timings)
        if not success:
            sys.exit(1)

    total_time = time.time() - start_time
    print(f"\nDaily pipeline completed successfully in {total_time:.1f}s")
    print_timing_summary(timings, total_time)


def _portfolio_steps_without_cache():
    """Fallback when --no-shared-state is set: portfolios load panels independently."""
    return [
        ("Build OM25 v3 portfolio", [
            sys.executable, "scripts/run_om25_v3_portfolio.py",
            "--prices-dir", "nse500_data",
            "--regime-index", "indices_data/NIFTY_100.csv",
            "--start", "2020-01-01",
        ]),
        ("Build TL25 v3 portfolio", [
            sys.executable, "scripts/run_tl25_v3_portfolio.py",
            "--prices-dir", "nse500_data",
            "--start", "2020-01-01",
        ]),
        ("Build L6 v2 portfolio", [
            sys.executable, "scripts/run_l6_v2_portfolio.py",
            "--prices-dir", "nse500_data",
            "--start", "2020-01-01",
        ]),
        ("Build COMBO Defensive portfolio", [
            sys.executable, "scripts/run_combo_defensive_portfolio.py",
            "--prices-dir", "nse500_data",
            "--start", "2020-01-01",
        ]),
    ]


def _cleanup_cache(path):
    try:
        if os.path.exists(path):
            os.remove(path)
    except OSError:
        pass


if __name__ == "__main__":
    main()
