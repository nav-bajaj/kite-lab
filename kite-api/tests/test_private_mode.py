"""
PRIVATE_MODE lockdown (tasks/site_gate, R-028).

With PRIVATE_MODE=true only admin-role tokens may use protected
endpoints, and the normally-public insights/indices readers require an
admin token. Health, system bootstrap, market-status, and the waitlist
POST stay open.

Reuses the endpoint inventories from test_clerk_authz so this suite
tracks the real surface automatically.
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
from tests.test_clerk_authz import (  # noqa: E402
    ADMIN_ENDPOINTS,
    CLIENT_READ_ENDPOINTS,
    PUBLIC_ENDPOINTS,
)

# Normally-public data readers that must demand an admin token under
# private mode (R-023 surface, gated via require_admin_when_private).
PUBLIC_DATA_READERS = [
    ("GET", "/api/insights/reading"),
    ("GET", "/api/indices/returns"),
]

# Endpoints that must stay open even under private mode.
STAYS_OPEN = [ep for ep in PUBLIC_ENDPOINTS]


@pytest.fixture(autouse=True)
def private_mode_on():
    settings = get_settings()  # lru_cached singleton — every call site sees this
    settings.private_mode = True
    yield
    settings.private_mode = False


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
def client_token(rsa_keypair) -> str:
    return _make_token(rsa_keypair, "client")


@pytest.fixture
def admin_token(rsa_keypair) -> str:
    return _make_token(rsa_keypair, "admin")


@pytest.fixture
def test_client() -> TestClient:
    return TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# Client tokens are locked out everywhere protected
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("method,path", CLIENT_READ_ENDPOINTS)
def test_client_read_endpoints_reject_client_token(
    test_client, client_token, method, path
):
    """Under private mode a client-role token must 403 on every endpoint
    it can normally read."""
    resp = test_client.request(
        method, path, headers={"Authorization": f"Bearer {client_token}"}
    )
    assert resp.status_code == 403, (
        f"{method} {path} returned {resp.status_code} for a client token under "
        f"private mode; expected 403. Body: {resp.text[:200]}"
    )


@pytest.mark.parametrize("method,path", ADMIN_ENDPOINTS)
def test_admin_endpoints_still_reject_client_token(
    test_client, client_token, method, path
):
    # 403 everywhere except GET /api/jobs/{id}/logs, whose get_optional_user
    # swallows the private-mode ForbiddenError and re-raises its own 401.
    # Either status is a denial; what matters is the caller is locked out.
    resp = test_client.request(
        method, path, headers={"Authorization": f"Bearer {client_token}"}
    )
    assert resp.status_code in (401, 403)


@pytest.mark.parametrize("method,path", CLIENT_READ_ENDPOINTS)
def test_client_read_endpoints_pass_admin_token(
    test_client, admin_token, method, path
):
    """Admin tokens keep working on everything under private mode."""
    resp = test_client.request(
        method, path, headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code not in (401, 403), (
        f"{method} {path} returned {resp.status_code} for an admin token under "
        f"private mode; expected auth to pass. Body: {resp.text[:200]}"
    )


# ---------------------------------------------------------------------------
# Normally-public data readers demand an admin token
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("method,path", PUBLIC_DATA_READERS)
def test_public_data_readers_reject_anonymous(test_client, method, path):
    resp = test_client.request(method, path)
    assert resp.status_code == 401, (
        f"{method} {path} returned {resp.status_code} anonymously under "
        f"private mode; expected 401."
    )


@pytest.mark.parametrize("method,path", PUBLIC_DATA_READERS)
def test_public_data_readers_reject_client_token(
    test_client, client_token, method, path
):
    resp = test_client.request(
        method, path, headers={"Authorization": f"Bearer {client_token}"}
    )
    assert resp.status_code == 403


@pytest.mark.parametrize("method,path", PUBLIC_DATA_READERS)
def test_public_data_readers_pass_admin_token(
    test_client, admin_token, method, path
):
    resp = test_client.request(
        method, path, headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert resp.status_code not in (401, 403), (
        f"{method} {path} returned {resp.status_code} for an admin token under "
        f"private mode. Body: {resp.text[:200]}"
    )


# ---------------------------------------------------------------------------
# Bootstrap surface stays open
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("method,path", STAYS_OPEN)
def test_bootstrap_endpoints_stay_open(test_client, method, path):
    """Health, system OAuth bootstrap, market-status, and the waitlist POST
    must keep working anonymously under private mode."""
    resp = test_client.request(method, path)
    assert resp.status_code not in (401, 403), (
        f"{method} {path} returned {resp.status_code} anonymously under "
        f"private mode; expected it to stay open."
    )


# ---------------------------------------------------------------------------
# SSE query-param token path
# ---------------------------------------------------------------------------


def test_validate_token_string_rejects_client_token(rsa_keypair, private_mode_on):
    token = _make_token(rsa_keypair, "client")
    with pytest.raises(auth_module.ForbiddenError):
        auth_module.validate_token_string(token)


def test_validate_token_string_passes_admin_token(rsa_keypair, private_mode_on):
    token = _make_token(rsa_keypair, "admin")
    user = auth_module.validate_token_string(token)
    assert user["role"] == "admin"
