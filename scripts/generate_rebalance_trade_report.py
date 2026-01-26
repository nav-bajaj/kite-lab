"""
Generate detailed rebalance trade report with prices, quantities, and dollar amounts

Usage:
    python scripts/generate_rebalance_trade_report.py \
        --changes experiments/final_portfolio/final_portfolio_20260125230911/rebalance/changes_2026-01-23.csv \
        --prices-dir nse500_data \
        --signal-date 2026-01-23 \
        --capital 1000000 \
        --output rebalance_trade_report.md
"""

import argparse
import csv
from datetime import datetime, timedelta
from pathlib import Path
import sys

import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))


def load_ohlc_for_symbol(symbol: str, prices_dir: Path) -> pd.DataFrame:
    """Load OHLC data for a single symbol"""
    csv_path = prices_dir / f"{symbol}_day.csv"
    if not csv_path.exists():
        return pd.DataFrame()

    df = pd.read_csv(csv_path, parse_dates=["date"])
    if df.empty or not {"open", "high", "low", "close"}.issubset(df.columns):
        return pd.DataFrame()

    df["trade_price"] = df[["open", "high", "low", "close"]].mean(axis=1)
    return df[["date", "open", "high", "low", "close", "trade_price"]]


def get_trade_date(signal_date: datetime) -> datetime:
    """Map signal date (Thursday) to trade date (Friday)"""
    # Signal date is Thursday, trade date is Friday (next day)
    return signal_date + timedelta(days=1)


