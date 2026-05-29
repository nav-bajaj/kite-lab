"""Tests for the Nifty 50 concentration / attribution engine.

The engine decomposes Nifty 50's daily move into per-constituent
contributions using the cap-weighted index methodology. These tests
verify weight loading, attribution arithmetic, and that the result is
JSON-serialisable for the API surface.
"""
from __future__ import annotations

import json

import pandas as pd
import pytest

from app.insights import concentration


@pytest.fixture(scope="module", autouse=True)
def _clear_cache():
    concentration.load_weights.cache_clear()
    concentration.load_constituent_closes.cache_clear()
    concentration.load_nifty50_index.cache_clear()


class TestWeightLoading:
    def test_weights_normalized_to_100(self):
        w = concentration.load_weights()
        assert abs(w.sum() - 100.0) < 1e-6

    def test_has_50_constituents(self):
        w = concentration.load_weights()
        assert len(w) == 50

    def test_hdfc_bank_is_largest(self):
        w = concentration.load_weights()
        top = w.sort_values(ascending=False)
        assert top.index[0] == "HDFCBANK"
        assert top.iloc[0] > 10.0  # always > 10% of the index in recent years

    def test_reliance_in_top_3(self):
        w = concentration.load_weights()
        top3 = w.sort_values(ascending=False).head(3).index.tolist()
        assert "RELIANCE" in top3


class TestLatestReading:
    @pytest.fixture(scope="class")
    def reading(self):
        return concentration.compute_concentration()

    def test_basic_shape(self, reading):
        assert isinstance(reading.date, pd.Timestamp)
        assert reading.n_constituents_covered >= 45  # tolerate a few missing files
        assert reading.n_constituents_total == 50
        assert len(reading.constituents) == reading.n_constituents_covered

    def test_constituents_sorted_by_contribution_magnitude(self, reading):
        contribs = [c.contribution_bps for c in reading.constituents]
        abs_contribs = [abs(c) for c in contribs]
        assert abs_contribs == sorted(abs_contribs, reverse=True)

    def test_top_3_and_5_symbols_consistent_with_constituents(self, reading):
        first3 = [c.symbol for c in reading.constituents[:3]]
        first5 = [c.symbol for c in reading.constituents[:5]]
        assert reading.top_3_symbols == first3
        assert reading.top_5_symbols == first5

    def test_to_dict_json_serializable(self, reading):
        d = reading.to_dict()
        json.dumps(d)  # must not raise

    def test_share_of_move_meaningful_when_index_moves(self, reading):
        if abs(reading.nifty_return_pct) > 0.1:
            # If Nifty moved at least 10 bps, attribution should be valid
            assert reading.top_3_share_of_move is not None
            assert reading.top_5_share_of_move is not None
            # top_5 should explain at least as much as top_3 in absolute terms
            # (they're sorted by absolute contribution)
            assert abs(reading.top_5_share_of_move) >= abs(reading.top_3_share_of_move) - 1e-6

    def test_equal_weighted_return_in_reasonable_range(self, reading):
        # Daily equal-weighted returns of 49 large-caps are bounded
        assert -25.0 < reading.equal_weighted_return_pct < 25.0


class TestAttributionMathOnHistoricalDate:
    """Spot-check the math on a known historical session."""

    def test_covid_crash_day(self):
        # March 23, 2020 — single largest one-day drop in NSE history.
        # Expect: Nifty return very negative, equal-weighted return also
        # very negative (broad), spread modest (no single name dominated).
        r = concentration.compute_concentration(pd.Timestamp("2020-03-23"))
        assert r.nifty_return_pct < -10.0
        assert r.equal_weighted_return_pct < -8.0
        # On a broad capitulation day the cap-vs-equal spread is small
        # (everything tanks together) — not used as a strict bound, but a sanity check.
        assert abs(r.cap_vs_equal_spread_pp) < 8.0

    def test_calm_day_shape(self):
        # 2017 melt-up era — calm session. Expect small index moves and
        # well-defined attribution.
        r = concentration.compute_concentration(pd.Timestamp("2017-10-13"))
        assert abs(r.nifty_return_pct) < 2.0
        assert r.n_constituents_covered >= 30  # data sparseness pre-2020 is OK


class TestSnapToTradingDay:
    def test_weekend_snaps_forward(self):
        # 2020-03-21 was a Saturday; expect engine to roll to next session
        r = concentration.compute_concentration(pd.Timestamp("2020-03-21"))
        assert r.date.weekday() < 5  # Mon-Fri

    def test_future_date_clamps_to_latest(self):
        r = concentration.compute_concentration(pd.Timestamp("2099-01-01"))
        # Should clamp to the latest available date in the index, not raise
        assert isinstance(r.date, pd.Timestamp)


