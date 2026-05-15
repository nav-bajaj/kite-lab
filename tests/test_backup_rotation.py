"""Tests for the rotation logic in scripts/backup_database.apply_rotation.

The DB-touching paths are exercised in a real environment with
DATABASE_URL set (the operator does that on the live Railway DB);
those don't have automated tests here. This file covers the offline,
file-naming-only retention math, which is where the easy-to-miss
calendar bugs live.
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from scripts.backup_database import apply_rotation, _parse_ts  # noqa: E402


def _make_backup(dir_: Path, ts: datetime) -> Path:
    name = ts.strftime("kitelab_db_%Y%m%d_%H%M%S.tar.gz")
    path = dir_ / name
    path.write_bytes(b"")
    return path


class ParseTsTests(unittest.TestCase):
    def test_valid_filename(self):
        ts = _parse_ts("kitelab_db_20260101_030405.tar.gz")
        self.assertEqual(ts, datetime(2026, 1, 1, 3, 4, 5))

    def test_invalid_prefix(self):
        self.assertIsNone(_parse_ts("other_20260101_030405.tar.gz"))

    def test_invalid_suffix(self):
        self.assertIsNone(_parse_ts("kitelab_db_20260101_030405.zip"))

    def test_invalid_timestamp(self):
        self.assertIsNone(_parse_ts("kitelab_db_notadate.tar.gz"))


class RotationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _populate(self, days_back: int, hour: int = 3) -> list[Path]:
        """Drop one backup per day going back days_back days from a fixed
        anchor date (mid-week mid-month so we get sensible week/month bins)."""
        anchor = datetime(2026, 6, 15, hour, 0, 0)  # Mon 2026-06-15 03:00
        files = []
        for d in range(days_back):
            ts = anchor - timedelta(days=d)
            files.append(_make_backup(self.dir, ts))
        return files

    def test_short_history_keeps_everything(self):
        """With 5 backups and 14d/12w/12m caps, nothing is dropped."""
        self._populate(5)
        removed = apply_rotation(self.dir, 14, 12, 12)
        self.assertEqual(removed, [])
        remaining = sorted(p.name for p in self.dir.iterdir())
        self.assertEqual(len(remaining), 5)

    def test_long_history_keeps_daily_plus_extras(self):
        """100 daily backups; expect 14 daily + ~12 weekly + ~3 monthly kept."""
        self._populate(100)
        removed = apply_rotation(self.dir, 14, 12, 12)
        remaining = [p for p in self.dir.iterdir() if p.is_file()]
        # Lower bound: at minimum we keep 14 daily (the others overlap)
        self.assertGreaterEqual(len(remaining), 14)
        # Upper bound: 14 daily + 12 weekly + 12 monthly = 38 max if no overlap
        self.assertLessEqual(len(remaining), 38)
        # Sanity: nothing removed twice
        self.assertEqual(len(removed) + len(remaining), 100)

    def test_most_recent_14_always_kept(self):
        """No matter what, the 14 most recent backups stay in the directory."""
        files = self._populate(60)
        most_recent_names = {p.name for p in sorted(files)[-14:]}
        apply_rotation(self.dir, 14, 12, 12)
        remaining_names = {p.name for p in self.dir.iterdir() if p.is_file()}
        self.assertTrue(most_recent_names.issubset(remaining_names))

    def test_dry_run_removes_nothing(self):
        self._populate(100)
        before = {p.name for p in self.dir.iterdir() if p.is_file()}
        removed = apply_rotation(self.dir, 14, 12, 12, dry_run=True)
        after = {p.name for p in self.dir.iterdir() if p.is_file()}
        # dry_run still reports what *would* be removed, but the files
        # themselves are untouched on disk.
        self.assertEqual(before, after)
        self.assertGreater(len(removed), 0)

    def test_ignores_non_backup_files(self):
        self._populate(5)
        (self.dir / "notes.txt").write_bytes(b"unrelated")
        apply_rotation(self.dir, 14, 12, 12)
        self.assertTrue((self.dir / "notes.txt").exists())


if __name__ == "__main__":
    unittest.main()
