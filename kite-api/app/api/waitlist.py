"""
Waitlist endpoints (tasks/site_gate).

POST /api/waitlist is public BY DESIGN (risk register R-027): while the
site shows the under-development page, anonymous visitors leave an email
to be notified at launch. Storage only — no email sending here.

Not under /api/system/* — that router is reserved for Zerodha OAuth
bootstrap (AD-1, R-003).
"""
import re

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from slowapi.util import get_remote_address
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth import require_admin
from app.middleware.rate_limiter import limiter
from app.models.database import get_db
from app.models.models import WaitlistSignup

router = APIRouter(prefix="/api/waitlist", tags=["waitlist"])

# Deliberately a permissive shape check, not full RFC validation: we store
# the address, we never deliver to it, and the unique index makes junk
# self-limiting. Avoids adding email-validator to the pip-audit surface.
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

_ALLOWED_SOURCES = frozenset({"coming_soon"})

_OK = {"status": "ok"}


def _waitlist_key(request: Request) -> str:
    """Rate-limit key for the public POST.

    uvicorn runs without --proxy-headers behind Railway's edge, so
    request.client.host is the proxy for every caller — a plain per-IP
    limit would be one global bucket. Railway sets X-Forwarded-For; a
    direct client can spoof it, so this is best-effort abuse damping, not
    a security control (the unique email index bounds real damage, and
    the global 60/min default still applies). See R-027.
    """
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return get_remote_address(request)


class WaitlistRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    source: str = Field(default="coming_soon", max_length=50)
    # Honeypot: real users never fill this hidden field.
    website: str = Field(default="", max_length=200)


@router.post("")  # nosemgrep: tools.security.fastapi-route-missing-auth  # public by design — R-027
@limiter.limit("10/hour", key_func=_waitlist_key)
async def join_waitlist(
    request: Request,
    body: WaitlistRequest,
    db: Session = Depends(get_db),
):
    """Add an email to the launch waitlist. Idempotent 200 in every
    accepted case (new, duplicate, honeypot) so responses never act as an
    email-enumeration oracle."""
    email = body.email.strip().lower()
    if not _EMAIL_RE.match(email):
        raise HTTPException(status_code=422, detail="Enter a valid email address")
    if body.source not in _ALLOWED_SOURCES:
        raise HTTPException(status_code=422, detail="Unknown source")

    if body.website:
        # Bot filled the honeypot — pretend success, write nothing.
        return _OK

    db.add(WaitlistSignup(email=email, source=body.source))
    try:
        db.commit()
    except IntegrityError:
        db.rollback()  # already on the list — same response as new
    return _OK


@router.get("")
async def list_waitlist(
    limit: int = 500,
    db: Session = Depends(get_db),
    user: dict = Depends(require_admin),
):
    """Admin-only readout of the waitlist, newest first."""
    limit = max(1, min(limit, 5000))
    rows = (
        db.query(WaitlistSignup)
        .order_by(WaitlistSignup.created_at.desc())
        .limit(limit)
        .all()
    )
    return {
        "count": db.query(WaitlistSignup).count(),
        "signups": [
            {
                "email": r.email,
                "source": r.source,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ],
    }
