# Task 1: Portfolio Service

**Status**: `completed`
**Blocked By**: None
**Blocks**: #2, #3

## Objective

Create a service to read portfolio data from CSV files and calculate P&L for each universe.

## Tasks

- [x] Create `portfolio_service.py` in `kite-api/app/services/`
- [x] Implement `get_portfolio_summary()` function
- [x] Implement `get_holdings()` function
- [x] Implement `get_allocation()` function
- [x] Support universe parameter (nse500, nifty100, nifty250)
- [x] Calculate P&L from holdings data

## Implementation

### File: `kite-api/app/services/portfolio_service.py`

Key functions:
- `get_latest_experiment_dir(universe)` - Find most recent experiment directory
- `get_portfolio_summary(universe)` - Return total value, P&L, holdings count
- `get_holdings(universe)` - Return list of holdings with details
- `get_allocation(universe)` - Return allocation breakdown

### Data Sources

| Universe | Holdings Path |
|----------|---------------|
| nse500 | `experiments/final_portfolio/final_portfolio_*/backtests/baseline/momentum_holdings.csv` |
| nifty100 | `nifty_100_tests/nifty100_portfolio_*/backtests/baseline/momentum_holdings.csv` |
| nifty250 | `nifty_250_tests/nifty250_portfolio_*/backtests/baseline/momentum_holdings.csv` |

## Verification

```python
from app.services.portfolio_service import get_portfolio_summary
result = get_portfolio_summary("nse500")
assert result["holdings_count"] == 24
```

## Notes

- Service reads from CSV files on local filesystem
- For production, the DB service is used instead (see Task 5)

---

*Completed: February 12, 2026*
