"""Add proposed_rebalances table

Revision ID: 0005
Revises: 0004
Create Date: 2026-06-26

Stores the EOD engine readout for the upcoming rebalance (membership-only:
SELL = full exit, BUY = new entry to target weight, HOLD = continuing).
Populated by ``data_pipeline/eod_proposal.py`` and synced by
``sync_service.sync_proposed_rebalance``. The rebalance page reads the
latest row per universe to render the "Actionable trades" card —
see ``tasks/rebalance_page/PLAN.md`` Phase 2 §1.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision: str = '0005'
down_revision: Union[str, None] = '0004'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'proposed_rebalances',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('universe', sa.String(length=20), nullable=False),
        sa.Column('exec_date', sa.Date(), nullable=False),
        sa.Column('signal_date', sa.Date(), nullable=False),
        sa.Column('data_as_of', sa.Date(), nullable=False),
        sa.Column('sell_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('buy_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('hold_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('sells', JSONB(), nullable=True),
        sa.Column('buys', JSONB(), nullable=True),
        sa.Column('holds', JSONB(), nullable=True),
        sa.Column('regime', sa.String(length=10), nullable=True),
        sa.Column('drawdown_from_peak', sa.Numeric(precision=18, scale=10), nullable=True),
        sa.Column('final_pv', sa.Numeric(precision=18, scale=4), nullable=True),
        sa.Column('initial_capital', sa.Numeric(precision=18, scale=4), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(
        'idx_proposed_rebalances_universe_exec',
        'proposed_rebalances', ['universe', 'exec_date'], unique=True,
    )
    op.create_index(
        'idx_proposed_rebalances_exec',
        'proposed_rebalances', ['exec_date'],
    )
    # `universe` benefits from its own index for the API's "latest by universe"
    # read. SQLAlchemy emits this implicitly from the column's index=True flag.
    op.create_index(
        op.f('ix_proposed_rebalances_universe'),
        'proposed_rebalances', ['universe'],
    )


def downgrade() -> None:
    op.drop_index(op.f('ix_proposed_rebalances_universe'),
                  table_name='proposed_rebalances')
    op.drop_index('idx_proposed_rebalances_exec',
                  table_name='proposed_rebalances')
    op.drop_index('idx_proposed_rebalances_universe_exec',
                  table_name='proposed_rebalances')
    op.drop_table('proposed_rebalances')
