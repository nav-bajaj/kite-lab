"""
Authorization gate for the Supabase migration (auth_stack_v2, B1.2).

Port of ``test_clerk_authz.py`` — same endpoint inventories, same gate
semantics, tokens now Supabase-shaped (ES256, aud=authenticated, role in
``app_metadata``). The Clerk harness stays green alongside until the
Phase 4 cutover removes the Clerk verification path; this file is the
permanent successor.

Additions over the straight port:
  * cross-issuer confusion cases (Supabase-signed token claiming the
    Clerk issuer and vice versa must 401)
  * SI-1 user_metadata spoof case at the endpoint level

Test JWTs are signed with a locally-generated ECDSA P-256 keypair; the
JWKS caches are patched so no network calls are made.
"""

from __future__ import annotations

import base64
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient
from jose import jwt as jose_jwt

TEST_SUPABASE_ISSUER = "https://testproject.supabase.co/auth/v1"
TEST_SUPABASE_JWKS_URL = f"{TEST_SUPABASE_ISSUER}/.well-known/jwks.json"
TEST_CLERK_ISSUER = "https://test.clerk.accounts.dev"
TEST_CLERK_JWKS_URL = f"{TEST_CLERK_ISSUER}/.well-known/jwks.json"
TEST_KID = "sb-authz-key-id"

os.environ.setdefault("SUPABASE_JWKS_URL", TEST_SUPABASE_JWKS_URL)
os.environ.setdefault("SUPABASE_ISSUER", TEST_SUPABASE_ISSUER)
os.environ.setdefault("CLERK_JWKS_URL", TEST_CLERK_JWKS_URL)
os.environ.setdefault("CLERK_ISSUER", TEST_CLERK_ISSUER)
os.environ.setdefault("ALLOWED_ORIGINS", "http://localhost:3000")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("DEBUG", "false")
os.environ.setdefault("DISABLE_AUTH", "false")

from app.main import app  # noqa: E402
from app import auth as auth_module  # noqa: E402
from app.config import get_settings  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def ec_keypair():
    return ec.generate_private_key(ec.SECP256R1())


def _b64url(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode("ascii")


@pytest.fixture(scope="module")
def jwks_dict(ec_keypair):
    pub = ec_keypair.public_key().public_numbers()
    return {
        "keys": [
            {
                "kty": "EC",
                "crv": "P-256",
                "use": "sig",
                "alg": "ES256",
                "kid": TEST_KID,
                "x": _b64url(pub.x.to_bytes(32, "big")),
                "y": _b64url(pub.y.to_bytes(32, "big")),
            }
        ]
    }


@pytest.fixture(autouse=True)
def fresh_settings():
    """The settings singleton may have been instantiated by another test
    module before this module's env vars were set — rebuild it."""
    if hasattr(get_settings, "cache_clear"):
        get_settings.cache_clear()
    yield
    if hasattr(get_settings, "cache_clear"):
        get_settings.cache_clear()


@pytest.fixture(autouse=True)
def patch_jwks(jwks_dict, monkeypatch):
    """Install the local EC JWKS for the Supabase URL and an EMPTY key
    set for the Clerk URL (so cross-issuer tokens fail with a kid miss,
    served from cache — never the network). Supports both the legacy
    single-slot cache (pre-B1.3, for the witnessed-red run) and the
    per-URL cache the rewrite introduces."""
    now = time.time()
    if hasattr(auth_module, "_JWKS_CACHES"):
        auth_module._JWKS_CACHES[TEST_SUPABASE_JWKS_URL] = {
            "keys": jwks_dict, "fetched_at": now,
        }
        auth_module._JWKS_CACHES[TEST_CLERK_JWKS_URL] = {
            "keys": {"keys": []}, "fetched_at": now,
        }
    else:  # legacy single cache — red run only
        auth_module._JWKS_CACHE["keys"] = jwks_dict
        auth_module._JWKS_CACHE["fetched_at"] = now

    def _no_network(*_args, **_kwargs):
        raise AssertionError(
            "Test attempted to fetch JWKS over the network — patch failed"
        )

    monkeypatch.setattr("httpx.get", _no_network)
    yield
    if hasattr(auth_module, "_JWKS_CACHES"):
        auth_module._JWKS_CACHES.clear()
    else:
        auth_module._JWKS_CACHE["keys"] = None
        auth_module._JWKS_CACHE["fetched_at"] = 0.0


def _private_pem(ec_keypair) -> str:
    return ec_keypair.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()


def _make_token(
    ec_keypair,
    role: str | None,
    *,
    user_metadata: dict | None = None,
    kid: str = TEST_KID,
    **overrides: Any,
) -> str:
    """Sign a Supabase-shaped access token. ``role=None`` omits the key
    from app_metadata (the fresh-user default)."""
    now = datetime.now(tz=timezone.utc)
    app_metadata: dict[str, Any] = {"provider": "email", "providers": ["email"]}
    if role is not None:
        app_metadata["role"] = role
    claims: dict[str, Any] = {
        "sub": f"00000000-0000-4000-8000-{(role or 'norole'):>012}"[:36],
        "iss": TEST_SUPABASE_ISSUER,
        "aud": "authenticated",
        "role": "authenticated",  # PostgREST role — never the app role
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=1)).timestamp()),
        "email": f"{role or 'norole'}@test.local",
        "app_metadata": app_metadata,
        "user_metadata": user_metadata if user_metadata is not None else {},
        "session_id": "authz-session",
    }
    claims.update(overrides)
    return jose_jwt.encode(
        claims,
        _private_pem(ec_keypair),
        algorithm="ES256",
        headers={"kid": kid},
    )


