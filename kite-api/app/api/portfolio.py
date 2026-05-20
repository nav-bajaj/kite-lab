"""
Portfolio API endpoints

Reads from database first, falls back to CSV files if database is empty.
All endpoints require authentication.
"""
from fastapi import APIRouter, Query, HTTPException, Depends

from app.config import is_valid_universe, UniverseId
from app.auth import get_current_user
from app.middleware.cache import cache_daily

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


def get_portfolio_service():
    """Get the appropriate portfolio service (DB or CSV)."""
    # Try database service first
    try:
        from app.services.portfolio_db_service import (
            get_portfolio_summary_db,
            get_holdings_db,
            get_allocation_db,
        )
        return {
            "get_summary": get_portfolio_summary_db,
            "get_holdings": get_holdings_db,
            "get_allocation": get_allocation_db,
            "source": "database",
        }
    except ImportError:
        pass

    # Fall back to CSV service
    try:
        from app.services.portfolio_service import (
            get_portfolio_summary,
            get_holdings,
            get_allocation,
        )
        return {
            "get_summary": get_portfolio_summary,
            "get_holdings": lambda u: get_holdings(u),
            "get_allocation": get_allocation,
            "source": "csv",
        }
    except ImportError as e:
        return {
            "error": str(e),
            "source": None,
        }


@router.get("", dependencies=[Depends(cache_daily)])
async def portfolio_summary(
    universe: UniverseId = Query(default="nse500", description="Portfolio universe"),
    user: dict = Depends(get_current_user)
):
    """
    Get portfolio summary for a universe.

    Returns total value, P&L, holdings count, and key metrics.
    """
    if not is_valid_universe(universe):
        raise HTTPException(status_code=400, detail=f"Invalid universe: {universe}")

    service = get_portfolio_service()

    if "error" in service:
        return {
            "error": f"Portfolio service not available: {service['error']}",
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

    result = service["get_summary"](universe)
    result["data_source"] = service["source"]
    return result


@router.get("/holdings", dependencies=[Depends(cache_daily)])
async def portfolio_holdings(
    universe: UniverseId = Query(default="nse500", description="Portfolio universe"),
    user: dict = Depends(get_current_user)
):
    """
    Get current holdings for a universe.

    Returns list of holdings with P&L and allocation info.
    """
    if not is_valid_universe(universe):
        raise HTTPException(status_code=400, detail=f"Invalid universe: {universe}")

    service = get_portfolio_service()

    if "error" in service:
        return {
            "holdings": [],
            "summary": {"total_pnl": 0, "winners": 0, "losers": 0},
            "error": f"Portfolio service not available: {service['error']}",
        }

    result = service["get_holdings"](universe)
    result["data_source"] = service["source"]
    return result


@router.get("/allocation", dependencies=[Depends(cache_daily)])
async def portfolio_allocation(
    universe: UniverseId = Query(default="nse500", description="Portfolio universe"),
    user: dict = Depends(get_current_user)
):
    """
    Get allocation breakdown for a universe.

    Returns allocation by symbol for pie chart visualization.
    """
    if not is_valid_universe(universe):
        raise HTTPException(status_code=400, detail=f"Invalid universe: {universe}")

    service = get_portfolio_service()

    if "error" in service:
        return {
            "allocations": [],
            "error": f"Portfolio service not available: {service['error']}",
        }

    result = service["get_allocation"](universe)
    result["data_source"] = service["source"]
    return result
