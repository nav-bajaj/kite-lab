"""
Predefined scheduled tasks for Kite-Lab.

These tasks run automatically based on their schedule.
Uses module-level functions for APScheduler serialization compatibility.
"""
import logging
from datetime import date

from app.config import EOD_STRATEGIES  # canonical list — see config.py

logger = logging.getLogger(__name__)


# Predefined scheduled tasks configuration
SCHEDULED_TASKS = [
    # Pre-market token refresh. Kite access tokens expire ~06:00 IST daily;
    # since daily_pipeline now runs post-close (16:30), the overnight token is
    # dead by morning. This login-only job at 08:30 IST (before the 09:15 open)
    # keeps the day's token valid for intraday positions, the live dashboard,
    # and the 16:00 EOD rebalance producer.
    {
        "id": "morning_login",
        "name": "Morning Login",
        "description": "Pre-market (08:30 IST) Kite login so the day's token is valid for intraday + the 16:00 EOD producer",
        "command": "login",
        "args": {"headless": True},
        "func_ref": "app.scheduler.tasks:run_morning_login",
        "trigger": "cron",
        "trigger_args": {
            "hour": 8,
            "minute": 30,
            "day_of_week": "mon-fri"
        },
    },
    # Post-close data + insights refresh. Moved from 07:00 (pre-market, which
    # only ever had prior-day closes) to 16:30 IST — after the 15:30 NSE close
    # plus Zerodha's adjusted-close publish delay — so the insight dashboard
    # and portfolios reflect the SAME day's close for evening viewers. Re-logins
    # as a self-contained fallback if the morning login failed.
    {
        "id": "daily_pipeline",
        "name": "Daily Pipeline",
        "description": "Post-close (16:30 IST): auto-login + fetch same-day data, build portfolios, sync insights, backup",
        "command": "daily_pipeline",
        "args": {"with-login": True, "headless": True},
        "func_ref": "app.scheduler.tasks:run_daily_pipeline",
        "trigger": "cron",
        "trigger_args": {
            "hour": 16,
            "minute": 30,
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


def run_morning_login():
    """Pre-market Kite login (token-only). Refreshes the daily access token
    before the 09:15 open so intraday positions, the live dashboard, and the
    16:00 EOD producer all have a valid token. Synchronous wrapper for
    APScheduler."""
    import asyncio
    task_config = next((t for t in SCHEDULED_TASKS if t["id"] == "morning_login"), {})
    asyncio.run(_execute_scheduled_task("login", args=task_config.get("args")))


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


def _is_eod_weekly_exit_day(strategy: str, today: date) -> bool:
    """True if ``today`` is a weekly exit-check Friday for a biweekly
    strategy — i.e. the off-week Friday where the engine's DD-stop / rank /
    regime block fires but no new entries do.

    Weekly strategies (``weekly_thu_fri`` — l6_v2) have no separate weekly
    exit day; their entry cadence *is* their weekly cadence, so this always
    returns False for them.
    """
    from datetime import timedelta

    from app.config import UNIVERSES
    from app.services.market_service import is_trading_day
    from app.services.rebalance_service import (
        CADENCE_META, DEFAULT_CADENCE,
    )

    if not is_trading_day(today):
        return False

    cadence_key = (UNIVERSES.get(strategy, {})
                   .get("rebalance_cadence", DEFAULT_CADENCE))
    _, _, signal_wd, has_weekly_exit = CADENCE_META.get(
        cadence_key, CADENCE_META[DEFAULT_CADENCE]
    )
    if not has_weekly_exit:
        return False

    # For biweekly-Friday strategies, weekly exit checks fire on Fridays.
    # Snap-back so a holiday-shifted Fri (e.g. Muharram) counts as the
    # week's signal too — matches the engine's ``fridays(calendar)``
    # (resample W-FRI, take last trading day of each week).
    from app.services.market_service import snap_back_to_trading_day
    days_to_wd = today.weekday() - signal_wd
    if days_to_wd < 0:
        return False  # too early in the week
    nominal = today - timedelta(days=days_to_wd)
    weekly_signal = snap_back_to_trading_day(nominal)
    if weekly_signal != today:
        return False

    # Ensure today isn't ALREADY an entry cadence day — that's covered by
    # ``_is_eod_signal_day``; the exit-only path is only for off-weeks.
    return not _is_eod_signal_day(strategy, today)


def run_eod_proposed_orders():
    """Fire one EOD proposed-orders job per signal-day strategy.

    Cron triggers this every weekday at 16:00 IST; the admin's "Run now"
    button on this scheduled task hits the same entry. Sequence:

    1. **Always** create a wrapper Job row up-front. Without this, days
       where no strategy is on cadence looked broken from the admin UI —
       the trigger succeeded but no visible Job appeared. Now the row is
       there with a log entry describing exactly why nothing dispatched.
    2. Compute eligible strategies via ``_is_eod_signal_day``.
    3. If any are eligible, dispatch a **fetch-only** ``daily_pipeline`` job
       first (refreshes today's close — the 07:00 IST daily_pipeline is
       pre-market so its data doesn't include today). Fetch-only skips the
       all-7-portfolio build + backup, which the producers don't need
       (they re-run each strategy themselves) — audit O1.
    4. Dispatch a per-strategy ``eod_proposed_orders`` job for each
       eligible strategy so per-strategy failures stay isolated.
    5. Verify each eligible strategy recorded a today-dated proposal;
       fail the wrapper Job if any is missing (dead-man's-switch, O4).

    ``_execute_scheduled_task`` awaits each dispatched Job to completion.
    """
    import asyncio
    from datetime import datetime

    asyncio.run(_run_eod_orchestrator())


async def _run_eod_orchestrator():
    """Async body of ``run_eod_proposed_orders`` — split out for testability
    + to keep the wrapper Job's lifecycle explicit."""
    from datetime import datetime

    from app.models.database import get_session_local
    from app.models.models import Job
    from app.services.job_service import JobService

    # Create the wrapper Job so the admin UI has a first-class row + log
    # for this orchestrator run. Downstream _execute_scheduled_task calls
    # will each create their own Jobs; those remain visible too.
    wrap = await JobService.create_job(
        command="eod_proposed_orders",
        label="EOD proposed orders (orchestrator)",
    )
    log_path = JobService.get_log_path(wrap.id)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log = open(log_path, "w")

    def w(msg):
        log.write(f"[{datetime.utcnow().isoformat()}] {msg}\n")
        log.flush()

    _set_job_status(wrap.id, status="running", started_at=datetime.utcnow())

    try:
        today = date.today()
        w(f"Today = {today}. Checking eligibility for {EOD_STRATEGIES!r}...")
        entry_eligible = []
        exit_eligible = []
        for s in EOD_STRATEGIES:
            entry_on = _is_eod_signal_day(s, today)
            exit_on = (not entry_on) and _is_eod_weekly_exit_day(s, today)
            label = ("ENTRY" if entry_on
                     else "EXIT-ONLY" if exit_on
                     else "not on signal-day")
            w(f"  {s}: {label}")
            if entry_on:
                entry_eligible.append(s)
            elif exit_on:
                exit_eligible.append(s)

        if not entry_eligible and not exit_eligible:
            w("")
            w("No strategies on cadence today — skipping data refresh + "
              "producer dispatch. Expected on non-signal weekdays.")
            _set_job_status(wrap.id, status="completed",
                             ended_at=datetime.utcnow())
            return

        w("")
        summary = []
        if entry_eligible:
            summary.append(f"entry={entry_eligible}")
        if exit_eligible:
            summary.append(f"exit_only={exit_eligible}")
        w(f"Eligible: {', '.join(summary)}. Running a fetch-only daily_pipeline "
          f"first to refresh today's adjusted closes before each producer...")
        daily_cfg = next((t for t in SCHEDULED_TASKS
                           if t["id"] == "daily_pipeline"), {})
        # Only refresh the data the producers read (NSE500 + indices + benchmark,
        # corporate-actions-adjusted); the producers re-run each strategy
        # themselves, so the full all-7-portfolio build + backup here is pure
        # duplicate compute (audit O1). The 07:00 run stays full.
        daily_args = dict(daily_cfg.get("args") or {})
        daily_args["fetch-only"] = True
        refresh_status = await _execute_scheduled_task(
            "daily_pipeline", args=daily_args,
        )
        if refresh_status != "completed":
            raise RuntimeError(
                f"daily_pipeline did not complete (status={refresh_status}); "
                f"refusing to run producers on possibly-stale data. Today's "
                f"proposals will be missing until the next successful run."
            )
        w("daily_pipeline complete.")

        w("")
        for strategy in entry_eligible:
            w(f"Dispatching entry producer for {strategy}...")
            await _execute_scheduled_task(
                "eod_proposed_orders", universe=strategy,
            )
            w(f"  {strategy} entry producer done.")
        for strategy in exit_eligible:
            w(f"Dispatching exit-only producer for {strategy}...")
            await _execute_scheduled_task(
                "eod_proposed_orders", universe=strategy,
                args={"mode": "exit_only"},
            )
            w(f"  {strategy} exit-only producer done.")

        w("")
        fired = entry_eligible + [f"{s} (exit-only)" for s in exit_eligible]
        w(f"Dispatched producers for: {', '.join(fired)}")

        # Dead-man's-switch (audit O4): confirm every eligible strategy actually
        # recorded a today-dated proposal. A producer that silently no-ops (the
        # l6_v2 miss that went unnoticed for days) otherwise leaves no signal.
        # Any gap fails the wrapper Job so it shows red in the admin Jobs UI —
        # the owner's existing visibility surface, no new endpoint needed.
        eligible = entry_eligible + exit_eligible
        missing = _strategies_missing_todays_proposal(eligible, today)
        if missing:
            msg = (f"EOD producers did not record today's proposal for: "
                   f"{', '.join(missing)} (eligible={eligible}). "
                   f"Investigate before clients rely on a stale rebalance.")
            w(msg)
            logger.error(msg)
            _set_job_status(wrap.id, status="failed",
                             ended_at=datetime.utcnow(), error_message=msg)
            return
        w(f"Verified today's proposal rows for all eligible: {eligible}")
        _set_job_status(wrap.id, status="completed",
                         ended_at=datetime.utcnow())
    except Exception as e:
        w(f"Orchestrator error: {e!r}")
        _set_job_status(wrap.id, status="failed",
                         ended_at=datetime.utcnow(),
                         error_message=str(e))
        raise
    finally:
        log.close()


def _strategies_missing_todays_proposal(strategies, today) -> list:
    """Return the strategies with no ProposedRebalance row dated ``today``.

    ``data_as_of`` is the producer's signal date, which on a signal day is
    today, so a today-dated row per eligible strategy confirms its producer
    ran and synced. Used as the EOD orchestrator's completion check (O4).
    """
    from app.models.database import get_session_local
    from app.models.models import ProposedRebalance

    SessionLocal = get_session_local()
    db = SessionLocal()
    try:
        missing = []
        for s in strategies:
            row = db.query(ProposedRebalance).filter(
                ProposedRebalance.universe == s,
                ProposedRebalance.data_as_of == today,
            ).first()
            if row is None:
                missing.append(s)
        return missing
    finally:
        db.close()


def _set_job_status(job_id: str, **fields):
    """Update fields on a Job row + auto-compute duration_seconds if we're
    completing/failing."""
    from datetime import datetime

    from app.models.database import get_session_local
    from app.models.models import Job

    SessionLocal = get_session_local()
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if job is None:
            return
        for k, v in fields.items():
            setattr(job, k, v)
        if (fields.get("status") in ("completed", "failed")
                and job.started_at and job.ended_at):
            job.duration_seconds = int(
                (job.ended_at - job.started_at).total_seconds()
            )
        db.commit()
    finally:
        db.close()


async def _execute_scheduled_task(command: str, universe: str = None, args: dict = None):
    """
    Execute a scheduled task by creating and running a job.

    Args:
        command: Command name from COMMANDS
        universe: Target universe (optional)
        args: Additional command arguments (optional)

    Returns:
        The job's final status string ("completed"/"failed"/...), or None if the
        job could not be created. ``run_job`` records subprocess failure on the
        Job row rather than raising, so callers that must gate on success (e.g.
        the EOD orchestrator refusing to run producers on a failed data refresh)
        check this return value.
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

        final = JobService.get_job(job.id)
        status = final.status if final else None
        logger.info(f"Scheduled task finished: {command} (job_id={job.id}, "
                    f"status={status})")
        return status

    except Exception as e:
        logger.error(f"Scheduled task failed: {command} - {str(e)}")
        return None


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
