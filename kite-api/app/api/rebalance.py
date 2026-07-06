"""
Rebalance API endpoints.

Client-facing, cadence-aware read endpoints (``/summary``, ``/upcoming``,
``/history``) derived from the Trade/Holding tables + the EOD proposed-orders
producer — see tasks/rebalance_page/PLAN.md. The legacy ``/status`` /
``/preview`` / ``/orders`` endpoints predate that rebuild and remain only for
the admin legacy universes. All endpoints require authentication.
"""
from fastapi import APIRouter, Query, HTTPException, Depends
from fastapi.responses import StreamingResponse
import io

from app.config import is_valid_universe, UniverseId
from app.services.rebalance_service import (
    export_orders_csv,
    get_rebalance_history,
    get_rebalance_orders,
    get_rebalance_preview,
    get_rebalance_status,
    get_rebalance_summary,
    get_upcoming_rebalance,
)
from app.auth import get_current_user, check_universe_access
from app.middleware.cache import cache_daily, cache_rebalance

router = APIRouter(prefix="/api/rebalance", tags=["rebalance"])


@router.get("/status", dependencies=[Depends(cache_rebalance)])
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
    check_universe_access(universe, user)

    result = get_rebalance_status(universe)
    return result


@router.get("/summary", dependencies=[Depends(cache_rebalance)])
async def rebalance_summary(
    universe: UniverseId = Query(default="nse500", description="Portfolio universe"),
    user: dict = Depends(get_current_user)
):
    """
    Cadence-aware rebalance summary for the client view.

    Returns the previous rebalance (adds/drops, turnover), the next projected
    rebalance date, and the cadence label for the selected portfolio.
    """
    if not is_valid_universe(universe):
        raise HTTPException(status_code=400, detail=f"Invalid universe: {universe}")
    check_universe_access(universe, user)

    return get_rebalance_summary(universe)


@router.get("/preview", dependencies=[Depends(cache_rebalance)])
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
    check_universe_access(universe, user)

    result = get_rebalance_preview(universe)
    return result


@router.get("/orders", dependencies=[Depends(cache_rebalance)])
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
    check_universe_access(universe, user)

    result = get_rebalance_orders(universe)
    return result


@router.get("/orders/export", dependencies=[Depends(cache_rebalance)])
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
    check_universe_access(universe, user)

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


@router.get("/upcoming", dependencies=[Depends(cache_rebalance)])
async def rebalance_upcoming(
    universe: UniverseId = Query(default="nse500", description="Portfolio universe"),
    user: dict = Depends(get_current_user)
):
    """
    Get the EOD-produced "Actionable trades" payload for the upcoming rebalance.

    Membership-only (PLAN.md Phase 2 §3): sells = full exits, buys = new
    entries with the model's target weight + indicative ₹ sizing on the
    producer's notional base, holds = continuing names (no action). The
    rebalance page derives the subscriber's own ₹ sizing client-side.

    Returns ``available: false`` (with empty lists) when no proposal has been
    produced for this universe yet — strategies whose EOD producer hasn't
    been wired up land here, and the UI shows a "no upcoming rebalance" state
    instead of 404'ing.
    """
    if not is_valid_universe(universe):
        raise HTTPException(status_code=400, detail=f"Invalid universe: {universe}")
    check_universe_access(universe, user)

    return get_upcoming_rebalance(universe)


@router.get("/history", dependencies=[Depends(cache_daily)])
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
    check_universe_access(universe, user)

    result = get_rebalance_history(universe, limit)
    return result
