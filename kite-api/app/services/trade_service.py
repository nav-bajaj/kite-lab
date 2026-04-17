"""
Trade Service - Query and export trade history from database.
"""
from datetime import date
from typing import Optional, List
import io
import csv

from sqlalchemy import desc, func, case
from sqlalchemy.orm import Session

from app.models.database import get_session_local
from app.models.models import Trade, TradeMatch


def get_trades(
    universe: str = "nse500",
    limit: int = 50,
    offset: int = 0,
    symbol: Optional[str] = None,
    side: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> dict:
    """
    Get paginated trade history for a universe.

    Args:
        universe: Portfolio universe (nse500, nifty100, nifty250)
        limit: Number of trades to return (max 500)
        offset: Pagination offset
        symbol: Filter by symbol (partial match)
        side: Filter by side (BUY or SELL)
        start_date: Filter trades on or after this date
        end_date: Filter trades on or before this date

    Returns:
        Dict with trades list, total count, and pagination info.
    """
    SessionLocal = get_session_local()
    db = SessionLocal()

    try:
        # Build base query
        query = db.query(Trade).filter(Trade.universe == universe)

        # Apply filters
        if symbol:
            query = query.filter(Trade.symbol.ilike(f"%{symbol}%"))
        if side:
            query = query.filter(Trade.side == side.upper())
        if start_date:
            query = query.filter(Trade.trade_date >= start_date)
        if end_date:
            query = query.filter(Trade.trade_date <= end_date)

        # Get total count before pagination
        total_count = query.count()

        # Apply pagination and ordering
        query = query.order_by(desc(Trade.trade_date), desc(Trade.id))
        query = query.offset(offset).limit(min(limit, 500))

        trades = query.all()

        # Batch-fetch matches for any SELL trades on this page
        sell_ids = [t.id for t in trades if t.side == "SELL"]
        matches_by_sell: dict[int, list[dict]] = {}
        if sell_ids:
            match_rows = (
                db.query(TradeMatch)
                .filter(TradeMatch.sell_trade_id.in_(sell_ids))
                .order_by(TradeMatch.id.asc())
                .all()
            )
            for m in match_rows:
                matches_by_sell.setdefault(m.sell_trade_id, []).append({
                    "buy_trade_id": m.buy_trade_id,
                    "entry_date": str(m.entry_date),
                    "entry_price": round(float(m.entry_price), 4),
                    "shares_matched": round(float(m.shares_matched), 6),
                    "holding_days": m.holding_days,
                    "realized_pnl": round(float(m.realized_pnl), 2),
                    "realized_pnl_pct": round(float(m.realized_pnl_pct), 4),
                })

        # Format response
        trade_list = []
        for t in trades:
            row = {
                "id": t.id,
                "date": str(t.trade_date),
                "symbol": t.symbol,
                "side": t.side,
                "shares": round(float(t.shares), 2),
                "price": round(float(t.price), 2),
                "notional": round(float(t.notional), 2),
                "slippage": round(float(t.slippage), 2) if t.slippage else 0,
            }
            if t.side == "SELL":
                row["matches"] = matches_by_sell.get(t.id, [])
            trade_list.append(row)

        return {
            "universe": universe,
            "trades": trade_list,
            "total_count": total_count,
            "limit": limit,
            "offset": offset,
            "has_more": offset + len(trades) < total_count,
        }
    finally:
        db.close()


def get_trade_summary(universe: str = "nse500") -> dict:
    """
    Get summary statistics for trades in a universe.
    """
    SessionLocal = get_session_local()
    db = SessionLocal()

    try:
        # Total counts
        total = db.query(Trade).filter(Trade.universe == universe).count()
        buys = db.query(Trade).filter(
            Trade.universe == universe,
            Trade.side == "BUY"
        ).count()
        sells = db.query(Trade).filter(
            Trade.universe == universe,
            Trade.side == "SELL"
        ).count()

        # Date range
        first_trade = db.query(Trade).filter(
            Trade.universe == universe
        ).order_by(Trade.trade_date).first()

        last_trade = db.query(Trade).filter(
            Trade.universe == universe
        ).order_by(desc(Trade.trade_date)).first()

        # Total notional
        total_notional = db.query(func.sum(Trade.notional)).filter(
            Trade.universe == universe
        ).scalar() or 0

        # Realized P&L stats from trade_matches
        winner_expr = case((TradeMatch.realized_pnl > 0, 1), else_=0)
        loser_expr = case((TradeMatch.realized_pnl < 0, 1), else_=0)
        winner_pct = case(
            (TradeMatch.realized_pnl > 0, TradeMatch.realized_pnl_pct), else_=None
        )
        loser_pct = case(
            (TradeMatch.realized_pnl < 0, TradeMatch.realized_pnl_pct), else_=None
        )

        match_stats = db.query(
            func.sum(TradeMatch.realized_pnl).label("pnl_total"),
            func.count(TradeMatch.id).label("match_count"),
            func.sum(winner_expr).label("winners"),
            func.sum(loser_expr).label("losers"),
            func.avg(TradeMatch.holding_days).label("avg_hold"),
            func.max(TradeMatch.realized_pnl_pct).label("best_pct"),
            func.min(TradeMatch.realized_pnl_pct).label("worst_pct"),
            func.avg(winner_pct).label("avg_winner_pct"),
            func.avg(loser_pct).label("avg_loser_pct"),
        ).filter(TradeMatch.universe == universe).one()

        match_count = int(match_stats.match_count or 0)
        winners = int(match_stats.winners or 0)

        realized_pnl_total = float(match_stats.pnl_total) if match_stats.pnl_total is not None else None
        win_rate = (winners / match_count * 100) if match_count > 0 else None
        avg_holding_days = float(match_stats.avg_hold) if match_stats.avg_hold is not None else None
        best_trade_pct = float(match_stats.best_pct) if match_stats.best_pct is not None else None
        worst_trade_pct = float(match_stats.worst_pct) if match_stats.worst_pct is not None else None
        avg_winner_pct = float(match_stats.avg_winner_pct) if match_stats.avg_winner_pct is not None else None
        avg_loser_pct = float(match_stats.avg_loser_pct) if match_stats.avg_loser_pct is not None else None

        return {
            "universe": universe,
            "total_trades": total,
            "buys": buys,
            "sells": sells,
            "first_trade_date": str(first_trade.trade_date) if first_trade else None,
            "last_trade_date": str(last_trade.trade_date) if last_trade else None,
            "total_notional": round(float(total_notional), 2),
            "realized_pnl_total": round(realized_pnl_total, 2) if realized_pnl_total is not None else None,
            "win_rate": round(win_rate, 2) if win_rate is not None else None,
            "avg_holding_days": round(avg_holding_days, 1) if avg_holding_days is not None else None,
            "best_trade_pct": round(best_trade_pct, 2) if best_trade_pct is not None else None,
            "worst_trade_pct": round(worst_trade_pct, 2) if worst_trade_pct is not None else None,
            "avg_winner_pct": round(avg_winner_pct, 2) if avg_winner_pct is not None else None,
            "avg_loser_pct": round(avg_loser_pct, 2) if avg_loser_pct is not None else None,
        }
    finally:
        db.close()


def export_trades_csv(
    universe: str = "nse500",
    symbol: Optional[str] = None,
    side: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> str:
    """
    Export trades to CSV format.

    Returns CSV string.
    """
    SessionLocal = get_session_local()
    db = SessionLocal()

    try:
        query = db.query(Trade).filter(Trade.universe == universe)

        if symbol:
            query = query.filter(Trade.symbol.ilike(f"%{symbol}%"))
        if side:
            query = query.filter(Trade.side == side.upper())
        if start_date:
            query = query.filter(Trade.trade_date >= start_date)
        if end_date:
            query = query.filter(Trade.trade_date <= end_date)

        query = query.order_by(Trade.trade_date, Trade.id)
        trades = query.all()

        # Create CSV
        output = io.StringIO()
        writer = csv.writer(output)

        # Header
        writer.writerow([
            "date", "symbol", "side", "shares", "price", "notional", "slippage"
        ])

        # Data rows
        for t in trades:
            writer.writerow([
                str(t.trade_date),
                t.symbol,
                t.side,
                round(float(t.shares), 6),
                round(float(t.price), 4),
                round(float(t.notional), 2),
                round(float(t.slippage), 4) if t.slippage else 0,
            ])

        return output.getvalue()
    finally:
        db.close()


def get_recent_trades(universe: str = "nse500", days: int = 7) -> dict:
    """
    Get trades from the last N days.
    """
    from datetime import timedelta

    SessionLocal = get_session_local()
    db = SessionLocal()

    try:
        cutoff_date = date.today() - timedelta(days=days)

        trades = db.query(Trade).filter(
            Trade.universe == universe,
            Trade.trade_date >= cutoff_date
        ).order_by(desc(Trade.trade_date), Trade.symbol).all()

        trade_list = []
        for t in trades:
            trade_list.append({
                "id": t.id,
                "date": str(t.trade_date),
                "symbol": t.symbol,
                "side": t.side,
                "shares": round(float(t.shares), 2),
                "price": round(float(t.price), 2),
                "notional": round(float(t.notional), 2),
            })

        return {
            "universe": universe,
            "trades": trade_list,
            "count": len(trade_list),
            "since": str(cutoff_date),
        }
    finally:
        db.close()
