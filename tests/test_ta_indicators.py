"""
Unit tests for technical analysis indicators

Tests compare against known reference values and edge cases.
"""

import numpy as np
import pandas as pd
import pytest
import sys
from pathlib import Path

# Add parent directory to path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import ta_indicators as ta


@pytest.fixture
def sample_prices():
    """Sample price data for testing"""
    return pd.Series([
        100.0, 102.0, 101.0, 103.0, 105.0,
        104.0, 106.0, 108.0, 107.0, 109.0,
        111.0, 110.0, 112.0, 114.0, 113.0
    ])


@pytest.fixture
def sample_ohlc():
    """Sample OHLC data for testing"""
    return pd.DataFrame({
        'open': [100, 102, 101, 103, 105, 104, 106, 108, 107, 109],
        'high': [102, 103, 103, 105, 106, 106, 108, 109, 109, 111],
        'low': [99, 101, 100, 102, 104, 103, 105, 107, 106, 108],
        'close': [102, 101, 103, 105, 104, 106, 108, 107, 109, 111]
    })


class TestEMA:
    def test_ema_basic(self, sample_prices):
        """Test EMA calculation"""
        result = ta.ema(sample_prices, span=5)

        # EMA should have same length as input
        assert len(result) == len(sample_prices)

        # First values should be NaN
        assert result.iloc[:4].isna().all()

        # EMA should be between min and max of input
        assert result.dropna().min() >= sample_prices.min()
        assert result.dropna().max() <= sample_prices.max()

    def test_ema_trending(self):
        """Test EMA on trending data"""
        trending = pd.Series(range(1, 21))
        result = ta.ema(trending, span=5)

        # EMA should be monotonically increasing for increasing prices
        result_clean = result.dropna()
        assert (result_clean.diff().dropna() > 0).all()


class TestSMA:
    def test_sma_basic(self, sample_prices):
        """Test SMA calculation"""
        result = ta.sma(sample_prices, window=5)

        assert len(result) == len(sample_prices)
        assert result.iloc[:4].isna().all()

        # Check first valid SMA manually
        expected_first = sample_prices.iloc[:5].mean()
        assert abs(result.iloc[4] - expected_first) < 1e-10


class TestRSI:
    def test_rsi_range(self, sample_prices):
        """Test RSI stays within 0-100"""
        result = ta.rsi(sample_prices, period=5)

        assert len(result) == len(sample_prices)

        # RSI should be between 0 and 100
        valid_rsi = result.dropna()
        assert (valid_rsi >= 0).all()
        assert (valid_rsi <= 100).all()

    def test_rsi_trending_up(self):
        """Test RSI on strongly bullish data"""
        bullish = pd.Series(range(100, 120))
        result = ta.rsi(bullish, period=14)

        # RSI should be high (>50) for strong uptrend
        assert result.iloc[-1] > 50

    def test_rsi_trending_down(self):
        """Test RSI on strongly bearish data"""
        bearish = pd.Series(range(120, 100, -1))
        result = ta.rsi(bearish, period=14)

        # RSI should be low (<50) for strong downtrend
        assert result.iloc[-1] < 50

    def test_rsi_flat(self):
        """Test RSI on flat prices"""
        flat = pd.Series([100] * 20)
        result = ta.rsi(flat, period=14)

        # RSI should be ~50 for flat prices (or NaN)
        valid = result.dropna()
        if len(valid) > 0:
            # Should be close to 50 or undefined
            assert valid.iloc[-1] > 45 and valid.iloc[-1] < 55 or np.isnan(valid.iloc[-1])


class TestMACD:
    def test_macd_basic(self, sample_prices):
        """Test MACD calculation"""
        macd_line, signal_line, histogram = ta.macd(sample_prices, fast=5, slow=10, signal=3)

        # All should have same length
        assert len(macd_line) == len(sample_prices)
        assert len(signal_line) == len(sample_prices)
        assert len(histogram) == len(sample_prices)

        # Histogram should equal macd - signal
        valid_idx = histogram.notna()
        np.testing.assert_array_almost_equal(
            histogram[valid_idx],
            (macd_line - signal_line)[valid_idx]
        )

    def test_macd_trending(self):
        """Test MACD on trending data"""
        trending = pd.Series(range(1, 51))
        macd_line, signal_line, histogram = ta.macd(trending, fast=12, slow=26, signal=9)

        # MACD line should be positive for uptrend
        assert macd_line.iloc[-1] > 0


class TestATR:
    def test_atr_basic(self, sample_ohlc):
        """Test ATR calculation"""
        result = ta.atr(
            sample_ohlc['high'],
            sample_ohlc['low'],
            sample_ohlc['close'],
            period=5
        )

        assert len(result) == len(sample_ohlc)

        # ATR should always be positive
        assert (result.dropna() >= 0).all()

    def test_atr_increases_with_volatility(self):
        """Test ATR increases with higher volatility"""
        # Low volatility
        low_vol = pd.DataFrame({
            'high': [101] * 20,
            'low': [100] * 20,
            'close': [100.5] * 20
        })

        # High volatility
        high_vol = pd.DataFrame({
            'high': [110] * 20,
            'low': [90] * 20,
            'close': [100] * 20
        })

        atr_low = ta.atr(low_vol['high'], low_vol['low'], low_vol['close'], period=5)
        atr_high = ta.atr(high_vol['high'], high_vol['low'], high_vol['close'], period=5)

        # High volatility should have higher ATR
        assert atr_high.iloc[-1] > atr_low.iloc[-1]


