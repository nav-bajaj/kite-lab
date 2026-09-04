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

    # Authentication — Supabase Auth (primary; session-token verification
    # via the project JWKS, issuer https://<ref>.supabase.co/auth/v1)
    supabase_jwks_url: str = ""
    supabase_issuer: str = ""

    # Legacy authentication settings. The NextAuth HS256 path was retired
    # in the Clerk migration and Clerk itself at E3. Kept only because
    # they are still referenced by config consumers; nothing in the auth
    # path reads them.
    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"

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

    # Site-gate lockdown (tasks/site_gate). While the public site shows the
    # under-development page, only admin-role tokens may use protected
    # endpoints; the normally-public insights/indices readers require an
    # admin token too. Flip to false at launch.
    private_mode: bool = False

    # Outbound email (tasks/email_channel). Sent through AWS SES over SMTP
    # using stdlib smtplib — no boto3, so no new dependency on a pip-audit
    # surface that already carries an open High row (R-018).
    #
    # SES SENDS BUT CANNOT RECEIVE. email_from must be a real monitored
    # Google Workspace mailbox or every reply is lost.
    smtp_host: str = ""          # e.g. email-smtp.eu-north-1.amazonaws.com
    # 2587, NOT 587. Railway blocks outbound connections on the standard
    # SMTP ports (25/465/587) — verified 2026-08-27, the socket connect
    # simply times out with no error from SES. SES also listens on the
    # alternates 2465 and 2587, which are open. Same STARTTLS protocol,
    # only the port differs. Do not "fix" this back to 587.
    smtp_port: int = 2587
    smtp_user: str = ""
    smtp_password: str = ""
    email_from: str = "mail@marketworks.in"
    email_from_name: str = "Marketworks"
    email_reply_to: str = ""     # defaults to email_from when blank

    # Public origins used to build links inside emails. Wrong values here
    # produce dead unsubscribe links, which is a compliance failure, not a
    # cosmetic one.
    public_site_url: str = "https://marketworks.in"
    public_api_url: str = "https://kite-lab-production.up.railway.app"

    # Master switch. False = render and log, never hand anything to SES.
    # Left OFF by default so no environment starts mailing people by
    # accident; production turns it on deliberately.
    email_enabled: bool = False

    # Waitlist consent mode (tasks/email_channel). False = single opt-in:
    # a signup is mailable immediately. True = double opt-in: the signup
    # stays 'pending' until it clicks a confirm link.
    #
    # Founder chose single opt-in 2026-08-27 to see how signups behave.
    # The tradeoff is real: the form is public and unauthenticated, so
    # anyone can enter anyone else's address and we would mail someone who
    # never asked. Watch the SES complaint rate; if it climbs, flip this to
    # true — the confirm-token machinery is already built and waiting.
    waitlist_double_opt_in: bool = False

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

# Canonical strategy/universe lists — single source of truth to prevent the
# multi-file drift the rebalance audit flagged (O6/T-14). Import these instead
# of re-listing the strategies inline.
ALL_UNIVERSES: list = list(UNIVERSES.keys())

# The 4 client v3 portfolios that have an EOD proposed-orders producer
# (data_pipeline/eod_proposal.py). Distinct from the legacy nse500/nifty
# universes, which have no producer.
EOD_STRATEGIES = ("om25_v3", "tl25_v3", "l6_v2", "combo_defensive")


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
