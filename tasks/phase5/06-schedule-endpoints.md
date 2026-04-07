# Task 6: Schedule Endpoints

**Status**: `pending`
**Blocked By**: #5 (Scheduler Setup)
**Blocks**: #12, #14

## Objective

Create API endpoints for managing scheduled jobs - listing, adding, removing, and triggering.

## Tasks

- [ ] Create `schedule.py` in `kite-api/app/api/`
- [ ] Implement `GET /api/schedule` - List scheduled jobs
- [ ] Implement `POST /api/schedule` - Add scheduled job
- [ ] Implement `DELETE /api/schedule/{id}` - Remove scheduled job
- [ ] Implement `POST /api/schedule/{id}/run` - Run job immediately
- [ ] Add router to `main.py`

## Implementation

### File: `kite-api/app/api/schedule.py`

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

from app.scheduler.scheduler import (
    scheduler,
    get_scheduled_jobs,
    add_scheduled_job,
    remove_scheduled_job,
    run_job_now
)
from app.scheduler.tasks import create_task_wrapper, SCHEDULED_TASKS
from app.services.job_service import COMMANDS

router = APIRouter(prefix="/api/schedule", tags=["schedule"])


class ScheduledJobResponse(BaseModel):
    """Response for a scheduled job."""
    id: str
    name: str
    trigger: str
    next_run: Optional[datetime] = None
    enabled: bool = True


class ScheduleListResponse(BaseModel):
    """Response for schedule list."""
    jobs: List[ScheduledJobResponse]


class CreateScheduleRequest(BaseModel):
    """Request to create a scheduled job."""
    id: str
    name: str
    command: str
    universe: Optional[str] = None
    trigger: str = "cron"  # cron or interval
    # Cron options
    hour: Optional[int] = None
    minute: Optional[int] = 0
    day_of_week: Optional[str] = None  # "mon-fri", "sun", etc.
    # Interval options
    hours: Optional[int] = None
    minutes: Optional[int] = None


class RunNowResponse(BaseModel):
    """Response for run now."""
    success: bool
    job_id: str
    message: str


@router.get("", response_model=ScheduleListResponse)
async def list_scheduled_jobs():
    """
    List all scheduled jobs.

    Returns jobs with their next run time.
    """
    jobs = get_scheduled_jobs()

    return ScheduleListResponse(jobs=[
        ScheduledJobResponse(
            id=job["id"],
            name=job["name"],
            trigger=job["trigger"],
            next_run=datetime.fromisoformat(job["next_run"]) if job["next_run"] else None,
            enabled=not job["pending"]
        ) for job in jobs
    ])


@router.post("", response_model=ScheduledJobResponse)
async def create_scheduled_job(request: CreateScheduleRequest):
    """
    Create a new scheduled job.

    Supports cron and interval triggers.

    Cron examples:
    - Daily at 7am: hour=7, minute=0
    - Weekdays at 7am: hour=7, minute=0, day_of_week="mon-fri"
    - Sunday at 3am: hour=3, minute=0, day_of_week="sun"

    Interval examples:
    - Every 2 hours: trigger="interval", hours=2
    - Every 30 minutes: trigger="interval", minutes=30
    """
    # Validate command
    if request.command not in COMMANDS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown command: {request.command}. Available: {list(COMMANDS.keys())}"
        )

    # Build trigger args
    trigger_args = {}

    if request.trigger == "cron":
        if request.hour is not None:
            trigger_args["hour"] = request.hour
        if request.minute is not None:
            trigger_args["minute"] = request.minute
        if request.day_of_week:
            trigger_args["day_of_week"] = request.day_of_week

    elif request.trigger == "interval":
        if request.hours:
            trigger_args["hours"] = request.hours
        if request.minutes:
            trigger_args["minutes"] = request.minutes

        if not trigger_args:
            raise HTTPException(
                status_code=400,
                detail="Interval trigger requires hours or minutes"
            )

    else:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid trigger: {request.trigger}. Use 'cron' or 'interval'"
        )

    # Create task wrapper
    func = create_task_wrapper(request.command, request.universe)

    # Add to scheduler
    job = add_scheduled_job(
        func=func,
        job_id=request.id,
        name=request.name,
        trigger=request.trigger,
        **trigger_args
    )

    return ScheduledJobResponse(
        id=job.id,
        name=job.name,
        trigger=str(job.trigger),
        next_run=job.next_run_time,
        enabled=True
    )


@router.delete("/{job_id}")
async def delete_scheduled_job(job_id: str):
    """
    Remove a scheduled job.

    Returns success status.
    """
    # Prevent deleting default tasks
    default_ids = [t["id"] for t in SCHEDULED_TASKS]
    if job_id in default_ids:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete default scheduled tasks"
        )

    success = remove_scheduled_job(job_id)

    if not success:
        raise HTTPException(status_code=404, detail="Scheduled job not found")

    return {"success": True, "job_id": job_id}


