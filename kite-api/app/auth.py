"""
Clerk session-token verification.

Verifies Clerk-issued JWTs against the project's JWKS endpoint. Exposes
the same ``get_current_user`` interface the route layer has always
depended on, so swapping from the legacy NextAuth HS256 path is a
zero-touch change for endpoint signatures.

Also exposes ``require_admin``: a FastAPI dependency that 403s any
caller whose ``publicMetadata.role`` (surfaced via the ``metadata``
session-token claim configured in the Clerk dashboard) is not
``"admin"``.
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
# JWKS cache
# ---------------------------------------------------------------------------
#
# Clerk's JWKS rotates rarely. We cache for an hour. On a `kid` miss we
# force a re-fetch once before giving up — covers the rotation case.

_JWKS_CACHE_TTL_SECONDS = 3600
_JWKS_CACHE: dict[str, Any] = {"keys": None, "fetched_at": 0.0}


def _fetch_jwks(force: bool = False) -> dict:
    """Fetch (and cache) the Clerk JWKS."""
    settings = get_settings()
    now = time.time()
    cached_keys = _JWKS_CACHE["keys"]
    cached_at = _JWKS_CACHE["fetched_at"]

    if (
        not force
        and cached_keys is not None
        and now - cached_at < _JWKS_CACHE_TTL_SECONDS
    ):
        return cached_keys

    if not settings.clerk_jwks_url:
        raise AuthError("CLERK_JWKS_URL is not configured on the server")

    try:
        resp = httpx.get(settings.clerk_jwks_url, timeout=5.0)
        resp.raise_for_status()
        keys = resp.json()
    except Exception as exc:
        # If the upstream fetch fails but we have a stale cache, prefer that
        # over a hard 401 — better to keep serving than to take the whole
        # API down on a transient Clerk-side blip.
        if cached_keys is not None:
            return cached_keys
        raise AuthError(f"Unable to fetch Clerk JWKS: {exc}")

    _JWKS_CACHE["keys"] = keys
    _JWKS_CACHE["fetched_at"] = now
    return keys


def _find_signing_key(token: str) -> dict:
    """Locate the JWK matching the token's ``kid`` header."""
    try:
        headers = jwt.get_unverified_header(token)
    except JWTError as exc:
        raise AuthError(f"Malformed token header: {exc}")

    kid = headers.get("kid")
    if not kid:
        raise AuthError("Token header missing kid")

    # First look in the cache; on miss, force a refresh and try once more.
    for force in (False, True):
        jwks = _fetch_jwks(force=force)
        for key in jwks.get("keys", []):
            if key.get("kid") == kid:
                return key
    raise AuthError("Unable to find Clerk signing key (kid not in JWKS)")


# ---------------------------------------------------------------------------
# Token decode + role extraction
# ---------------------------------------------------------------------------


def decode_token(token: str) -> dict:
    """Verify a Clerk session JWT and return its payload."""
    settings = get_settings()

    if not settings.clerk_jwks_url or not settings.clerk_issuer:
        raise AuthError("Clerk auth is not configured on the server")

    try:
        key = _find_signing_key(token)
        payload = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            issuer=settings.clerk_issuer,
            options={
                # Clerk session tokens don't carry an `aud` claim by default
                "verify_aud": False,
            },
        )
        return payload
    except JWTError:
        raise AuthError("Invalid or expired token")


def _extract_role(payload: dict) -> str:
    """Pull ``role`` from the Clerk ``publicMetadata`` claim. Defaults to
    ``"client"`` if missing/unknown — defense in depth so a bad role string
    can never accidentally land us as ``"admin"``."""
    metadata = payload.get("metadata") or {}
    role = metadata.get("role")
    if role in ("admin", "client"):
        return role
    return "client"


# ---------------------------------------------------------------------------
# FastAPI dependencies
# ---------------------------------------------------------------------------


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> dict:
    """Validate the Clerk session token; raise on failure.

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

    payload = decode_token(credentials.credentials)

    sub = payload.get("sub")
    if not sub:
        raise AuthError("Token missing sub claim")

    return {
        "sub": sub,
        "role": _extract_role(payload),
        "metadata": payload.get("metadata") or {},
        "claims": payload,
        "source": "clerk",
    }


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
    see ``tasks/client_portal/TASKS.md``.
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
    payload = decode_token(token)
    sub = payload.get("sub")
    if not sub:
        raise AuthError("Token missing sub claim")
    return {
        "sub": sub,
        "role": _extract_role(payload),
        "metadata": payload.get("metadata") or {},
        "claims": payload,
        "source": "clerk_query_param",
    }
