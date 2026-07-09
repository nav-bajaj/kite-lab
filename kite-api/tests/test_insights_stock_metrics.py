"""Spec tests for the per-stock feature engine (`stock_metrics.py`).

Authored FIRST per tasks/insight_engine/TDD_POLICY.md — these fail on
ImportError until the module exists, then pin the contract.

Inputs are hand-computed from the mathematical definition of each metric
(not read back from the implementation): synthetic OHLCV panels with known
closes/highs/lows/volumes, plus one real canonical-day cross-check
(2020-03-23 COVID crash) that must show a deeply negative median 1M return
and extreme volatility percentiles.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from app.insights import stock_metrics as sm


# ───────────────────────── synthetic panel helpers ─────────────────────────

def _ramp_panel(n: int = 300, step: float = 1.0, start: float = 100.0,
                symbol: str = "RAMP") -> dict[str, pd.DataFrame]:
    """Strictly-rising linear close ramp with a constant intraday range and
    flat volume. Every metric is analytically computable from this."""
    dates = pd.date_range("2023-01-02", periods=n, freq="B")
    close = start + step * np.arange(n, dtype=float)
    high = close + 2.0
    low = close - 2.0
    vol = np.full(n, 1000.0)
    idx = dates
    mk = lambda a: pd.DataFrame({symbol: a}, index=idx)
    return {"close": mk(close), "high": mk(high), "low": mk(low),
            "volume": mk(vol)}


# ───────────────────────────── returns ─────────────────────────────

class TestReturns:
    def test_multi_horizon_returns_match_definition(self):
        p = _ramp_panel(n=300)
        asof = p["close"].index[-1]
        m = sm.compute_stock_metrics(asof, p)["RAMP"]
        c = p["close"]["RAMP"].values
        assert m.ret_1d == pytest.approx(c[-1] / c[-2] - 1)
        assert m.ret_1w == pytest.approx(c[-1] / c[-6] - 1)      # 5 td
        assert m.ret_1m == pytest.approx(c[-1] / c[-22] - 1)     # 21 td
        assert m.ret_3m == pytest.approx(c[-1] / c[-64] - 1)     # 63 td
        assert m.ret_6m == pytest.approx(c[-1] / c[-127] - 1)    # 126 td
        assert m.ret_12m == pytest.approx(c[-1] / c[-253] - 1)   # 252 td

    def test_insufficient_history_returns_none_not_nan(self):
        p = _ramp_panel(n=30)   # < 63 td
        asof = p["close"].index[-1]
        m = sm.compute_stock_metrics(asof, p)["RAMP"]
        assert m.ret_1d is not None
        assert m.ret_1w is not None
        assert m.ret_3m is None
        assert m.ret_6m is None
        assert m.ret_12m is None
        # None, never NaN
        assert not any(isinstance(v, float) and np.isnan(v)
                       for v in m.to_dict().values())


# ───────────────────────── trend structure ─────────────────────────

class TestTrendStructure:
    def test_dma_positions_and_distance(self):
        p = _ramp_panel(n=300)
        asof = p["close"].index[-1]
        m = sm.compute_stock_metrics(asof, p)["RAMP"]
        c = p["close"]["RAMP"].values
        sma50 = c[-50:].mean()
        assert m.sma_50 == pytest.approx(sma50)
        assert m.above_50dma is True          # rising ramp always above
        assert m.dist_50dma_pct == pytest.approx(c[-1] / sma50 - 1)
        assert m.above_20dma and m.above_100dma and m.above_200dma

    def test_dma_slope_positive_on_rising_series(self):
        p = _ramp_panel(n=300)
        asof = p["close"].index[-1]
        m = sm.compute_stock_metrics(asof, p)["RAMP"]
        assert m.slope_50dma_20d > 0
        assert m.slope_200dma_20d > 0

    def test_golden_alignment_flag(self):
        p = _ramp_panel(n=300)
        asof = p["close"].index[-1]
        m = sm.compute_stock_metrics(asof, p)["RAMP"]
        assert m.dma_50_above_200 is True

    def test_below_dma_on_falling_series(self):
        p = _ramp_panel(n=300, step=-0.5, start=500.0)
        asof = p["close"].index[-1]
        m = sm.compute_stock_metrics(asof, p)["RAMP"]
        assert m.above_50dma is False
        assert m.dist_50dma_pct < 0
        assert m.dma_50_above_200 is False


# ───────────────────────────── levels ─────────────────────────────

class TestLevels:
    def test_fresh_52w_high_on_rising_ramp(self):
        p = _ramp_panel(n=300)
        asof = p["close"].index[-1]
        m = sm.compute_stock_metrics(asof, p)["RAMP"]
        assert m.dist_52w_high_pct == pytest.approx(0.0)
        assert m.days_since_52w_high == 0
        assert m.fresh_52w_high is True
        assert m.drawdown_from_peak_pct == pytest.approx(0.0)
        assert m.dist_52w_low_pct > 0

    def test_days_since_high_and_drawdown_after_pullback(self):
        # Rise to a peak 40 sessions ago, then decline into today.
        n = 300
        dates = pd.date_range("2023-01-02", periods=n, freq="B")
        close = np.concatenate([
            np.linspace(100, 200, n - 40),      # rise, peak at index n-41
            np.linspace(200, 180, 40),          # decline into today
        ])
        mk = lambda a: pd.DataFrame({"S": a}, index=dates)
        p = {"close": mk(close), "high": mk(close + 1),
             "low": mk(close - 1), "volume": mk(np.full(n, 1000.0))}
        m = sm.compute_stock_metrics(dates[-1], p)["S"]
        peak = close[:n - 40].max()
        assert m.days_since_52w_high == 39
        assert m.drawdown_from_peak_pct == pytest.approx(close[-1] / peak - 1)
        assert m.fresh_52w_high is False


# ───────────────────────────── risk ─────────────────────────────

class TestRisk:
    def test_atr_pct_constant_range(self):
        # H-L = 4 every day, ramp step 1 → TR = 4 every day → ATR14 = 4.
        p = _ramp_panel(n=300, step=1.0)
        asof = p["close"].index[-1]
        m = sm.compute_stock_metrics(asof, p)["RAMP"]
        assert m.atr_14 == pytest.approx(4.0)
        assert m.atr_pct == pytest.approx(4.0 / p["close"]["RAMP"].values[-1])

    def test_beta_two_x_market(self):
        # Stock daily simple return = 2x Nifty return every day → beta = 2.
        n = 120
        dates = pd.date_range("2023-01-02", periods=n, freq="B")
        rng = np.random.default_rng(7)
        r = rng.normal(0.0, 0.01, n)
        r[0] = 0.0
        nifty_close = pd.Series(1000.0 * np.cumprod(1 + r), index=dates)
        stock_close = 100.0 * np.cumprod(1 + 2 * r)
        mk = lambda a: pd.DataFrame({"BETA": a}, index=dates)
        p = {"close": mk(stock_close), "high": mk(stock_close + 1),
             "low": mk(stock_close - 1), "volume": mk(np.full(n, 1000.0))}
        m = sm.compute_stock_metrics(dates[-1], p, nifty_close=nifty_close)["BETA"]
        assert m.beta_60d == pytest.approx(2.0, abs=1e-6)

    def test_realized_vol_annualized(self):
        n = 120
        dates = pd.date_range("2023-01-02", periods=n, freq="B")
        rng = np.random.default_rng(3)
        r = rng.normal(0.0, 0.02, n)
        r[0] = 0.0
        close = 100.0 * np.cumprod(1 + r)
        mk = lambda a: pd.DataFrame({"V": a}, index=dates)
        p = {"close": mk(close), "high": mk(close + 1),
             "low": mk(close - 1), "volume": mk(np.full(n, 1000.0))}
        m = sm.compute_stock_metrics(dates[-1], p)["V"]
        rets = pd.Series(close).pct_change()
        exp20 = rets.iloc[-20:].std() * np.sqrt(252)
        assert m.vol_20d_annualized == pytest.approx(exp20, rel=1e-6)

    def test_vol_percentile_in_unit_interval(self):
        p = _ramp_panel(n=400)
        asof = p["close"].index[-1]
        m = sm.compute_stock_metrics(asof, p)["RAMP"]
        assert 0.0 <= m.vol_percentile_1y <= 1.0


# ───────────────────────────── volume ─────────────────────────────

class TestVolume:
    def test_volume_ratio_excludes_today(self):
        # Prior 20 sessions volume = 1000, today = 2500 → ratio 2.5.
        n = 300
        dates = pd.date_range("2023-01-02", periods=n, freq="B")
        close = 100.0 + np.arange(n)
        vol = np.full(n, 1000.0)
        vol[-1] = 2500.0
        mk = lambda a: pd.DataFrame({"VOL": a}, index=dates)
        p = {"close": mk(close), "high": mk(close + 1),
             "low": mk(close - 1), "volume": mk(vol)}
        m = sm.compute_stock_metrics(dates[-1], p)["VOL"]
        assert m.vol_ratio == pytest.approx(2.5)

    def test_turnover_cr_and_liquidity_tier(self):
        # close ~ 500, volume 1e6 → turnover ~ 5e8 = 50 Cr → Good tier.
        n = 60
        dates = pd.date_range("2023-01-02", periods=n, freq="B")
        close = np.full(n, 500.0)
        vol = np.full(n, 1_000_000.0)
        mk = lambda a: pd.DataFrame({"BIG": a}, index=dates)
        p = {"close": mk(close), "high": mk(close + 1),
             "low": mk(close - 1), "volume": mk(vol)}
        m = sm.compute_stock_metrics(dates[-1], p)["BIG"]
        assert m.avg_turnover_20d_cr == pytest.approx(50.0)
        assert m.liquidity_tier == "Good"

    def test_low_liquidity_tier(self):
        n = 60
        dates = pd.date_range("2023-01-02", periods=n, freq="B")
        close = np.full(n, 50.0)
        vol = np.full(n, 1000.0)          # turnover 50k = 0.005 Cr → Low
        mk = lambda a: pd.DataFrame({"TINY": a}, index=dates)
        p = {"close": mk(close), "high": mk(close + 1),
             "low": mk(close - 1), "volume": mk(vol)}
        m = sm.compute_stock_metrics(dates[-1], p)["TINY"]
        assert m.liquidity_tier == "Low"

    def test_updown_volume_ratio(self):
        # Alternating up/down days, higher volume on up days → ratio > 1.
        n = 60
        dates = pd.date_range("2023-01-02", periods=n, freq="B")
        close = np.array([100.0 + (1 if i % 2 == 0 else -0.5) * (i)
                          for i in range(n)])
        # Force clean alternation
        close = np.empty(n)
        close[0] = 100.0
        vol = np.empty(n)
        vol[0] = 1000.0
        for i in range(1, n):
            up = i % 2 == 1
            close[i] = close[i - 1] * (1.01 if up else 0.995)
            vol[i] = 2000.0 if up else 1000.0
        mk = lambda a: pd.DataFrame({"UD": a}, index=dates)
        p = {"close": mk(close), "high": mk(close + 1),
             "low": mk(close - 1), "volume": mk(vol)}
        m = sm.compute_stock_metrics(dates[-1], p)["UD"]
        assert m.updown_vol_ratio_20d is not None
        assert m.updown_vol_ratio_20d > 1.0


# ─────────────────────────── serialization ───────────────────────────

class TestSerialization:
    def test_to_dict_json_serializable_and_none_clean(self):
        import json
        p = _ramp_panel(n=300)
        m = sm.compute_stock_metrics(p["close"].index[-1], p)["RAMP"]
        d = m.to_dict()
        json.dumps(d)                     # must not raise
        for k, v in d.items():
            assert v is None or not (isinstance(v, float) and np.isnan(v)), k


# ─────────────────────── canonical historical day ───────────────────────

class TestCanonicalDay:
    """Cross-check against the real 16y panel on the COVID crash bottom."""

    def test_covid_crash_median_1m_return_deeply_negative(self):
        metrics = sm.get_stock_metrics(asof=pd.Timestamp("2020-03-23"))
        if not metrics:
            pytest.skip("panel data unavailable in this environment")
        r1m = [m.ret_1m for m in metrics.values() if m.ret_1m is not None]
        assert len(r1m) > 100
        assert float(np.median(r1m)) < -0.20, (
            "March 2020 crash: median trailing 1M return should be deeply negative"
        )

    def test_covid_crash_vol_percentiles_extreme(self):
        metrics = sm.get_stock_metrics(asof=pd.Timestamp("2020-03-23"))
        if not metrics:
            pytest.skip("panel data unavailable in this environment")
        vp = [m.vol_percentile_1y for m in metrics.values()
              if m.vol_percentile_1y is not None]
        assert float(np.median(vp)) > 0.85, (
            "March 2020: realized vol should sit near the top of each stock's own year"
        )
