# Task 5: Scheduler Setup

**Status**: `pending`
**Blocked By**: None
**Blocks**: #6

## Objective

Set up APScheduler with PostgreSQL job store for scheduled task execution.

## Tasks

- [ ] Create `app/scheduler/` package
- [ ] Create `scheduler.py` with APScheduler setup
- [ ] Create `tasks.py` with predefined scheduled tasks
- [ ] Configure timezone (Asia/Kolkata)
- [ ] Implement graceful shutdown handling
- [ ] Integrate with FastAPI lifespan

## Implementation

### File: `kite-api/app/scheduler/__init__.py`

```python
"""Scheduler package for background job scheduling."""

from app.scheduler.scheduler import scheduler, start_scheduler, shutdown_scheduler
from app.scheduler.tasks import SCHEDULED_TASKS, register_default_tasks

__all__ = [
    "scheduler",
    "start_scheduler",
    "shutdown_scheduler",
    "SCHEDULED_TASKS",
    "register_default_tasks",
]
```

### File: `kite-api/app/scheduler/scheduler.py`

```python
"""
APScheduler setup with PostgreSQL job store.

Uses AsyncIOScheduler for async job execution.
"""
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.asyncio import AsyncIOExecutor
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED
from pytz import timezone

from app.config import settings

logger = logging.getLogger(__name__)

# Timezone for India
IST = timezone("Asia/Kolkata")

# Job stores configuration
jobstores = {
    "default": SQLAlchemyJobStore(url=settings.database_url)
}

# Executors configuration
executors = {
    "default": AsyncIOExecutor()
}

# Job defaults
job_defaults = {
    "coalesce": True,  # Combine missed executions into one
    "max_instances": 1,  # Only one instance at a time
    "misfire_grace_time": 3600,  # 1 hour grace period for missed jobs
}

# Create scheduler
scheduler = AsyncIOScheduler(
    jobstores=jobstores,
    executors=executors,
    job_defaults=job_defaults,
    timezone=IST,
)


def job_listener(event):
    """Log job execution events."""
    if event.exception:
        logger.error(f"Job {event.job_id} failed: {event.exception}")
    else:
        logger.info(f"Job {event.job_id} executed successfully")


# Add event listeners
scheduler.add_listener(job_listener, EVENT_JOB_ERROR | EVENT_JOB_EXECUTED)


async def start_scheduler():
    """
    Start the scheduler.

    Called during FastAPI startup.
    """
    if not scheduler.running:
        scheduler.start()
        logger.info("Scheduler started")


async def shutdown_scheduler():
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

    # Trigger immediate execution
    job.modify(next_run_time=None)
    scheduler.wakeup()

    logger.info(f"Triggered immediate execution: {job_id}")
    return True
```

### File: `kite-api/app/scheduler/tasks.py`

```python
"""
Predefined scheduled tasks for Kite-Lab.

These tasks run automatically based on their schedule.
"""
import asyncio
import logging

from app.services.job_service import JobService

logger = logging.getLogger(__name__)


# Predefined scheduled tasks
SCHEDULED_TASKS = [
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
        },
    },
    {
        "id": "weekly_backup",
        "name": "Weekly Backup",
        "description": "Full data backup",
        "command": "backup_data",
        "trigger": "cron",
        "trigger_args": {
            "day_of_week": "sun",
            "hour": 3,
            "minute": 0
        },
    },
]


async def execute_scheduled_task(command: str, universe: str = None):
    """
    Execute a scheduled task by creating and running a job.

    Args:
        command: Command name from COMMANDS
        universe: Target universe (optional)
    """
    logger.info(f"Executing scheduled task: {command}")

    try:
        # Create job
        job = await JobService.create_job(
            command=command,
            universe=universe,
            label=f"Scheduled: {command}"
        )

        # Run job
        await JobService.run_job(job.id)

        logger.info(f"Scheduled task completed: {command} (job_id={job.id})")

    except Exception as e:
        logger.error(f"Scheduled task failed: {command} - {str(e)}")


def create_task_wrapper(command: str, universe: str = None):
    """
    Create an async wrapper function for a scheduled task.

    APScheduler calls this function on schedule.
    """
    async def wrapper():
        await execute_scheduled_task(command, universe)
    return wrapper


def register_default_tasks(scheduler):
    """
    Register predefined scheduled tasks with the scheduler.

    Called during startup to set up default schedules.
    """
    from app.scheduler.scheduler import add_scheduled_job

    for task in SCHEDULED_TASKS:
        func = create_task_wrapper(task["command"])

        add_scheduled_job(
            func=func,
            job_id=task["id"],
            name=task["name"],
            trigger=task["trigger"],
            **task["trigger_args"]
        )

    logger.info(f"Registered {len(SCHEDULED_TASKS)} default tasks")
```

### Update main.py

Update `kite-api/app/main.py` lifespan:

```python
from contextlib import asynccontextmanager
from app.scheduler import start_scheduler, shutdown_scheduler, register_default_tasks, scheduler

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    settings = get_settings()
    print(f"Starting Kite-Lab API (debug={settings.debug})")

    # Start scheduler
    await start_scheduler()
    register_default_tasks(scheduler)

    yield

    # Shutdown
    await shutdown_scheduler()
    print("Shutting down Kite-Lab API")
```

## Scheduler Configuration

### Timezone

All schedules use Asia/Kolkata (IST) timezone.

### Job Store

Uses PostgreSQL for persistent job storage. Jobs survive server restarts.

### Executor

AsyncIOExecutor for async job execution.

### Job Defaults

| Setting | Value | Description |
|---------|-------|-------------|
| coalesce | True | Combine missed runs |
| max_instances | 1 | One instance at a time |
| misfire_grace_time | 3600 | 1 hour grace period |

## Default Schedules

| Task | Schedule | Description |
|------|----------|-------------|
| Daily Pipeline | 07:00 IST Mon-Fri | Fetch data, signals, backup |
| Weekly Backup | 03:00 IST Sunday | Full data backup |

## Verification

```python
from app.scheduler import scheduler, get_scheduled_jobs

# Check scheduler is running
print(f"Scheduler running: {scheduler.running}")

# List scheduled jobs
jobs = get_scheduled_jobs()
for job in jobs:
    print(f"{job['id']}: next run at {job['next_run']}")

# Manually trigger a job
from app.scheduler.scheduler import run_job_now
run_job_now("daily_pipeline")
```

## Notes

- Jobs persist across server restarts (PostgreSQL store)
- Missed jobs execute on next startup (coalesce)
- Max 1 hour grace period for missed executions
- Graceful shutdown waits for running jobs

---

*Status Key: `pending` | `in_progress` | `completed`*
