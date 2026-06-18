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

    # Authentication — Clerk (session-token verification via JWKS)
    clerk_jwks_url: str = ""
    clerk_issuer: str = ""
    clerk_secret_key: str = ""  # For Clerk Backend API calls (future)

    # Legacy authentication settings (kept during transition; the NextAuth
    # HS256 path was retired in the Clerk migration. Safe to remove once
    # we're sure no code path references them.)
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    allowed_emails: str = ""  # Comma-separated list (legacy whitelist; unused with Clerk)

    # Kite API (optional - for live data fetch)
    kite_api_key: str = ""
    kite_api_secret: str = ""

    # Headless login (optional - for automated login without browser)
    kite_user_id: str = ""
    kite_password: str = ""
    totp_secret: str = ""

    # App settings
    debug: bool = False
    disable_auth: bool = False

    # Data directory
    @property
    def data_dir(self) -> Path:
        """Get the data directory.

        In Docker: /app (kite-api code is at /app, scripts at /app/scripts/)
        In local dev: kite-lab root (parent of kite-api/)
        """
        import os
        # Check if we're in Docker (working dir is /app and no parent kite-lab)
        app_dir = Path(__file__).parent.parent  # /app/app -> /app
        if app_dir == Path("/app"):
            return app_dir
        # Local development: go to parent (kite-lab root)
        return app_dir.parent

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Cached settings instance."""
    return Settings()


# Universe configuration
# Note: `om25_v3` is a strategy entry (not just a universe) — it runs the
# OM25 v3 regime-tilted strategy on the Nifty 250 stocks. Treated like a
# universe for dashboard/DB compatibility; UNIVERSES dict is now strategy×
# universe combinations.
UNIVERSES = {
    "nse500": {
        "id": "nse500",
        "name": "NSE 500",
        "description": "Full mid+large cap universe",
        "strategy": "L6 momentum",
        "stocks": 499,
        "risk_profile": "Growth-focused",
        "data_dir": "nse500_data",
        "universe_file": "data/static/nse500_universe.csv",
        "portfolio_dir": "data/final_portfolio",
        "rebalance_cadence": "weekly_thu_fri",
    },
    "nifty250": {
        "id": "nifty250",
        "name": "Nifty 250",
        "description": "Large + mid-cap blend",
        "strategy": "L6 momentum",
        "stocks": 250,
        "risk_profile": "Balanced",
        "data_dir": "nse500_data",
        "universe_file": "data/static/nifty250_universe.csv",
        "portfolio_dir": "nifty_250_tests",
        "rebalance_cadence": "weekly_thu_fri",
    },
    "nifty100": {
        "id": "nifty100",
        "name": "Nifty 100",
        "description": "Large-cap only",
        "strategy": "L6 momentum",
        "stocks": 100,
        "risk_profile": "Conservative",
        "data_dir": "nse500_data",
        "universe_file": "data/static/nifty100_universe.csv",
        "portfolio_dir": "nifty_100_tests",
        "rebalance_cadence": "weekly_thu_fri",
    },
    "om25_v3": {
        "id": "om25_v3",
        "name": "OM25 v3",
        "description": "Regime-tilted UC/CR composite on Nifty 250 (May 2026 OOS retune)",
        "strategy": "OM25 v3 (UC/CR composite, regime-tilted)",
        "stocks": 250,
        "risk_profile": "Quality momentum with defensive bear tilt",
        "data_dir": "nse500_data",
        "universe_file": "data/static/nifty250_universe.csv",
        "portfolio_dir": "data/om25_v3_portfolios",
        "rebalance_cadence": "biweekly_fri",
    },
    "tl25_v3": {
        "id": "tl25_v3",
        "name": "TL25 v3",
        "description": "Trend-quality score on NSE 500 (May 2026 OOS retune)",
        "strategy": "TL25 v3 (3-component trend score, weekly rank-exit)",
        "stocks": 499,
        "risk_profile": "Pure trend-following, diversifier vs OM25",
        "data_dir": "nse500_data",
        "universe_file": "data/static/nse500_universe.csv",
        "portfolio_dir": "data/tl25_v3_portfolios",
        "rebalance_cadence": "biweekly_fri",
    },
    "l6_v2": {
        "id": "l6_v2",
        "name": "L6 Momentum v2",
        "description": "L6 momentum on NSE 500 via new _momentum_engine (parallel-run for validation)",
        "strategy": "L6 momentum v2 (clean engine, same params as legacy L6 production)",
        "stocks": 499,
        "risk_profile": "Aggressive growth, no DD overlay",
        "data_dir": "nse500_data",
        "universe_file": "data/static/nse500_universe.csv",
        "portfolio_dir": "data/l6_v2_portfolios",
        "rebalance_cadence": "weekly_thu_fri",
    },
    "combo_defensive": {
        "id": "combo_defensive",
        "name": "COMBO Defensive",
        "description": "50-50 L6 + OM25 v3 with 100-DMA regime overlay (DD-conscious)",
        "strategy": "COMBO Defensive (L6 + OM25 priority-deduped + regime de-risk)",
        "stocks": 24,
        "risk_profile": "Growth with regime-aware capital preservation",
        "data_dir": "nse500_data",
        "universe_file": "data/static/nse500_universe.csv",
        "portfolio_dir": "data/combo_defensive_portfolios",
        "rebalance_cadence": "biweekly_fri_mon",
    },
}

UniverseId = Literal["nse500", "nifty250", "nifty100", "om25_v3", "tl25_v3", "l6_v2", "combo_defensive"]


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
