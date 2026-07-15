"""JobResponse must serialize timestamps with an explicit UTC offset.

Job rows are stamped naive-UTC (func.now() on UTC Postgres / utcnow()).
Without the offset the dashboard's `new Date()` parses them as browser-local
IST and every Recent Jobs entry renders ~5.5h stale.
"""
from datetime import datetime, timezone

from app.schemas.jobs import JobResponse


def _job(**kw):
    base = dict(id="j1", command="daily_pipeline", status="completed",
                created_at=datetime(2026, 7, 14, 16, 47, 59))
    base.update(kw)
    return JobResponse(**base)


def test_naive_timestamps_serialized_as_utc():
    j = _job(started_at=datetime(2026, 7, 14, 16, 48, 0), ended_at=None)
    data = j.model_dump_json()
    assert '"created_at":"2026-07-14T16:47:59Z"' in data
    assert '"started_at":"2026-07-14T16:48:00Z"' in data
    assert '"ended_at":null' in data


def test_aware_timestamps_left_untouched():
    aware = datetime(2026, 7, 14, 16, 47, 59, tzinfo=timezone.utc)
    j = _job(created_at=aware)
    assert j.created_at == aware
