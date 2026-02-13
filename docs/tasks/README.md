# Production Dashboard - Task Tracking

This directory contains task tracking files for the Kite-Lab Production Dashboard implementation.

## Project Overview

Building a production-grade web dashboard to manage, monitor, and operate the Kite-Lab momentum portfolio engine.

- **Full Plan Document**: [production_dashboard_plan.md](../production_dashboard_plan.md)
- **Tech Stack**: Next.js 14 + shadcn/ui (Vercel) → FastAPI + PostgreSQL (Railway)
- **Estimated Cost**: ~$5/month

## Production URLs

| Service | URL |
|---------|-----|
| Frontend (Vercel) | https://kite-lab.vercel.app |
| Backend (Railway) | https://kite-lab-production.up.railway.app |
| API Docs | https://kite-lab-production.up.railway.app/docs |

## Implementation Phases

| Phase | Duration | Status | Description |
|-------|----------|--------|-------------|
| [Phase 1](./phase1/README.md) | Week 1-2 | **Completed** | Foundation - Backend, Frontend, Auth, Database |
| [Phase 2](./phase2/README.md) | Week 3-4 | **Completed** | Portfolio View - Holdings, P&L, Allocation |
| [Phase 3](./phase3/README.md) | Week 5-6 | **Completed** | Performance Metrics - Equity curves, Benchmarks |
| [Phase 4](#phase-4-trades--rebalance) | Week 7-8 | Not Started | Trades & Rebalance - History, Workflow |
| [Phase 5](#phase-5-admin-control-panel) | Week 9-10 | Not Started | Admin Control Panel - Jobs, Scheduler |
| [Phase 6](#phase-6-polish--production) | Week 11-12 | Not Started | Polish & Production - Error handling, Docs |

---

## Phase Summaries

### Phase 1: Foundation (COMPLETED)

**Objective**: Set up project infrastructure, authentication, and deployment.

**Key Deliverables**:
- ✅ FastAPI backend with PostgreSQL
- ✅ Next.js frontend with shadcn/ui
- ✅ Google OAuth authentication
- ✅ Universe selector (NSE 500, Nifty 250, Nifty 100)
- ✅ Deployed to Vercel + Railway

**Files Created**: 12 task files in `phase1/`

---

### Phase 2: Portfolio View (COMPLETED)

**Objective**: Display holdings, P&L, and allocation for each universe.

**Key Deliverables**:
- ✅ Portfolio summary with value cards
- ✅ Holdings table with 24 positions
- ✅ Allocation pie chart
- ✅ Database sync service for production
- ✅ Auto-refresh with SWR

**API Endpoints**:
- `GET /api/portfolio?universe=nse500`
- `GET /api/portfolio/holdings?universe=nse500`
- `GET /api/portfolio/allocation?universe=nse500`
- `POST /api/sync?universe=nse500`

**Files Created**: 9 task files in `phase2/`

---

### Phase 3: Performance Metrics (IN PROGRESS)

**Objective**: Historical equity curves, performance metrics, benchmark comparison.

**Key Deliverables**:
- [ ] Metrics service with Sharpe, Sortino, Calmar calculations
- [ ] Equity curve chart (2020-present)
- [ ] Benchmark comparison toggle
- [ ] Drawdown visualization
- [ ] Monthly returns heatmap

**API Endpoints** (to build):
- `GET /api/metrics?universe=nse500`
- `GET /api/metrics/equity-curve?universe=nse500`
- `GET /api/metrics/monthly-returns?universe=nse500`

**Frontend Components** (to build):
- Performance page at `/performance`
- Metrics grid (CAGR, Sharpe, Max DD, Volatility)
- Equity curve chart with Recharts
- Drawdown chart
- Monthly heatmap

**Files Created**: 10 task files in `phase3/`

---

### Phase 4: Trades & Rebalance

**Objective**: Trade history with search/filter, Thursday/Friday rebalance workflow.

**Backend Tasks**:
| Task | Description | Endpoint |
|------|-------------|----------|
| Trade service | Query trades per universe | `app/services/trade_service.py` |
| Trade endpoints | Paginated API | `GET /api/trades?universe=nse500` |
| Export endpoint | CSV download | `GET /api/trades/export?universe=nse500` |
| Rebalance service | Parse change files | `app/services/rebalance_service.py` |
| Rebalance endpoints | Preview, orders | `GET /api/rebalance/*?universe=nse500` |
| Trades sync | Import historical | Part of sync_service |

**Frontend Tasks**:
| Task | Description | Component |
|------|-------------|-----------|
| Trades page | Layout with filters | `app/(dashboard)/trades/page.tsx` |
| Trades table | Paginated, filterable | `components/trades/trades-table.tsx` |
| Trade filters | Search, date, side | `components/trades/trade-filters.tsx` |
| Export button | CSV download | `components/trades/export-button.tsx` |
| Rebalance page | Workflow layout | `app/(dashboard)/rebalance/page.tsx` |
| Status card | Current state | `components/rebalance/status-card.tsx` |
| Changes preview | Thursday adds/removes | `components/rebalance/changes-preview.tsx` |
| Orders table | Friday orders | `components/rebalance/orders-table.tsx` |
| History list | Past rebalances | `components/rebalance/history-list.tsx` |

**Deliverables**:
- [ ] Searchable trade history per universe
- [ ] CSV export for selected universe
- [ ] Thursday preview (additions/removals)
- [ ] Friday order file download
- [ ] Rebalance history with filter

---

### Phase 5: Admin Control Panel

**Objective**: Sleek admin UI with visual controls, job execution, scheduling.

**Backend Tasks**:
| Task | Description | Endpoint |
|------|-------------|----------|
| Job service | Execute commands | `app/services/job_service.py` |
| Job endpoints | CRUD operations | `POST /api/jobs`, `GET /api/jobs/{id}` |
| Log streaming | SSE endpoint | `GET /api/jobs/{id}/logs?stream=true` |
| Scheduler setup | APScheduler | `app/scheduler/scheduler.py` |
| Scheduled tasks | Daily + weekly | `app/scheduler/tasks.py` |
| Script migration | Move from kite-lab | `app/engine/scripts/` |
| System status | Health + token | `GET /api/system/status` |

**Frontend Tasks**:
| Task | Description | Component |
|------|-------------|-----------|
| Admin page | Full control panel | `app/(dashboard)/admin/page.tsx` |
| Quick actions | One-click cards | `components/admin/quick-actions.tsx` |
| Portfolio form | Parameter dropdowns | `components/admin/portfolio-generator.tsx` |
| Advanced commands | Dropdown + args | `components/admin/advanced-commands.tsx` |
| Job list | Recent jobs | `components/admin/job-list.tsx` |
| Log viewer | Real-time streaming | `components/admin/log-viewer.tsx` |
| Schedule table | All scheduled jobs | `components/admin/schedule-table.tsx` |
| System status | Health indicators | `components/admin/system-status.tsx` |

**Quick Actions**:
- 🔄 Daily Pipeline - Fetch data & build signals
- 📊 Generate Portfolio - Build signals & run backtest
- 🔑 Kite Login - Refresh API access token
- 💾 Backup Data - Sync to backup folder

**Portfolio Generator Parameters**:
- Universe: NSE 500 / Nifty 250 / Nifty 100
- Lookback: 6 / 9 / 12 months
- Rebalance: Weekly / Bi-weekly
- Top-N: 24 (default)
- Vol Floor: 0.05 (default)
- Min Hold Days: 8 (default)

**Deliverables**:
- [ ] One-click Daily Pipeline button
- [ ] Portfolio generator with dropdowns
- [ ] Real-time log viewer with streaming
- [ ] Job history per universe
- [ ] Scheduled jobs for all universes
- [ ] System status dashboard

---

### Phase 6: Polish & Production

**Objective**: Production hardening, error handling, documentation.

**Tasks**:
| Category | Task |
|----------|------|
| **Error Handling** | Error boundaries, fallback UI |
| **Loading States** | Skeletons for all components |
| **Caching** | SWR cache, API-level caching |
| **Performance** | Query optimization, indexes |
| **Monitoring** | Sentry integration, Railway metrics |
| **Security** | CORS hardening, rate limiting |
| **Notifications** | Toast messages, email/Telegram alerts |
| **Mobile** | Responsive tweaks, touch interactions |
| **Documentation** | API docs (Swagger), README updates |
| **Testing** | Critical path E2E tests |

**Deliverables**:
- [ ] All error states handled gracefully
- [ ] Loading states everywhere
- [ ] Monitoring configured
- [ ] Documentation complete
- [ ] Mobile-responsive UI

---

## Database Schema

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   trades    │     │ equity_curve│     │  holdings   │
├─────────────┤     ├─────────────┤     ├─────────────┤
│ universe    │     │ universe    │     │ universe    │
│ trade_date  │     │ date        │     │ snapshot_dt │
│ symbol      │     │ port_value  │     │ symbol      │
│ side        │     │ benchmark   │     │ shares      │
│ shares      │     │ drawdown    │     │ avg_cost    │
│ price       │     └─────────────┘     │ pnl_pct     │
│ notional    │                         └─────────────┘
└─────────────┘

┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   metrics   │     │ rebalances  │     │    jobs     │
├─────────────┤     ├─────────────┤     ├─────────────┤
│ universe    │     │ universe    │     │ command     │
│ cagr        │     │ signal_date │     │ status      │
│ max_dd      │     │ additions   │     │ started_at  │
│ sharpe      │     │ removals    │     │ ended_at    │
│ turnover    │     │ orders_json │     │ log_path    │
└─────────────┘     └─────────────┘     └─────────────┘
```

---

## Directory Structure

```
docs/tasks/
├── README.md                 # This file (overview of all phases)
├── phase1/
│   ├── README.md            # Phase 1 summary
│   ├── 01-backend-setup.md
│   ├── 02-database-models.md
│   ├── ... (12 task files)
├── phase2/
│   ├── README.md            # Phase 2 summary
│   ├── 01-portfolio-service.md
│   ├── 02-portfolio-endpoints.md
│   ├── ... (9 task files)
├── phase3/
│   ├── README.md            # Phase 3 summary
│   ├── 01-metrics-service.md
│   ├── 02-metrics-endpoint.md
│   ├── ... (10 task files)
├── phase4/                  # Created when Phase 4 starts
├── phase5/                  # Created when Phase 5 starts
└── phase6/                  # Created when Phase 6 starts
```

---

## Key Technologies

**Frontend**:
- Next.js 14 (App Router)
- TypeScript
- Tailwind CSS + shadcn/ui
- Recharts (charts)
- SWR (data fetching)
- NextAuth.js (authentication)

**Backend**:
- Python 3.11
- FastAPI
- SQLAlchemy 2.0
- Alembic (migrations)
- APScheduler (Phase 5)

**Infrastructure**:
- Vercel (frontend hosting)
- Railway (backend + PostgreSQL)
- Google OAuth

---

## Sync Commands

Sync local CSV data to production database:

```bash
# Activate virtual environment
cd kite-api && source .venv/bin/activate

# Sync all universes to Railway PostgreSQL
python scripts/sync_to_production.py \
  --database-url "postgresql://postgres:PASSWORD@host:port/railway" \
  --data-dir /Users/navdeep/kite-lab
```

---

*Status Key: `pending` | `in_progress` | `completed`*

*Last updated: February 13, 2026*
