"""
Session-token verification — Supabase Auth (primary) + Clerk (until the
auth_stack_v2 Phase 4 cutover removes it).

Verification is issuer-routed: the token's (unverified) ``iss`` selects
which fully-pinned path verifies it. Each path has its own JWKS URL,
allowed algorithm, audience policy, and role-claim location; a token
whose issuer matches neither configured provider is rejected outright.

  Supabase  ES256, aud="authenticated" enforced, role from the
            server-controlled ``app_metadata.role`` claim. The
            client-editable ``user_metadata`` and PostgREST's native
            ``role`` claim NEVER influence authz (SI-1 in
            tasks/auth_stack_v2/PLAN.md).
  Clerk     RS256, no aud (Clerk session tokens carry none), role from
            the ``metadata`` claim (publicMetadata via dashboard
            mapping).

Exposes the same ``get_current_user`` dict shape the route layer has
always depended on: {sub, role, metadata, claims, source}.
"""

import time
from typing import Any, Optional

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.config import get_settings


# Security scheme for Swagger UI + Authorization header extraction.
security = HTTPBearer(auto_error=False)


class AuthError(HTTPException):
    """401 — no/invalid/expired token."""

    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class ForbiddenError(HTTPException):
    """403 — token is valid but the caller lacks the required role."""

    def __init__(self, detail: str):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
        )


# ---------------------------------------------------------------------------
# JWKS cache — one entry per JWKS URL (two providers during transition)
# ---------------------------------------------------------------------------
#
# Signing keys rotate rarely. Cache for an hour per URL; on a `kid` miss
# force one re-fetch before giving up — covers the rotation case. On a
# fetch failure prefer a stale cache over a hard 401 so a transient
# provider-side blip doesn't take the whole API down.

_JWKS_CACHE_TTL_SECONDS = 3600
_JWKS_CACHES: dict[str, dict[str, Any]] = {}


def _fetch_jwks(url: str, force: bool = False) -> dict:
    """Fetch (and cache) the JWKS document at ``url``."""
    if not url:
        raise AuthError("Auth JWKS URL is not configured on the server")

    now = time.time()
    entry = _JWKS_CACHES.get(url)

    if (
        not force
        and entry is not None
        and entry["keys"] is not None
        and now - entry["fetched_at"] < _JWKS_CACHE_TTL_SECONDS
    ):
        return entry["keys"]

    try:
        resp = httpx.get(url, timeout=5.0)
        resp.raise_for_status()
        keys = resp.json()
    except Exception as exc:
        if entry is not None and entry["keys"] is not None:
            return entry["keys"]
        raise AuthError(f"Unable to fetch JWKS: {exc}")

    _JWKS_CACHES[url] = {"keys": keys, "fetched_at": now}
    return keys


def _find_signing_key(token: str, jwks_url: str) -> dict:
    """Locate the JWK matching the token's ``kid`` header."""
    try:
        headers = jwt.get_unverified_header(token)
    except JWTError as exc:
        raise AuthError(f"Malformed token header: {exc}")

    kid = headers.get("kid")
    if not kid:
        raise AuthError("Token header missing kid")

    for force in (False, True):
        jwks = _fetch_jwks(jwks_url, force=force)
        for key in jwks.get("keys", []):
            if key.get("kid") == kid:
                return key
    raise AuthError("Unable to find signing key (kid not in JWKS)")


# ---------------------------------------------------------------------------
# Issuer routing + per-provider decode
# ---------------------------------------------------------------------------


def _token_issuer(token: str) -> str:
    try:
        return jwt.get_unverified_claims(token).get("iss") or ""
    except JWTError as exc:
        raise AuthError(f"Malformed token: {exc}")


def _decode_supabase(token: str) -> dict:
    """Verify a Supabase access token. ES256 only (the project's
    promoted signing key), issuer pinned, aud enforced."""
    settings = get_settings()
    key = _find_signing_key(token, settings.supabase_jwks_url)
    try:
        return jwt.decode(
            token,
            key,
            algorithms=["ES256"],
            issuer=settings.supabase_issuer,
            audience="authenticated",
            # python-jose only checks aud when the claim exists — require
            # it, else a token with no aud at all would verify.
            options={"require_aud": True},
        )
    except JWTError:
        raise AuthError("Invalid or expired token")


def _decode_clerk(token: str) -> dict:
    """Verify a Clerk session JWT. RS256 only, issuer pinned; Clerk
    session tokens carry no aud claim."""
    settings = get_settings()
    key = _find_signing_key(token, settings.clerk_jwks_url)
    try:
        return jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            issuer=settings.clerk_issuer,
            options={"verify_aud": False},
        )
    except JWTError:
        raise AuthError("Invalid or expired token")


def decode_token(token: str) -> tuple[dict, str]:
    """Verify a session JWT; return ``(payload, provider)`` where
    provider is ``"supabase"`` or ``"clerk"``.

    The unverified ``iss`` only ROUTES; the selected path then verifies
    signature + issuer + expiry (+ audience on Supabase), so a lying
    ``iss`` fails inside the path it routed to.
    """
    settings = get_settings()
    issuer = _token_issuer(token)

    if settings.supabase_issuer and issuer == settings.supabase_issuer:
        return _decode_supabase(token), "supabase"
    if settings.clerk_issuer and issuer == settings.clerk_issuer:
        return _decode_clerk(token), "clerk"

    raise AuthError("Token issuer not recognized")


