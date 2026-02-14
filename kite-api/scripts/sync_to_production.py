#!/usr/bin/env python3
"""
Sync local CSV data to production PostgreSQL database.

Usage:
    python scripts/sync_to_production.py --database-url "postgresql://..."

This script reads from local experiment directories and writes to
the specified PostgreSQL database (typically Railway production).
"""
import argparse
import glob
from datetime import date
from pathlib import Path
from typing import Optional

import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add parent directory to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.models.models import Base, Holding, EquityCurve, Metric, Trade


def get_latest_experiment_dir(data_dir: Path, universe: str = "nse500") -> Optional[Path]:
    """Find the most recent experiment directory for a universe."""
    if universe == "nse500":
        pattern = data_dir / "experiments" / "final_portfolio" / "final_portfolio_202*"
    elif universe == "nifty100":
        pattern = data_dir / "nifty_100_tests" / "nifty100_portfolio_202*"
    elif universe == "nifty250":
        pattern = data_dir / "nifty_250_tests" / "nifty250_portfolio_202*"
    else:
        return None

    dirs = sorted(glob.glob(str(pattern)), reverse=True)

    for d in dirs:
        holdings_path = Path(d) / "backtests" / "baseline" / "momentum_holdings.csv"
        if holdings_path.exists():
            return Path(d)

    return None


def sync_holdings(db, data_dir: Path, universe: str = "nse500") -> dict:
    """Sync holdings from CSV to database."""
    exp_dir = get_latest_experiment_dir(data_dir, universe)
    if not exp_dir:
        return {"error": f"No experiment directory found for {universe}", "count": 0}

    holdings_path = exp_dir / "backtests" / "baseline" / "momentum_holdings.csv"
    if not holdings_path.exists():
        return {"error": f"Holdings file not found: {holdings_path}", "count": 0}

    print(f"  Reading holdings from: {holdings_path}")
    df = pd.read_csv(holdings_path)
    snapshot_date = date.today()

    # Delete existing holdings for this universe and date
    deleted = db.query(Holding).filter(
        Holding.universe == universe,
        Holding.snapshot_date == snapshot_date
    ).delete()
    print(f"  Deleted {deleted} existing holdings for {universe} on {snapshot_date}")

    # Insert new holdings
    count = 0
    for _, row in df.iterrows():
        holding = Holding(
            universe=universe,
            snapshot_date=snapshot_date,
            symbol=row["symbol"],
            shares=float(row["shares"]),
            avg_cost=float(row["avg_cost"]),
            entry_date=pd.to_datetime(row["entry_date"]).date(),
            entry_rank=int(row["entry_rank"]),
            holding_days=int(row["holding_days"]),
            last_price=float(row["last_price"]),
            pnl_pct=float(row["pnl_pct"]),
            notional=float(row["notional"]),
            contribution_pct=float(row["contribution_pct"]),
        )
        db.add(holding)
        count += 1

    db.commit()
    return {"universe": universe, "count": count, "snapshot_date": str(snapshot_date)}


def sync_equity_curve(db, data_dir: Path, universe: str = "nse500") -> dict:
    """Sync equity curve from CSV to database."""
    exp_dir = get_latest_experiment_dir(data_dir, universe)
    if not exp_dir:
        return {"error": f"No experiment directory found for {universe}", "count": 0}

    equity_path = exp_dir / "backtests" / "baseline" / "momentum_equity.csv"
    if not equity_path.exists():
        return {"error": f"Equity file not found: {equity_path}", "count": 0}

    print(f"  Reading equity curve from: {equity_path}")
    df = pd.read_csv(equity_path, parse_dates=["date"])

    # Get existing dates to avoid duplicates
    existing_dates = set(
        row[0] for row in db.query(EquityCurve.date).filter(
            EquityCurve.universe == universe
        ).all()
    )
    print(f"  Found {len(existing_dates)} existing equity curve records")

    count = 0
    for _, row in df.iterrows():
        row_date = row["date"].date() if hasattr(row["date"], "date") else row["date"]

        if row_date in existing_dates:
            continue

        equity = EquityCurve(
            universe=universe,
            date=row_date,
            portfolio_value=float(row.get("portfolio_value", row.get("value", 0))),
            benchmark=float(row.get("benchmark", row.get("benchmark_value", 0))) if "benchmark" in row or "benchmark_value" in row else None,
            drawdown=float(row.get("drawdown", 0)) if "drawdown" in row else None,
        )
        db.add(equity)
        count += 1

    db.commit()
    return {"universe": universe, "count": count}


