"""EOD orchestrator dead-man's-switch (audit O4).

``_strategies_missing_todays_proposal`` is what turns a silently-missing
producer (the l6_v2 miss that went unnoticed) into a failed wrapper Job. We
stub the Session (ProposedRebalance uses JSONB, not sqlite-friendly).
"""
from __future__ import annotations

from datetime import date

import pytest

from app.scheduler import tasks
from app.models import database


class _FakeQuery:
    def __init__(self, present):
        self._present = present  # set of (universe, data_as_of)
        self._u = None
        self._d = None

    def filter(self, *exprs):
        for e in exprs:
            right = getattr(e, "right", None)
            val = getattr(right, "value", None) if right is not None else None
            if isinstance(val, str):
                self._u = val
            elif isinstance(val, date):
                self._d = val
        return self

    def first(self):
        return object() if (self._u, self._d) in self._present else None


class _FakeSession:
    def __init__(self, present):
        self._present = present

    def query(self, _model):
        return _FakeQuery(self._present)

    def close(self):
        pass


@pytest.fixture
def install_present(monkeypatch):
    def install(present):
        monkeypatch.setattr(database, "get_session_local",
                            lambda: (lambda: _FakeSession(set(present))))
    return install


TODAY = date(2026, 7, 6)


def test_all_present_returns_empty(install_present):
    install_present({("om25_v3", TODAY), ("tl25_v3", TODAY)})
    assert tasks._strategies_missing_todays_proposal(
        ["om25_v3", "tl25_v3"], TODAY) == []


def test_missing_one_is_flagged(install_present):
    install_present({("om25_v3", TODAY)})
    assert tasks._strategies_missing_todays_proposal(
        ["om25_v3", "tl25_v3"], TODAY) == ["tl25_v3"]


def test_stale_row_from_prior_day_counts_as_missing(install_present):
    # A row dated yesterday (producer didn't run today) must not satisfy it.
    install_present({("om25_v3", date(2026, 7, 3))})
    assert tasks._strategies_missing_todays_proposal(
        ["om25_v3"], TODAY) == ["om25_v3"]
