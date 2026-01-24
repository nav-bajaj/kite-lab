#!/usr/bin/env python3
"""
Test stock data accuracy by comparing CSV against fresh Zerodha API call

Verifies that stock price data in nse500_data/ matches fresh data fetched
from the Zerodha API. Useful for validating individual stocks in the portfolio.
"""

import pandas as pd
from pathlib import Path
import sys
import datetime as dt

# Add project root to path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

# Also add scripts directory
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.append(str(SCRIPTS))

from data_pipeline.price_client import PriceClient
from history_utils import init_kite_client


def load_nse500_universe():
    """Load NSE 500 universe from static file"""
    universe_path = ROOT / "data" / "static" / "nse500_universe.csv"
    if not universe_path.exists():
        raise FileNotFoundError(f"NSE 500 universe file not found: {universe_path}")

    df = pd.read_csv(universe_path)
    # Assuming column is "Symbol" - adjust if different
    if "Symbol" in df.columns:
        symbols = df["Symbol"].str.strip().str.upper().tolist()
    elif "symbol" in df.columns:
        symbols = df["symbol"].str.strip().str.upper().tolist()
    else:
        # Try first column
        symbols = df.iloc[:, 0].str.strip().str.upper().tolist()

    return set(symbols)


def test_stock_accuracy(symbol: str, days: int = 10):
    """
    Compare last N days of stock data against fresh API call

    Args:
        symbol: Stock symbol (e.g., 'TCS', 'INFY')
        days: Number of recent days to verify (default: 10)

    Returns:
        bool: True if all tests passed
    """
    symbol = symbol.upper().strip()

    print(f"Testing stock data accuracy for {symbol} (last {days} days)")
    print("=" * 80)

    # Validate symbol is in NSE 500
    try:
        nse500_symbols = load_nse500_universe()
        if symbol not in nse500_symbols:
            print(f"⚠ WARNING: {symbol} is not in the NSE 500 universe")
            print(f"Continuing anyway, but file may not exist...")
            print()
    except Exception as e:
        print(f"⚠ Could not load NSE 500 universe: {e}")
        print("Continuing anyway...")
        print()

    # Load stock data from CSV
    csv_path = ROOT / "nse500_data" / f"{symbol}_day.csv"
    if not csv_path.exists():
        print(f"✗ Stock data file not found: {csv_path}")
        print()
        print("Possible reasons:")
        print("  1. Symbol is not in NSE 500 universe")
        print("  2. Data has not been fetched yet (run: python scripts/fetch_nse500_history.py)")
        print("  3. Symbol name is incorrect")
        return False

    df = pd.read_csv(csv_path, parse_dates=["date"])
    print(f"✓ Loaded CSV file: {len(df)} rows")

    # Get last N days from CSV
    csv_data = df.tail(days).copy()
    print(f"✓ Extracted last {len(csv_data)} days from CSV")

    if len(csv_data) < days:
        print(f"⚠ WARNING: CSV only has {len(csv_data)} days, requested {days}")

    # Fetch fresh data from Zerodha API
    print("\n" + "=" * 80)
    print("FETCHING FRESH DATA FROM ZERODHA API")
    print("=" * 80)

    try:
        kite = init_kite_client()
        client = PriceClient(kite)

        # Get date range for fetching
        start_date = csv_data["date"].min()
        end_date = csv_data["date"].max() + pd.Timedelta(days=1)  # Add 1 day for safety

        print(f"Fetching {symbol} data from {start_date.date()} to {end_date.date()}...")

        api_data = client.fetch_history(
            symbol=symbol,
            start=start_date,
            end=end_date,
            interval="day",
            preferred_exchange="NSE"
        )

        if api_data.empty:
            raise ValueError("No data returned from API")

        print(f"✓ Fetched {len(api_data)} rows from API")

    except Exception as e:
        print(f"\n✗ Failed to fetch data from Zerodha API: {e}")
        print("\nPlease ensure:")
        print("  1. access_token.txt exists and is valid")
        print("  2. Run 'python scripts/login_and_save_token.py' if token expired")
        print("  3. Symbol name is correct (check instruments_full.csv)")
        sys.exit(1)

    # Compare the data
    print("\n" + "=" * 80)
    print("COMPARISON RESULTS")
    print("=" * 80)

    # Merge on date for comparison
    csv_data["date"] = pd.to_datetime(csv_data["date"]).dt.normalize()
    api_data["date"] = pd.to_datetime(api_data["date"])

    # Convert timezone-aware dates to naive (if present)
    if api_data["date"].dt.tz is not None:
        api_data["date"] = api_data["date"].dt.tz_localize(None)

    api_data["date"] = api_data["date"].dt.normalize()

    comparison = csv_data.merge(
        api_data[["date", "close"]],
        on="date",
        how="left",
        suffixes=("_csv", "_api")
    )

    # Check for missing dates
    missing_in_api = comparison[comparison["close_api"].isna()]
    if not missing_in_api.empty:
        print(f"\n⚠ WARNING: {len(missing_in_api)} dates in CSV not found in API data:")
        for _, row in missing_in_api.iterrows():
            print(f"  {row['date'].date()}: CSV has {row['close_csv']:.2f}, API has no data")
        print()

    # Compare prices where both exist
    comparison = comparison[comparison["close_api"].notna()].copy()

    # Define tolerance
    # For stocks, tolerance should be very tight (0.01 rupees = 1 paisa)
    TOLERANCE = 0.01

    comparison["diff"] = comparison["close_csv"] - comparison["close_api"]
    comparison["diff_pct"] = (comparison["diff"] / comparison["close_api"]) * 100
    comparison["match"] = comparison["diff"].abs() <= TOLERANCE

    all_tests_passed = True

    for idx, row in comparison.iterrows():
        date_str = row["date"].strftime('%Y-%m-%d')

        if row["match"]:
            print(f"\n{date_str}:")
            print(f"  ✓ CSV:  {row['close_csv']:.2f}")
            print(f"  ✓ API:  {row['close_api']:.2f}")
            print(f"  ✓ Diff: {row['diff']:.2f} ({row['diff_pct']:.4f}%)")
        else:
            print(f"\n{date_str}:")
            print(f"  ✗ MISMATCH DETECTED")
            print(f"    CSV:  {row['close_csv']:.2f}")
            print(f"    API:  {row['close_api']:.2f}")
            print(f"    Diff: {row['diff']:.2f} ({row['diff_pct']:.4f}%)")
            all_tests_passed = False

    # Summary statistics
    print("\n" + "=" * 80)
    print("SUMMARY STATISTICS")
    print("=" * 80)
    print(f"Symbol: {symbol}")
    print(f"Total dates compared: {len(comparison)}")
    print(f"Matching prices: {comparison['match'].sum()}")
    print(f"Mismatches: {(~comparison['match']).sum()}")

    if len(comparison) > 0:
        print(f"Max absolute difference: {comparison['diff'].abs().max():.2f}")
        print(f"Max percentage difference: {comparison['diff_pct'].abs().max():.4f}%")
        print(f"Average absolute difference: {comparison['diff'].abs().mean():.4f}")

    print("\n" + "=" * 80)
    if all_tests_passed and missing_in_api.empty:
        print(f"✅ ALL TESTS PASSED - {symbol} data is accurate!")
    elif all_tests_passed and not missing_in_api.empty:
        print(f"⚠ PARTIAL PASS - All prices match but some dates missing from API")
    else:
        print(f"❌ TESTS FAILED - {symbol} data has discrepancies!")
        print(f"\nRecommendation: Re-fetch {symbol} data:")
        print(f"  python scripts/update_prices.py --symbols {symbol} --daily-dir nse500_data")
    print("=" * 80)

    return all_tests_passed and missing_in_api.empty


def main():
    """Run stock data accuracy test"""
    import argparse

    parser = argparse.ArgumentParser(
        description="Test stock data accuracy against Zerodha API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test TCS for last 10 days
  python tests/test_stock_data_accuracy.py --symbol TCS

  # Test INFY for last 30 days
  python tests/test_stock_data_accuracy.py --symbol INFY --days 30

  # Test multiple stocks
  python tests/test_stock_data_accuracy.py --symbol TCS
  python tests/test_stock_data_accuracy.py --symbol WIPRO
  python tests/test_stock_data_accuracy.py --symbol ITC
        """
    )
    parser.add_argument(
        "--symbol",
        "-s",
        type=str,
        required=True,
        help="Stock symbol (e.g., TCS, INFY, RELIANCE)"
    )
    parser.add_argument(
        "--days",
        "-d",
        type=int,
        default=10,
        help="Number of recent days to verify (default: 10)"
    )
    args = parser.parse_args()

    success = test_stock_accuracy(args.symbol, args.days)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
