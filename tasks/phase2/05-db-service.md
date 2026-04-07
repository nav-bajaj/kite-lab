# Task 5: Portfolio DB Service

**Status**: `completed`
**Blocked By**: #4 (Sync Service)
**Blocks**: None

## Objective

Create a database-backed portfolio service for production deployment.

## Tasks

- [x] Create `portfolio_db_service.py` in `kite-api/app/services/`
- [x] Implement `get_portfolio_summary_db()` function
- [x] Implement `get_holdings_db()` function
- [x] Implement `get_allocation_db()` function
- [x] Update `portfolio.py` to use DB service first, fallback to CSV

## Implementation

### File: `kite-api/app/services/portfolio_db_service.py`

```python
def get_latest_snapshot_date(db: Session, universe: str) -> Optional[date]:
    """Get the most recent snapshot date for a universe."""
    ...

def get_portfolio_summary_db(universe: str) -> dict:
    """Get portfolio summary from database."""
    ...

def get_holdings_db(universe: str) -> dict:
    """Get holdings list from database."""
    ...

def get_allocation_db(universe: str) -> dict:
    """Get allocation breakdown from database."""
    ...
```

### File: `kite-api/app/api/portfolio.py` (Updated)

```python
def get_portfolio_service():
    """Get the appropriate portfolio service (DB or CSV)."""
    try:
        from app.services.portfolio_db_service import (...)
        return {"get_summary": get_portfolio_summary_db, "source": "database"}
    except ImportError:
        pass
    # Fall back to CSV service
    ...
```

## Response Enhancement

Added `data_source` field to all responses:
- `"database"` - Data from PostgreSQL
- `"csv"` - Data from local CSV files

## Notes

- DB service is primary for production (Railway)
- CSV service is fallback for local development
- Both return identical response structure

---

*Completed: February 13, 2026*
