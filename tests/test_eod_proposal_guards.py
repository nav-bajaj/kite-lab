"""Guards on the EOD producer (audit L5).

``_assert_panel_fresh`` is the backstop that stops a silently-failed data
refresh from emitting a back-dated proposal: on a real signal day the panel
must reach today's bar, else ``_pick_signal_date`` would fall back to the
previous cadence date and the API would serve an already-executed rebalance as
"upcoming".
"""
from __future__ import annotations

import pandas as pd
import pytest

from data_pipeline.eod_proposal import _assert_panel_fresh


def test_fresh_panel_passes_when_last_bar_reaches_required():
    # Panel includes today -> no raise.
    _assert_panel_fresh(pd.Timestamp("2026-06-19"),
                        pd.Timestamp("2026-06-19"), "tl25_v3")


def test_fresh_panel_passes_when_last_bar_beyond_required():
    _assert_panel_fresh(pd.Timestamp("2026-06-22"),
                        pd.Timestamp("2026-06-19"), "tl25_v3")


def test_stale_panel_raises():
    # Refresh failed: panel ends Thursday, but today (required) is Friday.
    with pytest.raises(RuntimeError, match="Stale price panel"):
        _assert_panel_fresh(pd.Timestamp("2026-06-18"),
                            pd.Timestamp("2026-06-19"), "tl25_v3")


def test_intraday_timestamps_compared_by_date_only():
    # A same-day bar with a time component still counts as fresh.
    _assert_panel_fresh(pd.Timestamp("2026-06-19 15:30"),
                        pd.Timestamp("2026-06-19 00:00"), "om25_v3")
