"""
Data Integrity Test Script

This script verifies that locally cached price data matches the Zerodha API.
It randomly samples stocks and dates, fetches fresh data from the API,
and compares against local CSV files.

Usage:
    python scripts/test_data_integrity.py
    python scripts/test_data_integrity.py --samples 5 --dates-per-stock 3
    python scripts/test_data_integrity.py --symbol INFY --date 2025-01-15

Requirements:
    - Valid access token (run scripts/login_and_save_token.py first)
    - Local price data in nse500_data/
"""

import argparse
import os
import random
import sys
from datetime import datetime, timedelta

import pandas as pd
from dotenv import load_dotenv
from kiteconnect import KiteConnect

# Add scripts directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import find_token

INDIA_TZ = "Asia/Kolkata"
UNIVERSE_CSV = "data/static/nse500_universe.csv"
PRICE_DATA_DIR = "nse500_data"


def load_credentials():
    """Load API credentials from .env and access_token.txt."""
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
        raise RuntimeError("Missing access_token.txt. Run scripts/login_and_save_token.py first.")

    return api_key, access_token


def init_kite_client():
    """Initialize KiteConnect client with credentials."""
    api_key, access_token = load_credentials()
    kite = KiteConnect(api_key=api_key)
    kite.set_access_token(access_token)
    return kite


def to_local_naive(date_series):
    """Convert date series to local naive timestamps (Asia/Kolkata)."""
    dates = pd.to_datetime(date_series, errors="coerce")
    tz = getattr(dates.dt, "tz", None)
    if tz is not None:
        dates = dates.dt.tz_convert(INDIA_TZ).dt.tz_localize(None)
    return dates


def load_symbols():
    """Load list of symbols from universe CSV."""
    if not os.path.exists(UNIVERSE_CSV):
        raise FileNotFoundError(f"Universe file not found: {UNIVERSE_CSV}")
    df = pd.read_csv(UNIVERSE_CSV)
    return df["Symbol"].dropna().str.strip().tolist()


def load_local_data(symbol):
    """Load local CSV data for a symbol."""
    csv_path = os.path.join(PRICE_DATA_DIR, f"{symbol}_day.csv")
    if not os.path.exists(csv_path):
        return None
    df = pd.read_csv(csv_path)
    df["date"] = pd.to_datetime(df["date"]).dt.normalize()
    return df


def fetch_api_data(kite, symbol, date):
    """Fetch single day's data from API."""
    try:
        token = find_token(symbol, exchange="NSE")
    except ValueError:
        try:
            token = find_token(symbol, exchange="BSE")
        except ValueError:
            return None

    # Fetch a small window around the target date
    start_date = date - timedelta(days=1)
    end_date = date + timedelta(days=2)

    try:
        candles = kite.historical_data(
            instrument_token=token,
            from_date=start_date,
            to_date=end_date,
            interval="day",
            continuous=False,
            oi=False,
        )
        if not candles:
            return None

        df = pd.DataFrame(candles)
        df["date"] = to_local_naive(df["date"]).dt.normalize()
        return df

    except Exception as e:
        print(f"  API error for {symbol}: {e}")
        return None


def compare_data(local_row, api_row, symbol, date):
    """Compare local and API data for a single date."""
    discrepancies = []

    columns = ["open", "high", "low", "close", "volume"]
    tolerances = {"open": 0.01, "high": 0.01, "low": 0.01, "close": 0.01, "volume": 1}

    for col in columns:
        local_val = local_row[col].values[0] if col in local_row.columns else None
        api_val = api_row[col].values[0] if col in api_row.columns else None

        if local_val is None or api_val is None:
            continue

        # Use percentage tolerance for prices, absolute for volume
        if col == "volume":
            diff = abs(local_val - api_val)
            if diff > tolerances[col]:
                discrepancies.append(f"{col}: local={local_val}, api={api_val}, diff={diff}")
        else:
            if api_val != 0:
                pct_diff = abs(local_val - api_val) / api_val * 100
                if pct_diff > tolerances[col]:
                    discrepancies.append(f"{col}: local={local_val:.2f}, api={api_val:.2f}, diff={pct_diff:.3f}%")

    return discrepancies


