"""Postgres persistence for the options engine (handover §13-§14).

Three tables, written by the worker, read (later) by the web API:
- option_minute_bars — the primary permanent dataset. One bulk insert per
  minute; PK (contract_id, minute) + ON CONFLICT DO NOTHING makes retries
  and replays idempotent (performance goal: no duplicate rows).
- option_chain_snapshots — single JSON row holding the latest chain,
  upserted every few seconds. Fast lookup, only-latest-version by design.
- daily_sessions — one row per trading day with quality stats.

Same self-contained Core + create_all(checkfirst) pattern as kite_session
(R-025 rationale); fold into Alembic at branch convergence. ``source``
distinguishes live-captured bars from historical-API backfill, whose
depth-derived columns are NULL.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import (
    BigInteger,
    Column,
    Date,
    DateTime,
    Float,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    create_engine,
    select,
)
from sqlalchemy.dialects.postgresql import insert as pg_insert

log = logging.getLogger(__name__)

_metadata = MetaData()

option_minute_bars = Table(
    "option_minute_bars",
    _metadata,
    Column("contract_id", String(40), primary_key=True),
    Column("minute", DateTime(timezone=True), primary_key=True),
    Column("kind", String(4), nullable=False),
    Column("expiry", Date, nullable=True),
    Column("strike", Float, nullable=True),
    Column("open", Float), Column("high", Float), Column("low", Float), Column("close", Float),
    Column("volume", BigInteger),
    Column("oi_open", BigInteger), Column("oi_high", BigInteger),
    Column("oi_low", BigInteger), Column("oi_close", BigInteger),
    Column("bid_close", Float), Column("ask_close", Float),
    Column("bid_qty_close", BigInteger), Column("ask_qty_close", BigInteger),
    Column("avg_spread", Float), Column("avg_depth_imbalance", Float),
    Column("tick_count", Integer),
    Column("source", String(8), nullable=False, default="live"),
)

option_chain_snapshots = Table(
    "option_chain_snapshots",
    _metadata,
    Column("id", Integer, primary_key=True),
    Column("payload", Text, nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)

daily_sessions = Table(
    "daily_sessions",
    _metadata,
    Column("session_date", Date, primary_key=True),
    Column("stats", Text, nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)

_SNAPSHOT_ROW_ID = 1


def _resolve_url(database_url: Optional[str]) -> str:
    if database_url:
        return database_url
    from app.config import get_settings

    return get_settings().database_url


class BarStore:
    """One engine held for the session — the worker writes every minute,
    unlike the once-a-day token path, so per-call engines would churn."""

    def __init__(self, database_url: Optional[str] = None):
        self.engine = create_engine(_resolve_url(database_url), pool_pre_ping=True)
        _metadata.create_all(self.engine, checkfirst=True)

    def insert_bars(self, rows: List[dict], source: str = "live") -> int:
        if not rows:
            return 0
        for r in rows:
            r.setdefault("source", source)
        with self.engine.begin() as conn:
            if conn.dialect.name == "postgresql":
                stmt = pg_insert(option_minute_bars).on_conflict_do_nothing(
                    index_elements=["contract_id", "minute"]
                )
                conn.execute(stmt, rows)
            else:  # tests on sqlite
                from sqlalchemy.dialects.sqlite import insert as lite_insert

                stmt = lite_insert(option_minute_bars).on_conflict_do_nothing(
                    index_elements=["contract_id", "minute"]
                )
                conn.execute(stmt, rows)
        return len(rows)

    def upsert_chain_snapshot(self, chain: dict) -> None:
        now = datetime.now(timezone.utc)
        payload = json.dumps(chain, default=str)
        with self.engine.begin() as conn:
            updated = conn.execute(
                option_chain_snapshots.update()
                .where(option_chain_snapshots.c.id == _SNAPSHOT_ROW_ID)
                .values(payload=payload, updated_at=now)
            )
            if updated.rowcount == 0:
                conn.execute(
                    option_chain_snapshots.insert().values(id=_SNAPSHOT_ROW_ID, payload=payload, updated_at=now)
                )

    def read_chain_snapshot(self) -> Optional[dict]:
        with self.engine.connect() as conn:
            row = (
                conn.execute(select(option_chain_snapshots).where(option_chain_snapshots.c.id == _SNAPSHOT_ROW_ID))
                .mappings()
                .first()
            )
        if row is None:
            return None
        return {"updated_at": row["updated_at"], "chain": json.loads(row["payload"])}

    def upsert_daily_session(self, session_date, stats: dict) -> None:
        now = datetime.now(timezone.utc)
        payload = json.dumps(stats, default=str)
        with self.engine.begin() as conn:
            updated = conn.execute(
                daily_sessions.update()
                .where(daily_sessions.c.session_date == session_date)
                .values(stats=payload, updated_at=now)
            )
            if updated.rowcount == 0:
                conn.execute(
                    daily_sessions.insert().values(session_date=session_date, stats=payload, updated_at=now)
                )

    def bar_count(self, session_date=None) -> int:
        from sqlalchemy import func

        q = select(func.count()).select_from(option_minute_bars)
        if session_date is not None:
            from sqlalchemy import cast

            q = q.where(cast(option_minute_bars.c.minute, Date) == session_date)
        with self.engine.connect() as conn:
            return conn.execute(q).scalar() or 0

    def dispose(self) -> None:
        self.engine.dispose()
