"""
Outbound email (tasks/email_channel Phase 2).

Loads the static HTML+text that React Email exported into app/emails/,
substitutes a CLOSED set of HTML-escaped tokens, and hands the result to
AWS SES over SMTP.

Two deliberate choices, both explained in tasks/email_channel/PLAN.md:

  * stdlib smtplib, not boto3 — sending needs no new dependency, and
    R-018 (dependency CVE surface) is an open High row.
  * Substitution is a closed token map, never a templating language.
    React-Email escaping and a template engine's escaping do not compose;
    running Jinja over exported HTML would be an injection vector in
    outbound mail. If a template ever needs a loop or a conditional, that
    is the signal to move rendering to a Node service — not to grow a
    dialect here.
"""
from __future__ import annotations

import html
import logging
import re
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr
from pathlib import Path
from typing import Mapping

from app.config import get_settings

logger = logging.getLogger(__name__)

TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "emails"

# Only these may appear as {{token}} in an exported template. A template
# containing anything else is a bug — fail loudly rather than mail a
# literal "{{whatever}}" to a real person.
ALLOWED_TOKENS = frozenset({"unsubscribe_url", "preferences_url"})

_TOKEN_RE = re.compile(r"\{\{(\w+)\}\}")


class EmailError(RuntimeError):
    """Raised for configuration and template problems — never for a
    transient SMTP failure, which callers handle separately."""


def render(template: str, tokens: Mapping[str, str]) -> tuple[str, str]:
    """Return (html, text) for `template` with tokens substituted.

    Values are HTML-escaped for the HTML part and left raw for the text
    part. Raises if the template carries a token we were not given, so a
    dead unsubscribe link cannot reach an inbox.
    """
    unknown = set(tokens) - ALLOWED_TOKENS
    if unknown:
        raise EmailError(f"Tokens not in the allowlist: {sorted(unknown)}")

    html_path = TEMPLATE_DIR / f"{template}.html"
    text_path = TEMPLATE_DIR / f"{template}.txt"
    if not html_path.is_file() or not text_path.is_file():
        raise EmailError(
            f"Template '{template}' is missing. Run `npm run emails:export` "
            f"in kite-dashboard and commit the output."
        )

    raw_html = html_path.read_text(encoding="utf-8")
    raw_text = text_path.read_text(encoding="utf-8")

    present = set(_TOKEN_RE.findall(raw_html)) | set(_TOKEN_RE.findall(raw_text))
    missing = present - set(tokens)
    if missing:
        raise EmailError(
            f"Template '{template}' needs tokens that were not supplied: "
            f"{sorted(missing)}"
        )

    def _sub(source: str, escape: bool) -> str:
        def repl(m: re.Match) -> str:
            value = tokens[m.group(1)]
            return html.escape(value, quote=True) if escape else value

        return _TOKEN_RE.sub(repl, source)

    return _sub(raw_html, escape=True), _sub(raw_text, escape=False)


def build_message(
    *,
    to: str,
    subject: str,
    html_body: str,
    text_body: str,
    unsubscribe_url: str | None = None,
) -> EmailMessage:
    """Assemble a multipart/alternative message.

    Plain text is set first and HTML added as the alternative, which is the
    order clients expect. An HTML-only message takes a real spam-score
    penalty, so the text part is not optional.
    """
    settings = get_settings()
    msg = EmailMessage()
    msg["From"] = formataddr((settings.email_from_name, settings.email_from))
    msg["To"] = to
    msg["Subject"] = subject
    msg["Reply-To"] = settings.email_reply_to or settings.email_from

    if unsubscribe_url:
        # RFC 8058 one-click. Gmail and Yahoo expect both headers, and the
        # URL must accept an unauthenticated POST — see the unsubscribe
        # endpoint in app/api/waitlist.py.
        msg["List-Unsubscribe"] = (
            f"<{unsubscribe_url}>, <mailto:{settings.email_from}?subject=unsubscribe>"
        )
        msg["List-Unsubscribe-Post"] = "List-Unsubscribe=One-Click"

    msg.set_content(text_body)
    msg.add_alternative(html_body, subtype="html")
    return msg


def send(msg: EmailMessage) -> bool:
    """Deliver via SES SMTP. Returns True on success.

    Never raises on a transient failure: the caller is usually a signup
    request, and a person who just handed us their address should not see
    an error because our mail relay blinked.
    """
    settings = get_settings()

    if not settings.email_enabled:
        logger.info(
            "email disabled — not sending %r to %s",
            msg["Subject"], msg["To"],
        )
        return False

    if not (settings.smtp_host and settings.smtp_user and settings.smtp_password):
        logger.error("email enabled but SMTP is not configured; dropping message")
        return False

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as s:
            s.starttls(context=context)
            s.login(settings.smtp_user, settings.smtp_password)
            s.send_message(msg)
        logger.info("sent %r to %s", msg["Subject"], msg["To"])
        return True
    except Exception:
        # Log the exception but not the recipient's address at ERROR level
        # any more than necessary — this line already carries it once.
        logger.exception("SMTP send failed for %s", msg["To"])
        return False


# ---------------------------------------------------------------------------
# Link builders — one place, so a malformed unsubscribe URL is one bug
# ---------------------------------------------------------------------------


def unsubscribe_url(token: str) -> str:
    """Human-facing page. Confirms before acting."""
    return f"{get_settings().public_site_url}/unsubscribe?token={token}"


def unsubscribe_post_url(token: str) -> str:
    """Machine-facing endpoint for the List-Unsubscribe header. Must accept
    POST without auth — mail clients call it directly."""
    return f"{get_settings().public_api_url}/api/waitlist/unsubscribe?token={token}"


def confirm_url(token: str) -> str:
    return f"{get_settings().public_site_url}/confirm?token={token}"


# ---------------------------------------------------------------------------
# The one message we send today
# ---------------------------------------------------------------------------

WELCOME_SUBJECT = "You're on the Marketworks waitlist"


def send_welcome(*, to: str, unsubscribe_token: str) -> bool:
    """Render and send the welcome mail. Returns True if SES accepted it."""
    html_body, text_body = render(
        "welcome", {"unsubscribe_url": unsubscribe_url(unsubscribe_token)}
    )
    msg = build_message(
        to=to,
        subject=WELCOME_SUBJECT,
        html_body=html_body,
        text_body=text_body,
        unsubscribe_url=unsubscribe_post_url(unsubscribe_token),
    )
    return send(msg)
