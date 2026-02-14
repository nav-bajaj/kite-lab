"""
APScheduler setup for scheduled task execution.

Uses BackgroundScheduler with ThreadPoolExecutor for reliable job execution.
Default tasks are registered on every startup (no persistence needed).
"""
import logging
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.pool import ThreadPoolExecutor
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED
from pytz import timezone

logger = logging.getLogger(__name__)

# Timezone for India
IST = timezone("Asia/Kolkata")

# Job stores configuration - use memory store (jobs re-register on startup)
jobstores = {
    "default": MemoryJobStore()
}

# Executors configuration - use thread pool for sync functions
executors = {
    "default": ThreadPoolExecutor(max_workers=2)
}

# Job defaults
job_defaults = {
    "coalesce": True,  # Combine missed executions into one
    "max_instances": 1,  # Only one instance at a time
    "misfire_grace_time": 3600,  # 1 hour grace period for missed jobs
}

# Create scheduler
scheduler = BackgroundScheduler(
    jobstores=jobstores,
    executors=executors,
    job_defaults=job_defaults,
    timezone=IST,
)


def job_listener(event):
    """Log job execution events."""
    if event.exception:
        logger.error(f"Scheduled job {event.job_id} failed: {event.exception}")
    else:
        logger.info(f"Scheduled job {event.job_id} executed successfully")


# Add event listeners
scheduler.add_listener(job_listener, EVENT_JOB_ERROR | EVENT_JOB_EXECUTED)


def start_scheduler():
    """
    Start the scheduler.

    Called during FastAPI startup.
    """
    if not scheduler.running:
        scheduler.start()
        logger.info("Scheduler started")


def shutdown_scheduler():
    """
    Gracefully shutdown the scheduler.

    Called during FastAPI shutdown.
    """
    if scheduler.running:
        scheduler.shutdown(wait=True)
        logger.info("Scheduler shutdown complete")


def get_scheduled_jobs():
    """
    Get list of all scheduled jobs.

    Returns job info including next run time.
    """
    jobs = []

    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "trigger": str(job.trigger),
            "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
            "pending": job.pending,
        })

    return jobs


def add_scheduled_job(
    func,
    job_id: str,
    name: str,
    trigger: str,
    **trigger_args
):
    """
    Add a new scheduled job.

    Args:
        func: Async function to execute
        job_id: Unique job identifier
        name: Human-readable name
        trigger: Trigger type (cron, interval, date)
        **trigger_args: Trigger-specific arguments

    Returns:
        The created job
    """
    # Remove existing job with same ID
    existing = scheduler.get_job(job_id)
    if existing:
        scheduler.remove_job(job_id)

    job = scheduler.add_job(
        func,
        trigger=trigger,
        id=job_id,
        name=name,
        replace_existing=True,
        **trigger_args
    )

    logger.info(f"Added scheduled job: {job_id} ({trigger})")
    return job


def remove_scheduled_job(job_id: str) -> bool:
    """
    Remove a scheduled job.

    Args:
        job_id: Job identifier

    Returns:
        True if removed, False if not found
    """
    try:
        scheduler.remove_job(job_id)
        logger.info(f"Removed scheduled job: {job_id}")
        return True
    except Exception:
        return False


def run_job_now(job_id: str) -> bool:
    """
    Run a scheduled job immediately.

    Args:
        job_id: Job identifier

    Returns:
        True if triggered, False if not found
    """
    job = scheduler.get_job(job_id)
    if not job:
        return False

    # Trigger immediate execution by modifying next run time
    job.modify(next_run_time=datetime.now(IST))

    logger.info(f"Triggered immediate execution: {job_id}")
    return True
