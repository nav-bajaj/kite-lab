# Task 3: Equity Curve Endpoint

**Status**: `pending`
**Blocked By**: #1 (Metrics Service)
**Blocks**: #7, #8, #9

## Objective

Create the REST API endpoint for equity curve data used in charts.

## Tasks

- [ ] Implement `GET /api/metrics/equity-curve` endpoint
- [ ] Add date range filtering (start, end parameters)
- [ ] Return portfolio value, benchmark, and drawdown
- [ ] Handle large datasets efficiently

## Implementation

### File: `kite-api/app/api/metrics.py` (add to existing)

```python
from datetime import date
from typing import Optional
from app.services.metrics_service import get_equity_curve


@router.get("/equity-curve")
async def equity_curve(
    universe: UniverseId = Query(default="nse500", description="Portfolio universe"),
    start: Optional[date] = Query(default=None, description="Start date (YYYY-MM-DD)"),
    end: Optional[date] = Query(default=None, description="End date (YYYY-MM-DD)")
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
```

## API Response

### GET /api/metrics/equity-curve?universe=nse500

```json
{
  "data": [
    {
      "date": "2020-07-10",
      "portfolio_value": 1000000,
      "benchmark_value": 1000000,
      "drawdown": 0
    },
    {
      "date": "2020-07-13",
      "portfolio_value": 1012500,
      "benchmark_value": 1005000,
      "drawdown": 0
    },
    {
      "date": "2020-07-14",
      "portfolio_value": 998000,
      "benchmark_value": 1002000,
      "drawdown": -1.43
    }
  ],
  "count": 1390
}
```

### With Date Range

```
GET /api/metrics/equity-curve?universe=nse500&start=2025-01-01&end=2025-12-31
```

## Data Volume

| Universe | Records | Date Range |
|----------|---------|------------|
| NSE500 | ~1390 | Jul 2020 - Feb 2026 |
| Nifty100 | ~1388 | Jul 2020 - Feb 2026 |
| Nifty250 | ~1389 | Jul 2020 - Feb 2026 |

## Performance Considerations

- ~1400 records per universe is manageable
- No pagination needed (frontend can handle)
- Consider data compression for slow connections
- Date range filter reduces payload when needed

## Verification

```bash
# Full equity curve
curl "http://localhost:8000/api/metrics/equity-curve?universe=nse500" | jq '.count'

# Date range
curl "http://localhost:8000/api/metrics/equity-curve?universe=nse500&start=2025-01-01" | jq '.count'
```

---

*Status Key: `pending` | `in_progress` | `completed`*
