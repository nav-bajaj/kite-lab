# Task 2: Metrics Endpoint

**Status**: `pending`
**Blocked By**: #1 (Metrics Service)
**Blocks**: #6

## Objective

Create the REST API endpoint for performance metrics.

## Tasks

- [ ] Create `metrics.py` in `kite-api/app/api/`
- [ ] Implement `GET /api/metrics` endpoint
- [ ] Add universe parameter validation
- [ ] Register router in `main.py`
- [ ] Update `__init__.py` exports

## Implementation

### File: `kite-api/app/api/metrics.py`

```python
from fastapi import APIRouter, Query, HTTPException
from app.config import is_valid_universe, UniverseId
from app.services.metrics_service import get_metrics

router = APIRouter(prefix="/api/metrics", tags=["metrics"])


@router.get("")
async def metrics_summary(
    universe: UniverseId = Query(default="nse500", description="Portfolio universe")
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
```

### Update: `kite-api/app/main.py`

```python
from app.api import health, auth_routes, portfolio, sync, metrics

# ... existing code ...

app.include_router(metrics.router, tags=["metrics"])
```

### Update: `kite-api/app/api/__init__.py`

```python
from . import health, auth_routes, portfolio, sync, metrics
```

## API Response

### GET /api/metrics?universe=nse500

```json
{
  "period": {
    "start": "2020-07-10",
    "end": "2026-02-13",
    "days": 2042
  },
  "returns": {
    "total_return": 1116.25,
    "cagr": 56.36,
    "mtd": 2.34,
    "ytd": 8.45
  },
  "risk": {
    "max_drawdown": -29.60,
    "max_dd_duration": 87,
    "volatility": 25.4,
    "sharpe_ratio": 1.87,
    "sortino_ratio": 2.45,
    "calmar_ratio": 1.90
  },
  "activity": {
    "total_trades": 2352,
    "avg_turnover": 2.5,
    "annualized_turnover": 123.0,
    "avg_holding_days": 43.3,
    "hit_rate": 49.3
  }
}
```

## Verification

```bash
# Local
curl "http://localhost:8000/api/metrics?universe=nse500" | jq

# Production
curl "https://kite-lab-production.up.railway.app/api/metrics?universe=nse500" | jq
```

## Notes

- All percentage values are returned as numbers (56.36, not 0.5636)
- Error responses include empty structure for frontend compatibility
- No authentication required (read-only public data)

---

*Status Key: `pending` | `in_progress` | `completed`*
