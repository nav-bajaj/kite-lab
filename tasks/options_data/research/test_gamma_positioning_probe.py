"""Spec tests for the gamma-positioning probe's pure functions.

The probe's conclusions are only as good as its scoring rule, and the
rule has two properties that must not drift: fills are taken at the side
a seller actually gets (bid in, ask out), and an afternoon decision is
scored on afternoon P&L alone. The first pass of this probe reported a
0.47 correlation because it scored a 13:00 decision with a 15:15 input;
test_split_at_excludes_morning_pnl is the regression guard for that.
"""
import numpy as np
import pandas as pd
import pytest

from gamma_positioning_probe import (
    bucket_slope, pick_nearest_strike, simulate_straddle, split_at,
)


def _bars(rows):
    return pd.DataFrame(rows, columns=["hm", "kind", "strike", "close",
                                       "bid_close", "ask_close"])


def _flat_day(strike=100.0, ce=10.0, pe=10.0, times=("09:20", "13:00", "15:15")):
    return _bars([[t, k, strike, v, v - 0.5, v + 0.5]
                  for t in times for k, v in (("CE", ce), ("PE", pe))])


class TestPickNearestStrike:
    def test_picks_the_closest_traded_strike(self):
        assert pick_nearest_strike([24200, 24250, 24300], 24263) == 24250.0

    def test_exact_hit_returns_that_strike(self):
        assert pick_nearest_strike([24200, 24250], 24250) == 24250.0

    def test_target_outside_the_grid_clamps_to_the_nearest_end(self):
        assert pick_nearest_strike([24200, 24250, 24300], 99999) == 24300.0

    def test_empty_grid_is_an_error_not_a_silent_nan(self):
        with pytest.raises(ValueError):
            pick_nearest_strike([], 24000)


class TestSimulateStraddle:
    def test_credit_is_taken_at_the_bid_and_exit_paid_at_the_ask(self):
        # bid 9.5 x2 in = 19.0 credit; ask 10.5 x2 out = 21.0 cost => -2.0
        sim = simulate_straddle(_flat_day(), 100.0)
        assert sim["credit"] == pytest.approx(19.0)
        assert sim["final"] == pytest.approx(-2.0)

    def test_decay_to_zero_earns_the_full_credit_less_the_exit_spread(self):
        bars = _bars([["09:20", "CE", 100.0, 10.0, 9.5, 10.5],
                      ["09:20", "PE", 100.0, 10.0, 9.5, 10.5],
                      ["15:15", "CE", 100.0, 0.2, 0.1, 0.3],
                      ["15:15", "PE", 100.0, 0.2, 0.1, 0.3]])
        sim = simulate_straddle(bars, 100.0)
        assert sim["final"] == pytest.approx(19.0 - 0.6)

    def test_mae_is_the_worst_mark_and_carries_its_timestamp(self):
        bars = _bars([["09:20", "CE", 100.0, 10.0, 9.5, 10.5],
                      ["09:20", "PE", 100.0, 10.0, 9.5, 10.5],
                      ["11:00", "CE", 100.0, 20.0, 19.5, 20.5],   # -21.0 vs credit
                      ["11:00", "PE", 100.0, 20.0, 19.5, 20.5],
                      ["15:15", "CE", 100.0, 5.0, 4.5, 5.5],
                      ["15:15", "PE", 100.0, 5.0, 4.5, 5.5]])
        sim = simulate_straddle(bars, 100.0)
        assert sim["mae"] == pytest.approx(19.0 - 40.0)
        assert sim["mae_t"] == "11:00"

    def test_missing_entry_leg_returns_none_rather_than_a_flat_day(self):
        # an unfillable variant must not score as 0.0 and dilute the mean
        bars = _flat_day()
        assert simulate_straddle(bars[bars.kind != "PE"], 100.0) is None

    def test_missing_exit_leg_returns_none(self):
        bars = _flat_day(times=("09:20", "13:00"))
        assert simulate_straddle(bars, 100.0, exit_t="15:15") is None

    def test_untraded_strike_returns_none(self):
        assert simulate_straddle(_flat_day(strike=100.0), 24999.0) is None

    def test_path_is_clipped_to_the_holding_window(self):
        bars = _flat_day(times=("09:15", "09:20", "13:00", "15:15", "15:29"))
        sim = simulate_straddle(bars, 100.0)
        assert sim["path"].index.min() == "09:20"
        assert sim["path"].index.max() == "15:15"


class TestSplitAt:
    def test_split_at_excludes_morning_pnl(self):
        # REGRESSION: the afternoon score must not inherit the morning's gain
        path = pd.Series({"09:20": 0.0, "13:00": 30.0, "15:15": 35.0})
        got = split_at(path, "13:00")
        assert got["at_t"] == pytest.approx(30.0)
        assert got["pnl_after"] == pytest.approx(5.0)

    def test_mae_after_is_measured_from_the_decision_point(self):
        path = pd.Series({"09:20": 0.0, "13:00": 30.0, "14:00": 10.0, "15:15": 35.0})
        assert split_at(path, "13:00")["mae_after"] == pytest.approx(-20.0)

    def test_mae_after_is_zero_when_the_afternoon_never_dips(self):
        path = pd.Series({"13:00": 10.0, "15:15": 25.0})
        assert split_at(path, "13:00")["mae_after"] == pytest.approx(0.0)

    def test_returns_none_when_the_split_point_has_no_afternoon(self):
        assert split_at(pd.Series({"09:20": 0.0, "12:00": 5.0}), "13:00") is None


class TestBucketSlope:
    @pytest.mark.parametrize("dc,want", [
        (0.05, "building"), (-0.05, "decaying"),
        (0.01, "building"), (-0.01, "decaying"),      # band edges are inclusive
        (0.009, "flat"), (-0.009, "flat"), (0.0, "flat"),
    ])
    def test_labels(self, dc, want):
        assert bucket_slope(dc) == want

    def test_dead_band_keeps_sampling_noise_from_reading_as_direction(self):
        assert bucket_slope(0.004) == "flat"
        assert bucket_slope(0.004, band=0.001) == "building"

    @pytest.mark.parametrize("bad", [None, np.nan])
    def test_missing_slope_is_unknown_not_flat(self, bad):
        assert bucket_slope(bad) == "unknown"
