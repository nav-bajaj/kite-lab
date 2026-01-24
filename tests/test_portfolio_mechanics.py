"""
Test portfolio mechanics:
1. Cash positions - do we hold cash when fewer than 24 stocks available?
2. Sells vs buys at each rebalance - are they balanced?
3. Holdings count - should always be 24 (or as many as available)
"""

import argparse
import sys
from pathlib import Path
from datetime import datetime

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))


def analyze_trades(trades_path: Path):
    """Analyze trade patterns at each rebalance"""
    trades = pd.read_csv(trades_path, parse_dates=["date"])

    print("\n" + "="*80)
    print("REBALANCE TRADE ANALYSIS")
    print("="*80)

    # Group by date to see buys/sells per rebalance
    rebalance_dates = trades["date"].unique()

    results = []
    for date in sorted(rebalance_dates):
        day_trades = trades[trades["date"] == date]
        buys = day_trades[day_trades["side"] == "BUY"]
        sells = day_trades[day_trades["side"] == "SELL"]

        results.append({
            "date": date,
            "num_buys": len(buys),
            "num_sells": len(sells),
            "buy_notional": buys["notional"].sum(),
            "sell_notional": sells["notional"].sum(),
            "net_flow": buys["notional"].sum() - sells["notional"].sum(),
            "cash_after": day_trades.iloc[-1]["cash_after"] if not day_trades.empty else None,
        })

    df = pd.DataFrame(results)

    print(f"\nTotal rebalance dates: {len(df)}")
    print(f"\nFirst 10 rebalances:")
    print(df.head(10).to_string(index=False))

    print(f"\nLast 10 rebalances:")
    print(df.tail(10).to_string(index=False))

    # Check balance
    unbalanced = df[df["num_buys"] != df["num_sells"]]
    print(f"\n{'='*80}")
    print(f"Unbalanced rebalances (buys ≠ sells): {len(unbalanced)}")
    if not unbalanced.empty:
        print("\nDates with unbalanced trades:")
        print(unbalanced[["date", "num_buys", "num_sells"]].to_string(index=False))

    # Cash position analysis
    print(f"\n{'='*80}")
    print("CASH POSITION ANALYSIS")
    print("="*80)
    print(f"\nFinal cash position: ${df.iloc[-1]['cash_after']:,.2f}")
    print(f"\nCash statistics:")
    print(f"  Min: ${df['cash_after'].min():,.2f}")
    print(f"  Max: ${df['cash_after'].max():,.2f}")
    print(f"  Mean: ${df['cash_after'].mean():,.2f}")
    print(f"  Median: ${df['cash_after'].median():,.2f}")

    # Check for high cash positions
    high_cash = df[df["cash_after"] > 100000]  # More than 100k cash
    if not high_cash.empty:
        print(f"\nDates with high cash (>$100k):")
        print(high_cash[["date", "cash_after", "num_buys", "num_sells"]].head(20).to_string(index=False))

    return df


def analyze_holdings(trades_path: Path, initial_capital: float = 1_000_000):
    """Reconstruct holdings over time"""
    trades = pd.read_csv(trades_path, parse_dates=["date"])

    print("\n" + "="*80)
    print("HOLDINGS COUNT ANALYSIS")
    print("="*80)

    # Reconstruct holdings
    holdings = {}
    holdings_over_time = []

    for date in sorted(trades["date"].unique()):
        day_trades = trades[trades["date"] == date]

        for _, trade in day_trades.iterrows():
            symbol = trade["symbol"]
            if trade["side"] == "BUY":
                holdings[symbol] = holdings.get(symbol, 0) + trade["shares"]
            else:  # SELL
                holdings[symbol] = holdings.get(symbol, 0) - trade["shares"]
                if holdings[symbol] <= 0.01:  # Account for floating point
                    holdings.pop(symbol, None)

        # Get portfolio value
        cash = day_trades.iloc[-1]["cash_after"] if not day_trades.empty else initial_capital

        holdings_over_time.append({
            "date": date,
            "num_holdings": len(holdings),
            "symbols": list(holdings.keys()),
            "cash": cash,
        })

    df = pd.DataFrame(holdings_over_time)

    print(f"\nHoldings count statistics:")
    print(df["num_holdings"].describe())

    print(f"\nFirst 10 rebalances:")
    print(df[["date", "num_holdings", "cash"]].head(10).to_string(index=False))

    print(f"\nLast 10 rebalances:")
    print(df[["date", "num_holdings", "cash"]].tail(10).to_string(index=False))

    # Check for holdings != 24
    not_24 = df[df["num_holdings"] != 24]
    print(f"\n{'='*80}")
    print(f"Rebalances with holdings ≠ 24: {len(not_24)}")
    if not not_24.empty:
        print("\nDates with non-standard holdings:")
        print(not_24[["date", "num_holdings", "cash"]].to_string(index=False))

    return df


def main():
    parser = argparse.ArgumentParser(description="Test portfolio mechanics")
    parser.add_argument("--trades", type=Path, required=True, help="Path to trades.csv")
    parser.add_argument("--initial-capital", type=float, default=1_000_000)
    args = parser.parse_args()

    if not args.trades.exists():
        print(f"ERROR: trades.csv not found at {args.trades}")
        return 1

    print(f"Analyzing trades from: {args.trades}")

    # Run analyses
    trade_stats = analyze_trades(args.trades)
    holdings_stats = analyze_holdings(args.trades, args.initial_capital)

    # Summary
    print("\n" + "="*80)
    print("SUMMARY - Answers to Key Questions")
    print("="*80)

    print("\n1. CASH POSITIONS")
    final_cash = trade_stats.iloc[-1]["cash_after"]
    avg_cash = trade_stats["cash_after"].mean()
    print(f"   - Final cash: ${final_cash:,.2f}")
    print(f"   - Average cash: ${avg_cash:,.2f}")
    if avg_cash > 50000:
        print("   ⚠️  Portfolio holds significant cash - not fully invested")
    else:
        print("   ✓ Portfolio is mostly invested (low cash balance)")

    print("\n2. BUYS vs SELLS BALANCE")
    balanced = (trade_stats["num_buys"] == trade_stats["num_sells"]).sum()
    total = len(trade_stats)
    print(f"   - Balanced rebalances: {balanced}/{total} ({100*balanced/total:.1f}%)")
    if balanced == total:
        print("   ✓ All rebalances are perfectly balanced")
    else:
        print(f"   ⚠️  {total - balanced} rebalances are unbalanced")

    print("\n3. HOLDINGS COUNT")
    always_24 = (holdings_stats["num_holdings"] == 24).sum()
    total_periods = len(holdings_stats)
    print(f"   - Periods with 24 holdings: {always_24}/{total_periods} ({100*always_24/total_periods:.1f}%)")
    if always_24 == total_periods:
        print("   ✓ Portfolio always holds exactly 24 stocks")
    else:
        min_holdings = holdings_stats["num_holdings"].min()
        max_holdings = holdings_stats["num_holdings"].max()
        print(f"   ⚠️  Holdings range: {min_holdings} - {max_holdings}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
