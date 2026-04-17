"""Add trade_matches table

Revision ID: 0004
Revises: 0003
Create Date: 2026-04-17

Adds trade_matches table linking SELL trades to their opening BUY trades
via FIFO matching. Enables per-trade realized P&L display on the Trades tab.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0004'
down_revision: Union[str, None] = '0003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'trade_matches',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('universe', sa.String(length=20), nullable=False),
        sa.Column('buy_trade_id', sa.Integer(), nullable=False),
        sa.Column('sell_trade_id', sa.Integer(), nullable=False),
        sa.Column('symbol', sa.String(length=50), nullable=False),
        sa.Column('shares_matched', sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column('entry_date', sa.Date(), nullable=False),
        sa.Column('exit_date', sa.Date(), nullable=False),
        sa.Column('entry_price', sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column('exit_price', sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column('holding_days', sa.Integer(), nullable=False),
        sa.Column('realized_pnl', sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column('realized_pnl_pct', sa.Numeric(precision=12, scale=6), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['buy_trade_id'], ['trades.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['sell_trade_id'], ['trades.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('idx_trade_matches_universe', 'trade_matches', ['universe'])
    op.create_index('idx_trade_matches_sell', 'trade_matches', ['sell_trade_id'])
    op.create_index('idx_trade_matches_buy', 'trade_matches', ['buy_trade_id'])
    op.create_index('idx_trade_matches_universe_symbol', 'trade_matches', ['universe', 'symbol'])


def downgrade() -> None:
    op.drop_index('idx_trade_matches_universe_symbol', table_name='trade_matches')
    op.drop_index('idx_trade_matches_buy', table_name='trade_matches')
    op.drop_index('idx_trade_matches_sell', table_name='trade_matches')
    op.drop_index('idx_trade_matches_universe', table_name='trade_matches')
    op.drop_table('trade_matches')
