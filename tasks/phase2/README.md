# Phase 2: Portfolio View

**Duration**: Week 3-4
**Status**: COMPLETED
**Started**: February 12, 2026
**Completed**: February 13, 2026

## Objectives

- Display current holdings for selected universe
- Show portfolio value and P&L per universe
- Allocation visualization
- Seamless universe switching with real data

## Task Progress

### Backend Tasks

| # | Task | Status | Description |
|---|------|--------|-------------|
| 1 | Portfolio service | `completed` | Read from DB, fallback to CSVs |
| 2 | Portfolio endpoints | `completed` | REST API: GET /api/portfolio?universe=nse500 |
| 3 | Holdings endpoint | `completed` | GET /api/portfolio/holdings?universe=nse500 |
| 4 | CSV sync service | `completed` | Import data for all 3 universes to PostgreSQL |
| 5 | Price service | `completed` | Prices from synced holdings data |

### Frontend Tasks

| # | Task | Status | Description |
|---|------|--------|-------------|
| 6 | Value cards | `completed` | Portfolio metrics (total value, CAGR, max DD) |
| 7 | Holdings table | `completed` | Sortable table with all 24 holdings |
| 8 | P&L display | `completed` | Color-coded profit/loss cells |
| 9 | Allocation chart | `completed` | Pie chart for position weights |
| 10 | Loading states | `completed` | Skeleton loaders while fetching |

## Deliverables Checklist

- [x] See all 24 holdings in table for selected universe
- [x] Portfolio value card with daily P&L
- [x] Allocation pie chart
- [x] Auto-refresh every 5 minutes
- [x] Instant switching between NSE 500, Nifty 250, Nifty 100

## Data Sources

Phase 2 reads from existing CSV files in the repo:

| File | Description |
|------|-------------|
| `data/final_portfolio/final_portfolio_24.csv` | Current holdings snapshot |
| `data/final_portfolio/final_top24_signals.csv` | Signal history |
| `nse500_data/*.csv` | Price data for P&L calculation |
| `experiments/*/momentum_equity.csv` | Equity curve data |

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/portfolio?universe=nse500` | Portfolio summary |
| GET | `/api/portfolio/holdings?universe=nse500` | Current holdings list |
| GET | `/api/portfolio/allocation?universe=nse500` | Allocation breakdown |

---

*Status Key: `pending` | `in_progress` | `completed`*
