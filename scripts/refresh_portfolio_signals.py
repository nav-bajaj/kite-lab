"""
Portfolio Signals Refresh

Comprehensive script to update prices and regenerate portfolio signals.
Automatically detects market hours and uses appropriate price fetch method.

Usage:
    # Auto-detect market hours, use default universe (nse500)
    python scripts/refresh_portfolio_signals.py

    # Specify universe
    python scripts/refresh_portfolio_signals.py --universe nifty100

    # Force historical fetch (even during market hours)
    python scripts/refresh_portfolio_signals.py --historical

    # Force live fetch (for testing)
    python scripts/refresh_portfolio_signals.py --live

    # Skip price fetch, just regenerate signals
    python scripts/refresh_portfolio_signals.py --skip-price-fetch

Prerequisites:
    - Daily pipeline must have run at least once (for full price history)
    - Valid access token
"""

import argparse
import os
import sys
import time
from datetime import datetime, date, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from kiteconnect import KiteConnect

# Add scripts directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from utils import find_token
from universe_config import (
    get_universe_config,
    list_universes,
    SIGNAL_DEFAULTS,
    MARKET_OPEN_HOUR,
    MARKET_OPEN_MINUTE,
    MARKET_CLOSE_HOUR,
    MARKET_CLOSE_MINUTE,
)

INDIA_TZ = ZoneInfo("Asia/Kolkata")


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


def is_market_hours() -> bool:
    """Check if Indian market is currently open."""
    now = datetime.now(INDIA_TZ)

    # Check if weekday (Mon=0 to Fri=4)
    if now.weekday() > 4:
        return False

    # Check time
    market_open = now.replace(hour=MARKET_OPEN_HOUR, minute=MARKET_OPEN_MINUTE, second=0, microsecond=0)
    market_close = now.replace(hour=MARKET_CLOSE_HOUR, minute=MARKET_CLOSE_MINUTE, second=0, microsecond=0)

    return market_open <= now <= market_close


def to_local_naive(date_series):
    """Convert date series to local naive timestamps."""
    dates = pd.to_datetime(date_series, errors="coerce")
    tz = getattr(dates.dt, "tz", None)
    if tz is not None:
        dates = dates.dt.tz_convert("Asia/Kolkata").dt.tz_localize(None)
    return dates


def check_pipeline_freshness(config: dict) -> tuple:
    """Verify daily pipeline has run (price data exists)."""
    price_dir = config["price_dir"]
    if not price_dir.exists():
        return False, f"Price directory not found: {price_dir}"

    # Check if we have recent price files
    csv_files = list(price_dir.glob("*_day.csv"))
    if not csv_files:
        return False, f"No price files found in {price_dir}"

    # Check modification time of a sample file
    sample_file = csv_files[0]
    mtime = datetime.fromtimestamp(sample_file.stat().st_mtime)
    days_old = (datetime.now() - mtime).days

    if days_old > 7:
        return False, f"Price data is {days_old} days old. Run daily pipeline first."

    return True, f"Price data last updated: {mtime.strftime('%Y-%m-%d %H:%M')}"


def load_portfolio_symbols(config: dict) -> list:
    """Load current portfolio symbols."""
    portfolio_file = config["portfolio_file"]
    if not portfolio_file.exists():
        # Fall back to loading from universe
        return load_universe_symbols(config)

    df = pd.read_csv(portfolio_file)
    return df["symbol"].tolist()


def load_universe_symbols(config: dict) -> list:
    """Load all symbols from universe file."""
    universe_file = config["universe_file"]
    if not universe_file.exists():
        raise FileNotFoundError(f"Universe file not found: {universe_file}")

    df = pd.read_csv(universe_file)
    return df["Symbol"].dropna().str.strip().tolist()


