"""
Job API endpoints for executing and managing background jobs.

All endpoints require authentication.
"""
import asyncio
from fastapi import APIRouter, BackgroundTasks, Query, HTTPException, Depends
from fastapi.responses import StreamingResponse
from typing import Optional
from pydantic import BaseModel, Field

from app.services.job_service import JobService, COMMANDS
from app.schemas.jobs import JobResponse, JobListResponse
from app.auth import (
    get_optional_user,
    require_admin,
    validate_token_string,
    AuthError,
)

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


class CreateJobRequest(BaseModel):
    """Request body for creating a job."""
    command: str = Field(..., max_length=100)
    universe: Optional[str] = Field(None, max_length=50)
    args: Optional[dict] = None
    label: Optional[str] = Field(None, max_length=500)


class LogsResponse(BaseModel):
    """Response for job logs."""
    job_id: str
    logs: str
    status: str


class CancelResponse(BaseModel):
    """Response for cancel operation."""
    success: bool
    job_id: str
    status: str


@router.post("", response_model=JobResponse)
async def create_job(
    request: CreateJobRequest,
    background_tasks: BackgroundTasks,
    user: dict = Depends(require_admin)
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


@router.get("", response_model=JobListResponse)
async def list_jobs(
    limit: int = Query(default=20, ge=1, le=100),
    universe: Optional[str] = None,
    status: Optional[str] = None,
    user: dict = Depends(require_admin)
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
async def get_job(job_id: str, user: dict = Depends(require_admin)):
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
    tail: int = Query(default=0, ge=0, description="Return last N lines only"),
    token: str = Query(default=None, description="JWT token (for SSE clients that can't send headers)"),
    user: dict = Depends(get_optional_user),
):
    """
    Get logs for a job.

    Auth: accepts token via query param (for EventSource) or Authorization header.
    """
    # Authenticate via header or query param token, then require admin role.
    # Job logs may contain subprocess output that could leak operational
    # data, so they're admin-only just like the other job endpoints.
    if user is None:
        if token:
            try:
                user = validate_token_string(token)
            except AuthError:
                raise HTTPException(status_code=401, detail="Invalid or expired token")
        else:
            raise HTTPException(status_code=401, detail="Authentication required")
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin role required")
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


@router.post("/{job_id}/cancel", response_model=CancelResponse)
async def cancel_job(job_id: str, user: dict = Depends(require_admin)):
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

    return CancelResponse(success=True, job_id=job_id, status="cancelled")


async def log_stream_generator(job_id: str):
    """
    Generator for streaming logs via SSE.

    Yields log lines as they're written to the file.
    """
    log_path = JobService.get_log_path(job_id)
    position = 0

    # Wait for log file to be created
    for _ in range(10):
        if log_path.exists():
            break
        await asyncio.sleep(0.5)

    if not log_path.exists():
        yield "data: Log file not found\n\n"
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
