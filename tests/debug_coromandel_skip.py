"""Debug why COROMANDEL wasn't bought on 2020-07-17"""

import sys
from pathlib import Path
import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

# Simulate the backtest logic for this specific date
def simulate_rebalance():
    # Load price data
    prices_dir = ROOT / "nse500_data"

    # Current holdings before rebalance
    holdings_before = {
        'ADANIGREEN', 'AJANTPHARM', 'ALKYLAMINE', 'APLLTD', 'AUROPHARMA',
        'BAYERCROP', 'DEEPAKNTR', 'DIXON', 'ESCORTS', 'GRANULES',
        'IDEA', 'INDIACEM', 'IPCALAB', 'IRB', 'IRCTC',
        'JBCHEPHARM', 'LAURUSLABS', 'LTFOODS', 'NAVINFLUOR', 'POLYMED',
        'SUZLON', 'TARIL', 'TATACOMM', 'TTML'
    }

    # Target signals
    target_signals = [
        'GRANULES', 'ALKYLAMINE', 'AUROPHARMA', 'APLLTD', 'SUZLON',
        'LTFOODS', 'ESCORTS', 'ADANIGREEN', 'TATACOMM', 'POLYMED',
        'NAVINFLUOR', 'JBCHEPHARM', 'LAURUSLABS', 'DIXON', 'BSOFT',
        'MUTHOOTFIN', 'BIOCON', 'IPCALAB', 'NEULANDLAB', 'TTML',
        'IRCTC', 'INDIACEM', 'BAYERCROP', 'COROMANDEL'
    ]

    target_set = set(target_signals)
    entrants = [sym for sym in target_signals if sym not in holdings_before]

    print(f"Entrants (in signal order): {entrants}")
    print(f"Number of entrants: {len(entrants)}")
    print()

    # Cash from sells
    sells_notional = 41761.27 + 41517.53 + 36440.86 + 39479.07 + 34971.90
    slippage = 0.002
    cash = sells_notional * (1 - slippage)

    print(f"Cash from sells: ${cash:,.2f}")

    # Deployment parameters
    exposure = 1.0  # Assuming 100% exposure
    # In incremental mode:
    # deploy_cash = target_cash * exposure - (target_cash - cash)
    # Since we have no other holdings value (all in cash), this simplifies to cash * exposure
    deploy_cash = cash * exposure

    print(f"Deploy cash: ${deploy_cash:,.2f}")

    allocation = deploy_cash / len(entrants)
    print(f"Allocation per stock: ${allocation:,.2f}")
    print()

    # Get prices
    prices = {}
    for sym in entrants:
        csv_path = prices_dir / f"{sym}_day.csv"
        if not csv_path.exists():
            print(f"WARNING: {sym} price file not found")
            continue
        df = pd.read_csv(csv_path, parse_dates=["date"])
        row = df[df["date"] == pd.Timestamp("2020-07-17")]
        if row.empty:
            print(f"WARNING: {sym} no price on 2020-07-17")
            continue
        # Use OHLC/4 average
        price = (row.iloc[0]["open"] + row.iloc[0]["high"] +
                 row.iloc[0]["low"] + row.iloc[0]["close"]) / 4
        prices[sym] = price

    # Simulate buys
    cash_remaining = cash
    buys_executed = []
    buys_skipped = []

    for sym in entrants:
        if sym not in prices:
            buys_skipped.append((sym, "no_price"))
            continue

        price = prices[sym]
        shares = allocation / (price * (1 + slippage))
        cost = shares * price * (1 + slippage)

        print(f"{sym:15} price={price:8.2f} shares={shares:8.2f} cost={cost:12.2f} cash={cash_remaining:12.2f}", end="")

        if cost > cash_remaining:
            print(f" SKIP (insufficient cash, need ${cost - cash_remaining:.2f} more)")
            buys_skipped.append((sym, "insufficient_cash"))
        else:
            print(f" BUY")
            cash_remaining -= cost
            buys_executed.append(sym)

    print()
    print(f"Buys executed: {len(buys_executed)}")
    print(f"Buys skipped: {len(buys_skipped)}")
    if buys_skipped:
        print("Skipped stocks:")
        for sym, reason in buys_skipped:
            print(f"  {sym}: {reason}")
    print()
    print(f"Final cash: ${cash_remaining:,.2f}")

if __name__ == "__main__":
    simulate_rebalance()
