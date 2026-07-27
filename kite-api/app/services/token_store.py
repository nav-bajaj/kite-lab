"""Kite access token in Postgres — cross-service handoff.

Railway volumes attach to exactly one service, so the options worker
cannot read the web service's access_token.txt. The daily login (08:30
IST scheduler job on the web service, or a manual login) upserts the
token here; the worker reads it. Single row, overwritten daily — the
token itself expires every morning ~7:30 IST regardless.

Deliberately self-contained SQLAlchemy Core (no ORM registry, no Alembic
migration yet): the web service deploys from the prod branch and the
worker from the options branch, whose Alembic heads differ — a shared new
revision would conflict at merge. ``ensure_table`` is idempotent from
either service; fold into a proper migration when the branches converge.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Column, DateTime, Integer, MetaData, String, Table, Text, create_engine, select

log = logging.getLogger(__name__)

_metadata = MetaData()

kite_session = Table(
    "kite_session",
    _metadata,
    Column("id", Integer, primary_key=True),
    Column("access_token", Text, nullable=False),
    Column("user_name", String(120), nullable=True),
    Column("login_source", String(40), nullable=True),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)

_ROW_ID = 1


def _resolve_url(database_url: Optional[str]) -> str:
    if database_url:
        return database_url
    from app.config import get_settings

    return get_settings().database_url


def upsert_token(
    access_token: str,
    user_name: str = "",
    login_source: str = "",
    database_url: Optional[str] = None,
) -> None:
    engine = create_engine(_resolve_url(database_url))
    try:
        _metadata.create_all(engine, checkfirst=True)
        now = datetime.now(timezone.utc)
        with engine.begin() as conn:
            updated = conn.execute(
                kite_session.update()
                .where(kite_session.c.id == _ROW_ID)
                .values(access_token=access_token, user_name=user_name, login_source=login_source, updated_at=now)
            )
            if updated.rowcount == 0:
                conn.execute(
                    kite_session.insert().values(
                        id=_ROW_ID,
                        access_token=access_token,
                        user_name=user_name,
                        login_source=login_source,
                        updated_at=now,
                    )
                )
        log.info("kite_session upserted (source=%s)", login_source)
    finally:
        engine.dispose()


def read_token(database_url: Optional[str] = None) -> Optional[dict]:
    """Latest stored token, or None on any failure — reads are non-fatal."""
    engine = None
    try:
        engine = create_engine(_resolve_url(database_url))
        with engine.connect() as conn:
            row = conn.execute(select(kite_session).where(kite_session.c.id == _ROW_ID)).mappings().first()
        if row is None:
            return None
        return dict(row)
    except Exception as exc:
        log.warning("kite_session read failed: %s", exc)
        return None
    finally:
        if engine is not None:
            engine.dispose()
