"""
Live Portfolio Price Refresh

Fetches real-time quotes for portfolio stocks using Kite's quote API.
This is fast (single API call) and shows current prices during market hours.

Usage:
    python scripts/refresh_portfolio_live.py
    python scripts/refresh_portfolio_live.py --universe nifty100
    python scripts/refresh_portfolio_live.py --detailed  # Show full quote data

Prerequisites:
    - Daily pipeline must have run today (ensures portfolio is current)
    - Valid access token
"""

import argparse
import os
import sys
from datetime import datetime, date
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from kiteconnect import KiteConnect

# Add scripts directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from universe_config import get_universe_config, list_universes


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


def check_pipeline_freshness(config: dict):
    """Verify daily pipeline ran recently (checks price data, not portfolio file)."""
    price_dir = config["price_dir"]
    if not price_dir.exists():
        return False, f"Price directory not found: {price_dir}"

    # Check modification time of price files
    csv_files = list(price_dir.glob("*_day.csv"))
    if not csv_files:
        return False, f"No price files found in {price_dir}"

    # Check the most recently modified file
    latest_file = max(csv_files, key=lambda f: f.stat().st_mtime)
    mtime = datetime.fromtimestamp(latest_file.stat().st_mtime)
    hours_old = (datetime.now() - mtime).total_seconds() / 3600

    if hours_old <= 24:
        return True, f"Price data updated {hours_old:.1f} hours ago"
    else:
        days_old = hours_old / 24
        return False, f"Price data is {days_old:.1f} days old. Run daily pipeline first."


def load_portfolio(config: dict):
    """Load current portfolio symbols."""
    df = pd.read_csv(config["portfolio_file"])
    return df["symbol"].tolist()


def get_previous_close(symbol, config: dict):
    """Get previous day's close from local data."""
    csv_path = config["price_dir"] / f"{symbol}_day.csv"
    if not csv_path.exists():
        return None
    try:
        df = pd.read_csv(csv_path)
        if not df.empty:
            return df.iloc[-1]["close"]
    except Exception:
        pass
    return None


def display_quotes(quotes, symbols, config, detailed=False):
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
        prev_close = ohlc.get("close", 0) or get_previous_close(symbol, config) or ltp
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
        "--universe", "-u",
        choices=list_universes(),
        default="nse500",
        help="Universe to use (default: nse500)"
    )
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

    # Get universe config
    config = get_universe_config(args.universe)

    # Check pipeline freshness
    if not args.skip_check:
        is_fresh, message = check_pipeline_freshness(config)
        if not is_fresh:
            print(f"Error: {message}")
            sys.exit(1)
        print(f"Pipeline check: {message}")

    # Load portfolio
    symbols = load_portfolio(config)
    print(f"Loaded {len(symbols)} portfolio stocks from {config['name']}")

    # Initialize Kite
    kite = init_kite_client()
    print("Connected to Kite API")

    # Fetch quotes (single API call for all symbols)
    instrument_list = [f"NSE:{s}" for s in symbols]
    print(f"Fetching live quotes...")

    try:
        quotes = kite.quote(instrument_list)
        display_quotes(quotes, symbols, config, detailed=args.detailed)
    except Exception as e:
        print(f"Error fetching quotes: {e}")
        sys.exit(1)

    return 0


if __name__ == "__main__":
    sys.exit(main())
