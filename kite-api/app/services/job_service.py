"""
Job Service - Execute and manage background jobs via subprocess.
"""
import asyncio
import uuid
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from app.models.database import get_session_local
from app.models.models import Job
from app.config import settings

# Log directory for job outputs
LOGS_DIR = settings.data_dir / "logs" / "jobs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

# Job timeout (30 minutes default)
DEFAULT_TIMEOUT = 1800

# Available commands with their script paths (relative to data_dir)
COMMANDS = {
    "daily_pipeline": "scripts/run_daily_pipeline.py",
    "generate_portfolio": "scripts/run_final_momentum_portfolio.py",
    "update_portfolios": "scripts/update_all_portfolios.py",
    "backup_data": "scripts/sync_data_backup.py",
    "fetch_prices": "scripts/fetch_nse500_history.py",
    "build_signals": "scripts/build_momentum_signals_flexible.py",
}


def resolve_script_path(command: str) -> Path:
    """Resolve the full path to a script, handling Docker vs local environments."""
    relative_path = COMMANDS.get(command)
    if not relative_path:
        raise ValueError(f"Unknown command: {command}")

    # Try data_dir first (works in Docker)
    script_path = settings.data_dir / relative_path
    if script_path.exists():
        return script_path

    # For local dev, some scripts are in kite-api/scripts/
    kite_api_path = settings.data_dir / "kite-api" / relative_path
    if kite_api_path.exists():
        return kite_api_path

    # Fall back to original path
    return script_path


class JobService:
    """Service for managing background job execution."""

    @staticmethod
    def generate_job_id() -> str:
        """Generate a unique job ID."""
        return uuid.uuid4().hex[:16]

    @staticmethod
    def get_log_path(job_id: str) -> Path:
        """Get the log file path for a job."""
        return LOGS_DIR / f"{job_id}.log"

    @staticmethod
    async def create_job(
        command: str,
        universe: Optional[str] = None,
        args: Optional[Dict[str, Any]] = None,
        label: Optional[str] = None
    ) -> Job:
        """
        Create a new job and save to database.

        Args:
            command: Command name (key from COMMANDS dict)
            universe: Target universe (nse500, nifty100, nifty250)
            args: Additional command arguments
            label: Human-readable description

        Returns:
            Created Job instance
        """
        SessionLocal = get_session_local()
        db = SessionLocal()

        try:
            job_id = JobService.generate_job_id()

            job = Job(
                id=job_id,
                command=command,
                label=label or f"Run {command}",
                universe=universe,
                args=args or {},
                status="queued",
                log_path=str(JobService.get_log_path(job_id)),
            )

            db.add(job)
            db.commit()
            db.refresh(job)

            return job
        finally:
            db.close()

    @staticmethod
    async def run_job(job_id: str, timeout: int = DEFAULT_TIMEOUT) -> None:
        """
        Execute a job in the background.

        Updates job status and captures output to log file.
        """
        SessionLocal = get_session_local()
        db = SessionLocal()

        try:
            job = db.query(Job).filter(Job.id == job_id).first()
            if not job:
                return

            # Validate command
            if job.command not in COMMANDS:
                job.status = "failed"
                job.error_message = f"Unknown command: {job.command}"
                job.ended_at = datetime.utcnow()
                db.commit()
                return

            # Update status to running
            job.status = "running"
            job.started_at = datetime.utcnow()
            db.commit()

            # Build command
            script_path = resolve_script_path(job.command)
            cmd_args = [sys.executable, str(script_path)]

            # Add universe argument if provided
            if job.universe:
                cmd_args.extend(["--universe", job.universe])

            # Add additional arguments
            if job.args:
                for key, value in job.args.items():
                    if value is None:
                        continue
                    flag = f"--{key.replace('_', '-')}"
                    # Boolean flags: pass flag only (no value) when True
                    if isinstance(value, bool):
                        if value:
                            cmd_args.append(flag)
                    else:
                        cmd_args.extend([flag, str(value)])

            # Open log file
            log_path = JobService.get_log_path(job_id)

            with open(log_path, "w") as log_file:
                log_file.write(f"[{datetime.now().isoformat()}] Starting job: {job.command}\n")
                log_file.write(f"[{datetime.now().isoformat()}] Command: {' '.join(cmd_args)}\n")
                log_file.write("-" * 60 + "\n")
                log_file.flush()

                try:
                    # Run subprocess
                    process = await asyncio.create_subprocess_exec(
                        *cmd_args,
                        stdout=log_file,
                        stderr=asyncio.subprocess.STDOUT,
                        cwd=str(settings.data_dir),
                    )

                    # Wait with timeout
                    try:
                        await asyncio.wait_for(process.wait(), timeout=timeout)

                        if process.returncode == 0:
                            job.status = "completed"
                        else:
                            job.status = "failed"
                            job.error_message = f"Process exited with code {process.returncode}"

                    except asyncio.TimeoutError:
                        process.kill()
                        await process.wait()
                        job.status = "failed"
                        job.error_message = f"Job timed out after {timeout} seconds"

                except Exception as e:
                    job.status = "failed"
                    job.error_message = str(e)
                    log_file.write(f"\n[ERROR] {str(e)}\n")

                log_file.write("-" * 60 + "\n")
                log_file.write(f"[{datetime.now().isoformat()}] Job {job.status}\n")

            # Update job completion
            job.ended_at = datetime.utcnow()
            if job.started_at:
                job.duration_seconds = int((job.ended_at - job.started_at).total_seconds())
            db.commit()

        finally:
            db.close()

    @staticmethod
    def get_job(job_id: str) -> Optional[Job]:
        """Get a job by ID."""
        SessionLocal = get_session_local()
        db = SessionLocal()

        try:
            return db.query(Job).filter(Job.id == job_id).first()
        finally:
            db.close()

    @staticmethod
    def list_jobs(
        limit: int = 20,
        universe: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[Job]:
        """
        List recent jobs with optional filters.

        Args:
            limit: Maximum number of jobs to return
            universe: Filter by universe
            status: Filter by status

        Returns:
            List of Job instances
        """
        SessionLocal = get_session_local()
        db = SessionLocal()

        try:
            query = db.query(Job)

            if universe:
                query = query.filter(Job.universe == universe)
            if status:
                query = query.filter(Job.status == status)

            return query.order_by(Job.created_at.desc()).limit(limit).all()
        finally:
            db.close()

    @staticmethod
    async def cancel_job(job_id: str) -> bool:
        """
        Cancel a running job.

        Note: This marks the job as cancelled but doesn't kill the process.
        For true cancellation, we'd need to track PIDs.
        """
        SessionLocal = get_session_local()
        db = SessionLocal()

        try:
            job = db.query(Job).filter(Job.id == job_id).first()
            if not job:
                return False

            if job.status not in ("queued", "running"):
                return False

            job.status = "cancelled"
            job.ended_at = datetime.utcnow()
            if job.started_at:
                job.duration_seconds = int((job.ended_at - job.started_at).total_seconds())

            db.commit()
            return True
        finally:
            db.close()

    @staticmethod
    def read_logs(job_id: str, tail: int = 0) -> str:
        """
        Read job logs from file.

        Args:
            job_id: Job ID
            tail: If > 0, return only last N lines

        Returns:
            Log content as string
        """
        log_path = JobService.get_log_path(job_id)

        if not log_path.exists():
            return ""

        with open(log_path, "r") as f:
            if tail > 0:
                lines = f.readlines()
                return "".join(lines[-tail:])
            return f.read()
