"""
Shared Supabase test-token plumbing.

Extracted at auth_stack_v2 E3. Before that, test_private_mode.py and
test_waitlist.py authenticated with Clerk-shaped RS256 tokens, which
worked only because the Clerk verification path was still mounted.
Removing that path broke 62 tests across the two suites at once — a good
signal that the fixture belonged in one place rather than copied into
each suite that needed an authenticated caller.

Everything here mints ES256 tokens against a locally generated P-256 key
and serves the matching JWKS from the auth module's cache, so no test
ever touches the network.
"""

from __future__ import annotations

import base64
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec
from jose import jwt as jose_jwt

TEST_SUPABASE_ISSUER = "https://testproject.supabase.co/auth/v1"
TEST_SUPABASE_JWKS_URL = f"{TEST_SUPABASE_ISSUER}/.well-known/jwks.json"
TEST_KID = "sb-test-key-id"


def generate_keypair():
    return ec.generate_private_key(ec.SECP256R1())


def _b64url(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode("ascii")


def jwks_for(keypair, kid: str = TEST_KID) -> dict:
    pub = keypair.public_key().public_numbers()
    return {
        "keys": [
            {
                "kty": "EC",
                "crv": "P-256",
                "use": "sig",
                "alg": "ES256",
                "kid": kid,
                "x": _b64url(pub.x.to_bytes(32, "big")),
                "y": _b64url(pub.y.to_bytes(32, "big")),
            }
        ]
    }


def private_pem(keypair) -> str:
    return keypair.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()


def make_token(keypair, role: str | None, *, kid: str = TEST_KID, **overrides: Any) -> str:
    """Sign a Supabase-shaped access token.

    ``role=None`` omits the key from app_metadata, which is what a freshly
    created user actually looks like — the backend must read that as
    ``client``, never as admin.
    """
    now = datetime.now(tz=timezone.utc)
    app_metadata: dict[str, Any] = {"provider": "email", "providers": ["email"]}
    if role is not None:
        app_metadata["role"] = role
    claims: dict[str, Any] = {
        "sub": f"00000000-0000-4000-8000-{(role or 'norole'):>012}"[:36],
        "iss": TEST_SUPABASE_ISSUER,
        "aud": "authenticated",
        # PostgREST's own role claim. Deliberately set to something that is
        # NOT the app role, so a suite that accidentally starts trusting it
        # fails loudly (SI-1).
        "role": "authenticated",
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=1)).timestamp()),
        "email": f"{role or 'norole'}@test.local",
        "app_metadata": app_metadata,
        "user_metadata": {},
        "session_id": "test-session",
    }
    claims.update(overrides)
    return jose_jwt.encode(
        claims, private_pem(keypair), algorithm="ES256", headers={"kid": kid}
    )


def install_jwks(auth_module, keypair, monkeypatch) -> None:
    """Seed the JWKS cache and make any real network fetch a hard failure."""
    auth_module._JWKS_CACHES[TEST_SUPABASE_JWKS_URL] = {
        "keys": jwks_for(keypair),
        "fetched_at": time.time(),
    }

    def _no_network(*_args, **_kwargs):
        raise AssertionError("Test attempted a real JWKS fetch")

    monkeypatch.setattr("httpx.get", _no_network)


def clear_jwks(auth_module) -> None:
    auth_module._JWKS_CACHES.clear()
