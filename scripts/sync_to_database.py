"""
Sync CSV data to PostgreSQL database.

Runs as a standalone script (called by job_service) to import
holdings, equity curves, metrics, and trades from experiment
directories into the production database.

Usage:
    python scripts/sync_to_database.py                  # Sync all universes
    python scripts/sync_to_database.py --universe nse500  # Sync one universe
"""
import argparse
import sys
import os
import json

# Add the kite-api app to Python path
# In Docker: /app (PYTHONPATH already set)
# Locally: need to add kite-api/ to path
script_dir = os.path.dirname(os.path.abspath(__file__))
repo_root = os.path.dirname(script_dir)
kite_api_dir = os.path.join(repo_root, "kite-api")
if os.path.isdir(kite_api_dir):
    sys.path.insert(0, kite_api_dir)


def main():
    parser = argparse.ArgumentParser(description="Sync CSV data to database")
    parser.add_argument("--universe", type=str, default=None,
                        help="Universe to sync (nse500, nifty100, nifty250). Default: all")
    args = parser.parse_args()

    from app.services.sync_service import sync_all, sync_all_universes

    if args.universe:
        print(f"Syncing {args.universe} to database...")
        result = sync_all(args.universe)
        print_result(args.universe, result)
    else:
        print("Syncing all universes to database...")
        results = sync_all_universes()
        for universe, result in results.items():
            print_result(universe, result)

    print("\nSync complete.")


def print_result(universe, result):
    print(f"\n{'='*50}")
    print(f"Universe: {universe}")
    print(f"{'='*50}")

    for key in ["holdings", "equity_curve", "metrics", "trades"]:
        if key in result:
            r = result[key]
            if "error" in r:
                print(f"  {key}: ERROR - {r['error']}")
            else:
                count = r.get("count", 0)
                print(f"  {key}: {count} records synced")


if __name__ == "__main__":
    main()