def run_integrity_test(kite, symbols, num_samples=4, dates_per_stock=2, specific_date=None):
    """Run integrity test on random sample of stocks and dates."""
    results = {"passed": 0, "failed": 0, "skipped": 0, "errors": []}

    # Sample random stocks
    if len(symbols) > num_samples:
        test_symbols = random.sample(symbols, num_samples)
    else:
        test_symbols = symbols

    print(f"\nTesting {len(test_symbols)} stocks with {dates_per_stock} date(s) each...")
    print("=" * 70)

    for symbol in test_symbols:
        print(f"\n[{symbol}]")

        # Load local data
        local_df = load_local_data(symbol)
        if local_df is None:
            print(f"  SKIP: No local data found")
            results["skipped"] += 1
            continue

        # Get available dates (exclude last 15 days which may have preliminary values)
        available_dates = local_df["date"].unique()
        cutoff = datetime.now() - timedelta(days=15)
        valid_dates = [d for d in available_dates if pd.Timestamp(d) < cutoff]

        if len(valid_dates) < dates_per_stock:
            print(f"  SKIP: Not enough historical dates")
            results["skipped"] += 1
            continue

        # Select test dates
        if specific_date:
            test_dates = [pd.Timestamp(specific_date)]
        else:
            test_dates = random.sample(list(valid_dates), min(dates_per_stock, len(valid_dates)))

        for test_date in test_dates:
            test_date = pd.Timestamp(test_date).normalize()
            date_str = test_date.strftime("%Y-%m-%d")

            # Get local row for this date
            local_row = local_df[local_df["date"] == test_date]
            if local_row.empty:
                print(f"  {date_str}: SKIP (no local data)")
                continue

            # Fetch API data
            api_df = fetch_api_data(kite, symbol, test_date.to_pydatetime())
            if api_df is None:
                print(f"  {date_str}: SKIP (API fetch failed)")
                continue

            api_row = api_df[api_df["date"] == test_date]
            if api_row.empty:
                print(f"  {date_str}: SKIP (date not in API response)")
                continue

            # Compare
            discrepancies = compare_data(local_row, api_row, symbol, test_date)

            if discrepancies:
                print(f"  {date_str}: FAIL")
                for d in discrepancies:
                    print(f"    - {d}")
                results["failed"] += 1
                results["errors"].append({
                    "symbol": symbol,
                    "date": date_str,
                    "discrepancies": discrepancies
                })
            else:
                print(f"  {date_str}: PASS")
                results["passed"] += 1

    return results


def main():
    parser = argparse.ArgumentParser(description="Test data integrity against Zerodha API")
    parser.add_argument(
        "--samples", "-n",
        type=int,
        default=4,
        help="Number of random stocks to test (default: 4)"
    )
    parser.add_argument(
        "--dates-per-stock", "-d",
        type=int,
        default=2,
        help="Number of random dates to test per stock (default: 2)"
    )
    parser.add_argument(
        "--symbol", "-s",
        type=str,
        help="Test a specific symbol instead of random sampling"
    )
    parser.add_argument(
        "--date",
        type=str,
        help="Test a specific date (YYYY-MM-DD) instead of random sampling"
    )
    parser.add_argument(
        "--seed",
        type=int,
        help="Random seed for reproducible testing"
    )

    args = parser.parse_args()

    if args.seed:
        random.seed(args.seed)

    print("=" * 70)
    print("DATA INTEGRITY TEST")
    print("=" * 70)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Initialize
    kite = init_kite_client()
    print("Connected to Kite API")

    # Load symbols
    if args.symbol:
        symbols = [args.symbol.upper()]
        print(f"Testing specific symbol: {args.symbol}")
    else:
        symbols = load_symbols()
        print(f"Loaded {len(symbols)} symbols from universe")

    # Run test
    results = run_integrity_test(
        kite,
        symbols,
        num_samples=args.samples if not args.symbol else 1,
        dates_per_stock=args.dates_per_stock,
        specific_date=args.date
    )

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"  Passed:  {results['passed']}")
    print(f"  Failed:  {results['failed']}")
    print(f"  Skipped: {results['skipped']}")

    if results["errors"]:
        print(f"\nFailed tests:")
        for err in results["errors"]:
            print(f"  - {err['symbol']} @ {err['date']}")

    total_tests = results["passed"] + results["failed"]
    if total_tests > 0:
        pass_rate = results["passed"] / total_tests * 100
        print(f"\nPass rate: {pass_rate:.1f}%")

        if pass_rate == 100:
            print("\n✓ All data integrity checks passed!")
            return 0
        else:
            print(f"\n✗ {results['failed']} integrity check(s) failed")
            return 1
    else:
        print("\nNo tests were executed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
