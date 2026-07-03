"""
Predefined scheduled tasks for Kite-Lab.

These tasks run automatically based on their schedule.
Uses module-level functions for APScheduler serialization compatibility.
"""
import logging
from datetime import date

logger = logging.getLogger(__name__)


# Strategies that have an EOD proposed-orders producer wired up — see
# data_pipeline/eod_proposal.py and tasks/rebalance_page/PLAN.md Phase 2.
# combo_defensive still needs a score adapter (uses regime + composite score).
EOD_STRATEGIES = ("om25_v3", "tl25_v3", "l6_v2")


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
    # rebalance_page Phase 2 §5 — EOD producer. 16:00 IST = NSE close 15:30
    # IST + 30min for Zerodha to publish the adjusted official closes the
    # engine needs. The 07:00 daily_pipeline run uses *prior-day* closes and
    # can't produce a today-signal-day proposal. Mon–Fri trigger; the task
    # function gates per-strategy on signal-day + NSE holiday.
    {
        "id": "eod_proposed_orders",
        "name": "EOD proposed orders",
        "description": (
            "After-close (16:00 IST) producer of the upcoming rebalance — "
            "writes proposed_orders_<exec>.csv + proposed_regime.json next "
            "to momentum_*.csv so the rebalance page picks it up."
        ),
        "command": "eod_proposed_orders",
        "func_ref": "app.scheduler.tasks:run_eod_proposed_orders",
        "trigger": "cron",
        "trigger_args": {
            "hour": 16,
            "minute": 0,
            "day_of_week": "mon-fri",
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


def _is_eod_signal_day(strategy: str, today: date) -> bool:
    """True if ``today`` is the next entry-cadence date for ``strategy``.

    Anchors on the most recent entry-bearing (BUY) trade in the DB and
    projects forward via ``rebalance_service.project_next_signal`` (uses
    the cadence in ``config.UNIVERSES["rebalance_cadence"]`` + the
    holiday-roll helpers, same as Phase 1's "Next rebalance" card). The
    Trade table is the single source of truth for every strategy, which
    replaces the per-strategy ``<prefix>_signals.csv`` lookup that used
    to gate the biweekly strategies (om25_v3, tl25_v3): weekly strategies
    like l6_v2 never emit a signals CSV so that path silently returned
    False and the cron never fired for Core Momentum.

    Returns False (with a log line) when we can't determine the anchor —
    no BUY trades on record for the strategy — or when today isn't a
    trading day. The scheduler treats that as "skip today" rather than
    risking a spurious run on a non-cadence day.
    """
    from datetime import timedelta

    from app.config import UNIVERSES
    from app.models.database import get_session_local
    from app.models.models import Trade
    from app.services.market_service import is_trading_day
    from app.services.rebalance_service import (
        DEFAULT_CADENCE, _exec_to_signal, project_next_signal,
    )
    from sqlalchemy import func

    if not is_trading_day(today):
        logger.info(f"[eod] {strategy}: skip — {today} is not an NSE trading day")
        return False

    cadence_key = (UNIVERSES.get(strategy, {})
                   .get("rebalance_cadence", DEFAULT_CADENCE))

    SessionLocal = get_session_local()
    db = SessionLocal()
    try:
        last_buy_exec = db.query(func.max(Trade.trade_date)).filter(
            Trade.universe == strategy,
            Trade.side == "BUY",
        ).scalar()
    finally:
        db.close()

    if last_buy_exec is None:
        logger.info(f"[eod] {strategy}: skip — no entry-bearing trades in DB")
        return False

    # exec_date → signal_date (the trading day strictly before exec_date).
    last_signal = _exec_to_signal(last_buy_exec)

    # project_next_signal returns the next entry date strictly AFTER `today`.
    # To ask "is today itself the next signal date?", probe with yesterday.
    projected = project_next_signal(last_signal, cadence_key,
                                     today - timedelta(days=1))
    return projected == today


def run_eod_proposed_orders():
    """Fire one EOD proposed-orders job per signal-day strategy.

    Cron triggers this every weekday at 16:00 IST. Sequence:

    1. Compute the eligible strategy set — those in ``EOD_STRATEGIES`` whose
       cadence lands today (holiday-rolled).
    2. If any are eligible, dispatch a full ``daily_pipeline`` job first.
       Without this, the panel on disk only has yesterday's close (the
       07:00 IST daily_pipeline fetches before market open), so the
       producer would pick last week's cadence date as its signal —
       silently emitting a stale proposal for a rebalance that already
       executed. The 16:00 IST timing was chosen so Zerodha's adjusted
       official closes (30 min after 15:30 IST close) are ready to
       fetch. Adds ~7 min to the cron but only fires on signal days.
    3. Dispatch a per-strategy ``eod_proposed_orders`` job for each
       eligible strategy so per-strategy failures stay isolated.

    ``_execute_scheduled_task`` awaits each job to completion, so this
    entire wrapper blocks until data + producers are done.
    """
    import asyncio

    today = date.today()
    eligible = [s for s in EOD_STRATEGIES if _is_eod_signal_day(s, today)]
    if not eligible:
        logger.info("[eod] no strategies on signal-day today — "
                    "skipping data refresh + producer")
        return

    logger.info(
        f"[eod] refreshing production data before producer for: "
        f"{', '.join(eligible)}"
    )
    daily_cfg = next((t for t in SCHEDULED_TASKS
                       if t["id"] == "daily_pipeline"), {})
    asyncio.run(_execute_scheduled_task(
        "daily_pipeline",
        args=daily_cfg.get("args"),
    ))

    fired = []
    for strategy in eligible:
        asyncio.run(_execute_scheduled_task(
            "eod_proposed_orders",
            universe=strategy,
        ))
        fired.append(strategy)
    if fired:
        logger.info(f"[eod] dispatched producers for: {', '.join(fired)}")
    else:
        logger.info("[eod] no strategies on signal-day today — nothing dispatched")


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
