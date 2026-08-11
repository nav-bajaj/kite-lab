"""Add users table (auth_stack_v2 lazy provisioning)

Revision ID: 0006
Revises: 0005
Create Date: 2026-08-11

App-side user rows keyed by the auth provider's ``sub``, lazily
upserted on first authenticated request (``app/services/user_service.py``,
SI-9 in ``tasks/auth_stack_v2/PLAN.md``). Roles stay in the token; the
entitlements initiative will reference this table.

Idempotent (checks for the table first): security-reviewer 2026-08-11
finding #3 — without this migration the fail-open provisioning would
silently no-op in production, since ``init_db()`` is never called at
runtime and deploy runs ``alembic upgrade head``.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0006'
down_revision: Union[str, None] = '0005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if sa.inspect(bind).has_table('users'):
        return
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('sub', sa.String(length=64), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('provider', sa.String(length=30), nullable=False,
                  server_default='supabase'),
        sa.Column('first_seen_at', sa.DateTime(), nullable=False,
                  server_default=sa.func.now()),
        sa.Column('last_seen_at', sa.DateTime(), nullable=False,
                  server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('sub'),
    )
    op.create_index('ix_users_sub', 'users', ['sub'])


def downgrade() -> None:
    op.drop_index('ix_users_sub', table_name='users')
    op.drop_table('users')
