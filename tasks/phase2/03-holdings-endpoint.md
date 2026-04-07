# Task 3: Holdings Endpoint

**Status**: `completed`
**Blocked By**: #1 (Portfolio Service)
**Blocks**: #7

## Objective

Implement the holdings endpoint with full position details.

## Tasks

- [x] Return all 24 holdings with position data
- [x] Include P&L calculations (absolute and percentage)
- [x] Include weight/allocation percentage
- [x] Include entry date and holding days
- [x] Include entry rank

## Response Format

```json
{
  "holdings": [
    {
      "symbol": "HINDCOPPER",
      "shares": 1201.47,
      "avg_cost": 367.0,
      "current_price": 598.35,
      "notional": 718902.21,
      "pnl": 277967.11,
      "pnl_pct": 63.04,
      "weight": 5.91,
      "entry_date": "2025-12-05",
      "holding_days": 67,
      "rank": 14
    }
  ],
  "summary": {
    "total_pnl": 1180134.06,
    "winners": 18,
    "losers": 6
  },
  "data_source": "database"
}
```

## CSV Columns Used

From `momentum_holdings.csv`:
- `symbol` - Stock symbol
- `shares` - Number of shares held
- `avg_cost` - Average entry price
- `entry_date` - Date of entry
- `entry_rank` - Rank at entry
- `holding_days` - Days held
- `last_price` - Current/last price
- `pnl_pct` - P&L percentage
- `notional` - Current value
- `contribution_pct` - Portfolio weight

---

*Completed: February 12, 2026*