@pytest.fixture
def client_token(ec_keypair) -> str:
    return _make_token(ec_keypair, role="client")


@pytest.fixture
def admin_token(ec_keypair) -> str:
    return _make_token(ec_keypair, role="admin")


@pytest.fixture
def expired_token(ec_keypair) -> str:
    now = datetime.now(tz=timezone.utc)
    return _make_token(
        ec_keypair,
        role="client",
        iat=int((now - timedelta(hours=2)).timestamp()),
        exp=int((now - timedelta(hours=1)).timestamp()),
    )


@pytest.fixture
def test_client() -> TestClient:
    # raise_server_exceptions=False: handler-side errors surface as 500s;
    # the auth gate firing before the body is what we assert.
    return TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# Endpoint inventories — mirror of test_clerk_authz.py (same coverage)
# ---------------------------------------------------------------------------


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
    # insights.py
    ("POST", "/api/insights/cache/clear"),
    # freshness.py
    ("GET", "/api/freshness"),
    # options_worker.py
    ("GET", "/api/options/worker-status"),
    ("GET", "/api/options/live-analytics"),
]

_U = "?universe=l6_v2"

CLIENT_READ_ENDPOINTS: list[tuple[str, str]] = [
    # portfolio.py
    ("GET", f"/api/portfolio{_U}"),
    ("GET", f"/api/portfolio/holdings{_U}"),
    ("GET", f"/api/portfolio/allocation{_U}"),
    # metrics.py
    ("GET", f"/api/metrics{_U}"),
    ("GET", f"/api/metrics/equity-curve{_U}"),
    ("GET", f"/api/metrics/monthly-returns{_U}"),
    # trades.py
    ("GET", f"/api/trades{_U}"),
    ("GET", f"/api/trades/summary{_U}"),
    ("GET", f"/api/trades/recent{_U}"),
    ("GET", f"/api/trades/export{_U}"),
    # rebalance.py
    ("GET", f"/api/rebalance/summary{_U}"),
    ("GET", f"/api/rebalance/preview{_U}"),
    ("GET", f"/api/rebalance/orders{_U}"),
    ("GET", f"/api/rebalance/orders/export{_U}"),
    ("GET", f"/api/rebalance/history{_U}"),
    ("GET", f"/api/rebalance/upcoming{_U}"),
    # positions.py reads
    ("GET", f"/api/positions{_U}"),
    ("GET", f"/api/positions/holdings{_U}"),
    ("GET", f"/api/positions/quotes{_U}"),
    # auth_routes.py
    ("GET", "/api/auth/me"),
    ("GET", "/api/auth/verify"),
]

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
    resp = test_client.request(method, path)
    assert resp.status_code in (401, 403), (
        f"{method} {path} returned {resp.status_code} with no token; "
        f"expected 401 or 403."
    )


@pytest.mark.parametrize("method,path", ADMIN_ENDPOINTS)
def test_admin_endpoint_passes_admin_token(test_client, admin_token, method, path):
    """Auth gate only — non-auth 4xx/5xx are fine."""
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
    resp = test_client.request(
        method, path, headers={"Authorization": f"Bearer {client_token}"}
    )
    assert resp.status_code not in (401, 403), (
        f"{method} {path} returned {resp.status_code} for a client-role token; "
        f"expected the call to pass auth. Body: {resp.text[:200]}"
    )


@pytest.mark.parametrize("method,path", CLIENT_READ_ENDPOINTS)
def test_client_read_endpoint_rejects_unauthenticated(test_client, method, path):
    resp = test_client.request(method, path)
    assert resp.status_code == 401, (
        f"{method} {path} returned {resp.status_code} with no token; expected 401."
    )


@pytest.mark.parametrize("method,path", PUBLIC_ENDPOINTS)
def test_public_endpoint_passes_unauthenticated(test_client, method, path):
    resp = test_client.request(method, path)
    assert resp.status_code not in (401, 403), (
        f"{method} {path} returned {resp.status_code} with no token; "
        f"expected the call to pass auth."
    )


def test_expired_token_returns_401(test_client, expired_token):
    resp = test_client.get(
        "/api/portfolio", headers={"Authorization": f"Bearer {expired_token}"}
    )
    assert resp.status_code == 401


def test_malformed_token_returns_401(test_client):
    resp = test_client.get(
        "/api/portfolio", headers={"Authorization": "Bearer not.a.real.jwt"}
    )
    assert resp.status_code == 401


