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
    # The Kite app key the token was generated under. A token only
    # validates with its own app's key, and logins can happen from
    # different environments (local .env vs Railway web service) holding
    # DIFFERENT Kite apps — so the pair must travel together.
    Column("api_key", String(40), nullable=True),
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


def _ensure_schema(engine) -> None:
    _metadata.create_all(engine, checkfirst=True)
    # api_key was added after the table first shipped; create_all won't
    # add columns to an existing table, so patch it in idempotently.
    from sqlalchemy import text

    try:
        with engine.begin() as conn:
            if engine.dialect.name == "postgresql":
                conn.execute(text("ALTER TABLE kite_session ADD COLUMN IF NOT EXISTS api_key VARCHAR(40)"))
            else:
                conn.execute(text("ALTER TABLE kite_session ADD COLUMN api_key VARCHAR(40)"))
    except Exception:
        pass  # column already exists (non-postgres path)


def upsert_token(
    access_token: str,
    api_key: str = "",
    user_name: str = "",
    login_source: str = "",
    database_url: Optional[str] = None,
) -> None:
    engine = create_engine(_resolve_url(database_url))
    try:
        _ensure_schema(engine)
        now = datetime.now(timezone.utc)
        with engine.begin() as conn:
            updated = conn.execute(
                kite_session.update()
                .where(kite_session.c.id == _ROW_ID)
                .values(
                    access_token=access_token,
                    api_key=api_key,
                    user_name=user_name,
                    login_source=login_source,
                    updated_at=now,
                )
            )
            if updated.rowcount == 0:
                conn.execute(
                    kite_session.insert().values(
                        id=_ROW_ID,
                        access_token=access_token,
                        api_key=api_key,
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
        _ensure_schema(engine)
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
