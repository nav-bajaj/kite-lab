"""
Portfolio API endpoints
"""
from fastapi import APIRouter, Query, HTTPException

from app.config import is_valid_universe, UniverseId
from app.services.portfolio_service import (
    get_portfolio_summary,
    get_holdings,
    get_allocation,
)

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


@router.get("")
async def portfolio_summary(
    universe: UniverseId = Query(default="nse500", description="Portfolio universe")
):
    """
    Get portfolio summary for a universe.

    Returns total value, P&L, holdings count, and key metrics.
    """
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
    if not is_valid_universe(universe):
        raise HTTPException(status_code=400, detail=f"Invalid universe: {universe}")

    return get_allocation(universe)
