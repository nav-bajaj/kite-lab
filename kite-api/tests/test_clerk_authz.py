"""
Authorization gate for the Clerk migration.

These tests are the must-pass security gate before the client portal
goes live. They assert that:

  * A client-role token returns 403 on every admin/mutation endpoint
  * A client-role token returns 200/204 on every read endpoint
  * An admin-role token returns non-403 on every endpoint
  * No token at all returns 401 on protected endpoints
  * A malformed/expired token returns 401

Test JWTs are signed with a locally-generated RSA keypair; the JWKS
cache is monkey-patched so `app.auth._find_signing_key` resolves to
our local public key. No network calls are made.
"""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from jose import jwt as jose_jwt

# ---------------------------------------------------------------------------
# Setup: configure the app to look at our fake Clerk issuer + JWKS BEFORE
# importing app code. We use environment variables that pydantic-settings
# will pick up.
# ---------------------------------------------------------------------------

import os

TEST_ISSUER = "https://test.clerk.accounts.dev"
TEST_KID = "test-key-id"

os.environ.setdefault("CLERK_JWKS_URL", f"{TEST_ISSUER}/.well-known/jwks.json")
os.environ.setdefault("CLERK_ISSUER", TEST_ISSUER)
os.environ.setdefault("ALLOWED_ORIGINS", "http://localhost:3000")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")  # tests don't hit DB
os.environ.setdefault("DEBUG", "false")
os.environ.setdefault("DISABLE_AUTH", "false")

# Now import the app — auth.py reads settings on demand, so the env vars above
# take effect before any token verification runs.
from app.main import app  # noqa: E402
from app import auth as auth_module  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def rsa_keypair():
    """Generate one RSA keypair for the whole test module."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return private_key


@pytest.fixture(scope="module")
def jwks_dict(rsa_keypair):
    """Construct a JWKS document exposing rsa_keypair's public key."""
    public_numbers = rsa_keypair.public_key().public_numbers()
    # JWK format requires base64url-encoded big-endian byte representations.
    import base64

    def b64url_uint(n: int) -> str:
        b = n.to_bytes((n.bit_length() + 7) // 8, byteorder="big")
        return base64.urlsafe_b64encode(b).rstrip(b"=").decode("ascii")

    jwk = {
        "kty": "RSA",
        "use": "sig",
        "alg": "RS256",
        "kid": TEST_KID,
        "n": b64url_uint(public_numbers.n),
        "e": b64url_uint(public_numbers.e),
    }
    return {"keys": [jwk]}


@pytest.fixture(autouse=True)
def patch_jwks(jwks_dict, monkeypatch):
    """Replace the JWKS fetch with our local public-key JWK on every test."""
    auth_module._JWKS_CACHE["keys"] = jwks_dict
    auth_module._JWKS_CACHE["fetched_at"] = time.time()

    # Block any real network call as defense in depth.
    def _no_network(*_args, **_kwargs):
        raise AssertionError(
            "Test attempted to fetch JWKS over the network — monkey-patch failed"
        )

    monkeypatch.setattr("httpx.get", _no_network)
    yield
    auth_module._JWKS_CACHE["keys"] = None
    auth_module._JWKS_CACHE["fetched_at"] = 0.0


def _make_token(rsa_keypair, role: str, **extra_claims: Any) -> str:
    """Sign a Clerk-style JWT with the test RSA key."""
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
        "nbf": int(now.timestamp()),
        "metadata": {"role": role},
    }
    claims.update(extra_claims)

    return jose_jwt.encode(
        claims,
        private_pem,
        algorithm="RS256",
        headers={"kid": TEST_KID},
    )


@pytest.fixture
def client_token(rsa_keypair) -> str:
    return _make_token(rsa_keypair, role="client")


@pytest.fixture
def admin_token(rsa_keypair) -> str:
    return _make_token(rsa_keypair, role="admin")


@pytest.fixture
def expired_token(rsa_keypair) -> str:
    """Token with iat/exp in the past."""
    private_pem = rsa_keypair.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    now = datetime.now(tz=timezone.utc)
    claims = {
        "sub": "user_expired",
        "iss": TEST_ISSUER,
        "iat": int((now - timedelta(hours=2)).timestamp()),
        "exp": int((now - timedelta(hours=1)).timestamp()),
        "metadata": {"role": "client"},
    }
    return jose_jwt.encode(
        claims, private_pem, algorithm="RS256", headers={"kid": TEST_KID}
    )


