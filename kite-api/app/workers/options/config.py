"""Options worker configuration.

Worker-specific knobs only. Kite credentials and the data directory come
from the main app Settings (app.config) so the worker and the web service
never disagree about where tokens and data live.
"""
from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings

from app.config import get_settings


class OptionsWorkerSettings(BaseSettings):
    # Strikes each side of ATM per expiry (decided 2026-07-27: 10)
    strike_window: int = 10

    # How many option expiries to track (current + next)
    option_expiries: int = 2
    # How many futures expiries to track (current + next month)
    future_expiries: int = 2

    # Re-widen the subscription window when spot's nearest strike drifts
    # this many strikes from the window center (widen-only, never re-center)
    recenter_drift_strikes: int = 2

    # Local health endpoint (never exposed publicly; Railway healthcheck only).
    # Default binds loopback; the Railway service sets OPTIONS_HEALTH_HOST=0.0.0.0
    # so the container healthcheck can reach it.
    health_host: str = "127.0.0.1"
    health_port: int = 8090

    # Main-loop cadence while idle / between clock checks
    poll_seconds: float = 5.0

    # Time-based raw-tick flush (size-based flush is recorder.FLUSH_ROWS)
    flush_seconds: float = 60.0

    # Heartbeat cadence to options_worker_health (admin dashboard source)
    heartbeat_seconds: float = 30.0

    # Testing only: capture regardless of the market clock (post-close
    # snapshot ticks still flow). Never leave on in normal operation —
    # it bypasses the session lifecycle entirely.
    force_capture: bool = False

    class Config:
        env_prefix = "OPTIONS_"
        env_file = ".env"
        extra = "ignore"

    @property
    def options_data_dir(self) -> Path:
        d = get_settings().data_dir / "data" / "options"
        return d

    @property
    def dump_dir(self) -> Path:
        return self.options_data_dir / "instrument_dumps"

    @property
    def tokens_dir(self) -> Path:
        return self.options_data_dir / "tokens"

    @property
    def ticks_dir(self) -> Path:
        return self.options_data_dir / "ticks"


def get_worker_settings() -> OptionsWorkerSettings:
    return OptionsWorkerSettings()
