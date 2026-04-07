"""
Refresh All Portfolios

Updates prices and regenerates signals for all three universes (NSE 500, Nifty 100, Nifty 250).
Generates an HTML report showing the updates instead of syncing to database.

Usage:
    python scripts/refresh_all_portfolios.py
    python scripts/refresh_all_portfolios.py --live      # Force live prices
    python scripts/refresh_all_portfolios.py --historical # Force historical prices
    python scripts/refresh_all_portfolios.py --output report.html  # Custom output path

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
    UNIVERSE_CONFIG,
    SIGNAL_DEFAULTS,
    MARKET_OPEN_HOUR,
    MARKET_OPEN_MINUTE,
    MARKET_CLOSE_HOUR,
    MARKET_CLOSE_MINUTE,
    list_universes,
)

INDIA_TZ = ZoneInfo("Asia/Kolkata")
REPORTS_DIR = Path("reports")


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
    if now.weekday() > 4:
        return False
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


def load_universe_symbols(config: dict) -> list:
    """Load all symbols from universe file."""
    universe_file = config["universe_file"]
    if not universe_file.exists():
        raise FileNotFoundError(f"Universe file not found: {universe_file}")
    df = pd.read_csv(universe_file)
    return df["Symbol"].dropna().str.strip().tolist()


def load_portfolio_symbols(config: dict) -> list:
    """Load current portfolio symbols."""
    portfolio_file = config["portfolio_file"]
    if not portfolio_file.exists():
        return []
    df = pd.read_csv(portfolio_file)
    return df["symbol"].tolist()


def get_all_symbols_to_fetch() -> set:
    """Get union of all symbols across all universes."""
    all_symbols = set()
    for universe_key in UNIVERSE_CONFIG:
        config = UNIVERSE_CONFIG[universe_key]
        try:
            symbols = load_universe_symbols(config)
            all_symbols.update(symbols)
        except Exception:
            pass
    return all_symbols


def fetch_live_prices(kite, symbols: list) -> dict:
    """Fetch live prices using quote API."""
    print(f"Fetching live prices for {len(symbols)} stocks...")

    # Kite API allows max 500 instruments per call
    quotes = {}
    batch_size = 500
    for i in range(0, len(symbols), batch_size):
        batch = symbols[i:i+batch_size]
        instrument_list = [f"NSE:{s}" for s in batch]
        try:
            batch_quotes = kite.quote(instrument_list)
            quotes.update(batch_quotes)
        except Exception as e:
            print(f"  Error fetching batch: {e}")

    return quotes


def update_price_files_from_quotes(quotes: dict, price_dir: Path):
    """Update CSV files with live quote data."""
    today = date.today()
    updated = 0

    for key, q in quotes.items():
        symbol = key.replace("NSE:", "")
        ohlc = q.get("ohlc", {})

        new_row = {
            "date": today.isoformat(),
            "open": ohlc.get("open", q.get("last_price")),
            "high": ohlc.get("high", q.get("last_price")),
            "low": ohlc.get("low", q.get("last_price")),
            "close": q.get("last_price"),
            "volume": q.get("volume", 0),
        }

        csv_path = price_dir / f"{symbol}_day.csv"
        if csv_path.exists():
            df = pd.read_csv(csv_path)
            df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
            df = df[df["date"] != today.isoformat()]
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            df = df.sort_values("date")
            df.to_csv(csv_path, index=False)
            updated += 1

    print(f"  Updated {updated} price files")
    return updated


def fetch_historical_prices(kite, symbols: list, price_dir: Path, days: int = 5):
    """Fetch historical prices and update CSVs."""
    print(f"Fetching historical prices for {len(symbols)} stocks (last {days} days)...")

    end_date = date.today()
    start_date = end_date - timedelta(days=days)
    updated = 0

    for i, symbol in enumerate(symbols, 1):
        try:
            token = find_token(symbol, exchange="NSE")
        except ValueError:
            try:
                token = find_token(symbol, exchange="BSE")
            except ValueError:
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

            if i % 50 == 0:
                print(f"  Progress: {i}/{len(symbols)}")

            time.sleep(0.34)

        except Exception:
            continue

    print(f"  Updated {updated} price files")
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


def compute_momentum_scores(prices: pd.DataFrame) -> dict:
    """Compute momentum scores."""
    skip_days = SIGNAL_DEFAULTS["skip_days"]
    lookback = SIGNAL_DEFAULTS["lookback_days"]
    vol_floor = SIGNAL_DEFAULTS["vol_floor"]
    vol_power = SIGNAL_DEFAULTS["vol_power"]

    prices = prices.sort_index()
    returns = prices.pct_change()
    past_prices = prices.shift(skip_days)

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


def generate_rankings(scores: dict, top_n: int) -> pd.DataFrame:
    """Generate rankings for the latest date."""
    composite = scores["composite"].dropna(how="all")
    latest_date = composite.index.max()

    row = composite.loc[latest_date].dropna().sort_values(ascending=False).head(top_n)

    rows = []
    for rank, (symbol, score) in enumerate(row.items(), start=1):
        rows.append({
            "rank": rank,
            "symbol": symbol,
            "score": score,
            "mom_6m": scores["mom_6m"].loc[latest_date].get(symbol, np.nan),
            "vol_6m": scores["vol_6m"].loc[latest_date].get(symbol, np.nan),
        })

    return pd.DataFrame(rows), latest_date


def compare_portfolios(old_portfolio: list, new_portfolio: list) -> dict:
    """Compare old and new portfolios to find changes."""
    old_set = set(old_portfolio)
    new_set = set(new_portfolio)

    return {
        "added": sorted(list(new_set - old_set)),
        "removed": sorted(list(old_set - new_set)),
        "unchanged": sorted(list(old_set & new_set)),
    }


def process_universe(universe_key: str, prices: pd.DataFrame, quotes: dict = None) -> dict:
    """Process a single universe and return results."""
    config = UNIVERSE_CONFIG[universe_key]

    # Load universe symbols
    universe_symbols = set(load_universe_symbols(config))

    # Filter prices to universe
    available_symbols = set(prices.columns) & universe_symbols
    universe_prices = prices[[s for s in prices.columns if s in available_symbols]]

    # Compute scores and rankings
    scores = compute_momentum_scores(universe_prices)
    rankings, signal_date = generate_rankings(scores, SIGNAL_DEFAULTS["top_n"])

    # Get current portfolio for comparison
    old_portfolio = load_portfolio_symbols(config)
    new_portfolio = rankings["symbol"].tolist()
    changes = compare_portfolios(old_portfolio, new_portfolio)

    # Add live prices if available
    if quotes:
        rankings["ltp"] = rankings["symbol"].apply(
            lambda s: quotes.get(f"NSE:{s}", {}).get("last_price", None)
        )
        rankings["day_change"] = rankings["symbol"].apply(
            lambda s: quotes.get(f"NSE:{s}", {}).get("change", None)
        )
        rankings["day_change_pct"] = rankings["symbol"].apply(
            lambda s: quotes.get(f"NSE:{s}", {}).get("change_percent", None) or
                      (quotes.get(f"NSE:{s}", {}).get("change", 0) /
                       (quotes.get(f"NSE:{s}", {}).get("last_price", 1) - quotes.get(f"NSE:{s}", {}).get("change", 0)) * 100
                       if quotes.get(f"NSE:{s}", {}).get("last_price") else None)
        )

    return {
        "name": config["name"],
        "signal_date": signal_date,
        "rankings": rankings,
        "changes": changes,
        "old_portfolio": old_portfolio,
        "new_portfolio": new_portfolio,
    }


def generate_html_report(results: dict, fetch_mode: str, output_path: Path) -> str:
    """Generate HTML report from results."""

    now = datetime.now()
    market_status = "OPEN" if is_market_hours() else "CLOSED"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Portfolio Refresh Report - {now.strftime('%Y-%m-%d %H:%M')}</title>
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f5f5;
            color: #333;
            line-height: 1.6;
            padding: 20px;
        }}
        .container {{ max-width: 1400px; margin: 0 auto; }}
        h1 {{ color: #1a1a1a; margin-bottom: 10px; }}
        .meta {{ color: #666; margin-bottom: 30px; font-size: 14px; }}
        .meta span {{
            display: inline-block;
            margin-right: 20px;
            padding: 4px 12px;
            background: #e0e0e0;
            border-radius: 4px;
        }}
        .meta .open {{ background: #c8e6c9; color: #2e7d32; }}
        .meta .closed {{ background: #ffcdd2; color: #c62828; }}
        .universe {{
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 30px;
            overflow: hidden;
        }}
        .universe-header {{
            background: #1976d2;
            color: white;
            padding: 15px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .universe-header h2 {{ font-size: 20px; }}
        .universe-header .date {{ font-size: 14px; opacity: 0.9; }}
        .changes {{
            padding: 15px 20px;
            background: #fafafa;
            border-bottom: 1px solid #eee;
            display: flex;
            gap: 30px;
        }}
        .change-group {{ }}
        .change-group .label {{
            font-size: 12px;
            text-transform: uppercase;
            color: #666;
            margin-bottom: 5px;
        }}
        .change-group .added {{ color: #2e7d32; font-weight: 600; }}
        .change-group .removed {{ color: #c62828; font-weight: 600; }}
        .change-group .unchanged {{ color: #666; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th {{
            text-align: left;
            padding: 12px 15px;
            background: #f5f5f5;
            font-weight: 600;
            font-size: 13px;
            color: #666;
            text-transform: uppercase;
        }}
        td {{
            padding: 10px 15px;
            border-bottom: 1px solid #eee;
        }}
        tr:hover {{ background: #f9f9f9; }}
        .rank {{
            font-weight: 600;
            color: #1976d2;
            width: 50px;
        }}
        .symbol {{ font-weight: 600; }}
        .score {{ font-family: monospace; }}
        .positive {{ color: #2e7d32; }}
        .negative {{ color: #c62828; }}
        .new-entry {{ background: #e8f5e9; }}
        .footer {{
            text-align: center;
            padding: 20px;
            color: #999;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Portfolio Refresh Report</h1>
        <div class="meta">
            <span>Generated: {now.strftime('%Y-%m-%d %H:%M:%S')}</span>
            <span class="{'open' if market_status == 'OPEN' else 'closed'}">Market: {market_status}</span>
            <span>Price Mode: {fetch_mode.upper()}</span>
        </div>
"""

    for universe_key in ["nse500", "nifty100", "nifty250"]:
        if universe_key not in results:
            continue

        r = results[universe_key]
        rankings = r["rankings"]
        changes = r["changes"]

        html += f"""
        <div class="universe">
            <div class="universe-header">
                <h2>{r['name']}</h2>
                <span class="date">Signal Date: {r['signal_date'].strftime('%Y-%m-%d')}</span>
            </div>
            <div class="changes">
                <div class="change-group">
                    <div class="label">Added</div>
                    <div class="added">{', '.join(changes['added']) if changes['added'] else 'None'}</div>
                </div>
                <div class="change-group">
                    <div class="label">Removed</div>
                    <div class="removed">{', '.join(changes['removed']) if changes['removed'] else 'None'}</div>
                </div>
                <div class="change-group">
                    <div class="label">Unchanged</div>
                    <div class="unchanged">{len(changes['unchanged'])} stocks</div>
                </div>
            </div>
            <table>
                <thead>
                    <tr>
                        <th>Rank</th>
                        <th>Symbol</th>
                        <th>Score</th>
                        <th>6M Momentum</th>
"""

        if "ltp" in rankings.columns:
            html += """
                        <th>LTP</th>
                        <th>Day Change</th>
"""

        html += """
                    </tr>
                </thead>
                <tbody>
"""

        for _, row in rankings.iterrows():
            is_new = row["symbol"] in changes["added"]
            row_class = "new-entry" if is_new else ""
            mom_pct = row["mom_6m"] * 100 if pd.notna(row["mom_6m"]) else 0
            mom_class = "positive" if mom_pct > 0 else "negative"

            html += f"""
                    <tr class="{row_class}">
                        <td class="rank">{int(row['rank'])}</td>
                        <td class="symbol">{row['symbol']}{'*' if is_new else ''}</td>
                        <td class="score">{row['score']:.2f}</td>
                        <td class="{mom_class}">{mom_pct:+.1f}%</td>
"""

            if "ltp" in rankings.columns:
                ltp = row.get("ltp")
                day_chg = row.get("day_change")
                day_chg_pct = row.get("day_change_pct")

                if pd.notna(ltp):
                    chg_class = "positive" if (day_chg or 0) >= 0 else "negative"
                    html += f"""
                        <td>{ltp:.2f}</td>
                        <td class="{chg_class}">{day_chg:+.2f} ({day_chg_pct:+.2f}%)</td>
""" if pd.notna(day_chg) else f"""
                        <td>{ltp:.2f}</td>
                        <td>-</td>
"""
                else:
                    html += """
                        <td>-</td>
                        <td>-</td>
"""

            html += """
                    </tr>
"""

        html += """
                </tbody>
            </table>
        </div>
"""

    html += f"""
        <div class="footer">
            Generated by Kite-Lab Portfolio Refresh | * = New entry this period
        </div>
    </div>
</body>
</html>
"""

    # Write report
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(html)

    return str(output_path)


