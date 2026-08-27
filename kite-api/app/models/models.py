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
    ForeignKey,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.models.database import Base


class WaitlistSignup(Base):
    """Coming-soon waitlist signups (tasks/site_gate) plus the consent
    lifecycle the email channel needs (tasks/email_channel).

    Emails are normalised (strip + lowercase) before insert; the unique
    index makes the public POST idempotent. Only ``status == 'confirmed'``
    is mailable.

    No consent IP / user-agent is stored on purpose — under double opt-in
    the confirmation click and ``confirmed_at`` are the evidence, and the
    address is enough PII for one table (R-027)."""

    __tablename__ = "waitlist_signups"

    id = Column(Integer, primary_key=True)
    email = Column(String(320), unique=True, nullable=False, index=True)
    source = Column(String(50), nullable=False, server_default="coming_soon")
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Consent lifecycle: pending -> confirmed -> unsubscribed;
    # bounced / complained are terminal and set from SES events (Phase 3).
    status = Column(
        String(20), nullable=False, server_default="pending", index=True
    )
    confirm_token = Column(String(64), unique=True, index=True)
    confirm_sent_at = Column(DateTime(timezone=True))
    confirmed_at = Column(DateTime(timezone=True))
    unsubscribe_token = Column(String(64), unique=True, index=True)
    unsubscribed_at = Column(DateTime(timezone=True))

    # Send bookkeeping — makes the welcome send idempotent under retry.
    welcome_sent_at = Column(DateTime(timezone=True))
    last_sent_at = Column(DateTime(timezone=True))

    def __repr__(self):
        return f"<WaitlistSignup(email='{self.email}' status='{self.status}')>"


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
    price = Column(Numeric(18, 6), nullable=False)
    notional = Column(Numeric(18, 4), nullable=False)
    slippage = Column(Numeric(18, 6))
    cash_after = Column(Numeric(18, 4))
    created_at = Column(DateTime, default=func.now())

    __table_args__ = (
        CheckConstraint("side IN ('BUY', 'SELL')", name="check_trade_side"),
        Index("idx_trades_universe_date", "universe", "trade_date"),
        Index("idx_trades_symbol", "symbol"),
        Index("idx_trades_date", "trade_date"),
    )

    def __repr__(self):
        return f"<Trade({self.trade_date} {self.side} {self.symbol})>"


class TradeMatch(Base):
    """
    FIFO-matched pair linking a SELL trade to the BUY trade(s) that opened
    the position. Realized P&L is net of slippage on both legs.

    Multiple rows per SELL are possible when one sell closes several earlier
    buy lots; multiple rows per BUY are possible when one buy is unwound in
    several sells. Populated by ``trade_matching_service.rebuild_matches``.
    """

    __tablename__ = "trade_matches"

    id = Column(Integer, primary_key=True)
    universe = Column(String(20), nullable=False, index=True)
    buy_trade_id = Column(Integer, ForeignKey("trades.id", ondelete="CASCADE"), nullable=False)
    sell_trade_id = Column(Integer, ForeignKey("trades.id", ondelete="CASCADE"), nullable=False)
    symbol = Column(String(50), nullable=False)
    shares_matched = Column(Numeric(18, 6), nullable=False)
    entry_date = Column(Date, nullable=False)
    exit_date = Column(Date, nullable=False)
    entry_price = Column(Numeric(18, 6), nullable=False)
    exit_price = Column(Numeric(18, 6), nullable=False)
    holding_days = Column(Integer, nullable=False)
    realized_pnl = Column(Numeric(18, 4), nullable=False)
    realized_pnl_pct = Column(Numeric(12, 6), nullable=False)
    created_at = Column(DateTime, default=func.now())

    buy_trade = relationship("Trade", foreign_keys=[buy_trade_id])
    sell_trade = relationship("Trade", foreign_keys=[sell_trade_id])

    __table_args__ = (
        Index("idx_trade_matches_universe", "universe"),
        Index("idx_trade_matches_sell", "sell_trade_id"),
        Index("idx_trade_matches_buy", "buy_trade_id"),
        Index("idx_trade_matches_universe_symbol", "universe", "symbol"),
    )

    def __repr__(self):
        return (
            f"<TradeMatch({self.symbol} buy={self.buy_trade_id} "
            f"sell={self.sell_trade_id} pnl={self.realized_pnl})>"
        )


