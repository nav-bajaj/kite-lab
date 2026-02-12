# Phase 2: Portfolio View

**Duration**: Week 3-4
**Status**: In Progress
**Started**: February 12, 2026

## Objectives

- Display current holdings for selected universe
- Show portfolio value and P&L per universe
- Allocation visualization
- Seamless universe switching with real data

## Task Progress

### Backend Tasks

| # | Task | Status | Description |
|---|------|--------|-------------|
| 1 | Portfolio service | `pending` | Read CSVs, calculate P&L per universe |
| 2 | Portfolio endpoints | `pending` | REST API: GET /api/portfolio?universe=nse500 |
| 3 | Holdings endpoint | `pending` | GET /api/portfolio/holdings?universe=nse500 |
| 4 | CSV sync service | `pending` | Import data for all 3 universes |
| 5 | Price service | `pending` | Current prices lookup from CSV |

### Frontend Tasks

| # | Task | Status | Description |
|---|------|--------|-------------|
| 6 | Value cards | `pending` | Portfolio metrics (total value, P&L, etc.) |
| 7 | Holdings table | `pending` | Sortable table with all 24 holdings |
| 8 | P&L display | `pending` | Color-coded profit/loss cells |
| 9 | Allocation chart | `pending` | Pie/donut chart for position weights |
| 10 | Loading states | `pending` | Skeleton loaders while fetching |

## Deliverables Checklist

- [ ] See all 24 holdings in table for selected universe
- [ ] Portfolio value card with daily P&L
- [ ] Allocation pie chart
- [ ] Auto-refresh every 5 minutes
- [ ] Instant switching between NSE 500, Nifty 250, Nifty 100

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