class TestBollingerBands:
    def test_bollinger_bands_basic(self, sample_prices):
        """Test Bollinger Bands calculation"""
        upper, middle, lower = ta.bollinger_bands(sample_prices, window=5, num_std=2)

        assert len(upper) == len(sample_prices)
        assert len(middle) == len(sample_prices)
        assert len(lower) == len(sample_prices)

        # Upper should be above middle, middle above lower
        valid_idx = upper.notna()
        assert (upper[valid_idx] >= middle[valid_idx]).all()
        assert (middle[valid_idx] >= lower[valid_idx]).all()


class TestStochasticOscillator:
    def test_stochastic_range(self, sample_ohlc):
        """Test Stochastic stays within 0-100"""
        k, d = ta.stochastic_oscillator(
            sample_ohlc['high'],
            sample_ohlc['low'],
            sample_ohlc['close'],
            k_period=5,
            d_period=3
        )

        # Both should be between 0 and 100
        assert (k.dropna() >= 0).all()
        assert (k.dropna() <= 100).all()
        assert (d.dropna() >= 0).all()
        assert (d.dropna() <= 100).all()


class TestADX:
    def test_adx_range(self, sample_ohlc):
        """Test ADX stays within 0-100"""
        result = ta.adx(
            sample_ohlc['high'],
            sample_ohlc['low'],
            sample_ohlc['close'],
            period=5
        )

        # ADX should be between 0 and 100
        valid = result.dropna()
        assert (valid >= 0).all()
        assert (valid <= 100).all()


class TestMomentum:
    def test_momentum_basic(self, sample_prices):
        """Test momentum calculation"""
        result = ta.momentum(sample_prices, period=3)

        assert len(result) == len(sample_prices)

        # Check manual calculation
        expected = sample_prices.iloc[3] - sample_prices.iloc[0]
        assert abs(result.iloc[3] - expected) < 1e-10


class TestROC:
    def test_roc_basic(self, sample_prices):
        """Test ROC calculation"""
        result = ta.roc(sample_prices, period=3)

        # ROC should be percentage change
        manual_roc = 100 * (sample_prices.iloc[3] / sample_prices.iloc[0] - 1)
        assert abs(result.iloc[3] - manual_roc) < 1e-10


class TestWilliamsR:
    def test_williams_r_range(self, sample_ohlc):
        """Test Williams %R stays within -100 to 0"""
        result = ta.williams_r(
            sample_ohlc['high'],
            sample_ohlc['low'],
            sample_ohlc['close'],
            period=5
        )

        valid = result.dropna()
        assert (valid >= -100).all()
        assert (valid <= 0).all()


class TestCrossoverFunctions:
    def test_crossover(self):
        """Test crossover detection"""
        series1 = pd.Series([1, 2, 3.5, 4, 5])
        series2 = pd.Series([5, 4, 3, 2, 1])

        result = ta.crossover(series1, series2)

        # Crossover should occur at index 2 (series1 goes from below to above)
        assert result.iloc[2] == True
        assert result.iloc[1] == False
        assert result.iloc[3] == False

    def test_crossunder(self):
        """Test crossunder detection"""
        series1 = pd.Series([5, 4, 2.5, 2, 1])
        series2 = pd.Series([1, 2, 3, 4, 5])

        result = ta.crossunder(series1, series2)

        # Crossunder should occur at index 2
        assert result.iloc[2] == True


class TestAboveBelow:
    def test_above_single_bar(self):
        """Test above for 1 bar"""
        series1 = pd.Series([1, 2, 3, 4, 5])
        series2 = pd.Series([2, 2, 2, 2, 2])

        result = ta.above(series1, series2, bars=1)

        assert result.iloc[0] == False
        assert result.iloc[2] == True
        assert result.iloc[4] == True

    def test_below_single_bar(self):
        """Test below for 1 bar"""
        series1 = pd.Series([1, 2, 3, 4, 5])
        series2 = pd.Series([3, 3, 3, 3, 3])

        result = ta.below(series1, series2, bars=1)

        assert result.iloc[0] == True
        assert result.iloc[2] == False


class TestEdgeCases:
    def test_empty_series(self):
        """Test with empty series"""
        empty = pd.Series([], dtype=float)

        result = ta.ema(empty, span=5)
        assert len(result) == 0

    def test_nan_handling(self):
        """Test with NaN values"""
        with_nan = pd.Series([100, np.nan, 102, 103, 104])

        # Should handle NaN gracefully
        result = ta.sma(with_nan, window=3)
        assert len(result) == len(with_nan)

    def test_constant_prices(self):
        """Test with constant prices"""
        constant = pd.Series([100] * 20)

        sma_result = ta.sma(constant, window=5)
        assert (sma_result.dropna() == 100).all()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
