"""
Portfolio Service - Reads holdings and calculates portfolio metrics
"""
import os
import glob
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd

from app.config import settings, UNIVERSE_DEFAULTS


def get_latest_experiment_dir(universe: str = "nse500") -> Optional[Path]:
    """Find the most recent experiment directory for a universe."""
    base_dir = settings.data_dir

    if universe == "nse500":
        pattern = base_dir / "experiments" / "final_portfolio" / "final_portfolio_202*"
    elif universe == "nifty100":
        pattern = base_dir / "nifty_100_tests" / "nifty100_portfolio_202*"
    elif universe == "nifty250":
        pattern = base_dir / "nifty_250_tests" / "nifty250_portfolio_202*"
    else:
        return None

    dirs = sorted(glob.glob(str(pattern)), reverse=True)

    # Find one that has the holdings file
    for d in dirs:
        holdings_path = Path(d) / "backtests" / "baseline" / "momentum_holdings.csv"
        if holdings_path.exists():
            return Path(d)

    return None


def get_holdings_path(universe: str = "nse500") -> Optional[Path]:
    """Get path to holdings CSV for a universe."""
    exp_dir = get_latest_experiment_dir(universe)
    if exp_dir:
        return exp_dir / "backtests" / "baseline" / "momentum_holdings.csv"
    return None


def get_equity_curve_path(universe: str = "nse500") -> Optional[Path]:
    """Get path to equity curve CSV for a universe."""
    exp_dir = get_latest_experiment_dir(universe)
    if exp_dir:
        return exp_dir / "backtests" / "baseline" / "momentum_equity.csv"
    return None


def get_metrics_path(universe: str = "nse500") -> Optional[Path]:
    """Get path to metrics CSV for a universe."""
    exp_dir = get_latest_experiment_dir(universe)
    if exp_dir:
        return exp_dir / "backtests" / "baseline" / "momentum_metrics.csv"
    return None


def get_trades_path(universe: str = "nse500") -> Optional[Path]:
    """Get path to trades CSV for a universe."""
    exp_dir = get_latest_experiment_dir(universe)
    if exp_dir:
        return exp_dir / "backtests" / "baseline" / "momentum_trades.csv"
    return None


def get_latest_price(symbol: str) -> Optional[float]:
    """Get the latest closing price for a symbol."""
    price_file = settings.data_dir / "nse500_data" / f"{symbol}_day.csv"
    if not price_file.exists():
        return None

    try:
        df = pd.read_csv(price_file)
        if len(df) > 0:
            return float(df.iloc[-1]["close"])
    except Exception:
        pass

    return None


def get_portfolio_summary(universe: str = "nse500") -> dict:
    """
    Get portfolio summary for a universe.

    Returns dict with:
    - total_value: Total portfolio value
    - cash: Cash balance (assumed 0 for fully invested)
    - invested: Total invested value
    - daily_pnl: Today's P&L (placeholder)
    - daily_pnl_pct: Today's P&L percentage
    - total_return: Total return amount
    - total_return_pct: Total return percentage
    - holdings_count: Number of holdings
    - as_of_date: Date of the data
    """
    holdings_path = get_holdings_path(universe)

    if not holdings_path or not holdings_path.exists():
        return {
            "total_value": 0,
            "cash": 0,
            "invested": 0,
            "daily_pnl": 0,
            "daily_pnl_pct": 0,
            "total_return": 0,
            "total_return_pct": 0,
            "holdings_count": 0,
            "as_of_date": datetime.now().strftime("%Y-%m-%d"),
            "universe": universe,
            "error": "No holdings data found"
        }

    df = pd.read_csv(holdings_path)

    # Calculate totals
    total_value = df["notional"].sum()
    total_cost = (df["shares"] * df["avg_cost"]).sum()
    total_return = total_value - total_cost
    total_return_pct = (total_return / total_cost) * 100 if total_cost > 0 else 0

    # Get metrics for more accurate data
    metrics_path = get_metrics_path(universe)
    cagr = None
    max_dd = None
    sharpe = None

    if metrics_path and metrics_path.exists():
        try:
            metrics_df = pd.read_csv(metrics_path)
            metrics_dict = dict(zip(metrics_df["metric"], metrics_df["value"]))
            cagr = float(metrics_dict.get("cagr", 0)) * 100
            max_dd = float(metrics_dict.get("max_drawdown", 0)) * 100
            sharpe = float(metrics_dict.get("sharpe_ratio", 0))
        except Exception:
            pass

    return {
        "total_value": round(total_value, 2),
        "cash": 0,
        "invested": round(total_cost, 2),
        "daily_pnl": 0,  # Would need intraday data
        "daily_pnl_pct": 0,
        "total_return": round(total_return, 2),
        "total_return_pct": round(total_return_pct, 2),
        "holdings_count": len(df),
        "as_of_date": datetime.now().strftime("%Y-%m-%d"),
        "universe": universe,
        "cagr": cagr,
        "max_drawdown": max_dd,
        "sharpe_ratio": sharpe,
    }


def get_holdings(universe: str = "nse500", update_prices: bool = False) -> dict:
    """
    Get holdings list for a universe.

    Returns dict with:
    - holdings: List of holding dicts
    - summary: Summary statistics
    """
    holdings_path = get_holdings_path(universe)

    if not holdings_path or not holdings_path.exists():
        return {
            "holdings": [],
            "summary": {
                "total_pnl": 0,
                "winners": 0,
                "losers": 0,
            },
            "error": "No holdings data found"
        }

    df = pd.read_csv(holdings_path)

    holdings = []
    for _, row in df.iterrows():
        current_price = row["last_price"]

        # Optionally update with latest prices
        if update_prices:
            latest = get_latest_price(row["symbol"])
            if latest:
                current_price = latest

        notional = row["shares"] * current_price
        cost_basis = row["shares"] * row["avg_cost"]
        pnl = notional - cost_basis
        pnl_pct = (pnl / cost_basis) * 100 if cost_basis > 0 else 0

        holdings.append({
            "symbol": row["symbol"],
            "shares": round(row["shares"], 2),
            "avg_cost": round(row["avg_cost"], 2),
            "current_price": round(current_price, 2),
            "notional": round(notional, 2),
            "pnl": round(pnl, 2),
            "pnl_pct": round(pnl_pct, 2),
            "weight": round(row["contribution_pct"] * 100, 2),
            "entry_date": row["entry_date"],
            "holding_days": int(row["holding_days"]),
            "rank": int(row["entry_rank"]),
        })

    # Calculate summary
    total_pnl = sum(h["pnl"] for h in holdings)
    winners = sum(1 for h in holdings if h["pnl"] > 0)
    losers = sum(1 for h in holdings if h["pnl"] < 0)

    return {
        "holdings": holdings,
        "summary": {
            "total_pnl": round(total_pnl, 2),
            "winners": winners,
            "losers": losers,
        }
    }


def get_allocation(universe: str = "nse500") -> dict:
    """
    Get allocation breakdown for a universe.

    Returns dict with allocation by symbol and optionally by sector.
    """
    holdings = get_holdings(universe)

    if "error" in holdings:
        return {"allocations": [], "error": holdings["error"]}

    allocations = [
        {
            "symbol": h["symbol"],
            "weight": h["weight"],
            "notional": h["notional"],
        }
        for h in holdings["holdings"]
    ]

    # Sort by weight descending
    allocations.sort(key=lambda x: x["weight"], reverse=True)

    return {"allocations": allocations}
