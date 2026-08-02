"""Phase 5 archival + last_error lifecycle."""
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import pytest

from app.services.market_service import IST
from app.workers.options.archive import archive_old_days


def make_day(ticks_dir: Path, d: str, files: int = 3) -> Path:
    day = ticks_dir / f"date={d}"
    day.mkdir(parents=True)
    for i in range(files):
        pd.DataFrame({"ltp": [1.0, 2.0], "volume": [10, 20]}).to_parquet(day / f"nifty_{i:05d}.parquet")
    return day


class TestArchive:
    def test_old_days_archived_and_pruned_recent_kept(self, tmp_path):
        ticks, arch = tmp_path / "ticks", tmp_path / "archive"
        make_day(ticks, "2026-07-25")
        make_day(ticks, "2026-07-27")
        keep_edge = make_day(ticks, "2026-07-28")  # exactly keep_raw_days old -> kept
        keep = make_day(ticks, "2026-07-29")
        today_dir = make_day(ticks, "2026-07-30")

        stats = archive_old_days(ticks, arch, keep_raw_days=2, today=date(2026, 7, 30))
        assert stats["archived"] == 2 and stats["pruned"] == 2 and stats["failed"] == 0
        assert not (ticks / "date=2026-07-25").exists()
        assert not (ticks / "date=2026-07-27").exists()
        assert keep_edge.exists() and keep.exists() and today_dir.exists()
        assert (arch / "2026-07-25.tar.gz").exists()
        assert (arch / "2026-07-27.tar.gz").exists()

    def test_idempotent_when_nothing_left(self, tmp_path):
        ticks, arch = tmp_path / "ticks", tmp_path / "archive"
        make_day(ticks, "2026-07-25")
        stats1 = archive_old_days(ticks, arch, 2, date(2026, 7, 30))
        stats2 = archive_old_days(ticks, arch, 2, date(2026, 7, 30))
        assert stats1["pruned"] == 1
        assert stats2 == {"archived": 0, "pruned": 0, "skipped": 0, "failed": 0}

    def test_resume_prunes_without_rewriting(self, tmp_path):
        ticks, arch = tmp_path / "ticks", tmp_path / "archive"
        make_day(ticks, "2026-07-25")
        archive_old_days(ticks, arch, 2, date(2026, 7, 30))
        mtime = (arch / "2026-07-25.tar.gz").stat().st_mtime
        make_day(ticks, "2026-07-25")  # raw resurrected (crash-between-steps case)
        stats = archive_old_days(ticks, arch, 2, date(2026, 7, 30))
        assert stats["pruned"] == 1 and stats["archived"] == 0
        assert (arch / "2026-07-25.tar.gz").stat().st_mtime == mtime  # untouched
        assert not (ticks / "date=2026-07-25").exists()

    def test_mismatched_archive_keeps_raw(self, tmp_path):
        ticks, arch = tmp_path / "ticks", tmp_path / "archive"
        day = make_day(ticks, "2026-07-25", files=3)
        arch.mkdir()
        import tarfile
        with tarfile.open(arch / "2026-07-25.tar.gz", "w:gz") as tf:
            tf.add(day / "nifty_00000.parquet", arcname="date=2026-07-25/nifty_00000.parquet")
        stats = archive_old_days(ticks, arch, 2, date(2026, 7, 30))
        assert stats["failed"] == 1
        assert day.exists() and len(list(day.iterdir())) == 3  # raw untouched


class TestErrorLifecycle:
    def test_grace_window_then_surface_then_clear(self, monkeypatch):
        from app.workers.options.worker import OptionsWorker

        worker = OptionsWorker()
        worker.settings.selection_error_grace_polls = 3

        def boom():
            raise RuntimeError("Incorrect `api_key` or `access_token`.")
        monkeypatch.setattr("app.workers.options.worker._kite_client", boom)

        now = IST.localize(datetime(2026, 7, 30, 8, 30, 5))
        for _ in range(3):
            worker._run_daily_selection(now)
        assert worker.last_error is None  # inside grace window
        worker._run_daily_selection(now)
        assert worker.last_error is not None  # persisted past grace -> surfaced

        # success clears
        monkeypatch.setattr(worker, "_run_daily_selection", lambda n: None)
        worker._selection_failures = 0
        worker.last_error = None
        assert worker.last_error is None


class TestCaptureCloseOverride:
    def test_custom_close_extends_capture(self):
        from datetime import datetime, time as t
        from app.workers.options.scheduler import Phase, market_phase

        d = datetime(2026, 8, 3, 15, 35)  # Monday 15:35 IST
        assert market_phase(d) == Phase.EOD_FLUSH  # default 15:30 close
        assert market_phase(d, capture_close=t(15, 40)) == Phase.CAPTURE
        d2 = datetime(2026, 8, 3, 15, 41)
        assert market_phase(d2, capture_close=t(15, 40)) == Phase.EOD_FLUSH

    def test_settings_parse_and_default(self, monkeypatch):
        from datetime import time as t
        from app.workers.options.config import OptionsWorkerSettings

        assert OptionsWorkerSettings().capture_close_time == t(15, 30)
        monkeypatch.setenv("OPTIONS_CAPTURE_CLOSE", "15:40")
        assert OptionsWorkerSettings().capture_close_time == t(15, 40)
