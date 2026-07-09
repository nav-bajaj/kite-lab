"""Spec tests for the relative-strength ranking engine (`rs_rank.py`).

Authored FIRST per TDD_POLICY.md. Inputs are synthetic close panels with
deterministic return orderings so the resulting ranks are analytically
known, plus an improver panel that pins the 21-day rank-delta / inflection
contract.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from app.insights import rs_rank as rr


def _panel_with_ordered_returns() -> pd.DataFrame:
    """Five stocks whose total return over the whole window is strictly
    ordered A > B > C > D > E at every horizon (monotone ramps of
    different slopes). A must rank 1 (strongest)."""
    n = 300
    dates = pd.date_range("2023-01-02", periods=n, freq="B")
    slopes = {"A": 0.40, "B": 0.30, "C": 0.20, "D": 0.10, "E": 0.02}
    data = {}
    for sym, sl in slopes.items():
        data[sym] = 100.0 * (1 + sl * np.linspace(0, 1, n))
    return pd.DataFrame(data, index=dates)


class TestComposite:
    def test_weights_documented_and_normalized(self):
        assert abs(sum(rr.RS_WEIGHTS.values()) - 1.0) < 1e-9
        assert set(rr.RS_WEIGHTS) == {"1m", "3m", "6m", "12m"}

    def test_strongest_stock_ranks_one(self):
        close = _panel_with_ordered_returns()
        table = rr.compute_rs_table(close.index[-1], close)
        assert table["A"].rank == 1
        assert table["E"].rank == 5
        # strictly decreasing ranks across the ordered set
        ranks = [table[s].rank for s in ["A", "B", "C", "D", "E"]]
        assert ranks == sorted(ranks)

    def test_percentile_monotonic_with_rank(self):
        close = _panel_with_ordered_returns()
        table = rr.compute_rs_table(close.index[-1], close)
        assert table["A"].percentile > table["E"].percentile
        assert 0.0 <= table["E"].percentile <= 100.0
        assert 0.0 <= table["A"].percentile <= 100.0

    def test_insufficient_history_gets_no_rank(self):
        # A stock with <252 sessions can't get a 12M return → unranked.
        n = 120
        dates = pd.date_range("2023-01-02", periods=n, freq="B")
        close = pd.DataFrame(
            {"X": np.linspace(100, 150, n), "Y": np.linspace(100, 120, n)},
            index=dates,
        )
        table = rr.compute_rs_table(dates[-1], close)
        assert table == {} or all(e.rank is None for e in table.values())


class TestRankDeltaAndInflection:
    def _improver_panel(self) -> pd.DataFrame:
        """Stock IMP is the weakest 21 sessions ago and among the strongest
        today (a late accelerator); STABLE stays strong throughout. IMP must
        show a large positive rank delta."""
        n = 320
        dates = pd.date_range("2023-01-02", periods=n, freq="B")
        base = np.linspace(0, 1, n)
        panel = {}
        # A cohort of steady names spanning the return spectrum
        for i, sym in enumerate([f"S{i}" for i in range(8)]):
            panel[sym] = 100.0 * (1 + (0.05 + 0.03 * i) * base)
        # STABLE: consistently strong
        panel["STABLE"] = 100.0 * (1 + 0.45 * base)
        # IMP: flat for most of the window, then a sharp late ramp so its
        # trailing short-horizon returns jump in the last ~21 sessions.
        imp = np.concatenate([
            np.full(n - 22, 100.0),
            np.linspace(100.0, 180.0, 22),
        ])
        panel["IMP"] = imp
        return pd.DataFrame(panel, index=dates)

    def test_rank_delta_positive_for_late_accelerator(self):
        close = self._improver_panel()
        asof = close.index[-1]
        table = rr.compute_rs_table(asof, close)
        imp = table["IMP"]
        assert imp.rank_21d_ago is not None and imp.rank_delta_21d is not None
        assert imp.rank_delta_21d > 0, "late accelerator should improve its rank"

    def test_inflection_cohort_sorted_by_delta(self):
        close = self._improver_panel()
        asof = close.index[-1]
        cohort = rr.get_inflection_cohort(asof, close, top_n=5)
        assert len(cohort) <= 5
        deltas = [e.rank_delta_21d for e in cohort]
        assert deltas == sorted(deltas, reverse=True)
        assert "IMP" in {e.symbol for e in cohort}


class TestSectorRank:
    def test_sector_relative_rank(self):
        close = _panel_with_ordered_returns()
        # Put A, C, E in one sector; B, D in another.
        sectors = {
            "A": ("SEC1",), "C": ("SEC1",), "E": ("SEC1",),
            "B": ("SEC2",), "D": ("SEC2",),
        }
        table = rr.compute_rs_table(close.index[-1], close, sectors_map=sectors)
        # Within SEC1: A strongest → sector_rank 1, E weakest → 3
        assert table["A"].sector_rank == 1
        assert table["E"].sector_rank == 3
        assert table["A"].sector_size == 3
        # Within SEC2: B strongest → 1, D → 2
        assert table["B"].sector_rank == 1
        assert table["D"].sector_rank == 2


class TestSerialization:
    def test_entries_json_serializable(self):
        import json
        close = _panel_with_ordered_returns()
        table = rr.compute_rs_table(close.index[-1], close)
        for e in table.values():
            json.dumps(e.to_dict())

    def test_historical_asof(self):
        close = _panel_with_ordered_returns()
        table = rr.compute_rs_table(pd.Timestamp("2023-11-01"), close)
        assert isinstance(table, dict)
