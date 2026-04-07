# Task 2: Job Endpoints

**Status**: `pending`
**Blocked By**: #1 (Job Service)
**Blocks**: #10, #11, #14

## Objective

Create API endpoints for job creation, listing, status checking, log streaming, and cancellation.

## Tasks

- [ ] Create `jobs.py` in `kite-api/app/api/`
- [ ] Implement `POST /api/jobs` - Create and start job
- [ ] Implement `GET /api/jobs` - List recent jobs
- [ ] Implement `GET /api/jobs/{id}` - Get job details
- [ ] Implement `GET /api/jobs/{id}/logs` - Get logs (with SSE option)
- [ ] Implement `POST /api/jobs/{id}/cancel` - Cancel job
- [ ] Add router to `main.py`

## Implementation

### File: `kite-api/app/api/jobs.py`

```python
import asyncio
from fastapi import APIRouter, BackgroundTasks, Query, HTTPException
from fastapi.responses import StreamingResponse
from typing import Optional, List
from pydantic import BaseModel
from datetime import datetime

from app.services.job_service import JobService, COMMANDS
from app.schemas.jobs import JobResponse, JobListResponse, JobCreate

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


class CreateJobRequest(BaseModel):
    """Request body for creating a job."""
    command: str
    universe: Optional[str] = None
    args: Optional[dict] = None
    label: Optional[str] = None


class LogsResponse(BaseModel):
    """Response for job logs."""
    job_id: str
    logs: str
    status: str


@router.post("", response_model=JobResponse)
async def create_job(
    request: CreateJobRequest,
    background_tasks: BackgroundTasks
):
    """
    Create and start a new job.

    Available commands:
    - daily_pipeline: Run full daily pipeline
    - generate_portfolio: Generate portfolio signals
    - backup_data: Backup data to external location
    - fetch_prices: Fetch NSE 500 price data
    - build_signals: Build momentum signals
    """
    # Validate command
    if request.command not in COMMANDS:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown command: {request.command}. Available: {list(COMMANDS.keys())}"
        )

    # Create job
    job = await JobService.create_job(
        command=request.command,
        universe=request.universe,
        args=request.args,
        label=request.label
    )

    # Start job in background
    background_tasks.add_task(JobService.run_job, job.id)

    return job


@router.get("", response_model=JobListResponse)
async def list_jobs(
    limit: int = Query(default=20, ge=1, le=100),
    universe: Optional[str] = None,
    status: Optional[str] = None
):
    """
    List recent jobs with optional filters.

    Query parameters:
    - limit: Number of jobs to return (1-100, default 20)
    - universe: Filter by universe (nse500, nifty100, nifty250)
    - status: Filter by status (queued, running, completed, failed, cancelled)
    """
    jobs = JobService.list_jobs(
        limit=limit,
        universe=universe,
        status=status
    )

    return JobListResponse(jobs=[
        JobResponse(
            id=j.id,
            command=j.command,
            label=j.label,
            universe=j.universe,
            args=j.args,
            status=j.status,
            started_at=j.started_at,
            ended_at=j.ended_at,
            duration_seconds=j.duration_seconds,
            error_message=j.error_message,
            created_at=j.created_at
        ) for j in jobs
    ])


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: str):
    """Get details for a specific job."""
    job = JobService.get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return JobResponse(
        id=job.id,
        command=job.command,
        label=job.label,
        universe=job.universe,
        args=job.args,
        status=job.status,
        started_at=job.started_at,
        ended_at=job.ended_at,
        duration_seconds=job.duration_seconds,
        error_message=job.error_message,
        created_at=job.created_at
    )


@router.get("/{job_id}/logs")
async def get_job_logs(
    job_id: str,
    stream: bool = Query(default=False, description="Enable SSE streaming"),
    tail: int = Query(default=0, ge=0, description="Return last N lines only")
):
    """
    Get logs for a job.

    Query parameters:
    - stream: If true, stream logs via Server-Sent Events
    - tail: If > 0, return only last N lines
    """
    job = JobService.get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if stream:
        return StreamingResponse(
            log_stream_generator(job_id),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
        )

    logs = JobService.read_logs(job_id, tail=tail)

    return LogsResponse(
        job_id=job_id,
        logs=logs,
        status=job.status
    )


@router.post("/{job_id}/cancel")
async def cancel_job(job_id: str):
    """
    Cancel a running or queued job.

    Returns success status.
    """
    job = JobService.get_job(job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status not in ("queued", "running"):
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel job with status: {job.status}"
        )

    success = await JobService.cancel_job(job_id)

    if not success:
        raise HTTPException(status_code=500, detail="Failed to cancel job")

    return {"success": True, "job_id": job_id, "status": "cancelled"}


async def log_stream_generator(job_id: str):
    """
    Generator for streaming logs via SSE.

    Yields log lines as they're written to the file.
    """
    import os

    log_path = JobService.get_log_path(job_id)
    position = 0

    # Wait for log file to be created
    for _ in range(10):
        if log_path.exists():
            break
        await asyncio.sleep(0.5)

    if not log_path.exists():
        yield f"data: Log file not found\n\n"
        return

    while True:
        job = JobService.get_job(job_id)

        with open(log_path, "r") as f:
            f.seek(position)
            new_content = f.read()
            position = f.tell()

        if new_content:
            # Send each line as SSE event
            for line in new_content.splitlines():
                yield f"data: {line}\n\n"

        # Stop if job is complete
        if job and job.status in ("completed", "failed", "cancelled"):
            yield f"event: done\ndata: {job.status}\n\n"
            break

        await asyncio.sleep(0.5)
```

