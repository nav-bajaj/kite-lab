"""
SQLAlchemy models for Kite-Lab API.

All tables include a `universe` column for multi-universe support.
"""
from sqlalchemy import (
    Column,
    Integer,
    String,
    Date,
    DateTime,
    Numeric,
    Boolean,
    Text,
    Index,
    CheckConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func

from app.models.database import Base


class AllowedUser(Base):
    """Whitelist of users allowed to access the dashboard."""

    __tablename__ = "allowed_users"

    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())

    def __repr__(self):
        return f"<AllowedUser(email='{self.email}')>"


class Trade(Base):
    """Trade history for all universes."""

    __tablename__ = "trades"

    id = Column(Integer, primary_key=True)
    universe = Column(String(20), nullable=False, default="nse500", index=True)
    trade_date = Column(Date, nullable=False)
    symbol = Column(String(50), nullable=False)
    side = Column(String(10), nullable=False)  # BUY or SELL
    shares = Column(Numeric(18, 6), nullable=False)
    price = Column(Numeric(18, 4), nullable=False)
    notional = Column(Numeric(18, 2), nullable=False)
    slippage = Column(Numeric(18, 4))
    cash_after = Column(Numeric(18, 2))
    created_at = Column(DateTime, default=func.now())

    __table_args__ = (
        CheckConstraint("side IN ('BUY', 'SELL')", name="check_trade_side"),
        Index("idx_trades_universe_date", "universe", "trade_date"),
        Index("idx_trades_symbol", "symbol"),
        Index("idx_trades_date", "trade_date"),
    )

    def __repr__(self):
        return f"<Trade({self.trade_date} {self.side} {self.symbol})>"


class EquityCurve(Base):
    """Daily equity curve for each universe."""

    __tablename__ = "equity_curve"

    id = Column(Integer, primary_key=True)
    universe = Column(String(20), nullable=False, default="nse500", index=True)
    date = Column(Date, nullable=False)
    portfolio_value = Column(Numeric(18, 2), nullable=False)
    cash = Column(Numeric(18, 2))
    invested = Column(Numeric(18, 2))
    benchmark = Column(Numeric(18, 2))
    drawdown = Column(Numeric(10, 6))
    exposure = Column(Numeric(5, 4), default=1.0)
    created_at = Column(DateTime, default=func.now())

    __table_args__ = (
        Index("idx_equity_universe_date", "universe", "date", unique=True),
        Index("idx_equity_date", "date"),
    )

    def __repr__(self):
        return f"<EquityCurve({self.universe} {self.date})>"


class Holding(Base):
    """Portfolio holdings snapshots."""

    __tablename__ = "holdings"

    id = Column(Integer, primary_key=True)
    universe = Column(String(20), nullable=False, default="nse500", index=True)
    snapshot_date = Column(Date, nullable=False)
    symbol = Column(String(50), nullable=False)
    rank = Column(Integer)
    shares = Column(Numeric(18, 6))
    avg_cost = Column(Numeric(18, 4))
    entry_date = Column(Date)
    entry_rank = Column(Integer)
    holding_days = Column(Integer)
    last_price = Column(Numeric(18, 4))
    pnl_pct = Column(Numeric(10, 6))
    notional = Column(Numeric(18, 2))
    contribution_pct = Column(Numeric(10, 6))
    sector = Column(String(100))
    industry = Column(String(100))
    created_at = Column(DateTime, default=func.now())

    __table_args__ = (
        Index("idx_holdings_universe_date", "universe", "snapshot_date"),
        Index("idx_holdings_date", "snapshot_date"),
        Index("idx_holdings_symbol", "symbol"),
    )

    def __repr__(self):
        return f"<Holding({self.universe} {self.snapshot_date} {self.symbol})>"


