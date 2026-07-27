"""Admin options-worker status API — reads the worker's Postgres heartbeat.

The options data worker (separate Railway service, branch options_data_v1)
upserts a single options_worker_health row every ~30s. This endpoint is the
/admin panel's source for "is the capture alive". Operational intelligence
only — admin-gated like /api/freshness.

Mounted at `/api/options/worker-status` from main.py.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Response

from app.auth import require_admin
from app.services.worker_health_store import read_heartbeat

router = APIRouter(prefix="/api/options", tags=["options"])

# The worker heartbeats every ~30s; during market hours anything older than
# this is a problem worth flagging loudly on the panel.
STALE_AFTER_SECONDS = 120


@router.get("/worker-status")
async def worker_status_endpoint(
    response: Response,
    user: dict = Depends(require_admin),
) -> dict:
    """Latest worker heartbeat + a derived staleness verdict.

    `found=False` means the worker has never heartbeat (table absent or
    empty) — expected until its first deploy, alarming afterwards.
    """
    response.headers["Cache-Control"] = "no-store"  # live ops view — never cache
    row = read_heartbeat()
    if row is None:
        return {"found": False}
    age = (datetime.now(timezone.utc) - row["updated_at"]).total_seconds()
    return {
        "found": True,
        "phase": row["phase"],
        "updated_at": row["updated_at"].isoformat(),
        "age_seconds": round(age, 1),
        "heartbeat_stale": age > STALE_AFTER_SECONDS,
        "snapshot": row["payload"],
    }
