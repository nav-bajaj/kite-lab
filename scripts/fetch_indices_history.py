"""
Fetch historical daily data for tracked indices (Nifty, sectoral, global, commodity).

This script:
1. Reads the list of tracked indices from data/static/tracked_indices.csv
2. Fetches daily historical data from 2020-01-01 to today
3. Supports incremental updates (only fetches new data)
4. Saves data to indices_data/ directory
5. Uses instrument tokens directly (no symbol resolution needed)

Usage:
    python scripts/fetch_indices_history.py

Requirements:
    - Valid access token (run scripts/login_and_save_token.py first)
    - data/static/tracked_indices.csv must exist
"""

import os
import time
import datetime as dt

import pandas as pd
from dotenv import load_dotenv
from kiteconnect import KiteConnect

INDIA_TZ = "Asia/Kolkata"
INDICES_CSV = "data/static/tracked_indices.csv"
OUTPUT_DIR = "indices_data"


def load_credentials():
    """Load API credentials from .env and access_token.txt."""
    load_dotenv()
    api_key = os.getenv("API_KEY") or os.getenv("KITE_API_KEY")
    if not api_key:
        raise RuntimeError("Missing API_KEY in environment. Populate .env before running this script.")

    token_paths = ["access_token.txt", "data/access_token.txt"]
    access_token = ""
    for path in token_paths:
        if os.path.exists(path):
            with open(path) as f:
                access_token = f.read().strip()
            if access_token:
                break
    if not access_token:
        raise RuntimeError("access_token.txt is empty. Re-run scripts/login_and_save_token.py to refresh the token.")

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


