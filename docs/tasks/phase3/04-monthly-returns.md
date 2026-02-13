# Task 4: Monthly Returns Endpoint

**Status**: `pending`
**Blocked By**: #1 (Metrics Service)
**Blocks**: #10

## Objective

Create the REST API endpoint for monthly returns data used in the heatmap.

## Tasks

- [ ] Implement `GET /api/metrics/monthly-returns` endpoint
- [ ] Calculate monthly returns from equity curve
- [ ] Return matrix format for heatmap visualization
- [ ] Include YTD for each year

## Implementation

### File: `kite-api/app/api/metrics.py` (add to existing)

```python
from app.services.metrics_service import get_monthly_returns


@router.get("/monthly-returns")
async def monthly_returns(
    universe: UniverseId = Query(default="nse500", description="Portfolio universe")
):
    """
    Get monthly returns matrix for heatmap display.

    Returns returns for each month organized by year.
    """
    if not is_valid_universe(universe):
        raise HTTPException(status_code=400, detail=f"Invalid universe: {universe}")

    result = get_monthly_returns(universe)
    return result
```

### Service Implementation

```python
def get_monthly_returns(universe: str = "nse500") -> dict:
    """Calculate monthly returns for heatmap."""
    # Get equity curve data
    equity_data = get_equity_curve_records(universe)

    # Group by year-month
    monthly = {}
    for record in equity_data:
        year = record.date.year
        month = record.date.month

        if year not in monthly:
            monthly[year] = {}

        if month not in monthly[year]:
            monthly[year][month] = {"start": record.portfolio_value, "end": record.portfolio_value}
        else:
            monthly[year][month]["end"] = record.portfolio_value

    # Calculate returns
    years = sorted(monthly.keys())
    data = []

    for year in years:
        months = [None] * 12  # Jan=0, Dec=11

        for month in range(1, 13):
            if month in monthly[year]:
                start = monthly[year][month]["start"]
                end = monthly[year][month]["end"]
                returns = ((end - start) / start) * 100
                months[month - 1] = round(returns, 2)

        # Calculate YTD
        ytd = calculate_ytd_for_year(monthly[year])

        data.append({
            "year": year,
            "months": months,
            "ytd": ytd
        })

    return {"years": years, "data": data}
```

## API Response

### GET /api/metrics/monthly-returns?universe=nse500

```json
{
  "years": [2020, 2021, 2022, 2023, 2024, 2025, 2026],
  "data": [
    {
      "year": 2020,
      "months": [null, null, null, null, null, null, 5.23, 8.12, -2.34, 12.45, 6.78, 3.21],
      "ytd": 38.52
    },
    {
      "year": 2021,
      "months": [7.12, 4.56, -1.23, 8.90, 3.45, -2.10, 5.67, 9.01, -0.45, 4.32, 6.78, 2.34],
      "ytd": 62.34
    },
    {
      "year": 2022,
      "months": [-3.45, 2.10, 5.67, -8.90, 1.23, 4.56, -2.34, 6.78, 3.21, -1.56, 4.89, 2.01],
      "ytd": 14.20
    },
    {
      "year": 2023,
      "months": [8.12, 3.45, -1.23, 5.67, 9.01, -2.34, 4.56, 7.89, 2.10, 5.43, -0.98, 3.67],
      "ytd": 58.35
    },
    {
      "year": 2024,
      "months": [4.56, 6.78, 2.34, -1.23, 5.67, 3.45, 8.90, -2.10, 4.32, 7.01, 2.89, 5.12],
      "ytd": 62.71
    },
    {
      "year": 2025,
      "months": [6.78, 3.21, 5.43, 2.10, -1.56, 4.89, 7.12, 3.45, 6.01, -0.78, 5.23, 4.67],
      "ytd": 58.55
    },
    {
      "year": 2026,
      "months": [5.23, 2.34, null, null, null, null, null, null, null, null, null, null],
      "ytd": 7.69
    }
  ]
}
```

## Month Indexing

| Index | Month |
|-------|-------|
| 0 | January |
| 1 | February |
| 2 | March |
| 3 | April |
| 4 | May |
| 5 | June |
| 6 | July |
| 7 | August |
| 8 | September |
| 9 | October |
| 10 | November |
| 11 | December |

## Notes

- `null` means no data for that month (partial year)
- YTD is cumulative return from Jan 1 (or first trading day)
- Returns are percentages, not decimals

---

*Status Key: `pending` | `in_progress` | `completed`*
