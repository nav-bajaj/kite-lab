"""
Portfolio API endpoints
"""
from fastapi import APIRouter, Query, HTTPException

from app.config import is_valid_universe, UniverseId

# Import portfolio service with error handling
try:
    from app.services.portfolio_service import (
        get_portfolio_summary,
        get_holdings,
        get_allocation,
    )
    PORTFOLIO_SERVICE_AVAILABLE = True
except ImportError as e:
    PORTFOLIO_SERVICE_AVAILABLE = False
    IMPORT_ERROR = str(e)

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


@router.get("")
async def portfolio_summary(
    universe: UniverseId = Query(default="nse500", description="Portfolio universe")
):
    """
    Get portfolio summary for a universe.

    Returns total value, P&L, holdings count, and key metrics.
    """
    if not PORTFOLIO_SERVICE_AVAILABLE:
        return {
            "error": f"Portfolio service not available: {IMPORT_ERROR}",
            "total_value": 0,
            "cash": 0,
            "invested": 0,
            "daily_pnl": 0,
            "daily_pnl_pct": 0,
            "total_return": 0,
            "total_return_pct": 0,
            "holdings_count": 0,
            "as_of_date": "",
            "universe": universe,
            "cagr": None,
            "max_drawdown": None,
            "sharpe_ratio": None,
        }

    if not is_valid_universe(universe):
        raise HTTPException(status_code=400, detail=f"Invalid universe: {universe}")

    return get_portfolio_summary(universe)


@router.get("/holdings")
async def portfolio_holdings(
    universe: UniverseId = Query(default="nse500", description="Portfolio universe"),
    update_prices: bool = Query(default=False, description="Update with latest prices"),
):
    """
    Get current holdings for a universe.

    Returns list of holdings with P&L and allocation info.
    """
    if not PORTFOLIO_SERVICE_AVAILABLE:
        return {
            "holdings": [],
            "summary": {"total_pnl": 0, "winners": 0, "losers": 0},
            "error": f"Portfolio service not available: {IMPORT_ERROR}",
        }

    if not is_valid_universe(universe):
        raise HTTPException(status_code=400, detail=f"Invalid universe: {universe}")

    return get_holdings(universe, update_prices=update_prices)


@router.get("/allocation")
async def portfolio_allocation(
    universe: UniverseId = Query(default="nse500", description="Portfolio universe"),
):
    """
    Get allocation breakdown for a universe.

    Returns allocation by symbol for pie chart visualization.
    """
    if not PORTFOLIO_SERVICE_AVAILABLE:
        return {
            "allocations": [],
            "error": f"Portfolio service not available: {IMPORT_ERROR}",
        }

    if not is_valid_universe(universe):
        raise HTTPException(status_code=400, detail=f"Invalid universe: {universe}")

    return get_allocation(universe)
