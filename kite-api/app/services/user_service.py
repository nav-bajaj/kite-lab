"""
Lazy user provisioning (auth_stack_v2 B1.7, SI-9).

``provision_user`` upserts a ``users`` row keyed by the verified token's
``sub`` the first time a caller is seen, then re-touches ``last_seen_at``
at most once per TTL window (in-process cache keeps the hot path free of
DB writes).

FAIL-OPEN by design: authentication and authorization never depend on
this table — the role comes from the verified token — so any DB failure
here is logged and swallowed. The (future) entitlements layer reads this
table through its own fail-closed dependency.
"""

from __future__ import annotations

import logging
import time

from sqlalchemy.exc import IntegrityError

logger = logging.getLogger(__name__)

_SEEN_TTL_SECONDS = 15 * 60
_SEEN_CACHE: dict[str, float] = {}


def _session_factory():
    """Indirection point — patched in tests."""
    from app.models.database import get_session_local

    return get_session_local()


def provision_user(user: dict) -> None:
    """Ensure a ``users`` row exists for the authenticated caller.

    ``user`` is the dict returned by ``app.auth.get_current_user`` /
    ``validate_token_string``. Never raises.
    """
    source = user.get("source") or ""
    if source == "dev_bypass":
        return
    sub = user.get("sub")
    if not sub:
        return

    now = time.time()
    last = _SEEN_CACHE.get(sub)
    if last is not None and now - last < _SEEN_TTL_SECONDS:
        return

    provider = "clerk" if source.startswith("clerk") else "supabase"
    email = (user.get("claims") or {}).get("email")

    try:
        factory = _session_factory()
        with factory() as db:
            from sqlalchemy.sql import func

            from app.models.models import User

            row = db.query(User).filter_by(sub=sub).one_or_none()
            if row is None:
                db.add(User(sub=sub, email=email, provider=provider))
                try:
                    db.commit()
                except IntegrityError:
                    # Concurrent first-sighting — the other writer won.
                    db.rollback()
                    row = db.query(User).filter_by(sub=sub).one_or_none()
                    if row is not None:
                        row.last_seen_at = func.now()
                        db.commit()
            else:
                row.last_seen_at = func.now()
                if email and row.email != email:
                    row.email = email
                db.commit()
        _SEEN_CACHE[sub] = now
    except Exception as exc:
        # Fail-open: provisioning must never break auth (see docstring).
        # Log the exception TYPE only — SQLAlchemy error text embeds the
        # statement and bound params (user email = PII, R-012).
        logger.warning(
            "user provisioning skipped for %s: %s", sub, type(exc).__name__
        )
