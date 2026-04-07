# Task 4: CSV Sync Service

**Status**: `completed`
**Blocked By**: None
**Blocks**: #5

## Objective

Create a service to import CSV data into PostgreSQL database for production deployment.

## Tasks

- [x] Create `sync_service.py` in `kite-api/app/services/`
- [x] Implement `sync_holdings()` function
- [x] Implement `sync_equity_curve()` function
- [x] Implement `sync_metrics()` function
- [x] Implement `sync_all()` for single universe
- [x] Implement `sync_all_universes()` for all universes
- [x] Create sync API endpoint
- [x] Create standalone sync script for local-to-production sync

## Implementation

### File: `kite-api/app/services/sync_service.py`

```python
def sync_holdings(db: Session, universe: str) -> dict:
    """Import holdings from CSV to database."""
    ...

def sync_equity_curve(db: Session, universe: str) -> dict:
    """Import equity curve from CSV to database."""
    ...

def sync_metrics(db: Session, universe: str) -> dict:
    """Import metrics from CSV to database."""
    ...

def sync_all(universe: str) -> dict:
    """Sync all data for a universe."""
    ...
```

### File: `kite-api/app/api/sync.py`

```python
@router.post("")
async def sync_universe(universe: UniverseId = Query(default="nse500")):
    ...

@router.post("/all")
async def sync_all_universes():
    ...
```

### File: `kite-api/scripts/sync_to_production.py`

Standalone script to sync local CSV data to remote PostgreSQL:

```bash
python kite-api/scripts/sync_to_production.py \
  --database-url "postgresql://..." \
  --data-dir /Users/navdeep/kite-lab
```

## Data Synced

| Universe | Holdings | Equity Curve | Metrics |
|----------|----------|--------------|---------|
| NSE500 | 24 | 1390 records | 1 |
| Nifty100 | 26 | 1388 records | 1 |
| Nifty250 | 24 | 1389 records | 1 |

## Notes

- Railway doesn't have CSV files, so data must be synced from local
- Sync script connects to Railway PostgreSQL from local machine
- Run sync after each portfolio generation

---

*Completed: February 13, 2026*
