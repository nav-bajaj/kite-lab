"""
Live Portfolio Price Refresh

Fetches real-time quotes for portfolio stocks using Kite's quote API.
This is fast (single API call) and shows current prices during market hours.

Usage:
    python scripts/refresh_portfolio_live.py
    python scripts/refresh_portfolio_live.py --detailed  # Show full quote data

Prerequisites:
    - Daily pipeline must have run today (ensures portfolio is current)
    - Valid access token
"""

import argparse
import os
import sys
from datetime import datetime, date

import pandas as pd
from dotenv import load_dotenv
from kiteconnect import KiteConnect

PORTFOLIO_FILE = "data/final_portfolio/final_portfolio_24.csv"
PRICE_DATA_DIR = "nse500_data"


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


def check_pipeline_freshness():
    """Verify daily pipeline ran today."""
    if not os.path.exists(PORTFOLIO_FILE):
        return False, "Portfolio file not found"

    # Check portfolio file date
    df = pd.read_csv(PORTFOLIO_FILE)
    if df.empty:
        return False, "Portfolio file is empty"

    portfolio_date = pd.to_datetime(df["date"].iloc[0]).date()
    today = date.today()

    # Allow for weekend - if today is weekend, accept Friday's data
    days_old = (today - portfolio_date).days

    if days_old == 0:
        return True, f"Pipeline data is current ({portfolio_date})"
    elif days_old <= 3 and today.weekday() in [5, 6]:  # Weekend
        return True, f"Pipeline data from {portfolio_date} (weekend, acceptable)"
    elif days_old <= 3 and today.weekday() == 0:  # Monday
        return True, f"Pipeline data from {portfolio_date} (Monday, acceptable)"
    else:
        return False, f"Pipeline data is stale ({portfolio_date}, {days_old} days old). Run daily pipeline first."


def load_portfolio():
    """Load current portfolio symbols."""
    df = pd.read_csv(PORTFOLIO_FILE)
    return df["symbol"].tolist()


def get_previous_close(symbol):
    """Get previous day's close from local data."""
    csv_path = os.path.join(PRICE_DATA_DIR, f"{symbol}_day.csv")
    if not os.path.exists(csv_path):
        return None
    try:
        df = pd.read_csv(csv_path)
        if not df.empty:
            return df.iloc[-1]["close"]
    except Exception:
        pass
    return None


def display_quotes(quotes, symbols, detailed=False):
    """Display quote data in a formatted table."""
    print("\n" + "=" * 80)
    print(f"PORTFOLIO LIVE PRICES - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    if detailed:
        print(f"{'Symbol':<12} {'LTP':>10} {'Change':>10} {'%Chg':>8} {'Open':>10} {'High':>10} {'Low':>10} {'Volume':>12}")
        print("-" * 94)
    else:
        print(f"{'Symbol':<12} {'LTP':>10} {'Change':>10} {'%Chg':>8} {'Day Range':>22}")
        print("-" * 66)

    total_value = 0
    gainers = 0
    losers = 0

    for symbol in symbols:
        key = f"NSE:{symbol}"
        if key not in quotes:
            print(f"{symbol:<12} {'N/A':>10}")
            continue

        q = quotes[key]
        ltp = q.get("last_price", 0)
        ohlc = q.get("ohlc", {})
        open_price = ohlc.get("open", 0)
        high = ohlc.get("high", 0)
        low = ohlc.get("low", 0)
        prev_close = ohlc.get("close", 0) or get_previous_close(symbol) or ltp
        volume = q.get("volume", 0)

        change = ltp - prev_close if prev_close else 0
        pct_change = (change / prev_close * 100) if prev_close else 0

        if change > 0:
            gainers += 1
            change_str = f"+{change:.2f}"
            pct_str = f"+{pct_change:.2f}%"
        elif change < 0:
            losers += 1
            change_str = f"{change:.2f}"
            pct_str = f"{pct_change:.2f}%"
        else:
            change_str = f"{change:.2f}"
            pct_str = f"{pct_change:.2f}%"

        if detailed:
            print(f"{symbol:<12} {ltp:>10.2f} {change_str:>10} {pct_str:>8} {open_price:>10.2f} {high:>10.2f} {low:>10.2f} {volume:>12,}")
        else:
            day_range = f"{low:.2f} - {high:.2f}"
            print(f"{symbol:<12} {ltp:>10.2f} {change_str:>10} {pct_str:>8} {day_range:>22}")

        total_value += ltp

    print("-" * (94 if detailed else 66))
    print(f"\nSummary: {gainers} gainers, {losers} losers, {len(symbols) - gainers - losers} unchanged")


def main():
    parser = argparse.ArgumentParser(description="Fetch live portfolio prices")
    parser.add_argument(
        "--detailed", "-d",
        action="store_true",
        help="Show detailed quote data (OHLC, volume)"
    )
    parser.add_argument(
        "--skip-check",
        action="store_true",
        help="Skip pipeline freshness check"
    )

    args = parser.parse_args()

    # Check pipeline freshness
    if not args.skip_check:
        is_fresh, message = check_pipeline_freshness()
        if not is_fresh:
            print(f"Error: {message}")
            sys.exit(1)
        print(f"Pipeline check: {message}")

    # Load portfolio
    symbols = load_portfolio()
    print(f"Loaded {len(symbols)} portfolio stocks")

    # Initialize Kite
    kite = init_kite_client()
    print("Connected to Kite API")

    # Fetch quotes (single API call for all symbols)
    instrument_list = [f"NSE:{s}" for s in symbols]
    print(f"Fetching live quotes...")

    try:
        quotes = kite.quote(instrument_list)
        display_quotes(quotes, symbols, detailed=args.detailed)
    except Exception as e:
        print(f"Error fetching quotes: {e}")
        sys.exit(1)

    return 0


if __name__ == "__main__":
    sys.exit(main())
