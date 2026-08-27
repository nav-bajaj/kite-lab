"""Add consent lifecycle columns to waitlist_signups

Revision ID: 0007_waitlist_consent
Revises: 0006_waitlist
Create Date: 2026-08-27

Extends the site_gate waitlist table with the state an email channel
needs (tasks/email_channel Phase 1): a status lifecycle, single-use
confirm and long-lived unsubscribe tokens, and send bookkeeping.

Deliberately does NOT store consent IP or user-agent. Under double
opt-in the confirmation click plus `confirmed_at` is the consent
evidence; an IP would add personal data to a table already flagged for
PII (R-027) while adding little. Keep the PII surface to the address
itself.

Adding the columns now, before Phase 2 needs them, avoids a second
migration against a live table.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0007_waitlist_consent'
down_revision: Union[str, None] = '0006_waitlist'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# status values, mirrored in app/api/waitlist.py
_STATUSES = ("pending", "confirmed", "unsubscribed", "bounced", "complained")


def _has_column(bind, table: str, column: str) -> bool:
    return column in {c["name"] for c in sa.inspect(bind).get_columns(table)}


def upgrade() -> None:
    bind = op.get_bind()
    if not sa.inspect(bind).has_table("waitlist_signups"):
        # Nothing to extend — 0006 will have created it on a fresh DB.
        return

    add = [
        ("status", sa.Column("status", sa.String(length=20), nullable=False,
                             server_default="pending")),
        ("confirm_token", sa.Column("confirm_token", sa.String(length=64), nullable=True)),
        ("confirm_sent_at", sa.Column("confirm_sent_at", sa.DateTime(timezone=True), nullable=True)),
        ("confirmed_at", sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True)),
        ("unsubscribe_token", sa.Column("unsubscribe_token", sa.String(length=64), nullable=True)),
        ("unsubscribed_at", sa.Column("unsubscribed_at", sa.DateTime(timezone=True), nullable=True)),
        ("welcome_sent_at", sa.Column("welcome_sent_at", sa.DateTime(timezone=True), nullable=True)),
        ("last_sent_at", sa.Column("last_sent_at", sa.DateTime(timezone=True), nullable=True)),
    ]
    for name, col in add:
        if not _has_column(bind, "waitlist_signups", name):
            op.add_column("waitlist_signups", col)

    existing = {i["name"] for i in sa.inspect(bind).get_indexes("waitlist_signups")}
    if "ix_waitlist_signups_status" not in existing:
        op.create_index("ix_waitlist_signups_status", "waitlist_signups", ["status"])
    if "ix_waitlist_signups_confirm_token" not in existing:
        op.create_index("ix_waitlist_signups_confirm_token", "waitlist_signups",
                        ["confirm_token"], unique=True)
    if "ix_waitlist_signups_unsubscribe_token" not in existing:
        op.create_index("ix_waitlist_signups_unsubscribe_token", "waitlist_signups",
                        ["unsubscribe_token"], unique=True)


def downgrade() -> None:
    for idx in ("ix_waitlist_signups_unsubscribe_token",
                "ix_waitlist_signups_confirm_token",
                "ix_waitlist_signups_status"):
        op.drop_index(idx, table_name="waitlist_signups")
    for col in ("last_sent_at", "welcome_sent_at", "unsubscribed_at",
                "unsubscribe_token", "confirmed_at", "confirm_sent_at",
                "confirm_token", "status"):
        op.drop_column("waitlist_signups", col)