@router.post("/{job_id}/run", response_model=RunNowResponse)
async def run_scheduled_job_now(job_id: str):
    """
    Run a scheduled job immediately.

    Triggers the job outside its normal schedule.
    """
    job = scheduler.get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Scheduled job not found")

    success = run_job_now(job_id)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to trigger job")

    return RunNowResponse(
        success=True,
        job_id=job_id,
        message=f"Job '{job.name}' triggered for immediate execution"
    )


@router.get("/defaults")
async def get_default_schedules():
    """
    Get list of default scheduled tasks.

    Returns predefined task configurations.
    """
    return {"tasks": SCHEDULED_TASKS}
```

### Update main.py

Add to `kite-api/app/main.py`:

```python
from app.api import schedule

# Include router
app.include_router(schedule.router, tags=["schedule"])
```

## API Specification

### GET /api/schedule

List all scheduled jobs.

**Response:**
```json
{
  "jobs": [
    {
      "id": "daily_pipeline",
      "name": "Daily Pipeline",
      "trigger": "cron[hour='7', minute='0', day_of_week='mon-fri']",
      "next_run": "2026-02-15T07:00:00+05:30",
      "enabled": true
    },
    {
      "id": "weekly_backup",
      "name": "Weekly Backup",
      "trigger": "cron[day_of_week='sun', hour='3', minute='0']",
      "next_run": "2026-02-16T03:00:00+05:30",
      "enabled": true
    }
  ]
}
```

### POST /api/schedule

Create a new scheduled job.

**Request (Cron - Daily):**
```json
{
  "id": "hourly_check",
  "name": "Hourly Health Check",
  "command": "fetch_prices",
  "trigger": "cron",
  "hour": 9,
  "minute": 30
}
```

**Request (Cron - Weekdays):**
```json
{
  "id": "morning_pipeline",
  "name": "Morning Pipeline",
  "command": "daily_pipeline",
  "trigger": "cron",
  "hour": 7,
  "minute": 0,
  "day_of_week": "mon-fri"
}
```

**Request (Interval):**
```json
{
  "id": "periodic_fetch",
  "name": "Periodic Fetch",
  "command": "fetch_prices",
  "trigger": "interval",
  "hours": 2
}
```

**Response:**
```json
{
  "id": "hourly_check",
  "name": "Hourly Health Check",
  "trigger": "cron[hour='9', minute='30']",
  "next_run": "2026-02-14T09:30:00+05:30",
  "enabled": true
}
```

### DELETE /api/schedule/{id}

Remove a scheduled job.

**Response:**
```json
{
  "success": true,
  "job_id": "hourly_check"
}
```

**Error (default task):**
```json
{
  "detail": "Cannot delete default scheduled tasks"
}
```

### POST /api/schedule/{id}/run

Run a scheduled job immediately.

**Response:**
```json
{
  "success": true,
  "job_id": "daily_pipeline",
  "message": "Job 'Daily Pipeline' triggered for immediate execution"
}
```

### GET /api/schedule/defaults

Get default task configurations.

**Response:**
```json
{
  "tasks": [
    {
      "id": "daily_pipeline",
      "name": "Daily Pipeline",
      "description": "Fetch data, build signals, backup",
      "command": "daily_pipeline",
      "trigger": "cron",
      "trigger_args": {
        "hour": 7,
        "minute": 0,
        "day_of_week": "mon-fri"
      }
    }
  ]
}
```

## Trigger Examples

### Cron Triggers

| Schedule | hour | minute | day_of_week |
|----------|------|--------|-------------|
| Daily 7am | 7 | 0 | - |
| Weekdays 7am | 7 | 0 | mon-fri |
| Sunday 3am | 3 | 0 | sun |
| Every hour | * | 0 | - |

### Interval Triggers

| Schedule | hours | minutes |
|----------|-------|---------|
| Every 2 hours | 2 | - |
| Every 30 min | - | 30 |
| Every 4 hours | 4 | - |

## Verification

```bash
# List scheduled jobs
curl http://localhost:8000/api/schedule | jq

# Create new scheduled job
curl -X POST http://localhost:8000/api/schedule \
  -H "Content-Type: application/json" \
  -d '{"id": "test_job", "name": "Test Job", "command": "backup_data", "trigger": "cron", "hour": 12}'

# Run job immediately
curl -X POST http://localhost:8000/api/schedule/daily_pipeline/run

# Delete job
curl -X DELETE http://localhost:8000/api/schedule/test_job

# Get defaults
curl http://localhost:8000/api/schedule/defaults | jq
```

## Notes

- Default tasks cannot be deleted
- Jobs persist across restarts (PostgreSQL store)
- Run now triggers immediate execution
- Timezone is Asia/Kolkata (IST)

---

*Status Key: `pending` | `in_progress` | `completed`*