def load_changes(changes_csv: Path):
    """Load changes from CSV"""
    additions = []
    removals = []
    rank_changes = []

    with changes_csv.open("r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            action = row["action"]
            symbol = row["symbol"]
            rank = row.get("rank", "")
            new_rank = row.get("new_rank", "")

            if action == "add":
                # For adds, new_rank is in the "new_rank" column, not "rank"
                rank_val = int(new_rank) if new_rank else (int(rank) if rank else None)
                additions.append((symbol, rank_val))
            elif action == "remove":
                removals.append((symbol, int(rank) if rank else None))
            elif action == "rank_change":
                old_rank = int(row["rank"]) if rank else None
                new_rank_val = int(new_rank) if new_rank else None
                if old_rank and new_rank_val:
                    rank_changes.append((symbol, old_rank, new_rank_val))

    return additions, removals, rank_changes


def generate_report(changes_csv: Path, prices_dir: Path, signal_date: datetime,
                   capital: float, output_path: Path, slippage: float = 0.002, portfolio_size: int = 24):
    """Generate detailed rebalance trade report"""

    # Load changes
    additions, removals, rank_changes = load_changes(changes_csv)

    # Get trade date (Friday after Thursday signal)
    trade_date = get_trade_date(signal_date)

    # Calculate allocation per stock (equal weight)
    # Portfolio size is fixed (e.g., 24 stocks), not just additions + rank_changes
    num_positions = portfolio_size
    if num_positions == 0:
        print("No positions to trade")
        return

    allocation_per_stock = capital / num_positions
    num_unchanged = num_positions - len(additions) - len(removals)

    # Collect trade details
    exit_trades = []
    entry_trades = []
    total_proceeds = 0
    total_deployment = 0

    # Process exits (removals)
    print(f"Loading exit prices for {len(removals)} removals...")
    for symbol, old_rank in removals:
        df = load_ohlc_for_symbol(symbol, prices_dir)
        if df.empty:
            print(f"  Warning: No price data for {symbol}")
            continue

        # Find Friday's trade price
        trade_row = df[df["date"] == pd.Timestamp(trade_date)]
        if trade_row.empty:
            # Try to find closest date
            trade_row = df[df["date"] <= pd.Timestamp(trade_date)].tail(1)
            if trade_row.empty:
                print(f"  Warning: No price data for {symbol} on/before {trade_date.date()}")
                continue

        exit_price = trade_row["trade_price"].iloc[0]

        # We don't know actual shares held, so we'll estimate based on equal allocation
        # This assumes the position was fully allocated at entry
        estimated_shares = allocation_per_stock / exit_price
        proceeds = estimated_shares * exit_price * (1 - slippage)

        exit_trades.append({
            "symbol": symbol,
            "old_rank": old_rank,
            "exit_price": exit_price,
            "shares": estimated_shares,
            "proceeds": proceeds,
            "date": trade_row["date"].iloc[0].date()
        })
        total_proceeds += proceeds

    # Process entries (additions)
    print(f"Loading entry prices for {len(additions)} additions...")
    for symbol, new_rank in additions:
        df = load_ohlc_for_symbol(symbol, prices_dir)
        if df.empty:
            print(f"  Warning: No price data for {symbol}")
            continue

        # Find Friday's trade price
        trade_row = df[df["date"] == pd.Timestamp(trade_date)]
        if trade_row.empty:
            # Try to find closest date
            trade_row = df[df["date"] <= pd.Timestamp(trade_date)].tail(1)
            if trade_row.empty:
                print(f"  Warning: No price data for {symbol} on/before {trade_date.date()}")
                continue

        entry_price = trade_row["trade_price"].iloc[0]

        # Calculate shares based on allocation
        shares = allocation_per_stock / (entry_price * (1 + slippage))
        cost = shares * entry_price * (1 + slippage)

        entry_trades.append({
            "symbol": symbol,
            "new_rank": new_rank,
            "entry_price": entry_price,
            "shares": shares,
            "cost": cost,
            "date": trade_row["date"].iloc[0].date()
        })
        total_deployment += cost

    # Generate report
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w") as f:
        f.write("# Detailed Rebalance Trade Report\n\n")
        f.write(f"**Signal Date (Thursday):** {signal_date.date()}\n\n")
        f.write(f"**Trade Date (Friday):** {trade_date.date()}\n\n")
        f.write(f"**Pricing Model:** OHLC/4 (average of Open, High, Low, Close)\n\n")
        f.write(f"**Slippage:** {slippage*100:.2f}%\n\n")
        f.write(f"**Portfolio Capital:** ${capital:,.2f}\n\n")
        f.write(f"**Portfolio Size:** {num_positions} stocks (equal-weighted)\n\n")
        f.write(f"**Allocation per Stock:** ${allocation_per_stock:,.2f}\n\n")
        f.write(f"**Holdings Unchanged:** {num_unchanged} stocks (no trades)\n\n")
        f.write("---\n\n")

        # Exit trades
        if exit_trades:
            f.write(f"## Exit Trades ({len(exit_trades)} stocks)\n\n")
            f.write("Stocks being sold on Friday:\n\n")
            f.write("| Symbol | Old Rank | Exit Price | Shares | Proceeds | Trade Date |\n")
            f.write("|--------|----------|------------|--------|----------|------------|\n")
            for trade in exit_trades:
                f.write(f"| {trade['symbol']} | {trade['old_rank']} | "
                       f"${trade['exit_price']:.2f} | {trade['shares']:.2f} | "
                       f"${trade['proceeds']:,.2f} | {trade['date']} |\n")
            f.write(f"\n**Total Proceeds:** ${total_proceeds:,.2f}\n\n")
        else:
            f.write("## Exit Trades\n\nNo exits.\n\n")

        # Entry trades
        if entry_trades:
            f.write(f"## Entry Trades ({len(entry_trades)} stocks)\n\n")
            f.write("Stocks being bought on Friday:\n\n")
            f.write("| Symbol | New Rank | Entry Price | Shares | Cost | Trade Date |\n")
            f.write("|--------|----------|-------------|--------|------|------------|\n")
            for trade in entry_trades:
                f.write(f"| {trade['symbol']} | {trade['new_rank']} | "
                       f"${trade['entry_price']:.2f} | {trade['shares']:.2f} | "
                       f"${trade['cost']:,.2f} | {trade['date']} |\n")
            f.write(f"\n**Total Deployment:** ${total_deployment:,.2f}\n\n")
        else:
            f.write("## Entry Trades\n\nNo entries.\n\n")

        # Rank changes (no trades)
        if rank_changes:
            f.write(f"## Rank Changes ({len(rank_changes)} stocks)\n\n")
            f.write("Holdings maintained with rank changes:\n\n")
            f.write("| Symbol | Old Rank | New Rank | Change |\n")
            f.write("|--------|----------|----------|--------|\n")
            for symbol, old_rank, new_rank in rank_changes:
                change = new_rank - old_rank
                direction = "↓" if change < 0 else "↑" if change > 0 else "→"
                f.write(f"| {symbol} | {old_rank} | {new_rank} | {direction} {abs(change)} |\n")
            f.write("\n")

        # Summary
        f.write("## Summary\n\n")
        f.write(f"- **Exits:** {len(exit_trades)} stocks, ${total_proceeds:,.2f} proceeds\n")
        f.write(f"- **Entries:** {len(entry_trades)} stocks, ${total_deployment:,.2f} deployment\n")
        f.write(f"- **Net Cash Flow:** ${total_deployment - total_proceeds:,.2f}\n")
        f.write(f"- **Rank Changes Only:** {len(rank_changes)} stocks (no trades)\n")
        f.write(f"- **Holdings Unchanged:** {num_unchanged} stocks (no trades)\n")
        f.write(f"- **Total Portfolio Size:** {num_positions} stocks\n")
        f.write(f"- **Turnover:** {(len(exit_trades) / num_positions * 100):.1f}%\n")
        f.write("\n---\n\n")
        f.write("*Note: Share quantities and dollar amounts are estimates based on equal-weight allocation. ")
        f.write("Actual shares held may differ based on portfolio history.*\n")

    print(f"\nReport saved to {output_path}")
    print(f"Exits: {len(exit_trades)}, Entries: {len(entry_trades)}, Rank changes: {len(rank_changes)}")


def main():
    parser = argparse.ArgumentParser(description="Generate detailed rebalance trade report")
    parser.add_argument("--changes", type=Path, required=True, help="Path to changes CSV file")
    parser.add_argument("--prices-dir", type=Path, default=Path("nse500_data"), help="Directory with price data")
    parser.add_argument("--signal-date", type=str, required=True, help="Signal date (Thursday) in YYYY-MM-DD format")
    parser.add_argument("--capital", type=float, default=1_000_000, help="Portfolio capital")
    parser.add_argument("--portfolio-size", type=int, default=24, help="Number of stocks in portfolio (default 24)")
    parser.add_argument("--slippage", type=float, default=0.002, help="Slippage rate (default 0.2%)")
    parser.add_argument("--output", type=Path, required=True, help="Output path for report")

    args = parser.parse_args()

    if not args.changes.exists():
        print(f"ERROR: Changes file not found: {args.changes}")
        return 1

    if not args.prices_dir.exists():
        print(f"ERROR: Prices directory not found: {args.prices_dir}")
        return 1

    try:
        signal_date = datetime.strptime(args.signal_date, "%Y-%m-%d")
    except ValueError:
        print(f"ERROR: Invalid date format: {args.signal_date}. Use YYYY-MM-DD")
        return 1

    generate_report(args.changes, args.prices_dir, signal_date, args.capital, args.output,
                   args.slippage, args.portfolio_size)
    return 0


if __name__ == "__main__":
    sys.exit(main())
