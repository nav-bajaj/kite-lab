"""
Email rendering and message assembly (tasks/email_channel Phase 2).

The send path itself is not exercised against a real SMTP server here —
that is the Phase 3 seed-inbox check. What matters at this level is that a
message cannot leave with a broken unsubscribe link, an unescaped token,
or a missing plaintext part.
"""
from __future__ import annotations

import os

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("ALLOWED_ORIGINS", "http://localhost:3000")

from app.config import get_settings  # noqa: E402
from app.services import email_service  # noqa: E402


# ---------------------------------------------------------------------------
# render()
# ---------------------------------------------------------------------------


def test_welcome_template_exists_and_renders():
    html, text = email_service.render(
        "welcome", {"unsubscribe_url": "https://marketworks.in/unsubscribe?token=abc"}
    )
    assert "marketworks" in html.lower()
    assert len(text) > 200          # a real plaintext part, not a stub
    assert "{{" not in html         # every placeholder consumed
    assert "{{" not in text


def test_render_escapes_into_html_but_not_text():
    evil = 'https://x.test/?a=1&b="><script>alert(1)</script>'
    html, text = email_service.render("welcome", {"unsubscribe_url": evil})
    assert "<script>" not in html
    assert "&lt;script&gt;" in html or "&amp;" in html
    assert "<script>" in text  # plaintext is not an HTML context


def test_render_refuses_unknown_token():
    with pytest.raises(email_service.EmailError):
        email_service.render("welcome", {"evil_token": "x"})


def test_render_refuses_missing_token():
    """A template whose placeholder we cannot fill must fail loudly rather
    than mail a literal {{unsubscribe_url}} to someone."""
    with pytest.raises(email_service.EmailError) as exc:
        email_service.render("welcome", {})
    assert "unsubscribe_url" in str(exc.value)


def test_render_refuses_unknown_template():
    with pytest.raises(email_service.EmailError):
        email_service.render("no_such_template", {})


# ---------------------------------------------------------------------------
# build_message()
# ---------------------------------------------------------------------------


def test_message_is_multipart_with_text_and_html():
    msg = email_service.build_message(
        to="a@b.co", subject="s", html_body="<p>hi</p>", text_body="hi"
    )
    types = {p.get_content_type() for p in msg.walk()}
    assert "text/plain" in types
    assert "text/html" in types


def test_one_click_unsubscribe_headers():
    """Gmail and Yahoo expect both headers for RFC 8058 one-click."""
    msg = email_service.build_message(
        to="a@b.co", subject="s", html_body="<p>hi</p>", text_body="hi",
        unsubscribe_url="https://api.test/api/waitlist/unsubscribe?token=t",
    )
    assert "https://api.test/api/waitlist/unsubscribe?token=t" in msg["List-Unsubscribe"]
    assert msg["List-Unsubscribe-Post"] == "List-Unsubscribe=One-Click"


def test_from_and_reply_to_are_set():
    settings = get_settings()
    msg = email_service.build_message(
        to="a@b.co", subject="s", html_body="<p>hi</p>", text_body="hi"
    )
    assert settings.email_from in msg["From"]
    assert msg["Reply-To"]  # replies must land somewhere; SES cannot receive


# ---------------------------------------------------------------------------
# send() safety
# ---------------------------------------------------------------------------


def test_send_is_a_noop_when_disabled():
    """email_enabled defaults False so no environment starts mailing people
    by accident."""
    settings = get_settings()
    assert settings.email_enabled is False
    msg = email_service.build_message(
        to="a@b.co", subject="s", html_body="<p>hi</p>", text_body="hi"
    )
    assert email_service.send(msg) is False


def test_send_returns_false_when_enabled_but_unconfigured(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "email_enabled", True)
    monkeypatch.setattr(settings, "smtp_host", "")
    msg = email_service.build_message(
        to="a@b.co", subject="s", html_body="<p>hi</p>", text_body="hi"
    )
    assert email_service.send(msg) is False


# ---------------------------------------------------------------------------
# link builders
# ---------------------------------------------------------------------------


def test_unsubscribe_links_point_at_the_right_hosts():
    """The visible link goes to the site page (which confirms first); the
    List-Unsubscribe header goes to the API, which accepts POST."""
    settings = get_settings()
    assert email_service.unsubscribe_url("tok").startswith(settings.public_site_url)
    assert "/unsubscribe?token=tok" in email_service.unsubscribe_url("tok")
    assert email_service.unsubscribe_post_url("tok").startswith(settings.public_api_url)
    assert "/api/waitlist/unsubscribe?token=tok" in email_service.unsubscribe_post_url("tok")


def test_unsubscribe_link_opts_out_of_ses_click_tracking():
    """SES click-tracking rewrites links through awstrack.me. Found in the
    first real send: it produced a double-encoded redirect that Gmail then
    wrapped again, and the link did not work.

    An unsubscribe link is a compliance mechanism, not a marketing metric —
    it must never be instrumented, and must never be broken by
    instrumentation. `ses:no-track` on the anchor opts it out.
    """
    html, _ = email_service.render(
        "welcome", {"unsubscribe_url": "https://marketworks.in/unsubscribe?token=t"}
    )
    # the attribute must sit on the SAME anchor as the unsubscribe href
    import re
    anchors = re.findall(r"<a\b[^>]*>", html, flags=re.S)
    unsub = [a for a in anchors if "unsubscribe" in a]
    assert unsub, "no unsubscribe anchor in the rendered welcome email"
    assert all("ses:no-track" in a for a in unsub), (
        "unsubscribe anchor lost its ses:no-track attribute — SES will "
        "rewrite the link and break it"
    )


def test_every_link_opts_out_of_ses_click_tracking():
    """Not just unsubscribe — EVERY link. The templates have to be immune
    to click tracking regardless of how the SES configuration set is set
    up, because a rewritten awstrack.me URL both breaks tokenised links
    and reads as phishing.
    """
    import re
    for template in ("welcome", "product-update"):
        html, _ = email_service.render(
            template, {"unsubscribe_url": "https://marketworks.in/unsubscribe?token=t"}
        )
        anchors = re.findall(r"<a\b[^>]*>", html, flags=re.S)
        assert anchors, f"{template}: no anchors at all"
        unprotected = [a for a in anchors if "ses:no-track" not in a]
        assert not unprotected, (
            f"{template}: {len(unprotected)} link(s) missing ses:no-track — "
            f"SES will rewrite them: {unprotected[:1]}"
        )
