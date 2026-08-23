"""Tests for ca_lib pure functions.

Run:  .venv/bin/python -m pytest tasks/corporate_actions_fix/test_ca_lib.py -q
"""

import numpy as np
import pandas as pd
import pytest

from tasks.corporate_actions_fix.ca_lib import (
    classify_cliffs, classify_ratio, definitive_ca_mask, detect_cliffs,
    file_is_clean, seam_ratio,
)


def _series(vals, start="2026-01-01"):
    idx = pd.bdate_range(start, periods=len(vals))
    return pd.Series(vals, index=idx, dtype=float)


class TestDetectCliffs:
    def test_flat_series_has_no_cliffs(self):
        s = _series([100, 101, 99, 102, 103])
        assert detect_cliffs(s).empty

    def test_bonus_1_1_cliff_detected(self):
        s = _series([100, 102, 51, 52])       # ~x0.5 step
        c = detect_cliffs(s)
        assert len(c) == 1
        assert c.iloc[0]["move_pct"] == -50.0

    def test_normal_limit_moves_not_flagged(self):
        s = _series([100, 120, 96, 115])      # ±20% circuit-style moves
        assert detect_cliffs(s).empty

    def test_real_crash_detected_but_unclassified(self):
        s = _series([100, 100, 44, 43])       # -56% YESBANK-style
        c = classify_cliffs(detect_cliffs(s))
        assert len(c) == 1
        assert c.iloc[0]["label"] == "unclassified"


class TestClassifyRatio:
    def test_exact_bonus_1_1(self):
        assert classify_ratio(0.5) == "bonus_1:1_or_split_1:2"

    def test_bonus_1_2_with_market_move_on_top(self):
        # 1:2 bonus (x0.6667) plus a -2% market day
        assert classify_ratio(0.6667 * 0.98) == "bonus_1:2"

    def test_undo_ratio_for_flip_flop_files(self):
        assert classify_ratio(1.96).startswith("undo_")

    def test_arbitrary_demerger_ratio_is_none(self):
        assert classify_ratio(0.172) is None   # ADANIENT 2015 observed

    def test_tolerance_boundary(self):
        assert classify_ratio(0.5 * 1.05) is None   # 5% off → no snap


class TestSeamRatio:
    def test_recovers_rebase_factor(self):
        old = _series([300, 303, 306, 309, 312, 315])
        new = old * (2 / 3)                    # 1:2 bonus re-base
        r = seam_ratio(old, new)
        assert r == pytest.approx(2 / 3, rel=1e-9)

    def test_thin_overlap_returns_none(self):
        old = _series([300, 303, 306])
        assert seam_ratio(old, old * 0.5) is None

    def test_mixed_regime_overlap_refused(self):
        old = _series([300, 303, 306, 309, 312, 315])
        new = old.copy()
        new.iloc[3:] *= 0.5                    # half raw, half adjusted
        assert seam_ratio(old, new) is None

    def test_identity_when_no_action(self):
        old = _series([100, 101, 102, 103, 104, 105])
        assert seam_ratio(old, old) == pytest.approx(1.0)


class TestDefinitiveCaMask:
    def test_flip_flop_pair_is_definitive(self):
        # ECLERX-style oscillation: -50% then +97% four sessions later
        s = _series([1000, 1010, 495, 500, 505, 500, 985, 990])
        c = classify_cliffs(detect_cliffs(s))
        assert definitive_ca_mask(c).all()

    def test_isolated_33pct_rally_not_definitive(self):
        # BANKBARODA 2017-10-25 PSU-recap day: +31% real, snaps to 4/3
        s = _series([140, 141, 185, 184, 186])
        c = classify_cliffs(detect_cliffs(s))
        assert len(c) == 1 and c.iloc[0]["label"] != "unclassified"
        assert not definitive_ca_mask(c).any()

    def test_isolated_split_1_10_is_definitive(self):
        s = _series([3000, 3030, 303, 305])    # ANGELONE-style -90%
        c = classify_cliffs(detect_cliffs(s))
        assert definitive_ca_mask(c).all()

    def test_far_apart_cliffs_not_flip_flop(self):
        vals = [140, 141, 185, 184] + [184] * 40 + [123, 124]
        s = _series(vals)
        c = classify_cliffs(detect_cliffs(s))
        assert len(c) == 2
        assert not definitive_ca_mask(c).any()


class TestFileIsClean:
    def test_clean_file(self):
        assert file_is_clean(_series(list(np.linspace(100, 140, 30))))

    def test_ca_signature_file_is_dirty(self):
        assert not file_is_clean(_series([100, 102, 51, 52]))

    def test_real_crash_allowed_by_default(self):
        assert file_is_clean(_series([100, 100, 44, 43]))

    def test_real_crash_rejected_when_strict(self):
        assert not file_is_clean(_series([100, 100, 44, 43]),
                                 allow_unclassified=False)
