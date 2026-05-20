"""
Open Positions API endpoints.

Provides live portfolio tracking with real-time prices from Zerodha API.
All endpoints require authentication except market-status.
"""
from datetime import datetime
from typing import Optional
import asyncio
import logging

from fastapi import APIRouter, Query, HTTPException, Depends
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse

import pytz

from app.config import UniverseId, is_valid_universe
from app.schemas.positions import (
    PositionsResponse,
    QuotesResponse,
    HoldingsOnlyResponse,
    SyncResponse,
    PositionsSyncRequest,
    MarketStatus,
)
from app.services.positions_service import PositionsService
from app.services.quotes_service import (
    get_cached_quotes,
    TokenExpiredError,
    QuotesFetchError,
)
from app.services.market_service import get_market_status, is_market_open
from app.auth import get_current_user, require_admin, validate_token_string, AuthError
from app.middleware.cache import cache_live

logger = logging.getLogger(__name__)
IST = pytz.timezone("Asia/Kolkata")

router = APIRouter(prefix="/api/positions", tags=["positions"])


@router.get("", response_model=PositionsResponse, dependencies=[Depends(cache_live)])
async def get_positions(
    universe: UniverseId = Query(default="nse500", description="Portfolio universe"),
    user: dict = Depends(get_current_user)
):
    """
    Get all open positions with live prices and P&L calculations.

    Returns positions with:
    - Current holdings (symbol, qty, avg_price)
    - Live prices (LTP, day change)
    - P&L calculations (total P&L, day P&L)
    - Portfolio summary
    - Market status
    """
    if not is_valid_universe(universe):
        raise HTTPException(status_code=400, detail=f"Invalid universe: {universe}")

    try:
        return PositionsService.get_positions(universe)
    except TokenExpiredError:
        raise HTTPException(
            status_code=401,
            detail="Zerodha access token expired. Please login again."
        )
    except QuotesFetchError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Failed to fetch live quotes: {str(e)}"
        )


@router.get("/holdings", response_model=HoldingsOnlyResponse, dependencies=[Depends(cache_live)])
async def get_holdings(
    universe: UniverseId = Query(default="nse500", description="Portfolio universe"),
    user: dict = Depends(get_current_user)
):
    """
    Get raw holdings without live prices.

    Useful for checking what positions are stored without making API calls.
    """
    if not is_valid_universe(universe):
        raise HTTPException(status_code=400, detail=f"Invalid universe: {universe}")

    return PositionsService.get_holdings_response(universe)


@router.get("/quotes", response_model=QuotesResponse, dependencies=[Depends(cache_live)])
async def get_quotes(
    universe: UniverseId = Query(default="nse500", description="Portfolio universe"),
    user: dict = Depends(get_current_user)
):
    """
    Get live quotes for all holdings.

    Returns raw quote data without P&L calculations.
    """
    if not is_valid_universe(universe):
        raise HTTPException(status_code=400, detail=f"Invalid universe: {universe}")

    holdings = PositionsService.get_holdings(universe)
    if not holdings:
        return QuotesResponse(
            quotes={},
            market_status=get_market_status(),
            last_updated=datetime.now(IST)
        )

    symbols = [h.symbol for h in holdings]

    try:
        quotes = get_cached_quotes(symbols, universe)
        return QuotesResponse(
            quotes=quotes,
            market_status=get_market_status(),
            last_updated=datetime.now(IST)
        )
    except TokenExpiredError:
        raise HTTPException(
            status_code=401,
            detail="Zerodha access token expired. Please login again."
        )
    except QuotesFetchError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Failed to fetch quotes: {str(e)}"
        )


@router.get("/market-status", response_model=MarketStatus, dependencies=[Depends(cache_live)])  # nosemgrep: tools.security.fastapi-route-missing-auth  # AD-1: NSE market open/closed; no user data — see docs/security/attack-surface.md
async def get_market_status_endpoint():
    """
    Get current NSE market status.

    Returns whether market is open/closed with timing information.
    """
    return get_market_status()


