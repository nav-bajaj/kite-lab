"""Merge the auth_stack_v2 and email_channel migration branches

Revision ID: 0008_merge
Revises: 0006, 0007_waitlist_consent
Create Date: 2026-09-03

Both lines branched from 0005 independently:

    0005 ─┬─ 0006                 (users table, auth_stack_v2)
          └─ 0006_waitlist ─ 0007_waitlist_consent  (email_channel)

Leaving two heads makes `alembic upgrade head` fail with "Multiple head
revisions", which the Railway entrypoint runs on every deploy — so the
service would refuse to start.

This is an empty merge point. Both parents create different tables and
touch nothing in common, so there is no data reconciliation to do; the
merge exists purely to give the graph a single head again.

The two lines were deliberately given distinct revision ids rather than
both claiming '0006', which is what makes this a routine merge instead of
a duplicate-revision error.
"""
from typing import Sequence, Union


revision: str = '0008_merge'
down_revision: Union[str, Sequence[str], None] = ('0006', '0007_waitlist_consent')
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