def main():
    parser = argparse.ArgumentParser(description="Refresh all portfolios and generate HTML report")
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
        "--days", "-d",
        type=int,
        default=5,
        help="Days of historical data to fetch (default: 5)"
    )
    parser.add_argument(
        "--output", "-o",
        type=Path,
        help="Output path for HTML report (default: reports/portfolio_refresh_<timestamp>.html)"
    )
    parser.add_argument(
        "--skip-price-fetch",
        action="store_true",
        help="Skip price fetch, just regenerate signals from existing data"
    )

    args = parser.parse_args()

    print("=" * 70)
    print("REFRESH ALL PORTFOLIOS")
    print("=" * 70)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

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

    # Get all symbols to fetch
    all_symbols = list(get_all_symbols_to_fetch())
    print(f"Total symbols across all universes: {len(all_symbols)}")

    # Fetch prices
    quotes = None
    price_dir = UNIVERSE_CONFIG["nse500"]["price_dir"]

    if fetch_mode == "live":
        quotes = fetch_live_prices(kite, all_symbols)
        update_price_files_from_quotes(quotes, price_dir)
    elif fetch_mode == "historical":
        fetch_historical_prices(kite, all_symbols, price_dir, days=args.days)
    else:
        print("Skipping price fetch")

    # Load price panel once (shared across all universes)
    print("\nLoading price panel...")
    prices = load_price_panel(price_dir)
    print(f"Price panel: {len(prices)} dates, {len(prices.columns)} stocks")

    # Process each universe
    results = {}
    for universe_key in ["nse500", "nifty100", "nifty250"]:
        print(f"\nProcessing {UNIVERSE_CONFIG[universe_key]['name']}...")
        try:
            results[universe_key] = process_universe(universe_key, prices, quotes)
            changes = results[universe_key]["changes"]
            print(f"  Added: {len(changes['added'])}, Removed: {len(changes['removed'])}, Unchanged: {len(changes['unchanged'])}")
        except Exception as e:
            print(f"  Error: {e}")

    # Generate HTML report
    if args.output:
        output_path = args.output
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = REPORTS_DIR / f"portfolio_refresh_{timestamp}.html"

    print(f"\nGenerating HTML report...")
    report_path = generate_html_report(results, fetch_mode, output_path)
    print(f"Report saved to: {report_path}")

    # Print summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    for universe_key, r in results.items():
        changes = r["changes"]
        print(f"\n{r['name']}:")
        print(f"  Signal date: {r['signal_date'].strftime('%Y-%m-%d')}")
        if changes["added"]:
            print(f"  + Added: {', '.join(changes['added'])}")
        if changes["removed"]:
            print(f"  - Removed: {', '.join(changes['removed'])}")
        print(f"  = Unchanged: {len(changes['unchanged'])} stocks")

    print(f"\nHTML Report: {report_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