def fetch_live_prices(kite, symbols: list, config: dict) -> dict:
    """Fetch live prices using quote API and update CSVs."""
    print(f"\nFetching live prices for {len(symbols)} stocks...")

    instrument_list = [f"NSE:{s}" for s in symbols]
    quotes = kite.quote(instrument_list)

    updated = 0
    today = date.today()
    price_dir = config["price_dir"]

    for symbol in symbols:
        key = f"NSE:{symbol}"
        if key not in quotes:
            continue

        q = quotes[key]
        ohlc = q.get("ohlc", {})

        # Create row for today
        new_row = {
            "date": today.isoformat(),
            "open": ohlc.get("open", q.get("last_price")),
            "high": ohlc.get("high", q.get("last_price")),
            "low": ohlc.get("low", q.get("last_price")),
            "close": q.get("last_price"),
            "volume": q.get("volume", 0),
        }

        # Update CSV file
        csv_path = price_dir / f"{symbol}_day.csv"
        if csv_path.exists():
            df = pd.read_csv(csv_path)
            df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")

            # Remove today's row if exists, then append new
            df = df[df["date"] != today.isoformat()]
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            df = df.sort_values("date")
            df.to_csv(csv_path, index=False)
            updated += 1

    print(f"  Updated {updated} price files with live data")
    return quotes


def fetch_historical_prices(kite, symbols: list, config: dict, days: int = 5) -> int:
    """Fetch historical prices and update CSVs."""
    print(f"\nFetching historical prices for {len(symbols)} stocks (last {days} days)...")

    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    price_dir = config["price_dir"]

    updated = 0
    failed = []

    for i, symbol in enumerate(symbols, 1):
        try:
            token = find_token(symbol, exchange="NSE")
        except ValueError:
            try:
                token = find_token(symbol, exchange="BSE")
            except ValueError:
                failed.append(symbol)
                continue

        try:
            candles = kite.historical_data(
                instrument_token=token,
                from_date=start_date,
                to_date=end_date + timedelta(days=1),
                interval="day",
                continuous=False,
                oi=False,
            )

            if not candles:
                continue

            new_df = pd.DataFrame(candles)
            new_df["date"] = to_local_naive(new_df["date"])

            # Update CSV file
            csv_path = price_dir / f"{symbol}_day.csv"
            if csv_path.exists():
                existing_df = pd.read_csv(csv_path)
                existing_df["date"] = to_local_naive(existing_df["date"])

                combined = pd.concat([existing_df, new_df], ignore_index=True)
                combined = combined.sort_values("date").drop_duplicates(subset=["date"], keep="last")
            else:
                combined = new_df.sort_values("date")

            combined.to_csv(csv_path, index=False)
            updated += 1

            if i % 10 == 0:
                print(f"  Progress: {i}/{len(symbols)}")

            time.sleep(0.34)  # Rate limiting

        except Exception as e:
            failed.append(symbol)

    print(f"  Updated {updated} price files")
    if failed:
        print(f"  Failed: {', '.join(failed[:10])}{'...' if len(failed) > 10 else ''}")

    return updated


def load_price_panel(price_dir: Path, universe: set = None) -> pd.DataFrame:
    """Load price panel from CSV files."""
    series = []
    for csv_path in sorted(price_dir.glob("*_day.csv")):
        symbol = csv_path.name.replace("_day.csv", "")
        if universe and symbol not in universe:
            continue
        df = pd.read_csv(csv_path, parse_dates=["date"])
        if df.empty or "close" not in df.columns:
            continue
        df = df[["date", "close"]].dropna()
        df["symbol"] = symbol
        series.append(df)

    if not series:
        raise RuntimeError(f"No price files found in {price_dir}")

    combined = pd.concat(series, ignore_index=True)
    pivot = combined.pivot(index="date", columns="symbol", values="close").sort_index()
    return pivot


def row_zscore(df: pd.DataFrame) -> pd.DataFrame:
    """Compute row-wise z-scores."""
    mean = df.mean(axis=1)
    std = df.std(axis=1).replace(0, np.nan)
    return df.sub(mean, axis=0).div(std, axis=0)


