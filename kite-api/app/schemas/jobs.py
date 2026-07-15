"""
Job-related schemas.
"""
from pydantic import BaseModel, field_validator
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime, timezone


JobStatus = Literal["queued", "running", "completed", "failed", "cancelled"]


class JobCreate(BaseModel):
    """Request to create a new job."""
    command: str
    parameters: Optional[Dict[str, Any]] = None


class JobResponse(BaseModel):
    """Job details response."""
    id: str
    command: str
    label: Optional[str] = None
    universe: Optional[str] = None
    args: Optional[Dict[str, Any]] = None
    status: JobStatus
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    error_message: Optional[str] = None
    created_at: datetime

    @field_validator("started_at", "ended_at", "created_at")
    @classmethod
    def _assume_utc(cls, v: Optional[datetime]) -> Optional[datetime]:
        # Job rows are stamped naive-UTC (models use func.now() on a UTC
        # Postgres; JobService uses datetime.utcnow()). Serialized without
        # an offset, the dashboard's `new Date()` parses them as browser-
        # local time and every job renders ~5.5h stale in IST. Attach the
        # offset here. ScheduleInfo.next_run is deliberately untouched —
        # APScheduler emits it timezone-aware already.
        if v is not None and v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v

    class Config:
        from_attributes = True


class JobListResponse(BaseModel):
    """List of jobs."""
    jobs: List[JobResponse]


class ScheduleInfo(BaseModel):
    """Scheduled job information."""
    id: str
    name: str
    universe: Optional[str] = None
    cron: str
    next_run: Optional[datetime] = None
    enabled: bool
