# Task 03: Update CLAUDE.md

**Status**: `pending`
**Priority**: MEDIUM
**Estimated Time**: 20 minutes

## Problem

`CLAUDE.md` does not mention the production dashboard that was built in phases 1-6. The document focuses on CLI scripts and local operations but doesn't reference:

- Production dashboard URLs
- Dashboard operation commands
- API endpoints
- Frontend/backend architecture

## Current State

CLAUDE.md covers:
- Momentum engine operation
- Script commands
- Backtest parameters
- Data directories

Missing:
- Dashboard section
- Production URLs
- API reference
- Dashboard-related workflows

## Changes Required

### 1. Add Dashboard Section (After Project Overview)

Add new section:

```markdown
## Production Dashboard

The Kite-Lab dashboard provides web-based monitoring and control of the momentum portfolio system.

**Production URLs:**
| Service | URL |
|---------|-----|
| Frontend | https://kite-lab.vercel.app |
| Backend API | https://kite-lab-production.up.railway.app |
| API Docs | https://kite-lab-production.up.railway.app/docs |

**Tech Stack:**
- Frontend: Next.js 14, TypeScript, Tailwind CSS, shadcn/ui
- Backend: FastAPI, PostgreSQL, SQLAlchemy
- Hosting: Vercel (frontend) + Railway (backend + DB)

**Key Features:**
- Portfolio view with holdings, P&L, allocation
- Performance metrics with equity curves and benchmarks
- Trade history with search and CSV export
- Rebalance workflow (Thursday preview, Friday orders)
- Admin panel with job execution and scheduling

**Authentication:** Google OAuth (email whitelist)
```

### 2. Add Dashboard Commands Section

Add after "Common Commands":

```markdown
### Dashboard Operations

```bash
# Sync local data to production database
cd kite-api && source .venv/bin/activate
python scripts/sync_to_production.py --data-dir /path/to/kite-lab

# Run backend locally
cd kite-api && uvicorn app.main:app --reload

# Run frontend locally
cd kite-dashboard && npm run dev
```
```

### 3. Update Architecture Section

Add dashboard architecture:

```markdown
### Dashboard Architecture (`kite-api/` and `kite-dashboard/`)

**Backend Services:**
- `portfolio_service.py` - Portfolio data retrieval
- `metrics_service.py` - Performance calculations
- `trade_service.py` - Trade history queries
- `rebalance_service.py` - Rebalance workflow
- `job_service.py` - Job execution
- `sync_service.py` - CSV to database sync

**API Endpoints:**
- `/api/portfolio` - Holdings and allocation
- `/api/metrics` - Performance metrics
- `/api/trades` - Trade history
- `/api/rebalance` - Rebalance workflow
- `/api/jobs` - Job management
- `/api/system` - Health and status
```

### 4. Update Last Updated Date

Change the date at the bottom of the file.

## Verification

After changes:
1. Dashboard URLs accessible from CLAUDE.md
2. Tech stack documented
3. Dashboard commands included
4. Architecture section updated

## Files Modified

- `CLAUDE.md`

---

*Task created: 2026-03-20*