def load_tracked_indices(csv_path):
    """
    Load tracked indices from CSV.

    Returns:
        list of dict with keys: instrument_token, tradingsymbol, name, exchange, category
    """
    if not os.path.exists(csv_path):
        raise FileNotFoundError(f"Indices configuration file not found: {csv_path}")

    df = pd.read_csv(csv_path)
    required_cols = ["instrument_token", "tradingsymbol", "name", "exchange", "category"]
    missing = [col for col in required_cols if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns in {csv_path}: {missing}")

    indices = []
    for _, row in df.iterrows():
        indices.append({
            "instrument_token": int(row["instrument_token"]),
            "tradingsymbol": str(row["tradingsymbol"]).strip(),
            "name": str(row["name"]).strip(),
            "exchange": str(row["exchange"]).strip(),
            "category": str(row["category"]).strip(),
        })

    return indices


def fetch_history(kite, instrument_token, start, end, interval="day"):
    """
    Fetch historical candles in safe-sized chunks.

    Args:
        kite: KiteConnect instance
        instrument_token: Instrument token (integer)
        start: Start date (pd.Timestamp or datetime)
        end: End date (pd.Timestamp or datetime)
        interval: Candle interval (default: "day")

    Returns:
        pd.DataFrame with columns: date, open, high, low, close, volume
    """
    start_ts = pd.Timestamp(start)
    end_ts = pd.Timestamp(end)

    # CRITICAL FIX: Zerodha API returns preliminary values when to_date equals
    # the target date. Adding +1 day ensures we get finalized values.
    # This is especially critical for indices but also affects stocks.
    # See: docs/zerodha_api_index_data_issue.md
    fetch_end = end_ts + pd.Timedelta(days=1)

    # For daily data, use large chunks (1900 days max per API call)
    chunk_days = 1900 if interval == "day" else 30
    frames = []
    cur = start_ts

    while cur < fetch_end:
        chunk_end = min(cur + pd.Timedelta(days=chunk_days), fetch_end)
        candles = kite.historical_data(
            instrument_token=instrument_token,
            from_date=cur.to_pydatetime(),
            to_date=chunk_end.to_pydatetime(),
            interval=interval,
            continuous=False,
            oi=False,
        )
        if candles:
            frames.append(pd.DataFrame(candles))
        cur = chunk_end

    if not frames:
        return pd.DataFrame()

    df = pd.concat(frames, ignore_index=True)
    df["date"] = to_local_naive(df["date"])
    return df.sort_values("date").drop_duplicates(subset=["date"])


def fetch_with_retries(fetch_callable, index_name, max_retries=3, throttle_seconds=0.2):
    """
    Fetch data with exponential backoff on rate limiting errors.

    Args:
        fetch_callable: Function to call for fetching data
        index_name: Name of index (for logging)
        max_retries: Maximum retry attempts
        throttle_seconds: Base throttle duration

    Returns:
        Result of fetch_callable
    """
    attempt = 0
    while True:
        try:
            return fetch_callable()
        except Exception as exc:
            message = str(exc)
            rate_limited = "Too many requests" in message or "429" in message
            if rate_limited and attempt < max_retries - 1:
                wait = max(throttle_seconds, 0.5) * (2 ** attempt)
                print(f"{index_name}: Rate limited, retrying in {wait:.1f}s ...")
                time.sleep(wait)
                attempt += 1
                continue
            raise


def download_indices(kite, indices, start_date, end_date, output_dir, throttle_seconds=0.2, max_retries=3):
    """
    Download historical data for all tracked indices.

    Args:
        kite: KiteConnect instance
        indices: List of index dictionaries (from load_tracked_indices)
        start_date: Start date for fetching (pd.Timestamp)
        end_date: End date for fetching (pd.Timestamp)
        output_dir: Directory to save CSV files
        throttle_seconds: Delay between API calls
        max_retries: Maximum retry attempts on rate limiting

    Returns:
        List of failed index names
    """
    os.makedirs(output_dir, exist_ok=True)
    successes = 0
    failures = []

    print(f"\nFetching daily data for {len(indices)} indices from {start_date.date()} to {end_date.date()} ...")

    for idx in indices:
        tradingsymbol = idx["tradingsymbol"]
        instrument_token = idx["instrument_token"]
        name = idx["name"]
        category = idx["category"]

        # Use tradingsymbol as filename (clean for filesystem)
        safe_name = tradingsymbol.replace(" ", "_").replace("/", "_")
        output_path = os.path.join(output_dir, f"{safe_name}.csv")

        # Check for existing data and determine fetch start date
        # CRITICAL FIX: Use rolling window instead of incremental updates
        # to capture revised/finalized values for recent data
        LOOKBACK_DAYS = 30
        existing_df = None
        fetch_start = start_date

        if os.path.exists(output_path):
            try:
                existing_df = pd.read_csv(output_path)
                if "date" in existing_df.columns and not existing_df.empty:
                    existing_df["date"] = to_local_naive(existing_df["date"])
                    last_ts = existing_df["date"].max()
                    if pd.notnull(last_ts):
                        # Re-fetch last N days to capture finalized values
                        # See: docs/zerodha_api_index_data_issue.md
                        fetch_start = max(start_date, last_ts - pd.Timedelta(days=LOOKBACK_DAYS))
            except Exception as read_exc:
                print(f"{tradingsymbol}: Warning - could not read existing data ({read_exc}). Re-fetching all.")
                existing_df = None
                fetch_start = start_date

        # Skip if already up to date
        if fetch_start >= end_date:
            print(f"{tradingsymbol} ({category}): Up to date, skipping")
            continue

        # Fetch new data
        try:
            df = fetch_with_retries(
                lambda: fetch_history(
                    kite,
                    instrument_token,
                    fetch_start,
                    end_date,
                    interval="day",
                ),
                tradingsymbol,
                max_retries,
                throttle_seconds,
            )

            if df.empty:
                print(f"{tradingsymbol} ({category}): No new data returned, skipping")
                continue

            # Merge with existing data if present
            if existing_df is not None and not existing_df.empty:
                df = pd.concat([existing_df, df], ignore_index=True)

            # Clean and sort - keep newer (more finalized) values for duplicates
            df["date"] = to_local_naive(df["date"])
            df = df.sort_values("date").drop_duplicates(subset=["date"], keep="last")

            # Save to CSV
            df.to_csv(output_path, index=False)
            print(f"{tradingsymbol} ({category}): Saved {len(df)} rows to {output_path}")
            successes += 1

            # Throttle to respect API rate limits
            if throttle_seconds:
                time.sleep(throttle_seconds)

        except Exception as exc:
            print(f"{tradingsymbol} ({category}): Failed - {exc}")
            failures.append(tradingsymbol)

    print(f"\nCompleted. Succeeded: {successes}, Failed: {len(failures)}")
    if failures:
        print("Indices with errors:", ", ".join(failures))

    return failures


def main():
    """Main entry point."""
    print("=" * 70)
    print("Fetching historical data for tracked indices")
    print("=" * 70)

    # Initialize
    kite = init_kite_client()
    indices = load_tracked_indices(INDICES_CSV)

    print(f"Loaded {len(indices)} indices from {INDICES_CSV}")

    # Group by category for display
    by_category = {}
    for idx in indices:
        cat = idx["category"]
        by_category.setdefault(cat, []).append(idx["tradingsymbol"])

    print("\nIndices by category:")
    for cat, symbols in sorted(by_category.items()):
        print(f"  {cat}: {len(symbols)} indices")

    # Fetch data from 2020-01-01 to today
    today = dt.date.today()
    start_date = pd.Timestamp("2020-01-01")
    end_date = pd.Timestamp(today.isoformat())

    failures = download_indices(
        kite,
        indices,
        start_date,
        end_date,
        OUTPUT_DIR,
        throttle_seconds=0.2,
        max_retries=3,
    )

    if failures:
        print(f"\n⚠️  {len(failures)} indices failed to fetch. Retry or check logs.")
        return 1

    print(f"\n✓ All indices fetched successfully. Data saved to {OUTPUT_DIR}/")
    return 0


if __name__ == "__main__":
    exit(main())
