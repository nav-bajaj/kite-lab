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
import math
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
    from app.services.positions_service import PositionsService

    if args.universe:
        universes = [args.universe]
        print(f"Syncing {args.universe} to database...")
        result = sync_all(args.universe)
        print_result(args.universe, result)
    else:
        universes = ["nse500", "nifty100", "nifty250"]
        print("Syncing all universes to database...")
        results = sync_all_universes()
        for universe, result in results.items():
            print_result(universe, result)

    # Also sync open positions from CSV
    print(f"\n{'='*50}")
    print("Syncing open positions...")
    print(f"{'='*50}")
    for universe in universes:
        try:
            pos_result = PositionsService.sync_from_csv(universe)
            if pos_result.success:
                print(f"  {universe}: {pos_result.synced_count} positions synced")
            else:
                print(f"  {universe}: {pos_result.message}")
        except Exception as e:
            print(f"  {universe}: ERROR - {e}")

    # Apply corporate action adjustments to open positions
    adjust_open_positions_for_corporate_actions()

    print("\nSync complete.")


def adjust_open_positions_for_corporate_actions():
    """
    Adjust avg_price in open_positions for any corporate actions.
    Uses threshold-based detection to identify unadjusted positions
    and applies the factor. Idempotent — skips already-adjusted positions.
    """
    actions_file = os.path.join(repo_root, "data", "corporate_actions.json")
    if not os.path.exists(actions_file):
        return

    with open(actions_file) as f:
        actions = json.load(f)

    if not actions:
        return

    from app.models.database import get_session_local
    from app.models.models import OpenPosition

    SessionLocal = get_session_local()
    db = SessionLocal()

    print(f"\n{'='*50}")
    print("Adjusting open positions for corporate actions...")
    print(f"{'='*50}")

    try:
        for action in actions:
            symbol = action["symbol"]
            factor = action["factor"]
            raw_pre_ex_close = action["raw_pre_ex_close"]
            threshold = raw_pre_ex_close * math.sqrt(factor)

            positions = db.query(OpenPosition).filter(
                OpenPosition.symbol == symbol
            ).all()

            if not positions:
                continue

            adjusted_count = 0
            for pos in positions:
                if pos.avg_price and float(pos.avg_price) > threshold:
                    pos.avg_price = round(float(pos.avg_price) * factor, 2)
                    adjusted_count += 1

            if adjusted_count > 0:
                db.commit()
                print(f"  {symbol}: Adjusted avg_price for {adjusted_count} position(s) (factor={factor})")
            else:
                print(f"  {symbol}: Already adjusted, skipping")
    except Exception as e:
        db.rollback()
        print(f"  ERROR: {e}")
    finally:
        db.close()


def print_result(universe, result):
    print(f"\n{'='*50}")
    print(f"Universe: {universe}")
    print(f"{'='*50}")

    for key in ["holdings", "equity_curve", "metrics", "trades", "trade_matches"]:
        if key in result:
            r = result[key]
            if "error" in r:
                print(f"  {key}: ERROR - {r['error']}")
            else:
                count = r.get("count", 0)
                suffix = ""
                if key == "trade_matches":
                    unmatched = r.get("unmatched_sell_shares", 0)
                    open_lots = r.get("open_lots_remaining", 0)
                    suffix = f" ({unmatched} unmatched sell shares, {open_lots} open lots)"
                print(f"  {key}: {count} records synced{suffix}")


if __name__ == "__main__":
    main()