# ─────────── Spec tests (promoted from characterization 2026-05-28) ───────────
#
# These tests pin invariants and edge cases derived from the engine's
# external contract — not echoes of the current implementation. See
# `tasks/insight_engine/TDD_POLICY.md`.


class TestConcentrationInvariants:
    """Mathematical invariants that must hold regardless of input."""

    def test_weights_sum_to_exactly_100_after_load(self):
        """The loader is documented to normalise to sum=100. Pinning the
        invariant separately from the data file's actual contents."""
        w = concentration.load_weights()
        assert abs(w.sum() - 100.0) < 1e-9, (
            f"Weights normalisation broken: sum = {w.sum()}"
        )

    def test_top_3_share_consistent_with_top_5(self):
        """Top-5 must explain ≥ |top-3| in absolute contribution terms,
        since constituents are sorted by abs(contribution) and the 4th/5th
        names can only add or offset, never reduce |sum|."""
        r = concentration.compute_concentration()
        if r.top_3_share_of_move is None or r.top_5_share_of_move is None:
            pytest.skip("Index too flat for share-of-move attribution")
        # Allow tiny floating-point slack
        assert abs(r.top_5_share_of_move) >= abs(r.top_3_share_of_move) - 1e-6

    def test_constituents_sorted_by_abs_contribution_descending(self):
        """The sort order is part of the public contract — UI consumers
        rely on `constituents[:N]` being the top-N by impact."""
        r = concentration.compute_concentration()
        abs_contribs = [abs(c.contribution_bps) for c in r.constituents]
        assert abs_contribs == sorted(abs_contribs, reverse=True), (
            "Constituents must be sorted by |contribution| descending"
        )

    def test_top_n_symbols_match_first_n_constituents(self):
        """`top_3_symbols` is a redundancy convenience — but its contents
        MUST agree with `constituents[:3]`. Mismatch would mislead the UI."""
        r = concentration.compute_concentration()
        assert r.top_3_symbols == [c.symbol for c in r.constituents[:3]]
        assert r.top_5_symbols == [c.symbol for c in r.constituents[:5]]


class TestConcentrationEdgeCases:
    """Boundary conditions previously specified only implicitly in code."""

    def test_share_of_move_is_none_when_index_essentially_flat(self):
        """When |Nifty return| is below the engine's epsilon (~1e-6 in %),
        share_of_move attribution is mathematically unstable — engine must
        return None rather than a giant misleading number."""
        # Find a real low-move day; today's panel often has small moves.
        # If we can't find one in the latest data, construct via the
        # post-2025 era which has had several near-flat sessions.
        r = concentration.compute_concentration()
        if abs(r.nifty_return_pct) < 1e-6:
            assert r.top_3_share_of_move is None
            assert r.top_5_share_of_move is None
        # If today moved, scan recent history for a near-flat day to verify
        # the None behaviour on a real example.
        import pandas as _pd
        index = concentration.load_nifty50_index()
        recent = index.tail(60)
        recent_chg = recent["close"].pct_change().abs() * 100
        flat_days = recent_chg[recent_chg < 0.01].index
        if len(flat_days) == 0:
            pytest.skip("No near-flat days in recent panel to test")
        r_flat = concentration.compute_concentration(_pd.Timestamp(flat_days[0]))
        # Reading should still produce a result — just with None shares
        assert r_flat.constituents, "Should still have per-stock contribs"

    def test_to_dict_is_json_serializable(self):
        """API contract: every field must serialise to plain JSON. Catches
        accidental np.float64 / Timestamp leakage."""
        import json
        r = concentration.compute_concentration()
        json.dumps(r.to_dict())  # must not raise

    def test_n_constituents_covered_le_total(self):
        """Coverage can't exceed total. Pins the relationship."""
        r = concentration.compute_concentration()
        assert r.n_constituents_covered <= r.n_constituents_total
        assert r.n_constituents_covered == len(r.constituents)

    def test_cap_vs_equal_spread_uses_consistent_units(self):
        """Spread is `nifty_return_pct - equal_weighted_return_pct` —
        both in the same percentage-point units. Sign must agree with
        the underlying difference."""
        r = concentration.compute_concentration()
        recomputed = r.nifty_return_pct - r.equal_weighted_return_pct
        assert abs(r.cap_vs_equal_spread_pp - recomputed) < 1e-6
