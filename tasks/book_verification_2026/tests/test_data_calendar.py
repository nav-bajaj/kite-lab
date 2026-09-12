"""Group B of TESTS_DATA.md — the store's session calendar (D-09..D-11)."""
from __future__ import annotations

import pandas as pd

from _store import master, scan, sessions_calendar


def _span():
    sc, cal = scan(), sessions_calendar()
    return sc, cal[(cal >= sc.sessions[0]) & (cal <= sc.sessions[-1])]


def test_d09_store_sessions_are_exactly_the_nse_session_calendar():
    sc, span = _span()
    extra = sc.sessions.difference(sessions_calendar())
    missing = span.difference(sc.sessions)
    assert extra.empty, f"D-09: {len(extra)} store sessions are not NSE sessions: {[str(d.date()) for d in extra[:8]]}"
    assert missing.empty, (f"D-09: {len(missing)} NSE sessions inside the store span are absent from every price file: "
                           f"{[str(d.date()) for d in missing[:8]]}")


def test_d10_weekend_sessions_only_where_the_calendar_has_them():
    sc, span = _span()
    store_wk = set(sc.sessions[sc.sessions.dayofweek >= 5])
    cal_wk = set(span[span.dayofweek >= 5])
    assert store_wk == cal_wk, (f"D-10: weekend/special sessions disagree — store-only "
                                f"{sorted(str(d.date()) for d in store_wk - cal_wk)}, "
                                f"calendar-only {sorted(str(d.date()) for d in cal_wk - store_wk)}")


def test_d11_store_calendar_defect_list_is_empty():
    cal = pd.read_csv(master() / "qa/calendar.csv")
    assert cal.empty, f"D-11: qa/calendar.csv lists {len(cal)} files with date defects: {cal.head(8).to_dict('records')}"
