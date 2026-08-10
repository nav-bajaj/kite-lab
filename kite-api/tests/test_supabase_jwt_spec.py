"""
Spec suite for Supabase JWT verification (auth_stack_v2, Phase 0/S0.3).

Written BEFORE the ``app/auth.py`` rewrite per the TDD policy (red
witnessed 2026-08-10: 6 failures; green after B1.3). Pins the security
invariants from ``tasks/auth_stack_v2/PLAN.md``:

  SI-1  Authz role comes exclusively from ``app_metadata.role``
        (server-controlled). ``user_metadata`` (client-editable) and the
        native Supabase ``role`` claim (PostgREST's ``authenticated`` /
        ``service_role``) must never influence app authz.
  SI-2  Asymmetric alg only (ES256 pinned pending S0.7 confirmation),
        ``kid`` resolved in JWKS, issuer pinned to the project's
        ``/auth/v1``. Legacy HS256 shared-secret tokens are rejected
        even with a colliding ``kid`` (alg-confusion case).
  SI-3  ``aud == "authenticated"`` enforced.
  SI-10 Dev bypass requires DEBUG and DISABLE_AUTH together.

Token surface under test is ``validate_token_string`` (pure decode path,
same dict shape as ``get_current_user``) plus ``get_current_user`` for
the bypass gate. The full endpoint-inventory harness is ported
separately in B1.2.

Signing uses a locally-generated ECDSA P-256 keypair; the JWKS cache is
patched so no network calls are made — same approach as
``test_clerk_authz.py``.
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
from jose import jwt as jose_jwt

TEST_SUPABASE_ISSUER = "https://testproject.supabase.co/auth/v1"
TEST_KID = "sb-test-key-id"
LEGACY_HS256_SECRET = "legacy-shared-jwt-secret-at-least-32-chars-long"

os.environ.setdefault(
    "SUPABASE_JWKS_URL", f"{TEST_SUPABASE_ISSUER}/.well-known/jwks.json"
)
os.environ.setdefault("SUPABASE_ISSUER", TEST_SUPABASE_ISSUER)
os.environ.setdefault("ALLOWED_ORIGINS", "http://localhost:3000")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("DEBUG", "false")
os.environ.setdefault("DISABLE_AUTH", "false")

from app import auth as auth_module  # noqa: E402
from app.auth import AuthError  # noqa: E402
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
    jwk = {
        "kty": "EC",
        "crv": "P-256",
        "use": "sig",
        "alg": "ES256",
        "kid": TEST_KID,
        "x": _b64url(pub.x.to_bytes(32, "big")),
        "y": _b64url(pub.y.to_bytes(32, "big")),
    }
    return {"keys": [jwk]}


@pytest.fixture(autouse=True)
def fresh_settings(monkeypatch):
    """Ensure the (possibly cached) settings singleton carries this
    module's Supabase env config, whatever other test modules did first."""
    if hasattr(get_settings, "cache_clear"):
        get_settings.cache_clear()
    yield
    if hasattr(get_settings, "cache_clear"):
        get_settings.cache_clear()


@pytest.fixture(autouse=True)
def patch_jwks(jwks_dict, monkeypatch):
    auth_module._JWKS_CACHES[os.environ["SUPABASE_JWKS_URL"]] = {
        "keys": jwks_dict,
        "fetched_at": time.time(),
    }

    def _no_network(*_args, **_kwargs):
        raise AssertionError(
            "Test attempted to fetch JWKS over the network — patch failed"
        )

    monkeypatch.setattr("httpx.get", _no_network)
    yield
    auth_module._JWKS_CACHES.clear()


def _private_pem(ec_keypair) -> str:
    return ec_keypair.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()


def _make_token(
    ec_keypair,
    *,
    app_metadata: dict | None = None,
    user_metadata: dict | None = None,
    kid: str = TEST_KID,
    **overrides: Any,
) -> str:
    """Sign a Supabase-shaped access token with the test EC key.

    Claim shape mirrors a real GoTrue access token: iss/aud/sub/exp plus
    ``role`` (PostgREST role, NOT the app role), ``app_metadata`` and
    ``user_metadata``.
    """
    now = datetime.now(tz=timezone.utc)
    claims: dict[str, Any] = {
        "sub": "8f7d9a2e-0000-4000-8000-000000000001",
        "iss": TEST_SUPABASE_ISSUER,
        "aud": "authenticated",
        "role": "authenticated",  # PostgREST role — never the app role
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=1)).timestamp()),
        "email": "spec@test.local",
        "app_metadata": app_metadata if app_metadata is not None else {},
        "user_metadata": user_metadata if user_metadata is not None else {},
        "session_id": "spec-session",
    }
    claims.update(overrides)
    return jose_jwt.encode(
        claims,
        _private_pem(ec_keypair),
        algorithm="ES256",
        headers={"kid": kid},
    )


# ---------------------------------------------------------------------------
# Positive path — these are RED until the B1.3 rewrite lands
# ---------------------------------------------------------------------------


def test_valid_token_accepted_with_default_client_role(ec_keypair):
    token = _make_token(ec_keypair)
    user = auth_module.validate_token_string(token)
    assert user["sub"] == "8f7d9a2e-0000-4000-8000-000000000001"
    assert user["role"] == "client"


def test_admin_role_read_from_app_metadata(ec_keypair):
    token = _make_token(ec_keypair, app_metadata={"role": "admin"})
    user = auth_module.validate_token_string(token)
    assert user["role"] == "admin"


