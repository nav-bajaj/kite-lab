"""Spec tests for the portfolio-crowding engine (app.insights.crowding).

Crowding = how clustered a book's holdings are once market beta is stripped.
The engine measures the mean off-diagonal pairwise correlation of the
holdings' market-residual returns, and contextualises it against a null
distribution of random same-size books from the universe.

These are specification tests: they pin the intended behaviour on small,
hand-crafted inputs BEFORE the engine exists. Written per
tasks/insight_engine/TDD_POLICY.md.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.insights import crowding


def _bdays(n, start="2024-01-01"):
    return pd.date_range(start, periods=n, freq="B")


class TestResidualStripsBeta:
    def test_residual_uncorrelated_with_market(self):
        # stock = 1.5 * market + independent noise -> residual ⟂ market
        idx = _bdays(400)
        rng = np.random.default_rng(1)
        mkt = pd.Series(rng.normal(0, 0.01, len(idx)), index=idx)
        market_close = (1 + mkt).cumprod() * 100
        noise = pd.Series(rng.normal(0, 0.01, len(idx)), index=idx)
        stock_ret = 1.5 * mkt + noise
        stock_close = (1 + stock_ret).cumprod() * 100
        close = pd.DataFrame({"S": stock_close})

        resid = crowding.residual_panel(close, market_close, beta_window=252)
        r = resid["S"].dropna()
        m = market_close.pct_change().reindex(r.index)
        # residual should have near-zero correlation with the market
        assert abs(r.corr(m)) < 0.2


class TestBookCrowding:
    def test_high_for_identical_residuals(self):
        idx = _bdays(120)
        rng = np.random.default_rng(2)
        a = pd.Series(rng.normal(size=len(idx)), index=idx)
        resid = pd.DataFrame({"A": a, "B": a, "C": pd.Series(rng.normal(size=len(idx)), index=idx)})
        c = crowding.book_crowding(resid, ["A", "B"], as_of=idx[-1], window=63)
        assert c > 0.95

    def test_low_for_independent_residuals(self):
        idx = _bdays(120)
        rng = np.random.default_rng(3)
        resid = pd.DataFrame({s: pd.Series(rng.normal(size=len(idx)), index=idx)
                              for s in ["A", "B", "C", "D"]})
        c = crowding.book_crowding(resid, ["A", "B", "C", "D"], as_of=idx[-1], window=63)
        assert abs(c) < 0.3

    def test_uses_only_trailing_window(self):
        # names decorrelated early, then identical in the last 63d -> high now
        idx = _bdays(200)
        rng = np.random.default_rng(4)
        a = pd.Series(rng.normal(size=len(idx)), index=idx)
        b = a.copy()
        b.iloc[:120] = rng.normal(size=120)  # differ in the distant past only
        resid = pd.DataFrame({"A": a, "B": b})
        c = crowding.book_crowding(resid, ["A", "B"], as_of=idx[-1], window=63)
        assert c > 0.95

    def test_nan_when_too_few_names(self):
        idx = _bdays(120)
        resid = pd.DataFrame({"A": pd.Series(np.random.default_rng(5).normal(size=len(idx)), index=idx)})
        c = crowding.book_crowding(resid, ["A"], as_of=idx[-1], window=63)
        assert np.isnan(c)


class TestNullPercentile:
    def test_crowded_book_ranks_high(self):
        # 6 names in a tight cluster (shared factor) + 30 independent names.
        # A book of the clustered names should sit high vs random draws.
        idx = _bdays(120)
        rng = np.random.default_rng(6)
        factor = pd.Series(rng.normal(size=len(idx)), index=idx)
        cols = {}
        cluster = [f"K{i}" for i in range(6)]
        for s in cluster:
            cols[s] = factor + 0.15 * pd.Series(rng.normal(size=len(idx)), index=idx)
        indep = [f"I{i}" for i in range(30)]
        for s in indep:
            cols[s] = pd.Series(rng.normal(size=len(idx)), index=idx)
        resid = pd.DataFrame(cols)
        universe = cluster + indep
        pct = crowding.crowding_null_percentile(
            resid, cluster, universe, as_of=idx[-1], window=63, n_draws=300, seed=0)
        assert pct > 0.85

    def test_deterministic_under_seed(self):
        idx = _bdays(120)
        rng = np.random.default_rng(7)
        resid = pd.DataFrame({f"S{i}": pd.Series(rng.normal(size=len(idx)), index=idx)
                              for i in range(20)})
        uni = list(resid.columns)
        hold = uni[:8]
        p1 = crowding.crowding_null_percentile(resid, hold, uni, as_of=idx[-1], n_draws=100, seed=42)
        p2 = crowding.crowding_null_percentile(resid, hold, uni, as_of=idx[-1], n_draws=100, seed=42)
        assert p1 == p2
