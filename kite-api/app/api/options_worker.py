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


@router.get("/live-analytics")
async def live_analytics_endpoint(
    response: Response,
    user: dict = Depends(require_admin),
) -> dict:
    """Live options analytics for /admin — computed on demand from the
    worker's 10-second chain snapshot (option_chain_snapshots) plus
    today's minute bars. Measured quantities only (Stage 2); regime
    labels are heuristic and marked as such. Snapshot age is returned so
    the panel can show 'as of'."""
    import json as _json
    from datetime import datetime as _dt, timezone as _tz, timedelta as _td

    from sqlalchemy import create_engine, text as _text

    from app.config import get_settings
    from app.microstructure.gamma_profile import compute_from_snapshot
    from app.microstructure.paper_straddle import compute_day

    response.headers["Cache-Control"] = "no-store"
    engine = create_engine(get_settings().database_url)
    try:
        with engine.connect() as conn:
            snap = conn.execute(
                _text("select payload, updated_at from option_chain_snapshots where id=1")
            ).first()
            if snap is None:
                return {"found": False}
            payload = _json.loads(snap[0])
            ist = _tz(_td(hours=5, minutes=30))
            now_ist = _dt.now(ist)
            analytics = compute_from_snapshot(payload, now_ist)
            straddle = None
            try:
                straddle = compute_day(conn, now_ist.date().isoformat())
                if straddle is not None:
                    straddle.pop("detail", None)
                    straddle["session_date"] = str(straddle["session_date"])
                    # live mark from the snapshot at the ledger strike
                    k = straddle["strike"]
                    legs = [
                        c.get("ltp")
                        for c in payload.get("contracts", {}).values()
                        if c.get("strike") == k and c.get("kind") in ("CE", "PE")
                        and c.get("expiry") == (analytics or {}).get("expiry")
                    ]
                    if len(legs) == 2 and all(legs):
                        straddle["live_pnl"] = round(straddle["entry_credit"] - sum(legs), 2)
            except Exception:
                pass  # straddle section is best-effort; analytics still serve
            age = (_dt.now(_tz.utc) - snap[1]).total_seconds()
            return {
                "found": True,
                "snapshot_at": snap[1].isoformat(),
                "snapshot_age_seconds": round(age, 1),
                "analytics": analytics,
                "paper_straddle": straddle,
            }
    finally:
        engine.dispose()