def sync_metrics(db, data_dir: Path, universe: str = "nse500") -> dict:
    """Sync metrics from CSV to database."""
    exp_dir = get_latest_experiment_dir(data_dir, universe)
    if not exp_dir:
        return {"error": f"No experiment directory found for {universe}", "count": 0}

    metrics_path = exp_dir / "backtests" / "baseline" / "momentum_metrics.csv"
    if not metrics_path.exists():
        return {"error": f"Metrics file not found: {metrics_path}", "count": 0}

    print(f"  Reading metrics from: {metrics_path}")
    df = pd.read_csv(metrics_path)

    # Handle both formats: single row with columns, or two-column metric/value format
    if "metric" in df.columns and "value" in df.columns:
        metrics_dict = dict(zip(df["metric"], df["value"]))
    else:
        # Single row format - columns are the metric names
        metrics_dict = df.iloc[0].to_dict()

    computed_date = date.today()

    # Delete existing metrics for this universe and date
    deleted = db.query(Metric).filter(
        Metric.universe == universe,
        Metric.computed_date == computed_date
    ).delete()
    print(f"  Deleted {deleted} existing metrics for {universe} on {computed_date}")

    metric = Metric(
        universe=universe,
        computed_date=computed_date,
        start_date=pd.to_datetime(metrics_dict.get("start")).date() if "start" in metrics_dict else None,
        end_date=pd.to_datetime(metrics_dict.get("end")).date() if "end" in metrics_dict else None,
        total_return=float(metrics_dict.get("total_return", 0)),
        cagr=float(metrics_dict.get("cagr", 0)),
        max_drawdown=float(metrics_dict.get("max_drawdown", 0)),
        max_drawdown_duration=int(metrics_dict.get("max_drawdown_duration_days", 0)) if "max_drawdown_duration_days" in metrics_dict else None,
        avg_turnover_pct=float(metrics_dict.get("avg_turnover_pct", 0)) if "avg_turnover_pct" in metrics_dict else None,
        annualized_turnover=float(metrics_dict.get("annualized_turnover", 0)) if "annualized_turnover" in metrics_dict else None,
        hit_rate=float(metrics_dict.get("hit_rate_overall", 0)) if "hit_rate_overall" in metrics_dict else None,
        avg_holding_days=float(metrics_dict.get("avg_holding_days", 0)) if "avg_holding_days" in metrics_dict else None,
        trades_total=int(metrics_dict.get("trades_total", 0)) if "trades_total" in metrics_dict else None,
        buys=int(metrics_dict.get("buys", 0)) if "buys" in metrics_dict else None,
        sells=int(metrics_dict.get("sells", 0)) if "sells" in metrics_dict else None,
    )
    db.add(metric)
    db.commit()

    return {"universe": universe, "count": 1, "computed_date": str(computed_date)}


def sync_trades(db, data_dir: Path, universe: str = "nse500") -> dict:
    """Sync trades from CSV to database."""
    exp_dir = get_latest_experiment_dir(data_dir, universe)
    if not exp_dir:
        return {"error": f"No experiment directory found for {universe}", "count": 0}

    trades_path = exp_dir / "backtests" / "baseline" / "momentum_trades.csv"
    if not trades_path.exists():
        return {"error": f"Trades file not found: {trades_path}", "count": 0}

    print(f"  Reading trades from: {trades_path}")
    df = pd.read_csv(trades_path, parse_dates=["date"])

    # Check existing trade count
    existing_count = db.query(Trade).filter(Trade.universe == universe).count()
    print(f"  Found {existing_count} existing trades")

    # If we already have trades, only add new ones
    if existing_count > 0:
        from sqlalchemy import desc
        last_trade = db.query(Trade).filter(
            Trade.universe == universe
        ).order_by(desc(Trade.trade_date)).first()

        if last_trade:
            df = df[df["date"] > pd.Timestamp(last_trade.trade_date)]
            print(f"  Adding trades after {last_trade.trade_date}")

    count = 0
    for _, row in df.iterrows():
        row_date = row["date"].date() if hasattr(row["date"], "date") else row["date"]

        trade = Trade(
            universe=universe,
            trade_date=row_date,
            symbol=row["symbol"],
            side=row["side"],
            shares=float(row["shares"]),
            price=float(row["price"]),
            notional=float(row["notional"]),
            slippage=float(row.get("slippage", 0)) if "slippage" in row else None,
            cash_after=float(row.get("cash_after", 0)) if "cash_after" in row else None,
        )
        db.add(trade)
        count += 1

    db.commit()
    return {"universe": universe, "count": count, "total": existing_count + count}


def main():
    parser = argparse.ArgumentParser(description="Sync local CSV data to production database")
    parser.add_argument(
        "--database-url",
        required=True,
        help="PostgreSQL database URL (e.g., postgresql://user:pass@host:port/db)"
    )
    parser.add_argument(
        "--universe",
        default="all",
        choices=["nse500", "nifty100", "nifty250", "all"],
        help="Universe to sync (default: all)"
    )
    parser.add_argument(
        "--data-dir",
        default=None,
        help="Path to kite-dashboard directory (default: auto-detect)"
    )
    args = parser.parse_args()

    # Determine data directory
    if args.data_dir:
        data_dir = Path(args.data_dir)
    else:
        # Auto-detect: this script is in kite-api/scripts/, data is in kite-dashboard/
        data_dir = Path(__file__).parent.parent.parent / "kite-dashboard"

    if not data_dir.exists():
        print(f"Error: Data directory not found: {data_dir}")
        sys.exit(1)

    print(f"Data directory: {data_dir}")
    print(f"Database: {args.database_url.split('@')[-1]}")  # Hide credentials
    print()

    # Create database connection
    engine = create_engine(args.database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()

    # Ensure tables exist
    Base.metadata.create_all(bind=engine)

    universes = ["nse500", "nifty100", "nifty250"] if args.universe == "all" else [args.universe]

    results = {}
    for universe in universes:
        print(f"Syncing {universe}...")
        results[universe] = {
            "holdings": sync_holdings(db, data_dir, universe),
            "equity_curve": sync_equity_curve(db, data_dir, universe),
            "metrics": sync_metrics(db, data_dir, universe),
            "trades": sync_trades(db, data_dir, universe),
        }
        print()

    db.close()

    # Print summary
    print("=" * 50)
    print("SYNC COMPLETE")
    print("=" * 50)
    for universe, data in results.items():
        print(f"\n{universe.upper()}:")
        print(f"  Holdings: {data['holdings'].get('count', 0)} records")
        print(f"  Equity curve: {data['equity_curve'].get('count', 0)} new records")
        print(f"  Metrics: {data['metrics'].get('count', 0)} records")
        print(f"  Trades: {data['trades'].get('count', 0)} new ({data['trades'].get('total', 0)} total)")


if __name__ == "__main__":
    main()