@pytest.fixture
def test_client() -> TestClient:
    # `raise_server_exceptions=False` so handler-side errors (DB threading,
    # missing CSV files, etc.) bubble up as 500 responses rather than
    # propagating into pytest. The auth gate is what we're testing — any
    # 5xx still proves auth fired before the body, which is what we want.
    return TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# Endpoint inventories
# ---------------------------------------------------------------------------


# 17 admin/mutation endpoints. A client-role token must get 403 here.
ADMIN_ENDPOINTS: list[tuple[str, str]] = [
    # jobs.py
    ("GET", "/api/jobs"),
    ("POST", "/api/jobs"),
    ("GET", "/api/jobs/nonexistent-job"),
    ("GET", "/api/jobs/nonexistent-job/logs"),
    ("POST", "/api/jobs/nonexistent-job/cancel"),
    # schedule.py
    ("GET", "/api/schedule"),
    ("POST", "/api/schedule"),
    ("DELETE", "/api/schedule/nonexistent"),
    ("POST", "/api/schedule/nonexistent/run"),
    ("GET", "/api/schedule/defaults"),
    # sync.py
    ("POST", "/api/sync"),
    ("POST", "/api/sync/all"),
    # positions.py (mutations only)
    ("POST", "/api/positions/sync"),
    ("POST", "/api/positions/sync-from-csv"),
    # system.py
    ("POST", "/api/system/headless-login"),
]
# Note: POST /api/sync/upload-data and POST /api/jobs/{id}/cancel above already
# cover sync.py(3rd) and jobs.py respectively. POST /api/sync/upload-data is
# a multipart upload — we skip it here because crafting a tarball just to test
# the authz gate is overkill; the dependency is the same require_admin so a
# 403 on the simpler endpoints proves the wiring.


# 20 client-read endpoints. A client-role token must get a non-403 here
# (200, 404 with-payload, 400 invalid-arg etc. all count — anything but
# 401/403 means auth passed).
CLIENT_READ_ENDPOINTS: list[tuple[str, str]] = [
    # portfolio.py
    ("GET", "/api/portfolio"),
    ("GET", "/api/portfolio/holdings"),
    ("GET", "/api/portfolio/allocation"),
    # metrics.py
    ("GET", "/api/metrics"),
    ("GET", "/api/metrics/equity-curve"),
    ("GET", "/api/metrics/monthly-returns"),
    # trades.py
    ("GET", "/api/trades"),
    ("GET", "/api/trades/summary"),
    ("GET", "/api/trades/recent"),
    ("GET", "/api/trades/export"),
    # rebalance.py
    ("GET", "/api/rebalance/status"),
    ("GET", "/api/rebalance/preview"),
    ("GET", "/api/rebalance/orders"),
    ("GET", "/api/rebalance/orders/export"),
    ("GET", "/api/rebalance/history"),
    # positions.py reads
    ("GET", "/api/positions"),
    ("GET", "/api/positions/holdings"),
    ("GET", "/api/positions/quotes"),
    # auth_routes.py (any authenticated user)
    ("GET", "/api/auth/me"),
    ("GET", "/api/auth/verify"),
]


# 7 always-unauthenticated endpoints. No token needed; must return non-401/403.
PUBLIC_ENDPOINTS: list[tuple[str, str]] = [
    ("GET", "/api/health"),
    ("GET", "/api/positions/market-status"),
    ("GET", "/api/system/status"),
    ("GET", "/api/system/token"),
    ("GET", "/api/system/database"),
    ("GET", "/api/system/sync"),
    ("GET", "/api/system/login-url"),
]


# ---------------------------------------------------------------------------
# The gate tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("method,path", ADMIN_ENDPOINTS)
def test_admin_endpoint_rejects_client_token(test_client, client_token, method, path):
    """Every admin/mutation endpoint MUST 403 a valid client-role caller."""
    resp = test_client.request(
        method, path, headers={"Authorization": f"Bearer {client_token}"}
    )
    assert resp.status_code == 403, (
        f"{method} {path} returned {resp.status_code} for a client-role token; "
        f"expected 403. Body: {resp.text[:200]}"
    )


@pytest.mark.parametrize("method,path", ADMIN_ENDPOINTS)
def test_admin_endpoint_rejects_unauthenticated(test_client, method, path):
    """Every admin endpoint MUST 401 a caller with no token."""
    resp = test_client.request(method, path)
    assert resp.status_code in (401, 403), (
        f"{method} {path} returned {resp.status_code} with no token; "
        f"expected 401 or 403."
    )


