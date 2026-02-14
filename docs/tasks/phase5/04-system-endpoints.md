# Task 4: System Endpoints

**Status**: `pending`
**Blocked By**: #3 (System Service)
**Blocks**: #13, #14

## Objective

Create API endpoints for system status and token status.

## Tasks

- [ ] Create `system.py` in `kite-api/app/api/`
- [ ] Implement `GET /api/system/status` - Full system status
- [ ] Implement `GET /api/system/token` - Token status only
- [ ] Implement `GET /api/system/login-url` - Get Kite login URL
- [ ] Add router to `main.py`

## Implementation

### File: `kite-api/app/api/system.py`

```python
from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

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
```

### Update main.py

Add to `kite-api/app/main.py`:

```python
from app.api import system

# Include router
app.include_router(system.router, tags=["system"])
```

## API Specification

### GET /api/system/status

Get full system status.

**Response:**
```json
{
  "api_health": true,
  "database": {
    "connected": true,
    "latency_ms": 2.34,
    "message": "Connected"
  },
  "token": {
    "valid": true,
    "expires_at": "2026-02-15T06:00:00",
    "message": "Token valid"
  },
  "sync": {
    "last_sync": "2026-02-14T07:05:32",
    "last_data_date": "2026-02-13",
    "message": "Data is 1 day old"
  },
  "version": "1.0.1",
  "environment": "production"
}
```

### GET /api/system/token

Get token status only.

**Response:**
```json
{
  "valid": true,
  "expires_at": "2026-02-15T06:00:00",
  "message": "Token valid"
}
```

**Response (expired):**
```json
{
  "valid": false,
  "expires_at": null,
  "message": "Token expired (created 2026-02-12)"
}
```

### GET /api/system/database

Get database status.

**Response:**
```json
{
  "connected": true,
  "latency_ms": 2.34,
  "message": "Connected"
}
```

### GET /api/system/sync

Get sync status.

**Response:**
```json
{
  "last_sync": "2026-02-14T07:05:32",
  "last_data_date": "2026-02-13",
  "message": "Data is 1 day old"
}
```

### GET /api/system/login-url

Get Kite login URL.

**Response:**
```json
{
  "url": "https://kite.zerodha.com/connect/login?api_key=xxx&v=3",
  "instructions": "1. Open this URL in your browser\n2. Login with your Zerodha credentials\n..."
}
```

## Status Indicators

### Token Status

| State | valid | message |
|-------|-------|---------|
| Valid | true | "Token valid" |
| Expired | false | "Token expired (created YYYY-MM-DD)" |
| Missing | false | "Token file not found" |
| Empty | false | "Token file is empty" |

### Database Status

| State | connected | message |
|-------|-----------|---------|
| Connected | true | "Connected" |
| Failed | false | "Connection failed: {error}" |

### Sync Status

| State | message |
|-------|---------|
| Current | "Data is current" |
| 1 day old | "Data is 1 day old" |
| N days old | "Data is N days old" |
| No data | "No sync history" |

## Verification

```bash
# Get full status
curl http://localhost:8000/api/system/status | jq

# Get token status
curl http://localhost:8000/api/system/token | jq

# Get database status
curl http://localhost:8000/api/system/database | jq

# Get sync status
curl http://localhost:8000/api/system/sync | jq

# Get login URL
curl http://localhost:8000/api/system/login-url | jq
```

## Notes

- Status endpoint provides quick health check
- Token status helps users know when to re-authenticate
- Sync status shows data freshness
- Login URL endpoint for OAuth flow guidance

---

*Status Key: `pending` | `in_progress` | `completed`*
