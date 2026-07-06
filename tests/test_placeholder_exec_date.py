"""Placeholder exec_date must roll off NSE holidays (audit L6).

The engine needs a synthetic "next bar" to execute the signal-day rebalance;
its date is also the exec_date label written to ProposedRebalance. Without a
holiday-aware roll it lands on a closed Friday, disagreeing with /summary's
holiday-aware next.exec_date. With ``market_service.next_trading_day_after``
injected it rolls to the true next trading day.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "kite-api"))

from app.services.market_service import next_trading_day_after
from data_pipeline.eod_proposal import StrategyState, _append_placeholder_bar


def _make_state():
    # A few June-2026 trading days ending Thursday 2026-06-25. Friday 2026-06-26
    # is Muharram (NSE holiday), so the next trading day is Monday 2026-06-29.
    idx = pd.to_datetime(["2026-06-23", "2026-06-24", "2026-06-25"])
    df = pd.DataFrame({"AAA": [100.0, 101.0, 102.0]}, index=idx)
    return StrategyState(
        close_panel=df.copy(), trade_panel=df.copy(),
        benchmark_aligned=pd.Series([1.0, 1.0, 1.0], index=idx),
        sma_200=df.copy(), atr_20=df.copy(),
        score_fn=lambda *a, **k: None,
        entry_signal_dates=pd.DatetimeIndex([]),
        weekly_signal_dates=pd.DatetimeIndex([]),
        top_n=25, exit_buffer=20, max_weight=0.1, slippage=0.0,
        drawdown_stop=0.2,
    )


def test_holiday_aware_resolver_rolls_to_monday():
    state = _make_state()
    exec_date = _append_placeholder_bar(
        state, pd.Timestamp("2026-06-25"),
        next_trading_day=next_trading_day_after,
    )
    # Skips Fri 06-26 (Muharram) + weekend -> Mon 06-29.
    assert exec_date == pd.Timestamp("2026-06-29")
    assert exec_date in state.close_panel.index


def test_default_weekend_only_bump_would_land_on_holiday_friday():
    # Documents the pre-fix behaviour: without the resolver it lands on the
    # closed Friday (this is exactly the mismatch T-05 fixes).
    state = _make_state()
    exec_date = _append_placeholder_bar(state, pd.Timestamp("2026-06-25"))
    assert exec_date == pd.Timestamp("2026-06-26")
