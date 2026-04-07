"""
Schedule API endpoints for managing scheduled jobs.

All endpoints require authentication.
"""
from fastapi import APIRouter, HTTPException, Depends
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
from app.auth import get_current_user

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


class DeleteResponse(BaseModel):
    """Response for delete operation."""
    success: bool
    job_id: str


@router.get("", response_model=ScheduleListResponse)
async def list_scheduled_jobs(user: dict = Depends(get_current_user)):
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
async def create_scheduled_job(request: CreateScheduleRequest, user: dict = Depends(get_current_user)):
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


@router.delete("/{job_id}", response_model=DeleteResponse)
async def delete_scheduled_job(job_id: str, user: dict = Depends(get_current_user)):
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

    return DeleteResponse(success=True, job_id=job_id)


@router.post("/{job_id}/run", response_model=RunNowResponse)
async def run_scheduled_job_now(job_id: str, user: dict = Depends(get_current_user)):
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
async def get_default_schedules(user: dict = Depends(get_current_user)):
    """
    Get list of default scheduled tasks.

    Returns predefined task configurations.
    """
    return {"tasks": SCHEDULED_TASKS}
