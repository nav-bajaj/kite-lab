"""
PRIVATE_MODE lockdown (tasks/site_gate, R-028).

With PRIVATE_MODE=true only admin-role tokens may use protected
endpoints, and the normally-public insights/indices readers require an
admin token. Health, system bootstrap, market-status, and the waitlist
POST stay open.

Reuses the shared endpoint inventory so this suite
tracks the real surface automatically.
"""

from __future__ import annotations

import os
import time
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest
from fastapi.testclient import TestClient
from jose import jwt as jose_jwt

from tests.supabase_token import (  # noqa: E402
    TEST_SUPABASE_ISSUER,
    TEST_SUPABASE_JWKS_URL,
    clear_jwks,
    generate_keypair,
    install_jwks,
    make_token,
)

os.environ.setdefault("SUPABASE_JWKS_URL", TEST_SUPABASE_JWKS_URL)
os.environ.setdefault("SUPABASE_ISSUER", TEST_SUPABASE_ISSUER)
os.environ.setdefault("ALLOWED_ORIGINS", "http://localhost:3000")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("DEBUG", "false")
os.environ.setdefault("DISABLE_AUTH", "false")

from app.main import app  # noqa: E402
from app import auth as auth_module  # noqa: E402
from app.config import get_settings  # noqa: E402
from tests.endpoint_inventory import (  # noqa: E402
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
def keypair():
    return generate_keypair()


@pytest.fixture(autouse=True)
def patch_jwks(keypair, monkeypatch):
    """Serve the local EC JWKS from cache so no test touches the network."""
    install_jwks(auth_module, keypair, monkeypatch)
    yield
    clear_jwks(auth_module)


@pytest.fixture
def client_token(keypair) -> str:
    return make_token(keypair, "client")


@pytest.fixture
def admin_token(keypair) -> str:
    return make_token(keypair, "admin")


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


def test_validate_token_string_rejects_client_token(keypair, private_mode_on):
    token = make_token(keypair, "client")
    with pytest.raises(auth_module.ForbiddenError):
        auth_module.validate_token_string(token)


def test_validate_token_string_passes_admin_token(keypair, private_mode_on):
    token = make_token(keypair, "admin")
    user = auth_module.validate_token_string(token)
    assert user["role"] == "admin"

