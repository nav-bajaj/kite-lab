"""Spec tests for the two load-bearing rules in the stickiness probe."""
import numpy as np
import pytest

from wall_stickiness_probe import convergence, wall_beta


class TestWallBeta:
    def test_anchored_wall_gives_beta_zero(self):
        assert wall_beta([24000] * 5, [23900, 23950, 24000, 24050, 24100]) == pytest.approx(0.0)

    def test_wall_tracking_spot_one_for_one_gives_beta_one(self):
        s = [23900, 23950, 24000, 24050, 24100]
        assert wall_beta(s, s) == pytest.approx(1.0)

    def test_wall_moving_half_as_far_gives_beta_half(self):
        spot = np.array([23900, 23950, 24000, 24050, 24100], float)
        assert wall_beta(24000 + (spot - 24000) / 2, spot) == pytest.approx(0.5)

    def test_flat_spot_is_none_not_a_divide_by_zero(self):
        assert wall_beta([24000, 24050], [24000, 24000]) is None

    def test_too_short_a_window_is_none(self):
        assert wall_beta([24000], [24000]) is None


class TestConvergence:
    def test_spot_moving_toward_the_wall_is_positive(self):
        # wall 24000, spot 24100 -> 24050: gap 100 -> 50
        assert convergence(24100, 24050, 24000) == pytest.approx(50.0)

    def test_spot_moving_away_is_negative(self):
        assert convergence(24100, 24150, 24000) == pytest.approx(-50.0)

    def test_overshooting_the_wall_counts_only_the_distance_closed(self):
        # 24100 -> 23950 crosses the wall and ends 50 away: 100 - 50
        assert convergence(24100, 23950, 24000) == pytest.approx(50.0)

    def test_wall_reference_is_the_decision_minute_not_the_later_wall(self):
        # REGRESSION: a wall that CHASES price must not score as convergence.
        # Spot runs 24100 -> 24300 away from the 13:00 wall at 24000. Had we
        # measured against a wall that followed to 24300, this would read as a
        # perfect pin instead of the divergence it is.
        assert convergence(24100, 24300, 24000) == pytest.approx(-200.0)
