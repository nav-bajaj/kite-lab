"""
Job-related schemas.
"""
from pydantic import BaseModel
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime


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
