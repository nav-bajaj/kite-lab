"""Initial tables

Revision ID: 0001
Revises:
Create Date: 2026-02-10

Creates all initial tables for Kite-Lab API:
- allowed_users: User whitelist for authentication
- trades: Trade history for all universes
- equity_curve: Daily portfolio values
- holdings: Portfolio holdings snapshots
- metrics: Performance metrics
- rebalances: Weekly rebalance events
- signals: Momentum signal rankings
- jobs: Background job history
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # allowed_users table
    op.create_table(
        'allowed_users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    op.create_index('ix_allowed_users_email', 'allowed_users', ['email'])

    # trades table
    op.create_table(
        'trades',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('universe', sa.String(length=20), nullable=False, server_default='nse500'),
        sa.Column('trade_date', sa.Date(), nullable=False),
        sa.Column('symbol', sa.String(length=50), nullable=False),
        sa.Column('side', sa.String(length=10), nullable=False),
        sa.Column('shares', sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column('price', sa.Numeric(precision=18, scale=4), nullable=False),
        sa.Column('notional', sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column('slippage', sa.Numeric(precision=18, scale=4), nullable=True),
        sa.Column('cash_after', sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("side IN ('BUY', 'SELL')", name='check_trade_side')
    )
    op.create_index('idx_trades_universe_date', 'trades', ['universe', 'trade_date'])
    op.create_index('idx_trades_symbol', 'trades', ['symbol'])
    op.create_index('idx_trades_date', 'trades', ['trade_date'])

    # equity_curve table
    op.create_table(
        'equity_curve',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('universe', sa.String(length=20), nullable=False, server_default='nse500'),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('portfolio_value', sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column('cash', sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column('invested', sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column('benchmark', sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column('drawdown', sa.Numeric(precision=10, scale=6), nullable=True),
        sa.Column('exposure', sa.Numeric(precision=5, scale=4), nullable=True, server_default='1.0'),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_equity_universe_date', 'equity_curve', ['universe', 'date'], unique=True)
    op.create_index('idx_equity_date', 'equity_curve', ['date'])

    # holdings table
    op.create_table(
        'holdings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('universe', sa.String(length=20), nullable=False, server_default='nse500'),
        sa.Column('snapshot_date', sa.Date(), nullable=False),
        sa.Column('symbol', sa.String(length=50), nullable=False),
        sa.Column('rank', sa.Integer(), nullable=True),
        sa.Column('shares', sa.Numeric(precision=18, scale=6), nullable=True),
        sa.Column('avg_cost', sa.Numeric(precision=18, scale=4), nullable=True),
        sa.Column('entry_date', sa.Date(), nullable=True),
        sa.Column('entry_rank', sa.Integer(), nullable=True),
        sa.Column('holding_days', sa.Integer(), nullable=True),
        sa.Column('last_price', sa.Numeric(precision=18, scale=4), nullable=True),
        sa.Column('pnl_pct', sa.Numeric(precision=10, scale=6), nullable=True),
        sa.Column('notional', sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column('contribution_pct', sa.Numeric(precision=10, scale=6), nullable=True),
        sa.Column('sector', sa.String(length=100), nullable=True),
        sa.Column('industry', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_holdings_universe_date', 'holdings', ['universe', 'snapshot_date'])
    op.create_index('idx_holdings_date', 'holdings', ['snapshot_date'])
    op.create_index('idx_holdings_symbol', 'holdings', ['symbol'])

    # metrics table
    op.create_table(
        'metrics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('universe', sa.String(length=20), nullable=False, server_default='nse500'),
        sa.Column('computed_date', sa.Date(), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=True),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('total_return', sa.Numeric(precision=18, scale=6), nullable=True),
        sa.Column('cagr', sa.Numeric(precision=10, scale=6), nullable=True),
        sa.Column('mtd_return', sa.Numeric(precision=10, scale=6), nullable=True),
        sa.Column('ytd_return', sa.Numeric(precision=10, scale=6), nullable=True),
        sa.Column('max_drawdown', sa.Numeric(precision=10, scale=6), nullable=True),
        sa.Column('max_drawdown_duration', sa.Integer(), nullable=True),
        sa.Column('volatility', sa.Numeric(precision=10, scale=6), nullable=True),
        sa.Column('sharpe_ratio', sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column('sortino_ratio', sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column('calmar_ratio', sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column('avg_turnover_pct', sa.Numeric(precision=10, scale=6), nullable=True),
        sa.Column('annualized_turnover', sa.Numeric(precision=10, scale=6), nullable=True),
        sa.Column('hit_rate', sa.Numeric(precision=10, scale=6), nullable=True),
        sa.Column('avg_holding_days', sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column('trades_total', sa.Integer(), nullable=True),
        sa.Column('buys', sa.Integer(), nullable=True),
        sa.Column('sells', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_metrics_universe_date', 'metrics', ['universe', 'computed_date'], unique=True)

    # rebalances table
    op.create_table(
        'rebalances',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('universe', sa.String(length=20), nullable=False, server_default='nse500'),
        sa.Column('signal_date', sa.Date(), nullable=False),
        sa.Column('order_date', sa.Date(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True, server_default='pending'),
        sa.Column('additions', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('removals', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('rank_changes', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('orders_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('turnover_pct', sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("status IN ('pending', 'preview', 'ready', 'executed')", name='check_rebalance_status')
    )
    op.create_index('idx_rebalances_universe_date', 'rebalances', ['universe', 'signal_date'], unique=True)
    op.create_index('idx_rebalances_date', 'rebalances', ['signal_date'])

    # signals table
    op.create_table(
        'signals',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('universe', sa.String(length=20), nullable=False, server_default='nse500'),
        sa.Column('signal_date', sa.Date(), nullable=False),
        sa.Column('rank', sa.Integer(), nullable=False),
        sa.Column('symbol', sa.String(length=50), nullable=False),
        sa.Column('score', sa.Numeric(precision=18, scale=6), nullable=True),
        sa.Column('score_6m', sa.Numeric(precision=18, scale=6), nullable=True),
        sa.Column('mom_6m', sa.Numeric(precision=18, scale=6), nullable=True),
        sa.Column('vol_6m', sa.Numeric(precision=18, scale=6), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_signals_universe_date', 'signals', ['universe', 'signal_date'])
    op.create_index('idx_signals_universe_date_symbol', 'signals', ['universe', 'signal_date', 'symbol'], unique=True)
    op.create_index('idx_signals_symbol', 'signals', ['symbol'])
    op.create_index('idx_signals_date', 'signals', ['signal_date'])

    # jobs table
    op.create_table(
        'jobs',
        sa.Column('id', sa.String(length=32), nullable=False),
        sa.Column('command', sa.String(length=100), nullable=False),
        sa.Column('label', sa.String(length=255), nullable=True),
        sa.Column('universe', sa.String(length=20), nullable=True),
        sa.Column('args', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True, server_default='queued'),
        sa.Column('started_at', sa.DateTime(), nullable=True),
        sa.Column('ended_at', sa.DateTime(), nullable=True),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('log_path', sa.String(length=500), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint("status IN ('queued', 'running', 'completed', 'failed', 'cancelled')", name='check_job_status')
    )
    op.create_index('idx_jobs_status', 'jobs', ['status'])
    op.create_index('idx_jobs_created', 'jobs', ['created_at'])
    op.create_index('idx_jobs_universe', 'jobs', ['universe'])


def downgrade() -> None:
    op.drop_table('jobs')
    op.drop_table('signals')
    op.drop_table('rebalances')
    op.drop_table('metrics')
    op.drop_table('holdings')
    op.drop_table('equity_curve')
    op.drop_table('trades')
    op.drop_table('allowed_users')
