"""
Update all portfolios: fetch latest prices, regenerate all three universes,
and sync results to the database.

Usage:
    python scripts/update_all_portfolios.py
    python scripts/update_all_portfolios.py --skip-fetch   # Skip price fetch
"""

import argparse
import os
import subprocess
import sys
import urllib.request
import json

UNIVERSES = ["nse500", "nifty100", "nifty250"]


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


def sync_to_database():
    """Call the API sync endpoint to load CSVs into PostgreSQL."""
    port = os.environ.get("PORT", "8000")
    url = f"http://localhost:{port}/api/sync/all"
    print(f"\n{'='*60}")
    print(">>> Sync all universes to database")
    print(f"{'='*60}")
    try:
        req = urllib.request.Request(url, method="POST")
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = json.loads(resp.read().decode())
            for universe, result in data.items():
                holdings = result.get("holdings", {}).get("count", 0)
                equity = result.get("equity_curve", {}).get("count", 0)
                print(f"  {universe}: {holdings} holdings, {equity} new equity points")
        print("OK: Database sync")
        return True
    except Exception as e:
        print(f"WARNING: Database sync failed: {e}")
        print("  (This is OK if running outside the API server)")
        return True  # Non-fatal


def main():
    parser = argparse.ArgumentParser(description="Update all portfolios")
    parser.add_argument("--skip-fetch", action="store_true",
                        help="Skip fetching latest prices")
    args = parser.parse_args()

    # Step 1: Fetch latest prices (non-fatal if it fails)
    fetch_ok = True
    if not args.skip_fetch:
        if not run_step("Fetch NSE 500 prices",
                        [sys.executable, "scripts/fetch_nse500_history.py"]):
            print("\nPrice fetch failed - continuing with existing data")
            fetch_ok = False

    # Step 2: Generate portfolio for each universe (these are critical)
    portfolio_failures = []
    for universe in UNIVERSES:
        if not run_step(f"Generate {universe} portfolio",
                        [sys.executable, "scripts/run_final_momentum_portfolio.py",
                         "--universe", universe]):
            portfolio_failures.append(universe)

    # Step 3: Sync to database
    sync_to_database()

    # Summary
    total_portfolios = len(UNIVERSES)
    ok_portfolios = total_portfolios - len(portfolio_failures)
    print(f"\n{'='*60}")
    print(f"UPDATE COMPLETE: {ok_portfolios}/{total_portfolios} portfolios updated")
    if not fetch_ok:
        print("  (price fetch failed - used existing data)")
    if portfolio_failures:
        print(f"  FAILED: {', '.join(portfolio_failures)}")
    print(f"{'='*60}")

    # Only fail if portfolio generation failed
    return 1 if portfolio_failures else 0


if __name__ == "__main__":
    sys.exit(main())
