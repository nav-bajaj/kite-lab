# Phase 5: Admin Control Panel

**Duration**: Week 9-10
**Status**: Completed
**Completed**: February 14, 2026

## Objectives

- Build sleek admin UI with visual controls
- Job execution with real-time log streaming
- Scheduled job management with APScheduler
- System health monitoring and token status
- Portfolio generation with custom parameters

## Production URLs

| Service | URL |
|---------|-----|
| Frontend | https://kite-lab.vercel.app |
| Backend | https://kite-lab-production.up.railway.app |

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend (Next.js)                        │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────────┐│
│  │Quick Actions│ │Portfolio Gen│ │    Job List + Logs      ││
│  │   Cards     │ │    Form     │ │   (SSE streaming)       ││
│  └─────────────┘ └─────────────┘ └─────────────────────────┘│
│  ┌─────────────────────────┐ ┌─────────────────────────────┐│
│  │   Schedule Table        │ │   System Status             ││
│  └─────────────────────────┘ └─────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Backend (FastAPI)                         │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────────┐│
│  │ Job Service │ │  Scheduler  │ │   System Service        ││
│  │ (subprocess)│ │ (APScheduler│ │   (health + token)      ││
│  └─────────────┘ └─────────────┘ └─────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

## Task Progress

### Backend Tasks

| # | Task | Status | Description |
|---|------|--------|-------------|
| 1 | Job service | `completed` | Execute scripts via subprocess with status tracking |
| 2 | Job endpoints | `completed` | POST/GET /api/jobs, logs streaming |
| 3 | System service | `completed` | Health checks, token status, last sync |
| 4 | System endpoints | `completed` | GET /api/system/status, token |
| 5 | Scheduler setup | `completed` | APScheduler with PostgreSQL job store |
| 6 | Schedule endpoints | `completed` | CRUD for scheduled jobs |

### Frontend Tasks

| # | Task | Status | Description |
|---|------|--------|-------------|
| 7 | Admin page layout | `completed` | Grid layout with all sections |
| 8 | Quick actions | `completed` | Action buttons with loading states |
| 9 | Portfolio generator | `completed` | Form with parameter dropdowns |
| 10 | Job list | `completed` | Recent jobs with status badges |
| 11 | Log viewer | `completed` | SSE streaming, auto-scroll |
| 12 | Schedule table | `completed` | Scheduled jobs management |
| 13 | System status | `completed` | Health indicators in header |
| 14 | API client + hooks | `completed` | Job/schedule/system API functions |

## Dependency Graph

```
Backend:                                Frontend:
┌───┐                                  ┌───┐
│ 1 │ Job Service                      │ 7 │ Admin Page Layout
└─┬─┘                                  └─┬─┘
  │                                      │
  ▼                                      ├────────┬────────┬────────┐
┌───┐   ┌───┐                            ▼        ▼        ▼        ▼
│ 2 │   │ 3 │ System Service           ┌───┐    ┌───┐    ┌───┐    ┌────┐
└───┘   └─┬─┘                          │ 8 │    │ 9 │    │12 │    │ 13 │
Jobs      │                            └─┬─┘    └───┘    └───┘    └────┘
Endpoints │                           Quick   Portfolio Schedule  System
          ▼                           Actions Generator  Table   Status
        ┌───┐                            │
        │ 4 │ System Endpoints           ▼
        └───┘                          ┌───┐    ┌────┐
                                       │10 │───▶│ 11 │
┌───┐   ┌───┐                          └───┘    └────┘
│ 5 │──▶│ 6 │                         Job List  Log Viewer
└───┘   └───┘
Scheduler Schedule
Setup    Endpoints

All frontend tasks depend on:
┌────┐
│ 14 │ API Client + Hooks
└────┘
```

## API Endpoints

### Jobs

```
POST /api/jobs              - Create and start job
GET  /api/jobs              - List recent jobs
GET  /api/jobs/{id}         - Get job details
GET  /api/jobs/{id}/logs    - Get job logs (SSE streaming option)
POST /api/jobs/{id}/cancel  - Cancel running job
```

### System

```
GET /api/system/status      - Full system status
GET /api/system/token       - Token status only
```

### Schedule

```
GET  /api/schedule          - List all scheduled jobs
POST /api/schedule          - Add scheduled job
DELETE /api/schedule/{id}   - Remove scheduled job
POST /api/schedule/{id}/run - Run scheduled job immediately
```

## UI Layout

```
┌─────────────────────────────────────────────────────────────┐
│ Admin Control Panel                    [System Status: ●]   │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Quick Actions                                         │   │
│  │ [🔄 Daily Pipeline] [📊 Generate] [🔑 Login] [💾 Backup]│   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────┐ ┌─────────────────────────────┐   │
│  │ Portfolio Generator  │ │ Recent Jobs                 │   │
│  │ Universe: [▼ NSE500] │ │ ┌─────────────────────────┐ │   │
│  │ Lookback: [▼ 6 mo  ] │ │ │ Daily Pipeline  ● Done  │ │   │
│  │ Rebalance: [▼ Weekly]│ │ │ 2 min ago              │ │   │
│  │ Top-N: [24]          │ │ ├─────────────────────────┤ │   │
│  │ [Generate Portfolio] │ │ │ Generate NSE500 ◐ Run  │ │   │
│  └──────────────────────┘ │ │ 5 min ago              │ │   │
│                           │ └─────────────────────────┘ │   │
│                           └─────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Job Logs                                    [Clear]   │   │
│  │ ┌────────────────────────────────────────────────────┐│   │
│  │ │ [07:00:01] Starting daily pipeline...              ││   │
│  │ │ [07:00:02] Fetching NSE 500 data...                ││   │
│  │ │ [07:05:32] Building momentum signals...            ││   │
│  │ │ [07:06:15] Pipeline completed successfully         ││   │
│  │ └────────────────────────────────────────────────────┘│   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ Scheduled Jobs                                        │   │
│  │ ┌────────┬───────────┬──────────┬─────────┬────────┐ │   │
│  │ │ Name   │ Schedule  │ Universe │ Next Run│ Action │ │   │
│  │ ├────────┼───────────┼──────────┼─────────┼────────┤ │   │
│  │ │ Daily  │ 07:00 IST │ All      │ Tomorrow│ [▶][✕] │ │   │
│  │ │ Backup │ Sun 03:00 │ All      │ 5 days  │ [▶][✕] │ │   │
│  │ └────────┴───────────┴──────────┴─────────┴────────┘ │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

## Files to Create

### Backend

| File | Description |
|------|-------------|
| `kite-api/app/services/job_service.py` | Job execution and management |
| `kite-api/app/services/system_service.py` | Health checks and token status |
| `kite-api/app/api/jobs.py` | Job endpoints |
| `kite-api/app/api/system.py` | System endpoints |
| `kite-api/app/scheduler/__init__.py` | Scheduler package |
| `kite-api/app/scheduler/scheduler.py` | APScheduler setup |
| `kite-api/app/scheduler/tasks.py` | Predefined scheduled tasks |
| `kite-api/app/api/schedule.py` | Schedule endpoints |

### Frontend

| File | Description |
|------|-------------|
| `kite-dashboard/src/app/(dashboard)/admin/page.tsx` | Admin page layout |
| `kite-dashboard/src/components/admin/index.ts` | Component exports |
| `kite-dashboard/src/components/admin/quick-actions.tsx` | Action buttons |
| `kite-dashboard/src/components/admin/portfolio-generator.tsx` | Parameter form |
| `kite-dashboard/src/components/admin/job-list.tsx` | Job list with badges |
| `kite-dashboard/src/components/admin/log-viewer.tsx` | Log viewer with SSE |
| `kite-dashboard/src/components/admin/schedule-table.tsx` | Scheduled jobs table |
| `kite-dashboard/src/components/admin/system-status.tsx` | Status indicators |
| `kite-dashboard/src/lib/api-client.ts` | Add job/schedule/system APIs |
| `kite-dashboard/src/lib/hooks.ts` | Add useJobs, useSchedule hooks |

## Key Decisions

### Login Script Handling

The `login_and_save_token.py` requires browser interaction (Zerodha OAuth). Approach:
- Show instructions modal with login URL
- User clicks manually to complete OAuth
- Cannot automate browser interaction

### Log Streaming

Use Server-Sent Events (SSE) for real-time log streaming:
```python
@router.get("/api/jobs/{job_id}/logs")
async def stream_logs(job_id: int, stream: bool = False):
    if stream:
        return StreamingResponse(log_generator(), media_type="text/event-stream")
    return {"logs": read_full_log()}
```

### Job Execution

Run scripts in subprocess with:
- Working directory: kite-lab root
- Virtual environment activation
- Timeout handling (30 min default)
- Output capture to log file

## Deliverables Checklist

- [x] Admin page accessible at `/admin`
- [x] Quick actions execute jobs successfully
- [x] Portfolio generator creates jobs with custom params
- [x] Job list shows recent jobs with correct status
- [x] Log viewer streams logs in real-time
- [x] Schedule table manages scheduled jobs
- [x] System status shows API health and token status
- [x] All components responsive on mobile/tablet/desktop
- [x] Database sync command added for loading CSV to database

## Technical Notes

### Job Status Flow

```
queued → running → completed
              ↘→ failed
              ↘→ cancelled
```

### Status Badges

| Status | Color | Icon |
|--------|-------|------|
| Queued | Yellow | ⏳ |
| Running | Blue (animated) | 🔄 |
| Completed | Green | ✅ |
| Failed | Red | ❌ |
| Cancelled | Gray | ⏹️ |

### Scheduler Configuration

```python
scheduler = BackgroundScheduler(
    jobstores={'default': MemoryJobStore()},
    executors={'default': ThreadPoolExecutor(max_workers=2)},
    timezone='Asia/Kolkata'
)

SCHEDULED_TASKS = [
    {"id": "daily_pipeline", "trigger": "cron", "hour": 7, "minute": 0, "day_of_week": "mon-fri"},
    {"id": "weekly_backup", "trigger": "cron", "day_of_week": "sun", "hour": 3},
]
```

## Database Tables Used

| Table | Usage |
|-------|-------|
| `jobs` | Store job execution history |

## Dependencies

### Backend
- APScheduler (already in requirements.txt)
- asyncio subprocess

### Frontend
- No new dependencies (use existing shadcn/ui components)

---

*Status Key: `pending` | `in_progress` | `completed`*

*Last updated: February 14, 2026*