def test_source_labels_supabase_query_param(ec_keypair):
    token = _make_token(ec_keypair)
    user = auth_module.validate_token_string(token)
    assert user["source"] == "supabase_query_param"


# ---------------------------------------------------------------------------
# SI-1 — role provenance
# ---------------------------------------------------------------------------


def test_role_in_user_metadata_only_is_ignored(ec_keypair):
    """user_metadata is end-user-editable via the Supabase client API. A
    self-granted role there must never become an app role."""
    token = _make_token(
        ec_keypair,
        app_metadata={},
        user_metadata={"role": "admin"},
    )
    user = auth_module.validate_token_string(token)
    assert user["role"] == "client"


def test_postgres_role_claim_never_maps_to_app_role(ec_keypair):
    """The native ``role`` claim is PostgREST plumbing. Even
    ``service_role`` there must not grant app-admin."""
    token = _make_token(ec_keypair, role="service_role", app_metadata={})
    user = auth_module.validate_token_string(token)
    assert user["role"] == "client"


def test_unknown_app_metadata_role_defaults_to_client(ec_keypair):
    token = _make_token(ec_keypair, app_metadata={"role": "superuser"})
    user = auth_module.validate_token_string(token)
    assert user["role"] == "client"


# ---------------------------------------------------------------------------
# SI-2 — algorithm / issuer / kid pinning
# ---------------------------------------------------------------------------


def test_wrong_issuer_rejected(ec_keypair):
    token = _make_token(
        ec_keypair, iss="https://evil-project.supabase.co/auth/v1"
    )
    with pytest.raises(AuthError):
        auth_module.validate_token_string(token)


def test_legacy_hs256_token_rejected_even_with_colliding_kid():
    """Alg-confusion: an HS256 token signed with the legacy shared
    secret, carrying a kid that resolves in the JWKS, must be rejected —
    verification is pinned to the asymmetric alg."""
    now = datetime.now(tz=timezone.utc)
    claims = {
        "sub": "8f7d9a2e-0000-4000-8000-00000000hs25",
        "iss": TEST_SUPABASE_ISSUER,
        "aud": "authenticated",
        "role": "authenticated",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=1)).timestamp()),
        "app_metadata": {"role": "admin"},
        "user_metadata": {},
    }
    token = jose_jwt.encode(
        claims,
        LEGACY_HS256_SECRET,
        algorithm="HS256",
        headers={"kid": TEST_KID},
    )
    with pytest.raises(AuthError):
        auth_module.validate_token_string(token)


def test_unknown_kid_rejected(ec_keypair):
    token = _make_token(ec_keypair, kid="some-other-key")
    with pytest.raises(AuthError):
        auth_module.validate_token_string(token)


def test_missing_kid_rejected(ec_keypair):
    now = datetime.now(tz=timezone.utc)
    claims = {
        "sub": "8f7d9a2e-0000-4000-8000-0000000nokid",
        "iss": TEST_SUPABASE_ISSUER,
        "aud": "authenticated",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=1)).timestamp()),
        "app_metadata": {},
        "user_metadata": {},
    }
    token = jose_jwt.encode(
        claims, _private_pem(ec_keypair), algorithm="ES256"
    )
    with pytest.raises(AuthError):
        auth_module.validate_token_string(token)


# ---------------------------------------------------------------------------
# SI-3 — audience
# ---------------------------------------------------------------------------


def test_wrong_audience_rejected(ec_keypair):
    token = _make_token(ec_keypair, aud="anon")
    with pytest.raises(AuthError):
        auth_module.validate_token_string(token)


def test_missing_audience_rejected(ec_keypair):
    now = datetime.now(tz=timezone.utc)
    claims = {
        "sub": "8f7d9a2e-0000-4000-8000-000000noaud1",
        "iss": TEST_SUPABASE_ISSUER,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=1)).timestamp()),
        "app_metadata": {},
        "user_metadata": {},
    }
    token = jose_jwt.encode(
        claims,
        _private_pem(ec_keypair),
        algorithm="ES256",
        headers={"kid": TEST_KID},
    )
    with pytest.raises(AuthError):
        auth_module.validate_token_string(token)


# ---------------------------------------------------------------------------
# Expiry / structure
# ---------------------------------------------------------------------------


def test_expired_token_rejected(ec_keypair):
    now = datetime.now(tz=timezone.utc)
    token = _make_token(
        ec_keypair,
        iat=int((now - timedelta(hours=2)).timestamp()),
        exp=int((now - timedelta(hours=1)).timestamp()),
    )
    with pytest.raises(AuthError):
        auth_module.validate_token_string(token)


def test_missing_sub_rejected(ec_keypair):
    token = _make_token(ec_keypair, sub=None)
    with pytest.raises(AuthError):
        auth_module.validate_token_string(token)


def test_empty_token_rejected():
    with pytest.raises(AuthError):
        auth_module.validate_token_string("")


# ---------------------------------------------------------------------------
# SI-10 — dev bypass stays double-gated
# ---------------------------------------------------------------------------


def test_disable_auth_alone_does_not_bypass(monkeypatch):
    """DISABLE_AUTH without DEBUG (prod-shaped config) must still 401
    when no token is presented."""
    settings = get_settings()
    monkeypatch.setattr(settings, "disable_auth", True, raising=False)
    monkeypatch.setattr(settings, "debug", False, raising=False)
    with pytest.raises(AuthError):
        auth_module.get_current_user(credentials=None)