def test_missing_kid_returns_401(test_client, ec_keypair):
    now = datetime.now(tz=timezone.utc)
    claims = {
        "sub": "00000000-0000-4000-8000-00000000nokid"[:36],
        "iss": TEST_SUPABASE_ISSUER,
        "aud": "authenticated",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=1)).timestamp()),
        "app_metadata": {"role": "admin"},
        "user_metadata": {},
    }
    token = jose_jwt.encode(claims, _private_pem(ec_keypair), algorithm="ES256")
    resp = test_client.get(
        "/api/portfolio", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 401


def test_missing_role_defaults_to_client(test_client, ec_keypair):
    """No role key in app_metadata -> client. Passes reads, blocked on admin."""
    token = _make_token(ec_keypair, role=None)
    resp = test_client.get(
        "/api/auth/verify", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    assert resp.json()["role"] == "client"

    resp = test_client.get(
        "/api/jobs", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 403


def test_user_metadata_role_never_grants_admin(test_client, ec_keypair):
    """SI-1 at the endpoint level: self-granted role in client-editable
    user_metadata must not open a single admin endpoint."""
    token = _make_token(
        ec_keypair, role=None, user_metadata={"role": "admin"}
    )
    resp = test_client.get(
        "/api/jobs", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 403
    resp = test_client.get(
        "/api/auth/verify", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 200
    assert resp.json()["role"] == "client"


# ---------------------------------------------------------------------------
# R-022: universe access — unchanged semantics under the new tokens
# ---------------------------------------------------------------------------

ADMIN_ONLY_UNIVERSES = ["nse500", "nifty100", "nifty250"]
CLIENT_VISIBLE_UNIVERSES = ["om25_v3", "tl25_v3", "l6_v2", "combo_defensive"]

UNIVERSE_ENDPOINTS = [
    "/api/portfolio",
    "/api/portfolio/holdings",
    "/api/portfolio/allocation",
    "/api/metrics",
    "/api/metrics/equity-curve",
    "/api/metrics/monthly-returns",
    "/api/trades",
    "/api/trades/summary",
    "/api/trades/recent",
    "/api/trades/export",
    "/api/rebalance/preview",
    "/api/rebalance/orders",
    "/api/rebalance/orders/export",
    "/api/rebalance/history",
    "/api/rebalance/upcoming",
    "/api/positions",
    "/api/positions/holdings",
    "/api/positions/quotes",
]


@pytest.mark.parametrize("path", UNIVERSE_ENDPOINTS)
@pytest.mark.parametrize("admin_universe", ADMIN_ONLY_UNIVERSES)
def test_client_token_blocked_on_admin_universe(
    test_client, client_token, path, admin_universe
):
    resp = test_client.get(
        f"{path}?universe={admin_universe}",
        headers={"Authorization": f"Bearer {client_token}"},
    )
    assert resp.status_code == 403, (
        f"GET {path}?universe={admin_universe} returned {resp.status_code} for "
        f"a client-role token; expected 403. Body: {resp.text[:200]}"
    )


@pytest.mark.parametrize("path", UNIVERSE_ENDPOINTS)
@pytest.mark.parametrize("client_universe", CLIENT_VISIBLE_UNIVERSES)
def test_client_token_passes_on_client_universe(
    test_client, client_token, path, client_universe
):
    resp = test_client.get(
        f"{path}?universe={client_universe}",
        headers={"Authorization": f"Bearer {client_token}"},
    )
    assert resp.status_code not in (401, 403), (
        f"GET {path}?universe={client_universe} returned {resp.status_code} for "
        f"a client-role token; expected auth to pass."
    )


@pytest.mark.parametrize("path", UNIVERSE_ENDPOINTS)
@pytest.mark.parametrize("admin_universe", ADMIN_ONLY_UNIVERSES)
def test_admin_token_passes_on_admin_universe(
    test_client, admin_token, path, admin_universe
):
    resp = test_client.get(
        f"{path}?universe={admin_universe}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert resp.status_code not in (401, 403), (
        f"GET {path}?universe={admin_universe} returned {resp.status_code} for "
        f"an admin token; expected auth to pass."
    )


# ---------------------------------------------------------------------------
# Issuer pinning + cross-issuer confusion
# ---------------------------------------------------------------------------


def test_wrong_issuer_returns_401(test_client, ec_keypair):
    token = _make_token(
        ec_keypair, role="admin", iss="https://attacker.example.com"
    )
    resp = test_client.get(
        "/api/portfolio", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 401


def test_supabase_key_with_clerk_issuer_returns_401(test_client, ec_keypair):
    """A token signed with the Supabase project key but claiming the
    Clerk issuer must fail on the Clerk path (kid not in Clerk JWKS) —
    never verify cross-issuer."""
    token = _make_token(ec_keypair, role="admin", iss=TEST_CLERK_ISSUER)
    resp = test_client.get(
        "/api/portfolio", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 401


def test_wrong_audience_returns_401(test_client, ec_keypair):
    token = _make_token(ec_keypair, role="admin", aud="anon")
    resp = test_client.get(
        "/api/portfolio", headers={"Authorization": f"Bearer {token}"}
    )
    assert resp.status_code == 401