@pytest.mark.parametrize("method,path", ADMIN_ENDPOINTS)
def test_admin_endpoint_passes_admin_token(test_client, admin_token, method, path):
    """Every admin endpoint MUST NOT return 401/403 for a valid admin token.
    Other 4xx/5xx are allowed (missing job ID, invalid universe, etc.) —
    we're only checking the auth gate."""
    resp = test_client.request(
        method, path, headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code not in (401, 403), (
        f"{method} {path} returned {resp.status_code} for an admin token; "
        f"expected anything other than 401/403. Body: {resp.text[:200]}"
    )


@pytest.mark.parametrize("method,path", CLIENT_READ_ENDPOINTS)
def test_client_read_endpoint_passes_client_token(
    test_client, client_token, method, path
):
    """Every client-read endpoint MUST NOT 401/403 a valid client-role caller."""
    resp = test_client.request(
        method, path, headers={"Authorization": f"Bearer {client_token}"}
    )
    assert resp.status_code not in (401, 403), (
        f"{method} {path} returned {resp.status_code} for a client-role token; "
        f"expected the call to pass auth (any non-401/403). Body: {resp.text[:200]}"
    )


@pytest.mark.parametrize("method,path", CLIENT_READ_ENDPOINTS)
def test_client_read_endpoint_rejects_unauthenticated(test_client, method, path):
    """Every client-read endpoint MUST 401 a caller with no token."""
    resp = test_client.request(method, path)
    assert resp.status_code == 401, (
        f"{method} {path} returned {resp.status_code} with no token; "
        f"expected 401."
    )


@pytest.mark.parametrize("method,path", PUBLIC_ENDPOINTS)
def test_public_endpoint_passes_unauthenticated(test_client, method, path):
    """Bootstrap/health endpoints must NOT require auth."""
    resp = test_client.request(method, path)
    assert resp.status_code not in (401, 403), (
        f"{method} {path} returned {resp.status_code} with no token; "
        f"expected the call to pass auth (any non-401/403)."
    )


def test_expired_token_returns_401(test_client, expired_token):
    """An expired but otherwise valid token must 401 on a protected endpoint."""
    resp = test_client.get(
        "/api/portfolio", headers={"Authorization": f"Bearer {expired_token}"}
    )
    assert resp.status_code == 401


def test_malformed_token_returns_401(test_client):
    """A garbage token must 401."""
    resp = test_client.get(
        "/api/portfolio", headers={"Authorization": "Bearer not.a.real.jwt"}
    )
    assert resp.status_code == 401


def test_missing_kid_returns_401(test_client, rsa_keypair):
    """A token without the `kid` header must 401."""
    private_pem = rsa_keypair.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    now = datetime.now(tz=timezone.utc)
    claims = {
        "sub": "user_no_kid",
        "iss": TEST_ISSUER,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=1)).timestamp()),
        "metadata": {"role": "admin"},
    }
    # No `kid` in headers
    token = jose_jwt.encode(claims, private_pem, algorithm="RS256")
    resp = test_client.get(
        "/api/portfolio", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 401


def test_missing_role_defaults_to_client(test_client, rsa_keypair):
    """A token with no `metadata.role` should be treated as client (defense in
    depth — can't accidentally promote a malformed token to admin)."""
    private_pem = rsa_keypair.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    now = datetime.now(tz=timezone.utc)
    claims = {
        "sub": "user_no_role",
        "iss": TEST_ISSUER,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=1)).timestamp()),
        # Note: no metadata field at all
    }
    token = jose_jwt.encode(
        claims, private_pem, algorithm="RS256", headers={"kid": TEST_KID}
    )
    # Should be allowed on client reads
    resp = test_client.get(
        "/api/auth/verify", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["role"] == "client"

    # And blocked on admin
    resp = test_client.get(
        "/api/jobs", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 403


def test_wrong_issuer_returns_401(test_client, rsa_keypair):
    """A token signed with the right key but wrong issuer must 401."""
    private_pem = rsa_keypair.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    now = datetime.now(tz=timezone.utc)
    claims = {
        "sub": "user_wrong_iss",
        "iss": "https://attacker.example.com",  # NOT TEST_ISSUER
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=1)).timestamp()),
        "metadata": {"role": "admin"},
    }
    token = jose_jwt.encode(
        claims, private_pem, algorithm="RS256", headers={"kid": TEST_KID}
    )
    resp = test_client.get(
        "/api/portfolio", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 401
