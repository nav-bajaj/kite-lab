"""
System API endpoints for health checks and status.
"""
from fastapi import APIRouter
from pydantic import BaseModel

from app.services.system_service import (
    SystemService,
    SystemStatus,
    TokenStatus,
    DatabaseStatus,
    SyncStatus
)

router = APIRouter(prefix="/api/system", tags=["system"])


class LoginUrlResponse(BaseModel):
    """Response for login URL."""
    url: str
    instructions: str


@router.get("/status", response_model=SystemStatus)
async def get_system_status():
    """
    Get full system status.

    Returns health of:
    - API server
    - Database connection
    - Kite API token
    - Data sync status
    """
    return SystemService.get_status()


@router.get("/token", response_model=TokenStatus)
async def get_token_status():
    """
    Get Kite API token status.

    Returns:
    - valid: Whether token is currently valid
    - expires_at: When the token expires
    - message: Human-readable status
    """
    return SystemService.check_token_status()


@router.get("/database", response_model=DatabaseStatus)
async def get_database_status():
    """
    Get database connection status.

    Returns:
    - connected: Connection status
    - latency_ms: Query latency
    - message: Status message
    """
    return SystemService.check_database()


@router.get("/sync", response_model=SyncStatus)
async def get_sync_status():
    """
    Get data sync status.

    Returns:
    - last_sync: Last sync job completion time
    - last_data_date: Latest data date in database
    - message: Data freshness message
    """
    return SystemService.get_last_sync()


@router.get("/login-url", response_model=LoginUrlResponse)
async def get_login_url():
    """
    Get Kite login URL for OAuth authentication.

    Returns URL to open in browser for Zerodha login.
    After login, run login_and_save_token.py with the request token.
    """
    url = SystemService.get_login_url()

    if not url:
        return LoginUrlResponse(
            url="",
            instructions="Kite API key not configured. Set KITE_API_KEY in environment."
        )

    return LoginUrlResponse(
        url=url,
        instructions=(
            "1. Open this URL in your browser\n"
            "2. Login with your Zerodha credentials\n"
            "3. After redirect, copy the 'request_token' from URL\n"
            "4. Run: python scripts/login_and_save_token.py <request_token>"
        )
    )