class EquityCurve(Base):
    """Daily equity curve for each universe."""

    __tablename__ = "equity_curve"

    id = Column(Integer, primary_key=True)
    universe = Column(String(20), nullable=False, default="nse500", index=True)
    date = Column(Date, nullable=False)
    portfolio_value = Column(Numeric(18, 4), nullable=False)
    cash = Column(Numeric(18, 4))
    invested = Column(Numeric(18, 4))
    benchmark = Column(Numeric(18, 4))
    drawdown = Column(Numeric(18, 10))
    exposure = Column(Numeric(10, 6), default=1.0)
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
    avg_cost = Column(Numeric(18, 8))
    entry_date = Column(Date)
    entry_rank = Column(Integer)
    holding_days = Column(Integer)
    last_price = Column(Numeric(18, 6))
    pnl_pct = Column(Numeric(18, 10))
    notional = Column(Numeric(18, 4))
    contribution_pct = Column(Numeric(18, 10))
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
    total_return = Column(Numeric(18, 10))
    cagr = Column(Numeric(18, 10))
    mtd_return = Column(Numeric(18, 10))
    ytd_return = Column(Numeric(18, 10))

    # Risk metrics
    max_drawdown = Column(Numeric(18, 10))
    max_drawdown_duration = Column(Integer)  # days
    volatility = Column(Numeric(18, 10))
    sharpe_ratio = Column(Numeric(18, 10))
    sortino_ratio = Column(Numeric(18, 10))
    calmar_ratio = Column(Numeric(18, 10))

    # Activity metrics
    avg_turnover_pct = Column(Numeric(18, 10))
    annualized_turnover = Column(Numeric(18, 10))
    hit_rate = Column(Numeric(18, 10))
    avg_holding_days = Column(Numeric(18, 4))

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


class ProposedRebalance(Base):
    """Upcoming rebalance the engine has decided at signal-day EOD.

    Populated by ``data_pipeline/eod_proposal.py`` (see
    ``tasks/rebalance_page/PLAN.md`` Phase 2 §1) and synced into the API by
    ``sync_service.sync_proposed_rebalance``. The page reads the latest row
    per universe to show the "Actionable trades" card.

    Membership-only: ``sells`` are full exits, ``buys`` are new entries with
    the model's target weight + optional rupee sizing, ``holds`` are
    continuing names (no action). Partial trims on continuing holdings are
    deliberately not surfaced — see the gotcha in PLAN.md.
    """

    __tablename__ = "proposed_rebalances"

    id = Column(Integer, primary_key=True)
    universe = Column(String(20), nullable=False, index=True)
    exec_date = Column(Date, nullable=False)
    signal_date = Column(Date, nullable=False)
    data_as_of = Column(Date, nullable=False)

    sell_count = Column(Integer, nullable=False, default=0)
    buy_count = Column(Integer, nullable=False, default=0)
    hold_count = Column(Integer, nullable=False, default=0)

    sells = Column(JSONB)   # ["SYM1", "SYM2", ...]
    buys = Column(JSONB)    # [{"symbol", "target_weight", "est_notional", "est_shares"}, ...]
    holds = Column(JSONB)   # ["SYM3", "SYM4", ...]

    regime = Column(String(10))                # "bull" | "bear" | None
    drawdown_from_peak = Column(Numeric(18, 10))
    final_pv = Column(Numeric(18, 4))
    initial_capital = Column(Numeric(18, 4))

    created_at = Column(DateTime, default=func.now())

    __table_args__ = (
        Index(
            "idx_proposed_rebalances_universe_exec",
            "universe", "exec_date", unique=True,
        ),
        Index("idx_proposed_rebalances_exec", "exec_date"),
    )

    def __repr__(self):
        return (f"<ProposedRebalance({self.universe} exec={self.exec_date} "
                f"S={self.sell_count} B={self.buy_count} H={self.hold_count})>")


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


class OpenPosition(Base):
    """
    Live portfolio positions for real-time tracking.

    Unlike the Holding model (which stores backtest snapshots), this table
    stores actual positions that the user holds for live P&L tracking.
    """

    __tablename__ = "open_positions"

    id = Column(Integer, primary_key=True)
    universe = Column(String(20), nullable=False, default="nse500", index=True)
    symbol = Column(String(50), nullable=False)
    instrument_token = Column(Integer)  # Zerodha instrument token for API calls
    qty = Column(Integer, nullable=False)
    avg_price = Column(Numeric(18, 4), nullable=False)
    entry_date = Column(Date)
    # Last known price (for when market is closed)
    last_price = Column(Numeric(18, 4))
    prev_close = Column(Numeric(18, 4))  # Previous day's closing price
    price_updated_at = Column(DateTime)  # When prices were last updated
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("idx_open_positions_universe", "universe"),
        Index("idx_open_positions_symbol", "symbol"),
        Index("idx_open_positions_universe_symbol", "universe", "symbol", unique=True),
    )

    def __repr__(self):
        return f"<OpenPosition({self.universe} {self.symbol} qty={self.qty})>"


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
