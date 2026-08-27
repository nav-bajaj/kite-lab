"""
Waitlist endpoint behaviour (tasks/site_gate).

POST /api/waitlist is public by design (R-029): validation, dedupe,
honeypot, and rate limiting. GET /api/waitlist is admin-only.

Auth plumbing (fake Clerk JWKS + locally-signed RS256 tokens) reuses the
pattern from test_clerk_authz. The DB is a per-module sqlite file with
only the waitlist table created (the full metadata contains Postgres
JSONB columns sqlite can't compile).
"""

from __future__ import annotations

import os
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from jose import jwt as jose_jwt
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

TEST_ISSUER = "https://test.clerk.accounts.dev"
TEST_KID = "test-key-id"

os.environ.setdefault("CLERK_JWKS_URL", f"{TEST_ISSUER}/.well-known/jwks.json")
os.environ.setdefault("CLERK_ISSUER", TEST_ISSUER)
os.environ.setdefault("ALLOWED_ORIGINS", "http://localhost:3000")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("DEBUG", "false")
os.environ.setdefault("DISABLE_AUTH", "false")

from app.main import app  # noqa: E402
from app import auth as auth_module  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.api import waitlist as waitlist_module  # noqa: E402
from app.middleware.rate_limiter import limiter  # noqa: E402
from app.models.database import get_db  # noqa: E402
from app.models.models import WaitlistSignup  # noqa: E402


# ---------------------------------------------------------------------------
# DB: shared in-memory sqlite with only the waitlist table
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def db_sessionmaker():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    WaitlistSignup.__table__.create(engine)
    yield sessionmaker(bind=engine, autocommit=False, autoflush=False)
    engine.dispose()


@pytest.fixture(autouse=True)
def override_db(db_sessionmaker):
    def _get_db():
        db = db_sessionmaker()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _get_db
    yield
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture(autouse=True)
def clean_state(db_sessionmaker):
    """Fresh table, rate-limit buckets, and row-count cache for every test."""
    limiter.reset()
    waitlist_module._count_cache["n"] = 0
    waitlist_module._count_cache["checked_at"] = 0.0
    db = db_sessionmaker()
    db.query(WaitlistSignup).delete()
    db.commit()
    db.close()
    yield


def _count(db_sessionmaker) -> int:
    db = db_sessionmaker()
    try:
        return db.query(WaitlistSignup).count()
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Auth fixtures (same pattern as test_clerk_authz)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def rsa_keypair():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)


@pytest.fixture(scope="module")
def jwks_dict(rsa_keypair):
    import base64

    public_numbers = rsa_keypair.public_key().public_numbers()

    def b64url_uint(n: int) -> str:
        b = n.to_bytes((n.bit_length() + 7) // 8, byteorder="big")
        return base64.urlsafe_b64encode(b).rstrip(b"=").decode("ascii")

    return {
        "keys": [
            {
                "kty": "RSA",
                "use": "sig",
                "alg": "RS256",
                "kid": TEST_KID,
                "n": b64url_uint(public_numbers.n),
                "e": b64url_uint(public_numbers.e),
            }
        ]
    }


@pytest.fixture(autouse=True)
def patch_jwks(jwks_dict, monkeypatch):
    auth_module._JWKS_CACHE["keys"] = jwks_dict
    auth_module._JWKS_CACHE["fetched_at"] = time.time()

    def _no_network(*_args, **_kwargs):
        raise AssertionError("Test attempted a real JWKS fetch")

    monkeypatch.setattr("httpx.get", _no_network)
    yield
    auth_module._JWKS_CACHE["keys"] = None
    auth_module._JWKS_CACHE["fetched_at"] = 0.0


def _make_token(rsa_keypair, role: str) -> str:
    private_pem = rsa_keypair.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    now = datetime.now(tz=timezone.utc)
    claims: dict[str, Any] = {
        "sub": f"user_test_{role}",
        "iss": TEST_ISSUER,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=1)).timestamp()),
        "metadata": {"role": role},
    }
    return jose_jwt.encode(
        claims, private_pem, algorithm="RS256", headers={"kid": TEST_KID}
    )


