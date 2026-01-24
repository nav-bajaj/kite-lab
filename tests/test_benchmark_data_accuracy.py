#!/usr/bin/env python3
"""
Test benchmark data accuracy by comparing CSV against fresh Zerodha API call

Verifies that the last 5 days of closing prices in nifty100.csv match
fresh data fetched from the Zerodha API.
"""

import pandas as pd
from pathlib import Path
import sys
import datetime as dt

# Add project root to path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

# Also add scripts directory for history_utils
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.append(str(SCRIPTS))

from data_pipeline.price_client import PriceClient
from history_utils import init_kite_client


def test_benchmark_accuracy(days: int = 5):
    """
    Compare last N days of benchmark data against fresh API call

    Args:
        days: Number of recent days to verify (default: 5)
    """
    print(f"Testing benchmark data accuracy for last {days} days")
    print("=" * 80)

    # Load existing benchmark file
    benchmark_path = ROOT / "data" / "benchmarks" / "nifty100.csv"
    if not benchmark_path.exists():
        raise FileNotFoundError(f"Benchmark file not found: {benchmark_path}")

    df = pd.read_csv(benchmark_path, parse_dates=["date"])
    print(f"✓ Loaded benchmark file: {len(df)} rows")

    # Get last N days from CSV
    csv_data = df.tail(days).copy()
    print(f"✓ Extracted last {len(csv_data)} days from CSV")

    # Fetch fresh data from Zerodha API
    print("\n" + "=" * 80)
    print("FETCHING FRESH DATA FROM ZERODHA API")
    print("=" * 80)

    try:
        kite = init_kite_client()
        client = PriceClient(kite)

        # Get date range for fetching
        start_date = csv_data["date"].min()
        end_date = csv_data["date"].max() + pd.Timedelta(days=1)  # Add 1 day to include last date

        print(f"Fetching NIFTY 100 data from {start_date.date()} to {end_date.date()}...")

        api_data = client.fetch_history(
            symbol="NIFTY 100",
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
        sys.exit(1)

    # Compare the data
    print("\n" + "=" * 80)
    print("COMPARISON RESULTS")
    print("=" * 80)

    # Merge on date for comparison
    # Normalize dates and handle timezone conversion
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

    # Define tolerance (allow small floating point differences)
    TOLERANCE = 0.01  # 1 paisa tolerance for price differences

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
    print(f"Total dates compared: {len(comparison)}")
    print(f"Matching prices: {comparison['match'].sum()}")
    print(f"Mismatches: {(~comparison['match']).sum()}")
    print(f"Max absolute difference: {comparison['diff'].abs().max():.2f}")
    print(f"Max percentage difference: {comparison['diff_pct'].abs().max():.4f}%")
    print(f"Average absolute difference: {comparison['diff'].abs().mean():.4f}")

    print("\n" + "=" * 80)
    if all_tests_passed and missing_in_api.empty:
        print("✅ ALL TESTS PASSED - Benchmark data is accurate!")
    elif all_tests_passed and not missing_in_api.empty:
        print("⚠ PARTIAL PASS - All prices match but some dates missing from API")
    else:
        print("❌ TESTS FAILED - Benchmark data has discrepancies!")
        print("\nRecommendation: Run 'python scripts/compute_benchmark.py' to refresh benchmark data")
    print("=" * 80)

    return all_tests_passed and missing_in_api.empty


def main():
    """Run benchmark accuracy test"""
    import argparse

    parser = argparse.ArgumentParser(description="Test benchmark data accuracy against Zerodha API")
    parser.add_argument(
        "--days",
        type=int,
        default=5,
        help="Number of recent days to verify (default: 5)"
    )
    args = parser.parse_args()

    success = test_benchmark_accuracy(days=args.days)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
