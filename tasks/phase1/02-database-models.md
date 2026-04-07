# Task 2: Set up PostgreSQL Database with SQLAlchemy Models

**Status**: `completed`
**Blocked By**: #1 (Backend Setup)
**Blocks**: #3

## Objective

Create SQLAlchemy models and database setup with Alembic migrations. All tables include a `universe` column for multi-universe support.

## Tasks

- [x] Create `app/models/database.py` with engine and session setup
- [x] Create all SQLAlchemy models
- [x] Initialize Alembic (`alembic init alembic`)
- [x] Configure `alembic.ini` and `env.py`
- [x] Create initial migration
- [x] Add indexes for common queries

## Models

### app/models/database.py

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
```

### app/models/models.py

```python
from sqlalchemy import Column, Integer, String, Date, DateTime, Numeric, Boolean, Text, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from app.models.database import Base

class AllowedUser(Base):
    __tablename__ = "allowed_users"

    id = Column(Integer, primary_key=True)
    email = Column(String(255), unique=True, nullable=False)
    name = Column(String(255))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())

class Trade(Base):
    __tablename__ = "trades"

    id = Column(Integer, primary_key=True)
    universe = Column(String(20), nullable=False, default="nse500")
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
        Index("idx_trades_universe_date", "universe", "trade_date"),
        Index("idx_trades_symbol", "symbol"),
    )

class EquityCurve(Base):
    __tablename__ = "equity_curve"

    id = Column(Integer, primary_key=True)
    universe = Column(String(20), nullable=False, default="nse500")
    date = Column(Date, nullable=False)
    portfolio_value = Column(Numeric(18, 2), nullable=False)
    cash = Column(Numeric(18, 2))
    invested = Column(Numeric(18, 2))
    benchmark = Column(Numeric(18, 2))
    drawdown = Column(Numeric(10, 6))
    exposure = Column(Numeric(5, 4), default=1.0)
    created_at = Column(DateTime, default=func.now())

    __table_args__ = (
        Index("idx_equity_universe_date", "universe", "date"),
    )

class Holding(Base):
    __tablename__ = "holdings"

    id = Column(Integer, primary_key=True)
    universe = Column(String(20), nullable=False, default="nse500")
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
    )

class Metric(Base):
    __tablename__ = "metrics"

    id = Column(Integer, primary_key=True)
    universe = Column(String(20), nullable=False, default="nse500")
    computed_date = Column(Date, nullable=False)
    start_date = Column(Date)
    end_date = Column(Date)
    total_return = Column(Numeric(18, 6))
    cagr = Column(Numeric(10, 6))
    max_drawdown = Column(Numeric(10, 6))
    max_drawdown_duration = Column(Integer)
    volatility = Column(Numeric(10, 6))
    sharpe_ratio = Column(Numeric(10, 4))
    sortino_ratio = Column(Numeric(10, 4))
    calmar_ratio = Column(Numeric(10, 4))
    avg_turnover_pct = Column(Numeric(10, 6))
    annualized_turnover = Column(Numeric(10, 6))
    hit_rate = Column(Numeric(10, 6))
    avg_holding_days = Column(Numeric(10, 2))
    trades_total = Column(Integer)
    buys = Column(Integer)
    sells = Column(Integer)
    created_at = Column(DateTime, default=func.now())

    __table_args__ = (
        Index("idx_metrics_universe_date", "universe", "computed_date"),
    )

class Rebalance(Base):
    __tablename__ = "rebalances"

    id = Column(Integer, primary_key=True)
    universe = Column(String(20), nullable=False, default="nse500")
    signal_date = Column(Date, nullable=False)
    order_date = Column(Date)
    status = Column(String(20), default="pending")  # pending, preview, ready, executed
    additions = Column(JSONB)
    removals = Column(JSONB)
    rank_changes = Column(JSONB)
    orders_json = Column(JSONB)
    turnover_pct = Column(Numeric(10, 4))
    created_at = Column(DateTime, default=func.now())

    __table_args__ = (
        Index("idx_rebalances_universe_date", "universe", "signal_date"),
    )

class Signal(Base):
    __tablename__ = "signals"

    id = Column(Integer, primary_key=True)
    universe = Column(String(20), nullable=False, default="nse500")
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
        Index("idx_signals_symbol", "symbol"),
    )

class Job(Base):
    __tablename__ = "jobs"

    id = Column(String(32), primary_key=True)
    command = Column(String(100), nullable=False)
    label = Column(String(255))
    args = Column(JSONB)
    status = Column(String(50), default="queued")  # queued, running, completed, failed, cancelled
    started_at = Column(DateTime)
    ended_at = Column(DateTime)
    duration_seconds = Column(Integer)
    log_path = Column(String(500))
    error_message = Column(Text)
    created_at = Column(DateTime, default=func.now())

    __table_args__ = (
        Index("idx_jobs_status", "status"),
        Index("idx_jobs_created", "created_at"),
    )
```

## Alembic Setup

```bash
cd kite-api
alembic init alembic
```

Edit `alembic/env.py`:
```python
from app.config import settings
from app.models.database import Base
from app.models.models import *  # Import all models

config.set_main_option("sqlalchemy.url", settings.database_url)
target_metadata = Base.metadata
```

Create migration:
```bash
alembic revision --autogenerate -m "Initial tables"
alembic upgrade head
```

## Verification

```bash
# Connect to database and verify tables
psql $DATABASE_URL -c "\dt"
```

## Notes

- All tables include `universe` column with default "nse500"
- JSONB used for flexible storage of additions/removals/orders
- Indexes on (universe, date) for efficient per-universe queries

---

*Last updated: February 2026*