@pytest.fixture
def test_client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# POST /api/waitlist
# ---------------------------------------------------------------------------


def test_valid_email_creates_row(test_client, db_sessionmaker):
    resp = test_client.post("/api/waitlist", json={"email": "person@example.com"})
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
    assert _count(db_sessionmaker) == 1


def test_email_normalised_and_duplicate_idempotent(test_client, db_sessionmaker):
    first = test_client.post("/api/waitlist", json={"email": "Person@Example.com "})
    dup = test_client.post("/api/waitlist", json={"email": "person@example.com"})
    assert first.status_code == 200
    assert dup.status_code == 200
    assert dup.json() == {"status": "ok"}  # identical response — no oracle
    assert _count(db_sessionmaker) == 1


@pytest.mark.parametrize(
    "bad_email",
    ["not-an-email", "a@b", "has space@example.com", "@example.com", "a@"],
)
def test_invalid_email_rejected(test_client, db_sessionmaker, bad_email):
    resp = test_client.post("/api/waitlist", json={"email": bad_email})
    assert resp.status_code == 422
    assert _count(db_sessionmaker) == 0


def test_overlong_email_rejected(test_client, db_sessionmaker):
    resp = test_client.post(
        "/api/waitlist", json={"email": "a" * 320 + "@example.com"}
    )
    assert resp.status_code == 422
    assert _count(db_sessionmaker) == 0


def test_unknown_source_rejected(test_client, db_sessionmaker):
    resp = test_client.post(
        "/api/waitlist",
        json={"email": "person@example.com", "source": "somewhere_else"},
    )
    assert resp.status_code == 422
    assert _count(db_sessionmaker) == 0


def test_row_ceiling_pretends_success_writes_nothing(
    test_client, db_sessionmaker, monkeypatch
):
    """Past _MAX_ROWS the endpoint returns the same 200 but stops writing
    (R-027 growth ceiling)."""
    monkeypatch.setattr(waitlist_module, "_MAX_ROWS", 0)
    resp = test_client.post("/api/waitlist", json={"email": "late@example.com"})
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
    assert _count(db_sessionmaker) == 0


def test_honeypot_pretends_success_writes_nothing(test_client, db_sessionmaker):
    resp = test_client.post(
        "/api/waitlist",
        json={"email": "bot@example.com", "website": "http://spam.example"},
    )
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
    assert _count(db_sessionmaker) == 0


def test_rate_limit_kicks_in(test_client):
    for i in range(10):
        resp = test_client.post(
            "/api/waitlist", json={"email": f"user{i}@example.com"}
        )
        assert resp.status_code == 200, f"request {i} unexpectedly {resp.status_code}"
    resp = test_client.post("/api/waitlist", json={"email": "user11@example.com"})
    assert resp.status_code == 429


def test_rate_limit_keyed_by_forwarded_for(test_client):
    """Distinct X-Forwarded-For values get distinct buckets (Railway sets
    XFF; without it every caller shares the proxy IP)."""
    for i in range(10):
        resp = test_client.post(
            "/api/waitlist",
            json={"email": f"a{i}@example.com"},
            headers={"X-Forwarded-For": "203.0.113.7"},
        )
        assert resp.status_code == 200
    blocked = test_client.post(
        "/api/waitlist",
        json={"email": "a11@example.com"},
        headers={"X-Forwarded-For": "203.0.113.7"},
    )
    assert blocked.status_code == 429
    other = test_client.post(
        "/api/waitlist",
        json={"email": "b1@example.com"},
        headers={"X-Forwarded-For": "203.0.113.99"},
    )
    assert other.status_code == 200


# ---------------------------------------------------------------------------
# GET /api/waitlist (admin-only)
# ---------------------------------------------------------------------------


def test_get_requires_auth(test_client):
    assert test_client.get("/api/waitlist").status_code == 401