def compute_momentum_scores(prices: pd.DataFrame, config: dict) -> dict:
    """Compute momentum scores."""
    skip_days = SIGNAL_DEFAULTS["skip_days"]
    lookback = SIGNAL_DEFAULTS["lookback_days"]
    vol_floor = SIGNAL_DEFAULTS["vol_floor"]
    vol_power = SIGNAL_DEFAULTS["vol_power"]

    prices = prices.sort_index()
    returns = prices.pct_change()
    past_prices = prices.shift(skip_days)

    # 6-month momentum
    mom = past_prices / past_prices.shift(lookback) - 1
    vol = returns.shift(skip_days).rolling(lookback).std()

    if vol_floor is not None:
        vol = vol.clip(lower=vol_floor)

    denom = vol.pow(vol_power)
    score = mom / denom
    z = row_zscore(score)

    return {
        "composite": z,
        "score_6m": z,
        "mom_6m": mom,
        "vol_6m": vol,
    }


def generate_latest_rankings(scores: dict, top_n: int) -> pd.DataFrame:
    """Generate rankings for the latest date."""
    composite = scores["composite"].dropna(how="all")

    # Get the latest date
    latest_date = composite.index.max()

    row = composite.loc[latest_date].dropna().sort_values(ascending=False).head(top_n)

    rows = []
    for rank, (symbol, score) in enumerate(row.items(), start=1):
        rows.append({
            "date": latest_date,
            "signal_date": latest_date,
            "rank": rank,
            "symbol": symbol,
            "score": score,
            "score_6m": scores["score_6m"].loc[latest_date].get(symbol, np.nan),
            "mom_6m": scores["mom_6m"].loc[latest_date].get(symbol, np.nan),
            "vol_6m": scores["vol_6m"].loc[latest_date].get(symbol, np.nan),
        })

    return pd.DataFrame(rows)


def compare_portfolios(old_portfolio: list, new_portfolio: list) -> dict:
    """Compare old and new portfolios to find changes."""
    old_set = set(old_portfolio)
    new_set = set(new_portfolio)

    return {
        "added": list(new_set - old_set),
        "removed": list(old_set - new_set),
        "unchanged": list(old_set & new_set),
    }


def display_results(new_rankings: pd.DataFrame, changes: dict, config: dict):
    """Display results and changes."""
    print("\n" + "=" * 70)
    print(f"PORTFOLIO REFRESH RESULTS - {config['name']}")
    print("=" * 70)

    print(f"\nLatest signal date: {new_rankings['date'].iloc[0]}")
    print(f"\nTop {len(new_rankings)} stocks:")
    print("-" * 50)
    print(f"{'Rank':<6} {'Symbol':<15} {'Score':>10} {'Mom 6M':>10}")
    print("-" * 50)

    for _, row in new_rankings.iterrows():
        mom_pct = row['mom_6m'] * 100 if pd.notna(row['mom_6m']) else 0
        print(f"{int(row['rank']):<6} {row['symbol']:<15} {row['score']:>10.2f} {mom_pct:>9.1f}%")

    print("\n" + "-" * 50)
    print("CHANGES FROM CURRENT PORTFOLIO:")
    print("-" * 50)

    if changes["added"]:
        print(f"  + ADDED ({len(changes['added'])}): {', '.join(changes['added'])}")
    else:
        print("  + ADDED: None")

    if changes["removed"]:
        print(f"  - REMOVED ({len(changes['removed'])}): {', '.join(changes['removed'])}")
    else:
        print("  - REMOVED: None")

    print(f"  = UNCHANGED: {len(changes['unchanged'])} stocks")


