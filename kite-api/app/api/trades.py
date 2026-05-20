"""
Trades API endpoints

Trade history with filtering, pagination, and CSV export.
All endpoints require authentication.
"""
from datetime import date
from typing import Optional

from fastapi import APIRouter, Query, HTTPException, Depends
from fastapi.responses import StreamingResponse
import io

from app.config import is_valid_universe, UniverseId
from app.services.trade_service import (
    get_trades,
    get_trade_summary,
    export_trades_csv,
    get_recent_trades,
)
from app.auth import get_current_user
from app.middleware.cache import cache_daily

router = APIRouter(prefix="/api/trades", tags=["trades"])


@router.get("", dependencies=[Depends(cache_daily)])
async def list_trades(
    universe: UniverseId = Query(default="nse500", description="Portfolio universe"),
    limit: int = Query(default=50, ge=1, le=500, description="Number of trades to return"),
    offset: int = Query(default=0, ge=0, description="Pagination offset"),
    symbol: Optional[str] = Query(default=None, description="Filter by symbol (partial match)"),
    side: Optional[str] = Query(default=None, description="Filter by side (BUY or SELL)"),
    start_date: Optional[date] = Query(default=None, description="Filter by start date"),
    end_date: Optional[date] = Query(default=None, description="Filter by end date"),
    user: dict = Depends(get_current_user)
):
    """
    Get paginated trade history for a universe.

    Supports filtering by symbol, side, and date range.
    """
    if not is_valid_universe(universe):
        raise HTTPException(status_code=400, detail=f"Invalid universe: {universe}")

    if side and side.upper() not in ["BUY", "SELL"]:
        raise HTTPException(status_code=400, detail="Side must be BUY or SELL")

    result = get_trades(
        universe=universe,
        limit=limit,
        offset=offset,
        symbol=symbol,
        side=side,
        start_date=start_date,
        end_date=end_date,
    )
    return result


@router.get("/summary", dependencies=[Depends(cache_daily)])
async def trade_summary(
    universe: UniverseId = Query(default="nse500", description="Portfolio universe"),
    user: dict = Depends(get_current_user)
):
    """
    Get summary statistics for trades.

    Returns total counts, date range, and total notional.
    """
    if not is_valid_universe(universe):
        raise HTTPException(status_code=400, detail=f"Invalid universe: {universe}")

    result = get_trade_summary(universe)
    return result


@router.get("/recent", dependencies=[Depends(cache_daily)])
async def recent_trades(
    universe: UniverseId = Query(default="nse500", description="Portfolio universe"),
    days: int = Query(default=7, ge=1, le=90, description="Number of days to look back"),
    user: dict = Depends(get_current_user)
):
    """
    Get trades from the last N days.
    """
    if not is_valid_universe(universe):
        raise HTTPException(status_code=400, detail=f"Invalid universe: {universe}")

    result = get_recent_trades(universe, days)
    return result


@router.get("/export", dependencies=[Depends(cache_daily)])
async def export_trades(
    universe: UniverseId = Query(default="nse500", description="Portfolio universe"),
    symbol: Optional[str] = Query(default=None, description="Filter by symbol"),
    side: Optional[str] = Query(default=None, description="Filter by side"),
    start_date: Optional[date] = Query(default=None, description="Filter by start date"),
    end_date: Optional[date] = Query(default=None, description="Filter by end date"),
    user: dict = Depends(get_current_user)
):
    """
    Export trades as CSV file.

    Returns a downloadable CSV file with all matching trades.
    """
    if not is_valid_universe(universe):
        raise HTTPException(status_code=400, detail=f"Invalid universe: {universe}")

    csv_content = export_trades_csv(
        universe=universe,
        symbol=symbol,
        side=side,
        start_date=start_date,
        end_date=end_date,
    )

    # Create filename with filters
    filename = f"trades_{universe}"
    if start_date:
        filename += f"_from_{start_date}"
    if end_date:
        filename += f"_to_{end_date}"
    filename += ".csv"

    return StreamingResponse(
        io.StringIO(csv_content),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