def test_get_rejects_client_role(test_client, rsa_keypair):
    token = _make_token(rsa_keypair, "client")
    resp = test_client.get(
        "/api/waitlist", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 403


def test_get_returns_signups_for_admin(test_client, rsa_keypair):
    test_client.post("/api/waitlist", json={"email": "person@example.com"})
    token = _make_token(rsa_keypair, "admin")
    resp = test_client.get(
        "/api/waitlist", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["count"] == 1
    assert body["signups"][0]["email"] == "person@example.com"
    assert body["signups"][0]["source"] == "coming_soon"


# ---------------------------------------------------------------------------
# Consent lifecycle (email_channel Phase 1)
# ---------------------------------------------------------------------------


def test_signup_single_opt_in_is_mailable_immediately(
    test_client, db_sessionmaker
):
    """Default (founder's choice): single opt-in — mailable at signup,
    with an unguessable unsubscribe token from the moment it exists."""
    test_client.post("/api/waitlist", json={"email": "person@example.com"})
    db = db_sessionmaker()
    try:
        row = db.query(WaitlistSignup).one()
        assert row.status == "confirmed"
        assert row.confirmed_at is not None
        assert row.confirm_token is None  # no confirm step under single opt-in
        assert row.unsubscribe_token
        assert len(row.unsubscribe_token) >= 32
    finally:
        db.close()


def test_signup_double_opt_in_stays_pending(test_client, db_sessionmaker):
    """Flipping WAITLIST_DOUBLE_OPT_IN holds the signup at 'pending' with a
    confirm token — the machinery is ready if complaint rates force it."""
    settings = get_settings()
    settings.waitlist_double_opt_in = True
    try:
        test_client.post("/api/waitlist", json={"email": "dbl@example.com"})
        db = db_sessionmaker()
        try:
            row = db.query(WaitlistSignup).one()
            assert row.status == "pending"
            assert row.confirmed_at is None
            assert row.confirm_token
            assert row.confirm_token != row.unsubscribe_token
        finally:
            db.close()
    finally:
        settings.waitlist_double_opt_in = False


def test_unsubscribe_tokens_are_unique_per_signup(test_client, db_sessionmaker):
    for i in range(5):
        test_client.post("/api/waitlist", json={"email": f"u{i}@example.com"})
    db = db_sessionmaker()
    try:
        tokens = [r.unsubscribe_token for r in db.query(WaitlistSignup).all()]
    finally:
        db.close()
    assert len(tokens) == 5
    assert len(set(tokens)) == 5


def test_status_breakdown_and_mailable_count(test_client, rsa_keypair, db_sessionmaker):
    """`mailable` counts only confirmed rows — the number that matters
    before any send."""
    for i in range(3):
        test_client.post("/api/waitlist", json={"email": f"s{i}@example.com"})
    db = db_sessionmaker()
    try:
        rows = db.query(WaitlistSignup).order_by(WaitlistSignup.id).all()
        rows[0].status = "confirmed"
        rows[1].status = "unsubscribed"
        rows[2].status = "pending"
        db.commit()
    finally:
        db.close()

    token = _make_token(rsa_keypair, "admin")
    body = test_client.get(
        "/api/waitlist", headers={"Authorization": f"Bearer {token}"}
    ).json()
    assert body["count"] == 3
    assert body["mailable"] == 1
    assert body["by_status"]["confirmed"] == 1
    assert body["by_status"]["unsubscribed"] == 1
    assert body["by_status"]["pending"] == 1


# ---------------------------------------------------------------------------
# CSV export
# ---------------------------------------------------------------------------


def test_export_requires_admin(test_client, rsa_keypair):
    assert test_client.get("/api/waitlist/export.csv").status_code == 401
    client = _make_token(rsa_keypair, "client")
    resp = test_client.get(
        "/api/waitlist/export.csv", headers={"Authorization": f"Bearer {client}"}
    )
    assert resp.status_code == 403


def test_export_returns_csv_without_tokens(test_client, rsa_keypair):
    """Tokens are live credentials for confirm/unsubscribe links — they
    must never leave the DB in a spreadsheet."""
    test_client.post("/api/waitlist", json={"email": "person@example.com"})
    token = _make_token(rsa_keypair, "admin")
    resp = test_client.get(
        "/api/waitlist/export.csv", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    assert "no-store" in resp.headers.get("cache-control", "")
    text = resp.text
    assert "person@example.com" in text
    assert "email,source,status" in text
    assert "token" not in text.lower()
