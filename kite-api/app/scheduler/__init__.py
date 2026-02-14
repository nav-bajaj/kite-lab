"""Scheduler package for background job scheduling."""

from app.scheduler.scheduler import scheduler, start_scheduler, shutdown_scheduler, get_scheduled_jobs, add_scheduled_job, remove_scheduled_job, run_job_now
from app.scheduler.tasks import SCHEDULED_TASKS, register_default_tasks

__all__ = [
    "scheduler",
    "start_scheduler",
    "shutdown_scheduler",
    "get_scheduled_jobs",
    "add_scheduled_job",
    "remove_scheduled_job",
    "run_job_now",
    "SCHEDULED_TASKS",
    "register_default_tasks",
]
