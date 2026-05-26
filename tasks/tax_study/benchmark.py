"""Nifty 50 buy-and-hold benchmark for the tax study.

The B&H investor buys ₹X worth of NIFTY 50 at window start, holds for the
full period, sells at window end. Only one realized event (almost always LT
given multi-year horizons), one tax payment near the end. Massive deferral
advantage vs active strategies.

We construct a synthetic trades.csv with one BUY and one SELL and pass it
through the same `tax_engine` / `forced_sale` machinery used for the active
strategies, so the tax law is applied identically.
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

NIFTY50_PATH = Path("/Users/navdeep/Documents/stock_data/indices_data_full/NIFTY_50.csv")
BH_SLIPPAGE = 0.003  # match the 30 bps used in the strategy backtests


def load_nifty50(start: str | pd.Timestamp | None = None,
                  end: str | pd.Timestamp | None = None,
                  path: Path = NIFTY50_PATH) -> pd.DataFrame:
    """Load NIFTY 50 OHLC and clip to window."""
    df = pd.read_csv(path, parse_dates=["date"]).sort_values("date").reset_index(drop=True)
    if start is not None:
        df = df[df["date"] >= pd.Timestamp(start)]
    if end is not None:
        df = df[df["date"] <= pd.Timestamp(end)]
    return df.reset_index(drop=True)


def build_bh_trades(close_df: pd.DataFrame,
                     initial_capital: float = 1_000_000,
                     slip_rate: float = BH_SLIPPAGE) -> pd.DataFrame:
    """Generate a 2-row trades.csv: BUY at first close, SELL at last close.

    The cost-per-share-effective = price × (1 + slip_rate). Sized so that
    (notional + slip) ≈ initial_capital, i.e. the investor commits exactly the
    initial capital and any rounding leftover stays in cash.
    """
    start = close_df.iloc[0]
    end = close_df.iloc[-1]
    start_price = float(start["close"])
    end_price = float(end["close"])

    shares = initial_capital / (start_price * (1 + slip_rate))
    buy_notional = shares * start_price
    buy_slip = buy_notional * slip_rate

    sell_notional = shares * end_price
    sell_slip = sell_notional * slip_rate

    return pd.DataFrame([
        {"date": start["date"], "symbol": "NIFTY50", "side": "BUY",
         "shares": shares, "price": start_price, "notional": buy_notional,
         "slippage": buy_slip, "reason": "entry"},
        {"date": end["date"], "symbol": "NIFTY50", "side": "SELL",
         "shares": shares, "price": end_price, "notional": sell_notional,
         "slippage": sell_slip, "reason": "exit"},
    ])


def build_bh_equity(close_df: pd.DataFrame, trades: pd.DataFrame,
                     initial_capital: float = 1_000_000) -> pd.DataFrame:
    """Daily PV curve for B&H. Logic:
       day 0: cash drops by (notional + slip), shares acquired
       day t (0 < t < N-1): PV = cash + shares × close[t]
       day N-1: SELL → cash += notional - slip; PV = cash
    """
    buy = trades[trades["side"] == "BUY"].iloc[0]
    sell = trades[trades["side"] == "SELL"].iloc[0]
    shares = float(buy["shares"])
    buy_cash_out = float(buy["notional"] + buy["slippage"])
    sell_cash_in = float(sell["notional"] - sell["slippage"])

    df = close_df[["date", "close"]].copy().reset_index(drop=True)
    # Cash starts at initial_capital. At the buy date and after, cash is reduced.
    df["cash"] = initial_capital - buy_cash_out  # residual after buying
    df["holdings_val"] = shares * df["close"]
    # On the SELL date, we close out: cash += sell_cash_in, holdings → 0
    sell_idx = int(df.index[df["date"] == sell["date"]][0])
    df.loc[sell_idx:, "cash"] = (initial_capital - buy_cash_out) + sell_cash_in
    df.loc[sell_idx:, "holdings_val"] = 0.0

    df["pv"] = df["cash"] + df["holdings_val"]
    return df[["date", "pv", "cash"]].copy()