def main():
    parser = argparse.ArgumentParser(description="Refresh portfolio prices and signals")
    parser.add_argument(
        "--universe", "-u",
        choices=list_universes(),
        default="nse500",
        help="Universe to refresh (default: nse500)"
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Force live price fetch (even outside market hours)"
    )
    parser.add_argument(
        "--historical",
        action="store_true",
        help="Force historical price fetch (even during market hours)"
    )
    parser.add_argument(
        "--skip-price-fetch",
        action="store_true",
        help="Skip price fetch, just regenerate signals"
    )
    parser.add_argument(
        "--days", "-d",
        type=int,
        default=5,
        help="Days of historical data to fetch (default: 5)"
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=SIGNAL_DEFAULTS["top_n"],
        help=f"Number of top stocks (default: {SIGNAL_DEFAULTS['top_n']})"
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help="Save updated portfolio to file"
    )
    parser.add_argument(
        "--skip-check",
        action="store_true",
        help="Skip pipeline freshness check"
    )

    args = parser.parse_args()

    # Get universe config
    config = get_universe_config(args.universe)

    print("=" * 70)
    print(f"PORTFOLIO SIGNALS REFRESH - {config['name']}")
    print("=" * 70)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Check pipeline freshness
    if not args.skip_check:
        is_fresh, message = check_pipeline_freshness(config)
        if not is_fresh:
            print(f"\nError: {message}")
            sys.exit(1)
        print(f"Pipeline check: {message}")

    # Initialize Kite
    kite = init_kite_client()
    print("Connected to Kite API")

    # Determine price fetch mode
    market_open = is_market_hours()
    print(f"Market status: {'OPEN' if market_open else 'CLOSED'}")

    if args.skip_price_fetch:
        fetch_mode = "skip"
    elif args.live:
        fetch_mode = "live"
    elif args.historical:
        fetch_mode = "historical"
    elif market_open:
        fetch_mode = "live"
    else:
        fetch_mode = "historical"

    print(f"Price fetch mode: {fetch_mode.upper()}")

    # Load current portfolio for comparison
    try:
        old_portfolio = load_portfolio_symbols(config)
        print(f"Loaded current portfolio: {len(old_portfolio)} stocks")
    except Exception:
        old_portfolio = []
        print("No existing portfolio found")

    # Fetch prices
    if fetch_mode == "live":
        # For live, we update universe stocks (not just portfolio)
        # to ensure signals are computed correctly
        symbols = load_universe_symbols(config)
        # But only fetch for top ~100 to be fast
        symbols_to_fetch = list(set(old_portfolio + symbols[:100]))
        fetch_live_prices(kite, symbols_to_fetch, config)
    elif fetch_mode == "historical":
        symbols = load_universe_symbols(config)
        # Fetch only portfolio + buffer for historical
        symbols_to_fetch = list(set(old_portfolio + symbols[:50]))
        fetch_historical_prices(kite, symbols_to_fetch, config, days=args.days)
    else:
        print("Skipping price fetch")

    # Load universe for signal generation
    universe_symbols = set(load_universe_symbols(config))
    print(f"\nLoaded universe: {len(universe_symbols)} stocks")

    # Load prices and compute signals
    print("Loading price panel...")
    prices = load_price_panel(config["price_dir"], universe_symbols)
    print(f"Price panel: {len(prices)} dates, {len(prices.columns)} stocks")

    print("Computing momentum scores...")
    scores = compute_momentum_scores(prices, config)

    print("Generating rankings...")
    new_rankings = generate_latest_rankings(scores, args.top_n)
    new_portfolio = new_rankings["symbol"].tolist()

    # Compare portfolios
    changes = compare_portfolios(old_portfolio, new_portfolio)

    # Display results
    display_results(new_rankings, changes, config)

    # Save if requested
    if args.save:
        config["portfolio_dir"].mkdir(parents=True, exist_ok=True)
        output_path = config["portfolio_file"]
        new_rankings.to_csv(output_path, index=False)
        print(f"\nSaved portfolio to {output_path}")
    else:
        print("\nNote: Use --save to update the portfolio file")

    return 0


if __name__ == "__main__":
    sys.exit(main())
