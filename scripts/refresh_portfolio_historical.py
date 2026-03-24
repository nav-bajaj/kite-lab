"""
Historical Portfolio Price Refresh

Updates CSV price data files for portfolio stocks only.
Much faster than full pipeline (~8s vs ~60s) for intraday updates.

Usage:
    python scripts/refresh_portfolio_historical.py
    python scripts/refresh_portfolio_historical.py --universe nifty100
    python scripts/refresh_portfolio_historical.py --days 3  # Fetch last 3 days

Prerequisites:
    - Daily pipeline must have run today (ensures portfolio is current)
    - Valid access token
"""

import argparse
import os
import sys
import time
from datetime import datetime, date, timedelta

import pandas as pd
from dotenv import load_dotenv
from kiteconnect import KiteConnect

# Add scripts directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import find_token
from universe_config import get_universe_config, list_universes

INDIA_TZ = "Asia/Kolkata"


def load_credentials():
    """Load API credentials."""
    load_dotenv()
    api_key = os.getenv("API_KEY") or os.getenv("KITE_API_KEY")
    if not api_key:
        raise RuntimeError("Missing API_KEY in environment.")

    token_paths = ["access_token.txt", "data/access_token.txt"]
    access_token = ""
    for path in token_paths:
        if os.path.exists(path):
            with open(path) as f:
                access_token = f.read().strip()
            if access_token:
                break
    if not access_token:
        raise RuntimeError("Missing access_token.txt")

    return api_key, access_token


def init_kite_client():
    """Initialize KiteConnect client."""
    api_key, access_token = load_credentials()
    kite = KiteConnect(api_key=api_key)
    kite.set_access_token(access_token)
    return kite


def to_local_naive(date_series):
    """Convert date series to local naive timestamps."""
    dates = pd.to_datetime(date_series, errors="coerce")
    tz = getattr(dates.dt, "tz", None)
    if tz is not None:
        dates = dates.dt.tz_convert(INDIA_TZ).dt.tz_localize(None)
    return dates


def check_pipeline_freshness(config: dict):
    """Verify daily pipeline ran today."""
    portfolio_file = config["portfolio_file"]
    if not portfolio_file.exists():
        return False, "Portfolio file not found"

    df = pd.read_csv(portfolio_file)
    if df.empty:
        return False, "Portfolio file is empty"

    portfolio_date = pd.to_datetime(df["date"].iloc[0]).date()
    today = date.today()

    days_old = (today - portfolio_date).days

    if days_old == 0:
        return True, f"Pipeline data is current ({portfolio_date})"
    elif days_old <= 3 and today.weekday() in [5, 6]:  # Weekend
        return True, f"Pipeline data from {portfolio_date} (weekend, acceptable)"
    elif days_old <= 3 and today.weekday() == 0:  # Monday
        return True, f"Pipeline data from {portfolio_date} (Monday, acceptable)"
    else:
        return False, f"Pipeline data is stale ({portfolio_date}, {days_old} days old). Run daily pipeline first."


def load_portfolio(config: dict):
    """Load current portfolio symbols."""
    df = pd.read_csv(config["portfolio_file"])
    return df["symbol"].tolist()


def fetch_symbol_data(kite, symbol, start_date, end_date):
    """Fetch historical data for a single symbol."""
    try:
        token = find_token(symbol, exchange="NSE")
    except ValueError:
        try:
            token = find_token(symbol, exchange="BSE")
        except ValueError:
            return None, f"Symbol not found"

    try:
        # Add 1 day to end_date for finalized values
        fetch_end = end_date + timedelta(days=1)

        candles = kite.historical_data(
            instrument_token=token,
            from_date=start_date,
            to_date=fetch_end,
            interval="day",
            continuous=False,
            oi=False,
        )

        if not candles:
            return None, "No data returned"

        df = pd.DataFrame(candles)
        df["date"] = to_local_naive(df["date"])
        return df, None

    except Exception as e:
        return None, str(e)


def update_csv_file(symbol, new_data, config: dict):
    """Update CSV file with new data, merging with existing."""
    csv_path = config["price_dir"] / f"{symbol}_day.csv"

    if csv_path.exists():
        existing_df = pd.read_csv(csv_path)
        existing_df["date"] = to_local_naive(existing_df["date"])

        # Merge: keep newer values for duplicates
        combined = pd.concat([existing_df, new_data], ignore_index=True)
        combined = combined.sort_values("date").drop_duplicates(subset=["date"], keep="last")
    else:
        combined = new_data.sort_values("date")

    combined.to_csv(csv_path, index=False)
    return len(combined)


def main():
    parser = argparse.ArgumentParser(description="Refresh historical data for portfolio stocks")
    parser.add_argument(
        "--universe", "-u",
        choices=list_universes(),
        default="nse500",
        help="Universe to use (default: nse500)"
    )
    parser.add_argument(
        "--days", "-d",
        type=int,
        default=5,
        help="Number of days to fetch (default: 5)"
    )
    parser.add_argument(
        "--skip-check",
        action="store_true",
        help="Skip pipeline freshness check"
    )
    parser.add_argument(
        "--throttle",
        type=float,
        default=0.34,
        help="Seconds between API calls (default: 0.34)"
    )

    args = parser.parse_args()

    # Get universe config
    config = get_universe_config(args.universe)

    print("=" * 60)
    print(f"PORTFOLIO HISTORICAL REFRESH - {config['name']}")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Check pipeline freshness
    if not args.skip_check:
        is_fresh, message = check_pipeline_freshness(config)
        if not is_fresh:
            print(f"\nError: {message}")
            sys.exit(1)
        print(f"Pipeline check: {message}")

    # Load portfolio
    symbols = load_portfolio(config)
    print(f"Loaded {len(symbols)} portfolio stocks from {config['name']}")

    # Initialize Kite
    kite = init_kite_client()
    print("Connected to Kite API")

    # Calculate date range
    end_date = date.today()
    start_date = end_date - timedelta(days=args.days)
    print(f"\nFetching data from {start_date} to {end_date}...")

    # Fetch and update each symbol
    successes = 0
    failures = []
    start_time = time.time()

    for i, symbol in enumerate(symbols, 1):
        df, error = fetch_symbol_data(kite, symbol, start_date, end_date)

        if error:
            print(f"  [{i}/{len(symbols)}] {symbol}: FAILED - {error}")
            failures.append(symbol)
        else:
            rows = update_csv_file(symbol, df, config)
            new_rows = len(df)
            print(f"  [{i}/{len(symbols)}] {symbol}: OK (+{new_rows} rows, {rows} total)")
            successes += 1

        # Throttle between requests
        if i < len(symbols):
            time.sleep(args.throttle)

    elapsed = time.time() - start_time

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"  Succeeded: {successes}")
    print(f"  Failed:    {len(failures)}")
    print(f"  Time:      {elapsed:.1f}s")

    if failures:
        print(f"\n  Failed symbols: {', '.join(failures)}")

    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
