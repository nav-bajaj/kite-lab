"""
Database connection and session management.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from functools import lru_cache

# Base class for models - can be imported without database connection
Base = declarative_base()

# Lazy-initialized engine and session
_engine = None
_SessionLocal = None


def get_engine():
    """Get or create the database engine (lazy initialization)."""
    global _engine
    if _engine is None:
        from app.config import get_settings
        settings = get_settings()
        _engine = create_engine(
            settings.database_url,
            pool_pre_ping=True,  # Verify connections before using
            echo=settings.debug,  # Log SQL in debug mode
        )
    return _engine


def get_session_local():
    """Get or create the session factory (lazy initialization)."""
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=get_engine()
        )
    return _SessionLocal


# Alias for backward compatibility
@property
def engine():
    return get_engine()


@property
def SessionLocal():
    return get_session_local()


def get_db():
    """
    Dependency for FastAPI routes to get database session.

    Usage:
        @app.get("/items")
        def get_items(db: Session = Depends(get_db)):
            ...
    """
    SessionLocal = get_session_local()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables. Call after all models are imported."""
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
