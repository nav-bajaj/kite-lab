"""
Universe Configuration

Centralized configuration for different stock universes (NSE 500, Nifty 100, Nifty 250).
Used by portfolio refresh and signal generation scripts.
"""

from pathlib import Path

UNIVERSE_CONFIG = {
    "nse500": {
        "name": "NSE 500",
        "universe_file": Path("data/static/nse500_universe.csv"),
        "price_dir": Path("nse500_data"),
        "portfolio_dir": Path("data/final_portfolio"),
        "portfolio_file": Path("data/final_portfolio/final_portfolio_24.csv"),
        "signals_file": Path("data/final_portfolio/final_top24_signals.csv"),
        "experiments_dir": Path("experiments/final_portfolio"),
    },
    "nifty100": {
        "name": "Nifty 100",
        "universe_file": Path("data/static/nifty100_universe.csv"),
        "price_dir": Path("nse500_data"),  # Uses same price data (subset)
        "portfolio_dir": Path("data/nifty100_portfolio"),
        "portfolio_file": Path("data/nifty100_portfolio/final_portfolio_24.csv"),
        "signals_file": Path("data/nifty100_portfolio/final_top24_signals.csv"),
        "experiments_dir": Path("nifty_100_tests"),
    },
    "nifty250": {
        "name": "Nifty 250",
        "universe_file": Path("data/static/nifty250_universe.csv"),
        "price_dir": Path("nse500_data"),  # Uses same price data (subset)
        "portfolio_dir": Path("data/nifty250_portfolio"),
        "portfolio_file": Path("data/nifty250_portfolio/final_portfolio_24.csv"),
        "signals_file": Path("data/nifty250_portfolio/final_top24_signals.csv"),
        "experiments_dir": Path("nifty_250_tests"),
    },
}

# Default signal generation parameters
SIGNAL_DEFAULTS = {
    "lookback_months": 6,
    "lookback_days": 126,
    "skip_days": 0,
    "vol_floor": 0.05,
    "vol_power": 1.0,
    "top_n": 24,
}

# Indian market hours (IST)
MARKET_OPEN_HOUR = 9
MARKET_OPEN_MINUTE = 15
MARKET_CLOSE_HOUR = 15
MARKET_CLOSE_MINUTE = 30


def get_universe_config(universe: str) -> dict:
    """Get configuration for a universe."""
    if universe not in UNIVERSE_CONFIG:
        valid = ", ".join(UNIVERSE_CONFIG.keys())
        raise ValueError(f"Unknown universe '{universe}'. Valid options: {valid}")
    return UNIVERSE_CONFIG[universe]


def list_universes() -> list:
    """List available universes."""
    return list(UNIVERSE_CONFIG.keys())
