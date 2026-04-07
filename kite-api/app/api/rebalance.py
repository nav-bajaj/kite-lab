"""
Rebalance API endpoints

Weekly rebalance workflow: Thursday preview, Friday orders.
All endpoints require authentication.
"""
from fastapi import APIRouter, Query, HTTPException, Depends
from fastapi.responses import StreamingResponse
import io

from app.config import is_valid_universe, UniverseId
from app.services.rebalance_service import (
    get_rebalance_status,
    get_rebalance_preview,
    get_rebalance_orders,
    get_rebalance_history,
    export_orders_csv,
)
from app.auth import get_current_user

router = APIRouter(prefix="/api/rebalance", tags=["rebalance"])


@router.get("/status")
async def rebalance_status(
    universe: UniverseId = Query(default="nse500", description="Portfolio universe"),
    user: dict = Depends(get_current_user)
):
    """
    Get current rebalance status.

    Returns current phase, available files, and next steps.
    """
    if not is_valid_universe(universe):
        raise HTTPException(status_code=400, detail=f"Invalid universe: {universe}")

    result = get_rebalance_status(universe)
    return result


@router.get("/preview")
async def rebalance_preview(
    universe: UniverseId = Query(default="nse500", description="Portfolio universe"),
    user: dict = Depends(get_current_user)
):
    """
    Get preview of upcoming rebalance changes (Thursday).

    Returns additions and removals for the upcoming rebalance.
    """
    if not is_valid_universe(universe):
        raise HTTPException(status_code=400, detail=f"Invalid universe: {universe}")

    result = get_rebalance_preview(universe)
    return result


@router.get("/orders")
async def rebalance_orders(
    universe: UniverseId = Query(default="nse500", description="Portfolio universe"),
    user: dict = Depends(get_current_user)
):
    """
    Get order file for execution (Friday).

    Returns buy/sell orders with share quantities and prices.
    """
    if not is_valid_universe(universe):
        raise HTTPException(status_code=400, detail=f"Invalid universe: {universe}")

    result = get_rebalance_orders(universe)
    return result


@router.get("/orders/export")
async def export_orders(
    universe: UniverseId = Query(default="nse500", description="Portfolio universe"),
    user: dict = Depends(get_current_user)
):
    """
    Export orders as CSV file for Kite execution.

    Returns a downloadable CSV in Kite basket order format.
    """
    if not is_valid_universe(universe):
        raise HTTPException(status_code=400, detail=f"Invalid universe: {universe}")

    csv_content = export_orders_csv(universe)

    if not csv_content:
        raise HTTPException(
            status_code=404,
            detail="No orders available for export. Orders are generated on Fridays."
        )

    filename = f"orders_{universe}.csv"

    return StreamingResponse(
        io.StringIO(csv_content),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get("/history")
async def rebalance_history(
    universe: UniverseId = Query(default="nse500", description="Portfolio universe"),
    limit: int = Query(default=20, ge=1, le=100, description="Number of records to return"),
    user: dict = Depends(get_current_user)
):
    """
    Get history of past rebalances.

    Returns past rebalance events with additions/removals counts.
    """
    if not is_valid_universe(universe):
        raise HTTPException(status_code=400, detail=f"Invalid universe: {universe}")

    result = get_rebalance_history(universe, limit)
    return result
