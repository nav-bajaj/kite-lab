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
                        help="Universe to sync (nse500, nifty100, nifty250, om25_v3, tl25_v3, l6_v2, combo_defensive). Default: all")
    parser.add_argument("--full", action="store_true",
                        help="Full trade re-sync (delete all trades and reinsert from CSV)")
    parser.add_argument("--skip-validation", action="store_true",
                        help="Skip pre-sync CSV validation (not recommended)")
    parser.add_argument("--validate-only", action="store_true",
                        help="Run pre-sync validation and exit without writing to DB")
    args = parser.parse_args()

    # Pre-sync validation: catch malformed/incomplete portfolio CSVs before
    # they touch the production database. Scoped to the four daily-pipeline
    # portfolios (om25_v3, tl25_v3, l6_v2, combo_defensive); the legacy
    # NSE 500 / Nifty 100 / Nifty 250 outputs use a different metrics
    # schema and are skipped by the validator.
    if not args.skip_validation:
        sys.path.insert(0, os.path.join(repo_root, "scripts"))
        from sync_validation import (
            validate_universes, format_report, RUN_DIR_GLOBS,
        )
        targets = (
            [args.universe] if args.universe in RUN_DIR_GLOBS
            else list(RUN_DIR_GLOBS.keys())
        )
        print(f"{'='*50}")
        print(f"Pre-sync validation ({len(targets)} universes)...")
        print(f"{'='*50}")
        reports = validate_universes(targets)
        any_fail = False
        for u in targets:
            rep = reports[u]
            print(format_report(rep))
            if not rep.ok:
                any_fail = True
        if any_fail:
            print("\nValidation FAILED. Aborting sync to protect production DB.")
            print("Re-run with --skip-validation only after manual review.")
            sys.exit(2)
        print("All validated universes passed.\n")
        if args.validate_only:
            print("--validate-only set; exiting before DB writes.")
            return

    from app.services.sync_service import sync_all, sync_all_universes
    from app.services.positions_service import PositionsService

    if args.full:
        print("Full trade re-sync enabled: all trades will be replaced from CSV")

    if args.universe:
        universes = [args.universe]
        print(f"Syncing {args.universe} to database...")
        result = sync_all(args.universe, full_trades=args.full)
        print_result(args.universe, result)
    else:
        universes = ["nse500", "nifty100", "nifty250", "om25_v3", "tl25_v3", "l6_v2", "combo_defensive"]
        print("Syncing all universes to database...")
        results = sync_all_universes(full_trades=args.full)
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
    Adjust prices in open_positions, trades, and trade_matches for corporate actions.
    Uses threshold-based detection to identify unadjusted records and applies the
    factor. Idempotent — skips already-adjusted records.
    """
    actions_file = os.path.join(repo_root, "data", "corporate_actions.json")
    if not os.path.exists(actions_file):
        print("\n  corporate_actions.json not found, skipping adjustments")
        return

    with open(actions_file) as f:
        actions = json.load(f)

    if not actions:
        return

    from app.models.database import get_session_local
    from app.models.models import OpenPosition, Trade, TradeMatch

    SessionLocal = get_session_local()
    db = SessionLocal()

    print(f"\n{'='*50}")
    print("Adjusting DB records for corporate actions...")
    print(f"{'='*50}")

    try:
        for action in actions:
            symbol = action["symbol"]
            factor = action["factor"]
            raw_pre_ex_close = action["raw_pre_ex_close"]
            threshold = raw_pre_ex_close * math.sqrt(factor)

            # 1. Adjust open_positions.avg_price
            positions = db.query(OpenPosition).filter(
                OpenPosition.symbol == symbol
            ).all()
            pos_count = 0
            for pos in positions:
                if pos.avg_price and float(pos.avg_price) > threshold:
                    pos.avg_price = round(float(pos.avg_price) * factor, 2)
                    pos_count += 1

            # 2. Adjust trades.price for BUY trades (entry prices)
            buy_trades = db.query(Trade).filter(
                Trade.symbol == symbol,
                Trade.side == "BUY",
                Trade.price > threshold,
            ).all()
            trade_count = 0
            for trade in buy_trades:
                trade.price = round(float(trade.price) * factor, 6)
                trade.notional = round(float(trade.shares) * float(trade.price), 4)
                if trade.slippage:
                    trade.slippage = round(float(trade.slippage) * factor, 6)
                trade_count += 1

            # 3. Adjust trade_matches.entry_price and recalculate P&L
            matches = db.query(TradeMatch).filter(
                TradeMatch.symbol == symbol,
                TradeMatch.entry_price > threshold,
            ).all()
            match_count = 0
            for match in matches:
                new_entry = round(float(match.entry_price) * factor, 6)
                exit_price = float(match.exit_price)
                shares = float(match.shares_matched)
                match.entry_price = new_entry
                match.realized_pnl = round((exit_price - new_entry) * shares, 4)
                if new_entry > 0:
                    match.realized_pnl_pct = round(exit_price / new_entry - 1, 6)
                match_count += 1

            if pos_count + trade_count + match_count > 0:
                db.commit()
                print(f"  {symbol}: Adjusted {pos_count} position(s), "
                      f"{trade_count} trade(s), {match_count} match(es) (factor={factor})")
            else:
                print(f"  {symbol}: All records already adjusted, skipping")
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
