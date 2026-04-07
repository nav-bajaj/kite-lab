"""Add open_positions table

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-07

Adds open_positions table for live portfolio tracking with real-time prices.
Unlike the holdings table (which stores backtest snapshots), this table
stores actual positions the user holds for live P&L tracking.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0002'
down_revision: Union[str, None] = '0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'open_positions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('universe', sa.String(length=20), nullable=False, server_default='nse500'),
        sa.Column('symbol', sa.String(length=50), nullable=False),
        sa.Column('instrument_token', sa.Integer(), nullable=True),
        sa.Column('qty', sa.Integer(), nullable=False),
        sa.Column('avg_price', sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column('entry_date', sa.Date(), nullable=True),
        sa.Column('last_price', sa.Numeric(precision=18, scale=4), nullable=True),
        sa.Column('prev_close', sa.Numeric(precision=18, scale=4), nullable=True),
        sa.Column('price_updated_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_open_positions_universe', 'open_positions', ['universe'])
    op.create_index('idx_open_positions_symbol', 'open_positions', ['symbol'])
    op.create_index('idx_open_positions_universe_symbol', 'open_positions', ['universe', 'symbol'], unique=True)


def downgrade() -> None:
    op.drop_table('open_positions')
