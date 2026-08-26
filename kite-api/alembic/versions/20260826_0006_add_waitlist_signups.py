"""Add waitlist_signups table

Revision ID: 0006_waitlist
Revises: 0005
Create Date: 2026-08-26

Coming-soon waitlist storage (tasks/site_gate). Public POST /api/waitlist
inserts here; admin GET reads it. No email sending.

Revision id is deliberately '0006_waitlist' rather than '0006': the
insights_dashboard_v2 branch already carries a '0006' (users table) off the
same '0005' parent, and distinct ids keep branch convergence a standard
two-head ``alembic merge`` instead of a duplicate-revision error.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0006_waitlist'
down_revision: Union[str, None] = '0005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Idempotent: Railway runs `alembic upgrade head` on every deploy and
    # this table may already exist from a prior partial run.
    bind = op.get_bind()
    if sa.inspect(bind).has_table("waitlist_signups"):
        return

    op.create_table(
        'waitlist_signups',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=320), nullable=False),
        sa.Column(
            'source', sa.String(length=50), nullable=False,
            server_default='coming_soon',
        ),
        sa.Column(
            'created_at', sa.DateTime(timezone=True), nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        op.f('ix_waitlist_signups_email'),
        'waitlist_signups', ['email'], unique=True,
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_waitlist_signups_email'), table_name='waitlist_signups')
    op.drop_table('waitlist_signups')