def _extract_role(payload: dict, provider: str) -> str:
    """Pull the app role from the provider's server-controlled claim.
    Defaults to ``"client"`` on anything missing/unknown — defense in
    depth so a bad role string can never accidentally land as admin.

    Supabase: ``app_metadata.role`` ONLY. ``user_metadata`` is
    end-user-editable and PostgREST's native ``role`` claim is
    infrastructure plumbing — neither is consulted (SI-1).
    Clerk: ``metadata.role`` (publicMetadata session-claim mapping).
    """
    if provider == "supabase":
        metadata = payload.get("app_metadata") or {}
    else:
        metadata = payload.get("metadata") or {}
    role = metadata.get("role")
    if role in ("admin", "client"):
        return role
    return "client"


def _user_dict(payload: dict, provider: str, source: str) -> dict:
    sub = payload.get("sub")
    if not sub:
        raise AuthError("Token missing sub claim")
    if provider == "supabase":
        metadata = payload.get("app_metadata") or {}
    else:
        metadata = payload.get("metadata") or {}
    return {
        "sub": sub,
        "role": _extract_role(payload, provider),
        "metadata": metadata,
        "claims": payload,
        "source": source,
    }


def _provision(user: dict) -> None:
    """Lazy user-row upsert (B1.7). Fail-open inside the service — a DB
    problem must never turn into a 401/403."""
    from app.services.user_service import provision_user

    provision_user(user)


# ---------------------------------------------------------------------------
# FastAPI dependencies
# ---------------------------------------------------------------------------


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> dict:
    """Validate the session token; raise on failure.

    Returns a dict with: sub, role, metadata, claims, source.
    """
    settings = get_settings()

    # Dev-only bypass — guarded by BOTH DEBUG and DISABLE_AUTH so it
    # cannot be flipped on in production by accident.
    if settings.disable_auth and settings.debug:
        return {
            "sub": "dev-user",
            "email": "dev@localhost",
            "role": "admin",  # Dev bypass has admin rights
            "metadata": {"role": "admin"},
            "claims": {},
            "source": "dev_bypass",
        }

    if credentials is None:
        raise AuthError("Missing authentication token")

    payload, provider = decode_token(credentials.credentials)
    user = _user_dict(payload, provider, source=provider)
    _provision(user)
    return user


def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[dict]:
    """Return current user if authenticated, else None.

    Used by endpoints (e.g. SSE) that accept an optional token.
    """
    if credentials is None:
        return None
    try:
        return get_current_user(credentials)
    except (AuthError, ForbiddenError):
        return None


def require_admin(user: dict = Depends(get_current_user)) -> dict:
    """Require the caller to have ``role == "admin"``.

    Any other role (including the default ``"client"``) gets a 403.
    Use this on every mutation / admin / engine endpoint. Inventory:
    see ``tests/test_supabase_authz.py``.
    """
    if user.get("role") != "admin":
        raise ForbiddenError("Admin role required")
    return user


# ---------------------------------------------------------------------------
# Universe access (R-022 defense in depth)
# ---------------------------------------------------------------------------
#
# The frontend universe selector filters to the 4 production products for
# client-role users (see ``kite-dashboard/src/lib/universes.ts``). Without
# the check below, a determined client could still craft a request like
# ``GET /api/portfolio?universe=nse500`` directly via DevTools and bypass
# the UI filter. The data isn't secret, but it's a UX-consistency hole
# and tracked as register row R-022.

CLIENT_VISIBLE_UNIVERSES = frozenset({
    "om25_v3",        # Quality Momentum
    "tl25_v3",        # Trend Leaders
    "l6_v2",          # Core Momentum
    "combo_defensive",  # Defensive Blend
})

# Admin-only legacy research universes (kept here as a constant for clarity
# but not actually used — the check below just verifies membership in
# CLIENT_VISIBLE_UNIVERSES for non-admin callers, so any new universe added
# to ``app/config.py:UNIVERSES`` is admin-only by default unless explicitly
# tagged client-visible above.)
ADMIN_ONLY_UNIVERSES = frozenset({"nse500", "nifty100", "nifty250"})


def check_universe_access(universe: str, user: dict) -> None:
    """Raise 403 if the caller doesn't have access to the universe.

    Admin role: all universes. Client role: only the 4 production products
    in ``CLIENT_VISIBLE_UNIVERSES``. Anything else from a non-admin caller
    is refused.

    Closes R-022 in ``docs/security/risk-register.md``.
    """
    if user.get("role") == "admin":
        return
    if universe not in CLIENT_VISIBLE_UNIVERSES:
        raise ForbiddenError(
            f"Universe '{universe}' is not available to your role"
        )


# Convenience aliases — back-compat with existing imports.
require_auth = Depends(get_current_user)
optional_auth = Depends(get_optional_user)


def validate_token_string(token: str) -> dict:
    """Validate a raw JWT string (used by SSE endpoints that can't send
    Authorization headers and pass the token via query param instead).

    Returns the same dict shape as ``get_current_user``.
    """
    if not token:
        raise AuthError("Missing authentication token")
    payload, provider = decode_token(token)
    user = _user_dict(payload, provider, source=f"{provider}_query_param")
    _provision(user)
    return user
