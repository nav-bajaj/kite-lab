"""Heartbeat store roundtrip + force-capture override."""
from datetime import datetime

import pytest

from app.services import worker_health_store as whs
from app.services.market_service import IST


@pytest.fixture()
def db_url(tmp_path):
    return f"sqlite:///{tmp_path}/health.db"


class TestHeartbeatStore:
    def test_read_empty_returns_none(self, db_url):
        assert whs.read_heartbeat(database_url=db_url) is None

    def test_write_read_roundtrip_single_row(self, db_url):
        whs.write_heartbeat("capture", {"packets": 12, "nested": {"a": 1}}, database_url=db_url)
        whs.write_heartbeat("capture", {"packets": 99}, database_url=db_url)
        row = whs.read_heartbeat(database_url=db_url)
        assert row["phase"] == "capture"
        assert row["payload"] == {"packets": 99}
        assert row["id"] == 1

    def test_write_failure_is_silent(self):
        whs.write_heartbeat("idle", {}, database_url="postgresql://nohost.invalid/db")


class TestForceCapture:
    def test_force_capture_overrides_clock(self, monkeypatch):
        from app.workers.options.scheduler import Phase
        from app.workers.options.worker import OptionsWorker

        worker = OptionsWorker()
        worker.settings.force_capture = True
        worker.settings.heartbeat_seconds = 10**9  # keep the test offline
        monkeypatch.setattr(worker, "_enter_capture", lambda now: None)

        sunday_night = IST.localize(datetime(2026, 7, 26, 23, 0))
        worker.tick(sunday_night)
        assert worker.phase == Phase.CAPTURE
