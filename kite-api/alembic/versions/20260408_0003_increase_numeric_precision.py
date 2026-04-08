"""Increase numeric precision to eliminate rounding discrepancies

Revision ID: 0003
Revises: 0002
Create Date: 2026-04-08

Increases decimal precision on financial columns to prevent data loss
during CSV-to-database sync. Previous precision (e.g. Numeric(18,2) for
portfolio values) was truncating values and causing discrepancies between
CSV-based local dev and DB-based production dashboard.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- equity_curve ---
    op.alter_column("equity_curve", "portfolio_value",
                    type_=sa.Numeric(18, 4), existing_type=sa.Numeric(18, 2))
    op.alter_column("equity_curve", "cash",
                    type_=sa.Numeric(18, 4), existing_type=sa.Numeric(18, 2))
    op.alter_column("equity_curve", "invested",
                    type_=sa.Numeric(18, 4), existing_type=sa.Numeric(18, 2))
    op.alter_column("equity_curve", "benchmark",
                    type_=sa.Numeric(18, 4), existing_type=sa.Numeric(18, 2))
    op.alter_column("equity_curve", "drawdown",
                    type_=sa.Numeric(18, 10), existing_type=sa.Numeric(10, 6))
    op.alter_column("equity_curve", "exposure",
                    type_=sa.Numeric(10, 6), existing_type=sa.Numeric(5, 4))

    # --- holdings ---
    op.alter_column("holdings", "avg_cost",
                    type_=sa.Numeric(18, 8), existing_type=sa.Numeric(18, 4))
    op.alter_column("holdings", "last_price",
                    type_=sa.Numeric(18, 6), existing_type=sa.Numeric(18, 4))
    op.alter_column("holdings", "pnl_pct",
                    type_=sa.Numeric(18, 10), existing_type=sa.Numeric(10, 6))
    op.alter_column("holdings", "notional",
                    type_=sa.Numeric(18, 4), existing_type=sa.Numeric(18, 2))
    op.alter_column("holdings", "contribution_pct",
                    type_=sa.Numeric(18, 10), existing_type=sa.Numeric(10, 6))

    # --- trades ---
    op.alter_column("trades", "price",
                    type_=sa.Numeric(18, 6), existing_type=sa.Numeric(18, 4))
    op.alter_column("trades", "notional",
                    type_=sa.Numeric(18, 4), existing_type=sa.Numeric(18, 2))
    op.alter_column("trades", "slippage",
                    type_=sa.Numeric(18, 6), existing_type=sa.Numeric(18, 4))
    op.alter_column("trades", "cash_after",
                    type_=sa.Numeric(18, 4), existing_type=sa.Numeric(18, 2))

    # --- metrics ---
    op.alter_column("metrics", "total_return",
                    type_=sa.Numeric(18, 10), existing_type=sa.Numeric(18, 6))
    op.alter_column("metrics", "cagr",
                    type_=sa.Numeric(18, 10), existing_type=sa.Numeric(10, 6))
    op.alter_column("metrics", "mtd_return",
                    type_=sa.Numeric(18, 10), existing_type=sa.Numeric(10, 6))
    op.alter_column("metrics", "ytd_return",
                    type_=sa.Numeric(18, 10), existing_type=sa.Numeric(10, 6))
    op.alter_column("metrics", "max_drawdown",
                    type_=sa.Numeric(18, 10), existing_type=sa.Numeric(10, 6))
    op.alter_column("metrics", "volatility",
                    type_=sa.Numeric(18, 10), existing_type=sa.Numeric(10, 6))
    op.alter_column("metrics", "sharpe_ratio",
                    type_=sa.Numeric(18, 10), existing_type=sa.Numeric(10, 4))
    op.alter_column("metrics", "sortino_ratio",
                    type_=sa.Numeric(18, 10), existing_type=sa.Numeric(10, 4))
    op.alter_column("metrics", "calmar_ratio",
                    type_=sa.Numeric(18, 10), existing_type=sa.Numeric(10, 4))
    op.alter_column("metrics", "avg_turnover_pct",
                    type_=sa.Numeric(18, 10), existing_type=sa.Numeric(10, 6))
    op.alter_column("metrics", "annualized_turnover",
                    type_=sa.Numeric(18, 10), existing_type=sa.Numeric(10, 6))
    op.alter_column("metrics", "hit_rate",
                    type_=sa.Numeric(18, 10), existing_type=sa.Numeric(10, 6))
    op.alter_column("metrics", "avg_holding_days",
                    type_=sa.Numeric(18, 4), existing_type=sa.Numeric(10, 2))


def downgrade() -> None:
    # --- equity_curve ---
    op.alter_column("equity_curve", "portfolio_value",
                    type_=sa.Numeric(18, 2), existing_type=sa.Numeric(18, 4))
    op.alter_column("equity_curve", "cash",
                    type_=sa.Numeric(18, 2), existing_type=sa.Numeric(18, 4))
    op.alter_column("equity_curve", "invested",
                    type_=sa.Numeric(18, 2), existing_type=sa.Numeric(18, 4))
    op.alter_column("equity_curve", "benchmark",
                    type_=sa.Numeric(18, 2), existing_type=sa.Numeric(18, 4))
    op.alter_column("equity_curve", "drawdown",
                    type_=sa.Numeric(10, 6), existing_type=sa.Numeric(18, 10))
    op.alter_column("equity_curve", "exposure",
                    type_=sa.Numeric(5, 4), existing_type=sa.Numeric(10, 6))

    # --- holdings ---
    op.alter_column("holdings", "avg_cost",
                    type_=sa.Numeric(18, 4), existing_type=sa.Numeric(18, 8))
    op.alter_column("holdings", "last_price",
                    type_=sa.Numeric(18, 4), existing_type=sa.Numeric(18, 6))
    op.alter_column("holdings", "pnl_pct",
                    type_=sa.Numeric(10, 6), existing_type=sa.Numeric(18, 10))
    op.alter_column("holdings", "notional",
                    type_=sa.Numeric(18, 2), existing_type=sa.Numeric(18, 4))
    op.alter_column("holdings", "contribution_pct",
                    type_=sa.Numeric(10, 6), existing_type=sa.Numeric(18, 10))

    # --- trades ---
    op.alter_column("trades", "price",
                    type_=sa.Numeric(18, 4), existing_type=sa.Numeric(18, 6))
    op.alter_column("trades", "notional",
                    type_=sa.Numeric(18, 2), existing_type=sa.Numeric(18, 4))
    op.alter_column("trades", "slippage",
                    type_=sa.Numeric(18, 4), existing_type=sa.Numeric(18, 6))
    op.alter_column("trades", "cash_after",
                    type_=sa.Numeric(18, 2), existing_type=sa.Numeric(18, 4))

    # --- metrics ---
    op.alter_column("metrics", "total_return",
                    type_=sa.Numeric(18, 6), existing_type=sa.Numeric(18, 10))
    op.alter_column("metrics", "cagr",
                    type_=sa.Numeric(10, 6), existing_type=sa.Numeric(18, 10))
    op.alter_column("metrics", "mtd_return",
                    type_=sa.Numeric(10, 6), existing_type=sa.Numeric(18, 10))
    op.alter_column("metrics", "ytd_return",
                    type_=sa.Numeric(10, 6), existing_type=sa.Numeric(18, 10))
    op.alter_column("metrics", "max_drawdown",
                    type_=sa.Numeric(10, 6), existing_type=sa.Numeric(18, 10))
    op.alter_column("metrics", "volatility",
                    type_=sa.Numeric(10, 6), existing_type=sa.Numeric(18, 10))
    op.alter_column("metrics", "sharpe_ratio",
                    type_=sa.Numeric(10, 4), existing_type=sa.Numeric(18, 10))
    op.alter_column("metrics", "sortino_ratio",
                    type_=sa.Numeric(10, 4), existing_type=sa.Numeric(18, 10))
    op.alter_column("metrics", "calmar_ratio",
                    type_=sa.Numeric(10, 4), existing_type=sa.Numeric(18, 10))
    op.alter_column("metrics", "avg_turnover_pct",
                    type_=sa.Numeric(10, 6), existing_type=sa.Numeric(18, 10))
    op.alter_column("metrics", "annualized_turnover",
                    type_=sa.Numeric(10, 6), existing_type=sa.Numeric(18, 10))
    op.alter_column("metrics", "hit_rate",
                    type_=sa.Numeric(10, 6), existing_type=sa.Numeric(18, 10))
    op.alter_column("metrics", "avg_holding_days",
                    type_=sa.Numeric(10, 2), existing_type=sa.Numeric(18, 4))
