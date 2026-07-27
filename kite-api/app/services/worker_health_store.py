"""Options-worker heartbeat in Postgres — the /admin monitoring source.

Same pattern (and rationale) as token_store: the worker and the web API
run as separate Railway services whose only shared surface is Postgres.
The worker upserts one row every ~30s; the admin endpoint reads it. The
payload is an opaque JSON snapshot so the worker can evolve its health
fields without schema churn. Core + create_all(checkfirst) for the same
cross-branch reason as kite_session (fold into Alembic at convergence).
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column, DateTime, Integer, MetaData, String, Table, Text, create_engine, select

log = logging.getLogger(__name__)

_metadata = MetaData()

options_worker_health = Table(
    "options_worker_health",
    _metadata,
    Column("id", Integer, primary_key=True),
    Column("phase", String(20), nullable=False),
    Column("payload", Text, nullable=False),  # JSON health snapshot
    Column("updated_at", DateTime(timezone=True), nullable=False),
)

_ROW_ID = 1


def _resolve_url(database_url: Optional[str]) -> str:
    if database_url:
        return database_url
    from app.config import get_settings

    return get_settings().database_url


def write_heartbeat(phase: str, snapshot: dict, database_url: Optional[str] = None) -> None:
    engine = None
    try:
        engine = create_engine(_resolve_url(database_url))
        _metadata.create_all(engine, checkfirst=True)
        now = datetime.now(timezone.utc)
        payload = json.dumps(snapshot, default=str)
        with engine.begin() as conn:
            updated = conn.execute(
                options_worker_health.update()
                .where(options_worker_health.c.id == _ROW_ID)
                .values(phase=phase, payload=payload, updated_at=now)
            )
            if updated.rowcount == 0:
                conn.execute(
                    options_worker_health.insert().values(id=_ROW_ID, phase=phase, payload=payload, updated_at=now)
                )
    except Exception as exc:
        # Monitoring must never take the capture path down.
        log.warning("heartbeat write failed: %s", exc)
    finally:
        if engine is not None:
            engine.dispose()


def read_heartbeat(database_url: Optional[str] = None) -> Optional[dict]:
    engine = None
    try:
        engine = create_engine(_resolve_url(database_url))
        with engine.connect() as conn:
            row = (
                conn.execute(select(options_worker_health).where(options_worker_health.c.id == _ROW_ID))
                .mappings()
                .first()
            )
        if row is None:
            return None
        out = dict(row)
        out["payload"] = json.loads(out["payload"])
        return out
    except Exception as exc:
        log.warning("heartbeat read failed: %s", exc)
        return None
    finally:
        if engine is not None:
            engine.dispose()
