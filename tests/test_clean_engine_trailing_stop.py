"""Spec: the ATR trailing stop must fire even when the 200-DMA is unavailable.

OM25 v3 runs with use_dma_exit=False and relies solely on the trailing stop.
The weekly exit guard in run_strategy used to skip the entire per-symbol exit
evaluation whenever sma_200 was NaN, which silently disabled the stop for any
name with <200 days of history. This test pins the invariant that the toggles
are independent: a >20%-from-peak crash must trigger an 'atr_stop' exit with an
all-NaN sma_200 panel.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from scripts._clean_engine import run_strategy


def _single_stock_crash_panels():
    cal = pd.bdate_range("2021-01-04", periods=40)
    sym = "AAA"

    prices = np.empty(40)
    prices[0:8] = 100.0                       # flat pre-entry
    prices[8:16] = np.linspace(105, 150, 8)   # ramp to a 150 peak
    prices[16:26] = np.linspace(145, 100, 10) # crash back down
    prices[26:40] = 100.0

    close = pd.DataFrame({sym: prices}, index=cal)
    trade = close.copy()                      # execute at close for simplicity
    sma_200 = pd.DataFrame(np.nan, index=cal, columns=[sym])  # never available
    atr_20 = pd.DataFrame(np.nan, index=cal, columns=[sym])   # -> default 0.02
    benchmark = pd.Series(100.0, index=cal)

    entry_signal = cal[5]    # executes cal[6]: buy AAA at 100, peak seeds at 100
    weekly_signal = cal[24]  # close 105 vs peak 150 = -30%, executes cal[25]

    def signal_function(date, **_):
        return pd.Series({sym: 1.0})

    return dict(
        close_panel=close,
        trade_panel=trade,
        calendar=cal,
        benchmark_aligned=benchmark,
        entry_signal_dates=[entry_signal],
        weekly_signal_dates=[weekly_signal],
        signal_function=signal_function,
        signal_function_args={},
        sma_200_panel=sma_200,
        atr_20_panel=atr_20,
    )


def test_trailing_stop_fires_without_dma():
    result = run_strategy(
        use_trailing_stop=True,
        use_dma_exit=False,
        **_single_stock_crash_panels(),
    )
    exits = result["exits"]
    assert not exits.empty, "expected the trailing stop to produce an exit"
    assert (exits["reason"] == "atr_stop").any(), (
        "trailing stop did not fire with an all-NaN sma_200 panel; "
        f"got reasons: {exits['reason'].tolist()}"
    )
