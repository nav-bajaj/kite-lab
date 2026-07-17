"""
Portfolio DB Service - Read portfolio data from PostgreSQL database
"""
from datetime import datetime, date
from typing import Optional

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models.database import get_session_local
from app.models.models import Holding, Metric, EquityCurve
from app.insights.zerodha_sectors import get_sector_for


def get_latest_snapshot_date(db: Session, universe: str) -> Optional[date]:
    """Get the most recent snapshot date for a universe."""
    result = db.query(Holding.snapshot_date).filter(
        Holding.universe == universe
    ).order_by(desc(Holding.snapshot_date)).first()

    return result[0] if result else None


def get_portfolio_summary_db(universe: str = "nse500") -> dict:
    """
    Get portfolio summary from database.
    """
    SessionLocal = get_session_local()
    db = SessionLocal()

    try:
        snapshot_date = get_latest_snapshot_date(db, universe)

        if not snapshot_date:
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
                "cagr": None,
                "max_drawdown": None,
                "sharpe_ratio": None,
                "error": "No holdings data found in database"
            }

        # Get holdings
        holdings = db.query(Holding).filter(
            Holding.universe == universe,
            Holding.snapshot_date == snapshot_date
        ).all()

        # Calculate totals
        total_value = sum(float(h.notional) for h in holdings)
        total_cost = sum(float(h.shares) * float(h.avg_cost) for h in holdings)
        total_return = total_value - total_cost
        total_return_pct = (total_return / total_cost) * 100 if total_cost > 0 else 0

        # Get metrics
        metric = db.query(Metric).filter(
            Metric.universe == universe
        ).order_by(desc(Metric.computed_date)).first()

        cagr = float(metric.cagr) * 100 if metric and metric.cagr else None
        max_dd = float(metric.max_drawdown) * 100 if metric and metric.max_drawdown else None
        sharpe = float(metric.sharpe_ratio) if metric and metric.sharpe_ratio else None

        return {
            "total_value": round(total_value, 2),
            "cash": 0,
            "invested": round(total_cost, 2),
            "daily_pnl": 0,
            "daily_pnl_pct": 0,
            "total_return": round(total_return, 2),
            "total_return_pct": round(total_return_pct, 2),
            "holdings_count": len(holdings),
            "as_of_date": str(snapshot_date),
            "universe": universe,
            "cagr": cagr,
            "max_drawdown": max_dd,
            "sharpe_ratio": sharpe,
        }
    finally:
        db.close()


def get_holdings_db(universe: str = "nse500") -> dict:
    """
    Get holdings list from database.
    """
    SessionLocal = get_session_local()
    db = SessionLocal()

    try:
        snapshot_date = get_latest_snapshot_date(db, universe)

        if not snapshot_date:
            return {
                "holdings": [],
                "summary": {"total_pnl": 0, "winners": 0, "losers": 0},
                "error": "No holdings data found in database"
            }

        holdings_rows = db.query(Holding).filter(
            Holding.universe == universe,
            Holding.snapshot_date == snapshot_date
        ).order_by(desc(Holding.contribution_pct)).all()

        holdings = []
        for h in holdings_rows:
            notional = float(h.notional)
            cost_basis = float(h.shares) * float(h.avg_cost)
            pnl = notional - cost_basis
            pnl_pct = float(h.pnl_pct) * 100

            holdings.append({
                "symbol": h.symbol,
                "shares": round(float(h.shares), 2),
                "avg_cost": round(float(h.avg_cost), 2),
                "current_price": round(float(h.last_price), 2),
                "notional": round(notional, 2),
                "pnl": round(pnl, 2),
                "pnl_pct": round(pnl_pct, 2),
                "weight": round(float(h.contribution_pct) * 100, 2),
                "entry_date": str(h.entry_date),
                "holding_days": int(h.holding_days),
                "rank": int(h.entry_rank),
                "sector": get_sector_for(h.symbol),
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
    finally:
        db.close()


def get_allocation_db(universe: str = "nse500") -> dict:
    """
    Get allocation breakdown from database.
    """
    holdings = get_holdings_db(universe)

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

    allocations.sort(key=lambda x: x["weight"], reverse=True)

    return {"allocations": allocations}
