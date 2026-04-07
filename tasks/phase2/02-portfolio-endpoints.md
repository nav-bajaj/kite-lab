# Task 2: Portfolio Endpoints

**Status**: `completed`
**Blocked By**: #1 (Portfolio Service)
**Blocks**: #6, #7, #8

## Objective

Create REST API endpoints for portfolio data with universe parameter support.

## Tasks

- [x] Create `portfolio.py` in `kite-api/app/api/`
- [x] Implement `GET /api/portfolio` endpoint
- [x] Implement `GET /api/portfolio/holdings` endpoint
- [x] Implement `GET /api/portfolio/allocation` endpoint
- [x] Add universe query parameter validation
- [x] Register router in `main.py`

## Endpoints

### GET /api/portfolio

Returns portfolio summary for a universe.

**Query Parameters:**
- `universe` (optional): `nse500` | `nifty100` | `nifty250` (default: `nse500`)

**Response:**
```json
{
  "total_value": 12156257.18,
  "cash": 0,
  "invested": 10976123.12,
  "daily_pnl": 0,
  "daily_pnl_pct": 0,
  "total_return": 1180134.06,
  "total_return_pct": 10.75,
  "holdings_count": 24,
  "as_of_date": "2026-02-13",
  "universe": "nse500",
  "cagr": 56.36,
  "max_drawdown": -29.60,
  "sharpe_ratio": null,
  "data_source": "database"
}
```

### GET /api/portfolio/holdings

Returns list of current holdings with P&L.

### GET /api/portfolio/allocation

Returns allocation breakdown for pie chart.

## Implementation

### File: `kite-api/app/api/portfolio.py`

```python
router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])

@router.get("")
async def portfolio_summary(universe: UniverseId = Query(default="nse500")):
    ...

@router.get("/holdings")
async def portfolio_holdings(universe: UniverseId = Query(default="nse500")):
    ...

@router.get("/allocation")
async def portfolio_allocation(universe: UniverseId = Query(default="nse500")):
    ...
```

## Verification

```bash
curl "https://kite-lab-production.up.railway.app/api/portfolio?universe=nse500"
```

---

*Completed: February 12, 2026*