### Update main.py

Add to `kite-api/app/main.py`:

```python
from app.api import jobs

# Include router
app.include_router(jobs.router, tags=["jobs"])
```

## API Specification

### POST /api/jobs

Create and start a new job.

**Request Body:**
```json
{
  "command": "daily_pipeline",
  "universe": "nse500",
  "args": {
    "with_login": true
  },
  "label": "Daily pipeline run"
}
```

**Response:**
```json
{
  "id": "a1b2c3d4e5f6g7h8",
  "command": "daily_pipeline",
  "label": "Daily pipeline run",
  "universe": "nse500",
  "args": {"with_login": true},
  "status": "queued",
  "created_at": "2026-02-14T07:00:00Z"
}
```

### GET /api/jobs

List recent jobs.

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| limit | int | 20 | Number of jobs (1-100) |
| universe | string | null | Filter by universe |
| status | string | null | Filter by status |

**Response:**
```json
{
  "jobs": [
    {
      "id": "a1b2c3d4e5f6g7h8",
      "command": "daily_pipeline",
      "status": "completed",
      "started_at": "2026-02-14T07:00:01Z",
      "ended_at": "2026-02-14T07:05:32Z",
      "duration_seconds": 331
    }
  ]
}
```

### GET /api/jobs/{id}

Get job details.

**Response:** Same as POST response with full details.

### GET /api/jobs/{id}/logs

Get job logs.

**Query Parameters:**
| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| stream | bool | false | Enable SSE streaming |
| tail | int | 0 | Return last N lines |

**Response (non-streaming):**
```json
{
  "job_id": "a1b2c3d4e5f6g7h8",
  "logs": "[2026-02-14T07:00:01] Starting...\n...",
  "status": "running"
}
```

**Response (streaming):**
```
data: [2026-02-14T07:00:01] Starting job...

data: [2026-02-14T07:00:02] Fetching data...

event: done
data: completed
```

### POST /api/jobs/{id}/cancel

Cancel a job.

**Response:**
```json
{
  "success": true,
  "job_id": "a1b2c3d4e5f6g7h8",
  "status": "cancelled"
}
```

## Verification

```bash
# Create a job
curl -X POST http://localhost:8000/api/jobs \
  -H "Content-Type: application/json" \
  -d '{"command": "daily_pipeline", "universe": "nse500"}'

# List jobs
curl http://localhost:8000/api/jobs

# Get job details
curl http://localhost:8000/api/jobs/a1b2c3d4e5f6g7h8

# Get logs
curl http://localhost:8000/api/jobs/a1b2c3d4e5f6g7h8/logs

# Stream logs
curl http://localhost:8000/api/jobs/a1b2c3d4e5f6g7h8/logs?stream=true

# Cancel job
curl -X POST http://localhost:8000/api/jobs/a1b2c3d4e5f6g7h8/cancel
```

## Notes

- Jobs start immediately in background after creation
- SSE streaming closes when job completes
- Cancel doesn't kill subprocess (marks as cancelled only)

---

*Status Key: `pending` | `in_progress` | `completed`*
