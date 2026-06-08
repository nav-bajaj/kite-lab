"""
Predefined scheduled tasks for Kite-Lab.

These tasks run automatically based on their schedule.
Uses module-level functions for APScheduler serialization compatibility.
"""
import logging

logger = logging.getLogger(__name__)


# Predefined scheduled tasks configuration
SCHEDULED_TASKS = [
    {
        "id": "daily_pipeline",
        "name": "Daily Pipeline",
        "description": "Auto-login + fetch data, build signals, backup",
        "command": "daily_pipeline",
        "args": {"with-login": True, "headless": True},
        "func_ref": "app.scheduler.tasks:run_daily_pipeline",
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
        "func_ref": "app.scheduler.tasks:run_weekly_backup",
        "trigger": "cron",
        "trigger_args": {
            "day_of_week": "sun",
            "hour": 3,
            "minute": 0
        },
    },
    # Phase 2.5.6 — Railway-side backup chain. Both jobs every day so
    # weekends don't go without a backup; the dump is small enough
    # that 7-days-a-week cost is negligible.
    {
        "id": "daily_db_backup",
        "name": "Daily DB Backup",
        "description": "Dump Postgres to /data/db_backups/ + smoke-test + rotation",
        "command": "db_backup",
        "func_ref": "app.scheduler.tasks:run_daily_db_backup",
        "trigger": "cron",
        "trigger_args": {
            "hour": 20,
            "minute": 0,
        },
    },
    {
        "id": "daily_cloud_upload",
        "name": "Daily Cloud Upload",
        "description": "Mirror /data backup tarballs + snapshot price dirs to Google Drive",
        "command": "cloud_upload",
        "func_ref": "app.scheduler.tasks:run_daily_cloud_upload",
        "trigger": "cron",
        "trigger_args": {
            "hour": 20,
            "minute": 30,
        },
    },
]


# Module-level task functions (required for APScheduler serialization)
def run_daily_pipeline():
    """Run the daily pipeline task (synchronous wrapper for APScheduler)."""
    import asyncio
    # Find the task config to get args
    task_config = next((t for t in SCHEDULED_TASKS if t["id"] == "daily_pipeline"), {})
    asyncio.run(_execute_scheduled_task(
        "daily_pipeline",
        args=task_config.get("args"),
    ))


def run_weekly_backup():
    """Run the weekly backup task (synchronous wrapper for APScheduler)."""
    import asyncio
    asyncio.run(_execute_scheduled_task("backup_data"))


def run_daily_db_backup():
    """Phase 2.5.6 — pg_dump-equivalent of the Railway Postgres into
    /data/db_backups/. Sync wrapper for APScheduler."""
    import asyncio
    asyncio.run(_execute_scheduled_task("db_backup"))


def run_daily_cloud_upload():
    """Phase 2.5.6 — upload /data backups + price-dir snapshots to
    Google Drive. Runs 30 minutes after the DB backup so the new
    tarball is in /data/db_backups/ before mirror-mode looks for it.
    Sync wrapper for APScheduler."""
    import asyncio
    asyncio.run(_execute_scheduled_task("cloud_upload"))


async def _execute_scheduled_task(command: str, universe: str = None, args: dict = None):
    """
    Execute a scheduled task by creating and running a job.

    Args:
        command: Command name from COMMANDS
        universe: Target universe (optional)
        args: Additional command arguments (optional)
    """
    from app.services.job_service import JobService

    logger.info(f"Executing scheduled task: {command}")

    try:
        # Create job
        job = await JobService.create_job(
            command=command,
            universe=universe,
            args=args,
            label=f"Scheduled: {command}"
        )

        # Run job
        await JobService.run_job(job.id)

        logger.info(f"Scheduled task completed: {command} (job_id={job.id})")

    except Exception as e:
        logger.error(f"Scheduled task failed: {command} - {str(e)}")


def create_task_wrapper(command: str, universe: str = None):
    """
    Create a synchronous wrapper function for a scheduled task.

    APScheduler calls this function on schedule.
    Since we're using MemoryJobStore, we don't need serialization.
    """
    def wrapper():
        import asyncio
        asyncio.run(_execute_scheduled_task(command, universe))
    return wrapper


def register_default_tasks(sched):
    """
    Register predefined scheduled tasks with the scheduler.

    Called during startup to set up default schedules.
    Uses string references for serialization compatibility.
    """
    from apscheduler.triggers.cron import CronTrigger

    for task in SCHEDULED_TASKS:
        job_id = task["id"]

        # Check if job already exists
        existing_job = sched.get_job(job_id)
        if existing_job:
            logger.info(f"Task already registered: {job_id}")
            continue

        # Create cron trigger.
        #
        # IMPORTANT: pin the trigger to the scheduler's timezone (IST). A
        # CronTrigger built without an explicit `timezone` falls back to the
        # *container-local* zone (UTC on Railway, where no TZ is set), NOT the
        # BackgroundScheduler's configured timezone. That silently shifted every
        # job by 5h30m — daily_pipeline fired at 07:00 UTC (12:30 IST) instead
        # of 07:00 IST. Passing sched.timezone makes the schedule env-independent.
        trigger = CronTrigger(timezone=sched.timezone, **task["trigger_args"])

        # Add job using string reference for serialization
        sched.add_job(
            func=task["func_ref"],
            trigger=trigger,
            id=job_id,
            name=task["name"],
            replace_existing=True,
        )

        logger.info(f"Registered task: {job_id}")

    logger.info(f"Registered {len(SCHEDULED_TASKS)} default tasks")
