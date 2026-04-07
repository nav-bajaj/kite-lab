# Task 3: System Service

**Status**: `pending`
**Blocked By**: None
**Blocks**: #4

## Objective

Create a service to check system health, API status, database connection, Kite token validity, and last data sync timestamp.

## Tasks

- [ ] Create `system_service.py` in `kite-api/app/services/`
- [ ] Implement `get_status()` function
- [ ] Implement `check_token_status()` function
- [ ] Implement `get_last_sync()` function
- [ ] Implement `check_database()` function

## Implementation

### File: `kite-api/app/services/system_service.py`

```python
from datetime import datetime, date
from pathlib import Path
from typing import Optional
from pydantic import BaseModel
from sqlalchemy import text

from app.models.database import get_session_local
from app.models.models import EquityCurve, Job
from app.config import settings


class TokenStatus(BaseModel):
    """Kite API token status."""
    valid: bool
    expires_at: Optional[datetime] = None
    message: str


class DatabaseStatus(BaseModel):
    """Database connection status."""
    connected: bool
    latency_ms: Optional[float] = None
    message: str


class SyncStatus(BaseModel):
    """Data sync status."""
    last_sync: Optional[datetime] = None
    last_data_date: Optional[date] = None
    message: str


class SystemStatus(BaseModel):
    """Full system status."""
    api_health: bool
    database: DatabaseStatus
    token: TokenStatus
    sync: SyncStatus
    version: str = "1.0.1"
    environment: str = "production"


class SystemService:
    """Service for checking system health and status."""

    @staticmethod
    def get_status() -> SystemStatus:
        """
        Get comprehensive system status.

        Returns health of API, database, token, and sync status.
        """
        return SystemStatus(
            api_health=True,  # If we're here, API is up
            database=SystemService.check_database(),
            token=SystemService.check_token_status(),
            sync=SystemService.get_last_sync(),
            version="1.0.1",
            environment="production" if not settings.debug else "development"
        )

    @staticmethod
    def check_database() -> DatabaseStatus:
        """
        Check database connection health.

        Returns connection status and latency.
        """
        SessionLocal = get_session_local()

        try:
            db = SessionLocal()
            start = datetime.utcnow()

            # Simple query to test connection
            db.execute(text("SELECT 1"))

            latency = (datetime.utcnow() - start).total_seconds() * 1000

            db.close()

            return DatabaseStatus(
                connected=True,
                latency_ms=round(latency, 2),
                message="Connected"
            )

        except Exception as e:
            return DatabaseStatus(
                connected=False,
                latency_ms=None,
                message=f"Connection failed: {str(e)}"
            )

    @staticmethod
    def check_token_status() -> TokenStatus:
        """
        Check Kite API access token status.

        Reads access_token.txt and checks validity.
        Token expires daily at 6 AM IST.
        """
        token_path = settings.data_dir / "access_token.txt"

        if not token_path.exists():
            return TokenStatus(
                valid=False,
                expires_at=None,
                message="Token file not found"
            )

        try:
            # Read token and check modification time
            mtime = datetime.fromtimestamp(token_path.stat().st_mtime)
            token_content = token_path.read_text().strip()

            if not token_content:
                return TokenStatus(
                    valid=False,
                    expires_at=None,
                    message="Token file is empty"
                )

            # Token expires at 6 AM IST next day
            # For simplicity, check if token was created today
            today = datetime.now().date()
            token_date = mtime.date()

            if token_date < today:
                return TokenStatus(
                    valid=False,
                    expires_at=None,
                    message=f"Token expired (created {token_date})"
                )

            # Calculate expiry (6 AM IST next day)
            # Assuming server is in IST
            from datetime import timedelta
            expires_at = datetime.combine(
                token_date + timedelta(days=1),
                datetime.strptime("06:00", "%H:%M").time()
            )

            return TokenStatus(
                valid=True,
                expires_at=expires_at,
                message="Token valid"
            )

        except Exception as e:
            return TokenStatus(
                valid=False,
                expires_at=None,
                message=f"Error reading token: {str(e)}"
            )

    @staticmethod
    def get_last_sync() -> SyncStatus:
        """
        Get last data sync timestamp.

        Checks latest equity curve date and last sync job.
        """
        SessionLocal = get_session_local()

        try:
            db = SessionLocal()

            # Get latest data date from equity curve
            latest_equity = db.query(EquityCurve).order_by(
                EquityCurve.date.desc()
            ).first()

            # Get last successful sync job
            last_sync_job = db.query(Job).filter(
                Job.command.in_(["daily_pipeline", "fetch_prices"]),
                Job.status == "completed"
            ).order_by(Job.ended_at.desc()).first()

            db.close()

            last_data_date = latest_equity.date if latest_equity else None
            last_sync = last_sync_job.ended_at if last_sync_job else None

            message = "No sync history"
            if last_data_date:
                days_old = (date.today() - last_data_date).days
                if days_old == 0:
                    message = "Data is current"
                elif days_old == 1:
                    message = "Data is 1 day old"
                else:
                    message = f"Data is {days_old} days old"

            return SyncStatus(
                last_sync=last_sync,
                last_data_date=last_data_date,
                message=message
            )

        except Exception as e:
            return SyncStatus(
                last_sync=None,
                last_data_date=None,
                message=f"Error checking sync: {str(e)}"
            )

    @staticmethod
    def get_login_url() -> str:
        """
        Get Kite login URL for OAuth.

        Returns URL user should open in browser.
        """
        api_key = settings.kite_api_key

        if not api_key:
            return ""

        return f"https://kite.zerodha.com/connect/login?api_key={api_key}&v=3"
```

## Status Models

### TokenStatus

| Field | Type | Description |
|-------|------|-------------|
| valid | bool | Whether token is valid |
| expires_at | datetime | Token expiry time |
| message | str | Human-readable status |

### DatabaseStatus

| Field | Type | Description |
|-------|------|-------------|
| connected | bool | Connection status |
| latency_ms | float | Query latency in ms |
| message | str | Status message |

### SyncStatus

| Field | Type | Description |
|-------|------|-------------|
| last_sync | datetime | Last sync job completion |
| last_data_date | date | Latest data date |
| message | str | Data freshness message |

### SystemStatus

| Field | Type | Description |
|-------|------|-------------|
| api_health | bool | API is responding |
| database | DatabaseStatus | DB connection status |
| token | TokenStatus | Kite token status |
| sync | SyncStatus | Data sync status |
| version | str | API version |
| environment | str | production/development |

## Token Lifecycle

```
login_and_save_token.py → access_token.txt (created)
                               │
                               ▼
                        Token valid until 6 AM IST next day
                               │
                               ▼
                        Token expires → valid: false
                               │
                               ▼
                        Re-run login script
```

## Verification

```python
from app.services.system_service import SystemService

# Get full status
status = SystemService.get_status()
print(f"API Health: {status.api_health}")
print(f"Database: {status.database.connected} ({status.database.latency_ms}ms)")
print(f"Token: {status.token.valid} - {status.token.message}")
print(f"Sync: {status.sync.message}")

# Check individual components
db_status = SystemService.check_database()
token_status = SystemService.check_token_status()
sync_status = SystemService.get_last_sync()
```

## Notes

- Token validation uses file modification time
- Token expires daily at 6 AM IST
- Sync status shows data freshness
- All errors are caught and returned as status messages

---

*Status Key: `pending` | `in_progress` | `completed`*