@router.post("/sync", response_model=SyncResponse)
async def sync_positions(request: PositionsSyncRequest, user: dict = Depends(require_admin)):
    """
    Sync positions from provided data.

    Replaces all existing positions for the universe with new data.
    """
    if not is_valid_universe(request.universe):
        raise HTTPException(status_code=400, detail=f"Invalid universe: {request.universe}")

    return PositionsService.sync_positions(request.universe, request.positions)


@router.post("/sync-from-csv", response_model=SyncResponse)
async def sync_from_csv(
    universe: UniverseId = Query(default="nse500", description="Portfolio universe"),
    user: dict = Depends(require_admin)
):
    """
    Sync positions from the portfolio CSV file.

    Reads holdings from the latest portfolio file for the universe.
    """
    if not is_valid_universe(universe):
        raise HTTPException(status_code=400, detail=f"Invalid universe: {universe}")

    return PositionsService.sync_from_csv(universe)


@router.get("/stream")  # nosemgrep: tools.security.fastapi-route-missing-auth  # SSE endpoint — token validated inside handler via query param (EventSource limitation). See R-005.
async def positions_stream(
    universe: UniverseId = Query(default="nse500", description="Portfolio universe"),
    interval: int = Query(default=3, ge=2, le=10, description="Update interval in seconds"),
    token: str = Query(default=None, description="JWT token (for SSE clients that can't send headers)"),
):
    """
    Server-Sent Events (SSE) stream for real-time position updates.

    Auth: accepts token via query param (EventSource can't send headers).

    Events:
    - price_update: Full positions response with live data
    - market_status: Market open/closed status
    - heartbeat: Keep-alive ping
    - error: Error messages
    """
    # Validate token from query param (EventSource can't send Authorization header)
    if not token:
        raise HTTPException(status_code=401, detail="Token required (pass as ?token=...)")
    try:
        validate_token_string(token)
    except AuthError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    if not is_valid_universe(universe):
        raise HTTPException(status_code=400, detail=f"Invalid universe: {universe}")

    async def event_generator():
        last_heartbeat = datetime.now(IST)
        heartbeat_interval = 30  # seconds
        error_count = 0
        max_errors = 5

        while True:
            try:
                market_status = get_market_status()
                now = datetime.now(IST)

                if market_status.is_open:
                    # Market is open - send live updates
                    try:
                        positions = PositionsService.get_positions(universe)
                        yield {
                            "event": "price_update",
                            "data": positions.model_dump_json()
                        }
                        error_count = 0  # Reset on success
                    except TokenExpiredError:
                        yield {
                            "event": "error",
                            "data": '{"error": "token_expired", "message": "Zerodha token expired. Please login again."}'
                        }
                        await asyncio.sleep(60)  # Wait longer on auth error
                        continue
                    except QuotesFetchError as e:
                        error_count += 1
                        yield {
                            "event": "error",
                            "data": f'{{"error": "fetch_failed", "message": "{str(e)}"}}'
                        }
                        if error_count >= max_errors:
                            yield {
                                "event": "error",
                                "data": '{"error": "max_errors", "message": "Too many errors. Stream stopping."}'
                            }
                            break

                    await asyncio.sleep(interval)
                else:
                    # Market is closed - send status only
                    yield {
                        "event": "market_status",
                        "data": market_status.model_dump_json()
                    }
                    await asyncio.sleep(60)  # Longer interval when closed

                # Heartbeat
                if (now - last_heartbeat).total_seconds() >= heartbeat_interval:
                    yield {
                        "event": "heartbeat",
                        "data": f'{{"timestamp": "{now.isoformat()}"}}'
                    }
                    last_heartbeat = now

            except asyncio.CancelledError:
                logger.info(f"SSE stream cancelled for {universe}")
                break
            except Exception as e:
                logger.error(f"SSE stream error: {e}")
                yield {
                    "event": "error",
                    "data": f'{{"error": "unknown", "message": "{str(e)}"}}'
                }
                await asyncio.sleep(5)

    return EventSourceResponse(event_generator())
