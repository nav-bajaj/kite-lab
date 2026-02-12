"""
Application configuration and universe definitions.
"""
from pathlib import Path
from pydantic_settings import BaseSettings
from typing import Literal
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    database_url: str = "postgresql://localhost/kitelab"

    # CORS
    allowed_origins: str = "http://localhost:3000"

    # Authentication
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    allowed_emails: str = ""  # Comma-separated list

    # Kite API (optional - for live data fetch)
    kite_api_key: str = ""
    kite_api_secret: str = ""

    # App settings
    debug: bool = False

    # Data directory (parent of kite-api, i.e., kite-lab root)
    @property
    def data_dir(self) -> Path:
        """Get the data directory (kite-lab root, parent of kite-api)."""
        # __file__ is app/config.py, so parent.parent is kite-api/, parent.parent.parent is kite-lab/
        return Path(__file__).parent.parent.parent

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Cached settings instance."""
    return Settings()


# Universe configuration
UNIVERSES = {
    "nse500": {
        "id": "nse500",
        "name": "NSE 500",
        "description": "Full mid+large cap universe",
        "stocks": 499,
        "risk_profile": "Growth-focused",
        "data_dir": "nse500_data",
        "universe_file": "data/static/nse500_universe.csv",
        "portfolio_dir": "data/final_portfolio",
    },
    "nifty250": {
        "id": "nifty250",
        "name": "Nifty 250",
        "description": "Large + mid-cap blend",
        "stocks": 250,
        "risk_profile": "Balanced",
        "data_dir": "nse500_data",  # Uses same price data
        "universe_file": "data/static/nifty250_universe.csv",
        "portfolio_dir": "nifty_250_tests",
    },
    "nifty100": {
        "id": "nifty100",
        "name": "Nifty 100",
        "description": "Large-cap only",
        "stocks": 100,
        "risk_profile": "Conservative",
        "data_dir": "nse500_data",  # Uses same price data
        "universe_file": "data/static/nifty100_universe.csv",
        "portfolio_dir": "nifty_100_tests",
    },
}

UniverseId = Literal["nse500", "nifty250", "nifty100"]


def get_universe(universe_id: UniverseId) -> dict:
    """Get universe configuration by ID."""
    if universe_id not in UNIVERSES:
        raise ValueError(f"Unknown universe: {universe_id}")
    return UNIVERSES[universe_id]


def is_valid_universe(universe_id: str) -> bool:
    """Check if universe ID is valid."""
    return universe_id in UNIVERSES


# Default settings instance
settings = get_settings()

# Universe defaults for portfolio parameters
UNIVERSE_DEFAULTS = {
    "nse500": {
        "top_n": 24,
        "lookback_months": 6,
        "rebalance_weeks": 1,
        "vol_floor": 0.05,
        "min_hold_days": 8,
    },
    "nifty250": {
        "top_n": 24,
        "lookback_months": 6,
        "rebalance_weeks": 1,
        "vol_floor": 0.05,
        "min_hold_days": 8,
    },
    "nifty100": {
        "top_n": 24,
        "lookback_months": 6,
        "rebalance_weeks": 1,
        "vol_floor": 0.05,
        "min_hold_days": 8,
    },
}
