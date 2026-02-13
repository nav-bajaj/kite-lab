# Phase 4: Trades & Rebalance

**Duration**: Week 7-8
**Status**: Completed
**Completed**: February 13, 2026

## Objectives

- Display searchable trade history for each universe
- CSV export functionality
- Weekly rebalance workflow (Thursday preview, Friday orders)
- Order file generation for Kite execution

## Production URLs

| Service | URL |
|---------|-----|
| Frontend | https://kite-lab.vercel.app |
| Backend | https://kite-lab-production.up.railway.app |

## Task Progress

### Backend Tasks

| # | Task | Status | Description |
|---|------|--------|-------------|
| 1 | Trade service | `completed` | Query trades with filters and pagination |
| 2 | Trade endpoints | `completed` | GET /api/trades with search/filter |
| 3 | Export endpoint | `completed` | GET /api/trades/export CSV download |
| 4 | Rebalance service | `completed` | Status, preview, orders, history |
| 5 | Rebalance endpoints | `completed` | GET /api/rebalance/* endpoints |
| 6 | Trades sync | `completed` | sync_trades in sync_service.py |

### Frontend Tasks

| # | Task | Status | Description |
|---|------|--------|-------------|
| 7 | Trades page | `completed` | Page layout with filters |
| 8 | Trades table | `completed` | Paginated, searchable table |
| 9 | Trade summary | `completed` | Stats cards (total, buys, sells) |
| 10 | Export button | `completed` | CSV download |
| 11 | Rebalance page | `completed` | Workflow layout |
| 12 | Status card | `completed` | Current phase indicator |
| 13 | Changes preview | `completed` | Thursday additions/removals |
| 14 | Orders table | `completed` | Friday execution orders |

## API Endpoints

### Trades

```
GET /api/trades?universe=nse500&limit=50&offset=0&symbol=&side=
GET /api/trades/summary?universe=nse500
GET /api/trades/recent?universe=nse500&days=7
GET /api/trades/export?universe=nse500
```

### Rebalance

```
GET /api/rebalance/status?universe=nse500
GET /api/rebalance/preview?universe=nse500
GET /api/rebalance/orders?universe=nse500
GET /api/rebalance/orders/export?universe=nse500
GET /api/rebalance/history?universe=nse500&limit=20
```

## Files Created

### Backend
- `kite-api/app/services/trade_service.py`
- `kite-api/app/services/rebalance_service.py`
- `kite-api/app/api/trades.py`
- `kite-api/app/api/rebalance.py`

### Frontend
- `kite-dashboard/src/components/trades/trades-table.tsx`
- `kite-dashboard/src/components/trades/trade-summary.tsx`
- `kite-dashboard/src/components/rebalance/status-card.tsx`
- `kite-dashboard/src/components/rebalance/changes-preview.tsx`
- `kite-dashboard/src/components/rebalance/orders-table.tsx`

## Deliverables Checklist

- [x] Searchable trade history per universe
- [x] CSV export for selected universe
- [x] Thursday preview (additions/removals)
- [x] Friday order file download
- [x] Rebalance status indicator

---

*Status Key: `pending` | `in_progress` | `completed`*

*Last updated: February 13, 2026*
