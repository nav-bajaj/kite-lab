"""
Spec suite for lazy user provisioning (auth_stack_v2, B1.7 / SI-9).

Written before the implementation per the TDD policy. Pins:

  * First authenticated sighting of a ``sub`` creates exactly one
    ``users`` row (sub, email, provider, timestamps — minimal fields).
  * Repeat sightings update ``last_seen_at`` (and email on change) but
    NEVER create a second row — idempotent, keyed by sub.
  * A concurrent-insert race (IntegrityError) resolves to the existing
    row, not a crash.
  * Provisioning is FAIL-OPEN: a dead/unreachable DB must not break
    authentication — roles come from the verified token, and the users
    table only feeds the (future, fail-closed) entitlements layer.
  * The dev bypass provisions nothing.
"""

from __future__ import annotations

import os
import time

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("ALLOWED_ORIGINS", "http://localhost:3000")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("DEBUG", "false")
os.environ.setdefault("DISABLE_AUTH", "false")

from app.services import user_service  # noqa: E402
from app.models.models import User  # noqa: E402


@pytest.fixture
def db_session_factory():
    """Isolated in-memory DB shared across connections. Creates only the
    users table — sibling models carry Postgres-only JSONB columns that
    SQLite can't compile."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    User.__table__.create(bind=engine)
    factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    yield factory
    engine.dispose()


@pytest.fixture(autouse=True)
def fresh_provision_cache(db_session_factory, monkeypatch):
    """Point the service at the test DB and clear the seen-cache."""
    monkeypatch.setattr(
        user_service, "_session_factory", lambda: db_session_factory
    )
    user_service._SEEN_CACHE.clear()
    yield
    user_service._SEEN_CACHE.clear()


def _auth_user(sub="8f7d9a2e-0000-4000-8000-0000000000aa",
               email="prov@test.local", source="supabase"):
    return {
        "sub": sub,
        "role": "client",
        "metadata": {},
        "claims": {"email": email},
        "source": source,
    }


def test_first_sighting_creates_one_row(db_session_factory):
    user_service.provision_user(_auth_user())
    with db_session_factory() as db:
        rows = db.query(User).all()
        assert len(rows) == 1
        row = rows[0]
        assert row.sub == "8f7d9a2e-0000-4000-8000-0000000000aa"
        assert row.email == "prov@test.local"
        assert row.provider == "supabase"
        assert row.first_seen_at is not None
        assert row.last_seen_at is not None


def test_repeat_sighting_is_idempotent(db_session_factory):
    user_service.provision_user(_auth_user())
    user_service._SEEN_CACHE.clear()  # force the DB path again
    user_service.provision_user(_auth_user())
    with db_session_factory() as db:
        assert db.query(User).count() == 1


def test_email_change_updates_row_not_duplicates(db_session_factory):
    user_service.provision_user(_auth_user(email="old@test.local"))
    user_service._SEEN_CACHE.clear()
    user_service.provision_user(_auth_user(email="new@test.local"))
    with db_session_factory() as db:
        rows = db.query(User).all()
        assert len(rows) == 1
        assert rows[0].email == "new@test.local"


def test_seen_cache_skips_db(db_session_factory, monkeypatch):
    """Within the TTL window, a repeat sighting must not open a session."""
    user_service.provision_user(_auth_user())

    def _boom():
        raise AssertionError("DB touched inside TTL window")

    monkeypatch.setattr(user_service, "_session_factory", _boom)
    user_service.provision_user(_auth_user())  # cached — no DB


def test_cache_expiry_re_touches(db_session_factory):
    user_service.provision_user(_auth_user())
    sub = "8f7d9a2e-0000-4000-8000-0000000000aa"
    user_service._SEEN_CACHE[sub] = time.time() - (
        user_service._SEEN_TTL_SECONDS + 1
    )
    user_service.provision_user(_auth_user())
    with db_session_factory() as db:
        assert db.query(User).count() == 1  # still one row, re-touched


def test_dead_db_is_fail_open(monkeypatch):
    """Provisioning must swallow DB failures — auth continues."""
    def _boom():
        raise RuntimeError("db down")

    monkeypatch.setattr(user_service, "_session_factory", _boom)
    user_service.provision_user(_auth_user())  # must not raise


def test_dev_bypass_not_provisioned(db_session_factory):
    user_service.provision_user(
        {"sub": "dev-user", "role": "admin", "metadata": {},
         "claims": {}, "source": "dev_bypass"}
    )
    with db_session_factory() as db:
        assert db.query(User).count() == 0


def test_two_providers_two_rows(db_session_factory):
    user_service.provision_user(_auth_user())
    user_service.provision_user(
        _auth_user(sub="user_clerk_abc123", email="c@test.local",
                   source="clerk")
    )
    with db_session_factory() as db:
        assert db.query(User).count() == 2
        clerk_row = db.query(User).filter_by(sub="user_clerk_abc123").one()
        assert clerk_row.provider == "clerk"