class Metric(Base):
    """Computed performance metrics for each universe."""

    __tablename__ = "metrics"

    id = Column(Integer, primary_key=True)
    universe = Column(String(20), nullable=False, default="nse500", index=True)
    computed_date = Column(Date, nullable=False)
    start_date = Column(Date)
    end_date = Column(Date)

    # Returns
    total_return = Column(Numeric(18, 6))
    cagr = Column(Numeric(10, 6))
    mtd_return = Column(Numeric(10, 6))
    ytd_return = Column(Numeric(10, 6))

    # Risk metrics
    max_drawdown = Column(Numeric(10, 6))
    max_drawdown_duration = Column(Integer)  # days
    volatility = Column(Numeric(10, 6))
    sharpe_ratio = Column(Numeric(10, 4))
    sortino_ratio = Column(Numeric(10, 4))
    calmar_ratio = Column(Numeric(10, 4))

    # Activity metrics
    avg_turnover_pct = Column(Numeric(10, 6))
    annualized_turnover = Column(Numeric(10, 6))
    hit_rate = Column(Numeric(10, 6))
    avg_holding_days = Column(Numeric(10, 2))

    # Trade counts
    trades_total = Column(Integer)
    buys = Column(Integer)
    sells = Column(Integer)

    created_at = Column(DateTime, default=func.now())

    __table_args__ = (
        Index("idx_metrics_universe_date", "universe", "computed_date", unique=True),
    )

    def __repr__(self):
        return f"<Metric({self.universe} {self.computed_date})>"


class Rebalance(Base):
    """Weekly rebalance events for each universe."""

    __tablename__ = "rebalances"

    id = Column(Integer, primary_key=True)
    universe = Column(String(20), nullable=False, default="nse500", index=True)
    signal_date = Column(Date, nullable=False)
    order_date = Column(Date)
    status = Column(String(20), default="pending")  # pending, preview, ready, executed

    # Changes as JSON
    additions = Column(JSONB)  # [{"symbol": "XYZ", "rank": 5, "score": 1.2}, ...]
    removals = Column(JSONB)   # [{"symbol": "ABC", "prev_rank": 25, "reason": "rank_drop"}, ...]
    rank_changes = Column(JSONB)  # [{"symbol": "DEF", "old_rank": 10, "new_rank": 3}, ...]
    orders_json = Column(JSONB)  # [{"action": "BUY", "symbol": "XYZ", "shares": 100, ...}, ...]

    turnover_pct = Column(Numeric(10, 4))
    created_at = Column(DateTime, default=func.now())

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'preview', 'ready', 'executed')",
            name="check_rebalance_status"
        ),
        Index("idx_rebalances_universe_date", "universe", "signal_date", unique=True),
        Index("idx_rebalances_date", "signal_date"),
    )

    def __repr__(self):
        return f"<Rebalance({self.universe} {self.signal_date} {self.status})>"


class Signal(Base):
    """Momentum signal rankings for each universe."""

    __tablename__ = "signals"

    id = Column(Integer, primary_key=True)
    universe = Column(String(20), nullable=False, default="nse500", index=True)
    signal_date = Column(Date, nullable=False)
    rank = Column(Integer, nullable=False)
    symbol = Column(String(50), nullable=False)
    score = Column(Numeric(18, 6))
    score_6m = Column(Numeric(18, 6))
    mom_6m = Column(Numeric(18, 6))
    vol_6m = Column(Numeric(18, 6))
    created_at = Column(DateTime, default=func.now())

    __table_args__ = (
        Index("idx_signals_universe_date", "universe", "signal_date"),
        Index("idx_signals_universe_date_symbol", "universe", "signal_date", "symbol", unique=True),
        Index("idx_signals_symbol", "symbol"),
        Index("idx_signals_date", "signal_date"),
    )

    def __repr__(self):
        return f"<Signal({self.universe} {self.signal_date} #{self.rank} {self.symbol})>"


class Job(Base):
    """Background job execution history."""

    __tablename__ = "jobs"

    id = Column(String(32), primary_key=True)  # UUID or similar
    command = Column(String(100), nullable=False)
    label = Column(String(255))  # Human-readable description
    universe = Column(String(20))  # Which universe this job affects
    args = Column(JSONB)  # Command arguments
    status = Column(String(50), default="queued")  # queued, running, completed, failed, cancelled

    started_at = Column(DateTime)
    ended_at = Column(DateTime)
    duration_seconds = Column(Integer)

    log_path = Column(String(500))  # Path to log file
    error_message = Column(Text)

    created_at = Column(DateTime, default=func.now())

    __table_args__ = (
        CheckConstraint(
            "status IN ('queued', 'running', 'completed', 'failed', 'cancelled')",
            name="check_job_status"
        ),
        Index("idx_jobs_status", "status"),
        Index("idx_jobs_created", "created_at"),
        Index("idx_jobs_universe", "universe"),
    )

    def __repr__(self):
        return f"<Job({self.id[:8]} {self.command} {self.status})>"
