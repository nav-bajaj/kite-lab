"""
Metrics API endpoints

Performance metrics, equity curve, and monthly returns.
All endpoints require authentication.
"""
from datetime import date
from typing import Optional

from fastapi import APIRouter, Query, HTTPException, Depends

from app.config import is_valid_universe, UniverseId
from app.services.metrics_service import get_metrics, get_equity_curve, get_monthly_returns
from app.auth import get_current_user

router = APIRouter(prefix="/api/metrics", tags=["metrics"])


@router.get("")
async def metrics_summary(
    universe: UniverseId = Query(default="nse500", description="Portfolio universe"),
    user: dict = Depends(get_current_user)
):
    """
    Get comprehensive performance metrics for a universe.

    Returns period info, returns, risk metrics, and activity stats.
    """
    if not is_valid_universe(universe):
        raise HTTPException(status_code=400, detail=f"Invalid universe: {universe}")

    result = get_metrics(universe)

    if "error" in result:
        return {
            "error": result["error"],
            "universe": universe,
            "period": {"start": None, "end": None, "days": 0},
            "returns": {"total_return": 0, "cagr": 0, "mtd": 0, "ytd": 0},
            "risk": {
                "max_drawdown": 0,
                "max_dd_duration": 0,
                "volatility": 0,
                "sharpe_ratio": 0,
                "sortino_ratio": 0,
                "calmar_ratio": 0
            },
            "activity": {
                "total_trades": 0,
                "avg_turnover": 0,
                "annualized_turnover": 0,
                "avg_holding_days": 0,
                "hit_rate": 0
            }
        }

    return result


@router.get("/equity-curve")
async def equity_curve(
    universe: UniverseId = Query(default="nse500", description="Portfolio universe"),
    start: Optional[date] = Query(default=None, description="Start date (YYYY-MM-DD)"),
    end: Optional[date] = Query(default=None, description="End date (YYYY-MM-DD)"),
    user: dict = Depends(get_current_user)
):
    """
    Get equity curve data for charting.

    Returns daily portfolio value, benchmark value, and drawdown percentage.
    Supports optional date range filtering.
    """
    if not is_valid_universe(universe):
        raise HTTPException(status_code=400, detail=f"Invalid universe: {universe}")

    result = get_equity_curve(universe, start, end)
    return result


@router.get("/monthly-returns")
async def monthly_returns(
    universe: UniverseId = Query(default="nse500", description="Portfolio universe"),
    user: dict = Depends(get_current_user)
):
    """
    Get monthly returns matrix for heatmap display.

    Returns returns for each month organized by year.
    """
    if not is_valid_universe(universe):
        raise HTTPException(status_code=400, detail=f"Invalid universe: {universe}")

    result = get_monthly_returns(universe)
    return result
