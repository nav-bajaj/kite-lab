"""
Update all portfolios: fetch latest prices (optional), regenerate every
universe, and sync to the database.

Builds **all 7 production-tracked universes** so the dashboard's
default view (nse500) and every alternative universe see today's run
after this script exits:

  Legacy / NSE500-family (run_final_momentum_portfolio.py):
    - nse500
    - nifty100
    - nifty250

  v3 daily-pipeline portfolios (own scripts on _clean_engine):
    - om25_v3
    - tl25_v3
    - l6_v2
    - combo_defensive

Usage:
    python scripts/update_all_portfolios.py
    python scripts/update_all_portfolios.py --skip-fetch
    python scripts/update_all_portfolios.py --skip-corporate-actions
    python scripts/update_all_portfolios.py --shared-state-file /tmp/state.pkl

Daily cron invokes this with --skip-fetch --skip-corporate-actions --shared-state-file
since run_daily_pipeline.py has already done those steps and built the cache.
"""

import argparse
import os
import subprocess
import sys

LEGACY_UNIVERSES = ["nse500", "nifty100", "nifty250"]


def run_step(name, command):
    print(f"\n{'='*60}")
    print(f">>> {name}")
    print(f"{'='*60}")
    print("Command:", " ".join(str(c) for c in command))
    result = subprocess.run(command)
    if result.returncode != 0:
        print(f"FAILED: {name} (exit code {result.returncode})")
        return False
    print(f"OK: {name}")
    return True


def sync_to_database(full=False):
    """Run sync_to_database.py script directly (no HTTP auth needed)."""
    cmd = [sys.executable, "scripts/sync_to_database.py"]
    if full:
        cmd.append("--full")
    return run_step("Sync all universes to database", cmd)


def legacy_portfolio_step(universe):
    return (
        f"Generate {universe} portfolio (legacy L6)",
        [sys.executable, "scripts/run_final_momentum_portfolio.py",
         "--universe", universe],
    )


def v3_portfolio_steps(shared_state_file=None):
    """The 4 v3 portfolios that landed in May 2026.

    Each accepts --shared-state-file to skip its own panel loads (Phase 2).
    """
    cache_args = ["--shared-state-file", shared_state_file] if shared_state_file else []
    return [
        ("Build OM25 v3 portfolio", [
            sys.executable, "scripts/run_om25_v3_portfolio.py",
            "--prices-dir", "nse500_data",
            "--regime-index", "indices_data/NIFTY_100.csv",
            "--start", "2020-01-01",
        ] + cache_args),
        ("Build TL25 v3 portfolio", [
            sys.executable, "scripts/run_tl25_v3_portfolio.py",
            "--prices-dir", "nse500_data",
            "--start", "2020-01-01",
        ] + cache_args),
        ("Build L6 v2 portfolio", [
            sys.executable, "scripts/run_l6_v2_portfolio.py",
            "--prices-dir", "nse500_data",
            "--start", "2020-01-01",
        ] + cache_args),
        ("Build COMBO Defensive portfolio", [
            sys.executable, "scripts/run_combo_defensive_portfolio.py",
            "--prices-dir", "nse500_data",
            "--start", "2020-01-01",
        ] + cache_args),
    ]


def main():
    parser = argparse.ArgumentParser(description="Update all portfolios")
    parser.add_argument("--skip-fetch", action="store_true",
                        help="Skip fetching latest prices (daily cron passes this)")
    parser.add_argument("--skip-corporate-actions", action="store_true",
                        help="Skip apply_corporate_actions.py (daily cron passes this)")
    parser.add_argument("--shared-state-file", default=None,
                        help="Pipeline_core shared-state cache; passed through to v3 portfolios only")
    args = parser.parse_args()

    # Step 1: Fetch latest prices (non-fatal)
    fetch_ok = True
    if not args.skip_fetch:
        if not run_step("Fetch NSE 500 prices",
                        [sys.executable, "scripts/fetch_nse500_history.py"]):
            print("\nPrice fetch failed - continuing with existing data")
            fetch_ok = False

    # Step 2: Apply corporate actions (idempotent, skipped when daily cron
    # already did it)
    if not args.skip_corporate_actions:
        run_step("Apply corporate actions",
                 [sys.executable, "scripts/apply_corporate_actions.py"])

    # Step 3: Generate legacy nse500/nifty100/nifty250 portfolios. These are
    # the universes the dashboard defaults to viewing — if we skip them the
    # nse500 page shows stale trades + positions.
    portfolio_failures = []
    for universe in LEGACY_UNIVERSES:
        name, cmd = legacy_portfolio_step(universe)
        if not run_step(name, cmd):
            portfolio_failures.append(universe)

    # Step 4: Generate the 4 v3 portfolios (the daily pipeline's actual
    # production momentum stack). Shared-state cache used iff passed in.
    for name, cmd in v3_portfolio_steps(args.shared_state_file):
        if not run_step(name, cmd):
            portfolio_failures.append(name)

    # Step 5: Sync to database
    # Use full trade re-sync when corporate actions exist (ensures stale
    # trades are replaced).
    ca_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "corporate_actions.json")
    has_corporate_actions = os.path.exists(ca_file)
    sync_to_database(full=has_corporate_actions)

    # Summary
    total = len(LEGACY_UNIVERSES) + 4
    ok = total - len(portfolio_failures)
    print(f"\n{'='*60}")
    print(f"UPDATE COMPLETE: {ok}/{total} portfolios updated")
    if not fetch_ok:
        print("  (price fetch failed - used existing data)")
    if portfolio_failures:
        print(f"  FAILED: {', '.join(portfolio_failures)}")
    print(f"{'='*60}")

    return 1 if portfolio_failures else 0


if __name__ == "__main__":
    sys.exit(main())
