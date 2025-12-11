"""
Technical Analysis Indicators Module

Provides vectorized, pandas-compatible functions for common technical indicators.
All functions operate on pandas Series or DataFrame columns and return the same shape.

Author: Kite-Lab
"""

import numpy as np
import pandas as pd
from typing import Optional, Tuple


def ema(series: pd.Series, span: int, adjust: bool = False) -> pd.Series:
    """
    Exponential Moving Average (EMA)

    Args:
        series: Price series (typically close prices)
        span: Number of periods for the EMA
        adjust: If True, uses adjusted weights (default False for traditional EMA)

    Returns:
        EMA series with same index as input

    Examples:
        >>> close = pd.Series([100, 102, 101, 103, 105])
        >>> ema_20 = ema(close, span=20)
    """
    return series.ewm(span=span, adjust=adjust, min_periods=span).mean()


def sma(series: pd.Series, window: int) -> pd.Series:
    """
    Simple Moving Average (SMA)

    Args:
        series: Price series
        window: Number of periods

    Returns:
        SMA series with same index as input
    """
    return series.rolling(window=window, min_periods=window).mean()


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """
    Relative Strength Index (RSI)

    Measures momentum on a scale of 0-100.
    - RSI > 70: Overbought
    - RSI < 30: Oversold

    Args:
        series: Price series (typically close prices)
        period: Lookback period (default 14)

    Returns:
        RSI series with same index as input (values 0-100)

    References:
        Wilder, J. W. (1978). New Concepts in Technical Trading Systems.
    """
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)

    # Wilder's smoothing (EMA with alpha = 1/period)
    avg_gain = gain.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1/period, min_periods=period, adjust=False).mean()

    rs = avg_gain / avg_loss
    rsi_values = 100 - (100 / (1 + rs))

    return rsi_values


def macd(
    series: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Moving Average Convergence Divergence (MACD)

    Trend-following momentum indicator.

    Args:
        series: Price series (typically close prices)
        fast: Fast EMA period (default 12)
        slow: Slow EMA period (default 26)
        signal: Signal line period (default 9)

    Returns:
        Tuple of (macd_line, signal_line, histogram)
        - macd_line: Fast EMA - Slow EMA
        - signal_line: EMA of macd_line
        - histogram: macd_line - signal_line

    Examples:
        >>> close = pd.Series([...])
        >>> macd_line, signal_line, histogram = macd(close)
        >>> # Buy when histogram crosses above 0
        >>> buy_signal = (histogram > 0) & (histogram.shift(1) <= 0)
    """
    ema_fast = ema(series, span=fast)
    ema_slow = ema(series, span=slow)
    macd_line = ema_fast - ema_slow
    signal_line = ema(macd_line, span=signal)
    histogram = macd_line - signal_line

    return macd_line, signal_line, histogram


def atr(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 14
) -> pd.Series:
    """
    Average True Range (ATR)

    Measures market volatility. Higher ATR = higher volatility.

    Args:
        high: High prices
        low: Low prices
        close: Close prices
        period: Lookback period (default 14)

    Returns:
        ATR series with same index as input

    References:
        Wilder, J. W. (1978). New Concepts in Technical Trading Systems.

    Examples:
        >>> atr_14 = atr(df['high'], df['low'], df['close'], period=14)
        >>> # Normalize by price for comparison
        >>> atr_pct = atr_14 / df['close']
    """
    high_low = high - low
    high_close = (high - close.shift()).abs()
    low_close = (low - close.shift()).abs()

    true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr_values = true_range.ewm(alpha=1/period, min_periods=period, adjust=False).mean()

    return atr_values


def bollinger_bands(
    series: pd.Series,
    window: int = 20,
    num_std: float = 2.0
) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Bollinger Bands

    Volatility bands placed above and below a moving average.

    Args:
        series: Price series (typically close prices)
        window: Moving average period (default 20)
        num_std: Number of standard deviations (default 2.0)

    Returns:
        Tuple of (upper_band, middle_band, lower_band)

    Examples:
        >>> upper, middle, lower = bollinger_bands(close, window=20, num_std=2)
        >>> # Price near upper band (potential overbought)
        >>> near_upper = close > (upper - 0.1 * (upper - middle))
    """
    middle_band = sma(series, window)
    std_dev = series.rolling(window=window, min_periods=window).std()
    upper_band = middle_band + (std_dev * num_std)
    lower_band = middle_band - (std_dev * num_std)

    return upper_band, middle_band, lower_band


def stochastic_oscillator(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    k_period: int = 14,
    d_period: int = 3
) -> Tuple[pd.Series, pd.Series]:
    """
    Stochastic Oscillator (%K and %D)

    Momentum indicator comparing closing price to price range.
    - Values > 80: Overbought
    - Values < 20: Oversold

    Args:
        high: High prices
        low: Low prices
        close: Close prices
        k_period: %K lookback period (default 14)
        d_period: %D smoothing period (default 3)

    Returns:
        Tuple of (%K, %D)
        - %K: Fast stochastic (0-100)
        - %D: Slow stochastic (SMA of %K)
    """
    lowest_low = low.rolling(window=k_period, min_periods=k_period).min()
    highest_high = high.rolling(window=k_period, min_periods=k_period).max()

    k_percent = 100 * (close - lowest_low) / (highest_high - lowest_low)
    d_percent = k_percent.rolling(window=d_period, min_periods=d_period).mean()

    return k_percent, d_percent


def adx(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 14
) -> pd.Series:
    """
    Average Directional Index (ADX)

    Measures trend strength (NOT direction).
    - ADX < 20: Weak trend
    - ADX 20-40: Moderate trend
    - ADX > 40: Strong trend

    Args:
        high: High prices
        low: Low prices
        close: Close prices
        period: Lookback period (default 14)

    Returns:
        ADX series with same index as input (values 0-100)

    References:
        Wilder, J. W. (1978). New Concepts in Technical Trading Systems.
    """
    # Calculate +DM and -DM
    up_move = high - high.shift()
    down_move = low.shift() - low

    plus_dm = up_move.where((up_move > down_move) & (up_move > 0), 0.0)
    minus_dm = down_move.where((down_move > up_move) & (down_move > 0), 0.0)

    # Calculate True Range
    tr = atr(high, low, close, period=1)  # True range without smoothing

    # Smooth +DM, -DM, and TR
    atr_smooth = tr.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
    plus_di = 100 * plus_dm.ewm(alpha=1/period, min_periods=period, adjust=False).mean() / atr_smooth
    minus_di = 100 * minus_dm.ewm(alpha=1/period, min_periods=period, adjust=False).mean() / atr_smooth

    # Calculate DX and ADX
    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
    adx_values = dx.ewm(alpha=1/period, min_periods=period, adjust=False).mean()

    return adx_values


def momentum(series: pd.Series, period: int = 10) -> pd.Series:
    """
    Price Momentum

    Simple rate of change over a period.

    Args:
        series: Price series
        period: Lookback period (default 10)

    Returns:
        Momentum values (current price - price N periods ago)
    """
    return series - series.shift(period)


def roc(series: pd.Series, period: int = 10) -> pd.Series:
    """
    Rate of Change (ROC)

    Percentage change over a period.

    Args:
        series: Price series
        period: Lookback period (default 10)

    Returns:
        ROC values as percentage (100 * (price/price[n] - 1))
    """
    return 100 * (series / series.shift(period) - 1)


def williams_r(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 14
) -> pd.Series:
    """
    Williams %R

    Momentum indicator (inverted stochastic).
    - Values -20 to 0: Overbought
    - Values -100 to -80: Oversold

    Args:
        high: High prices
        low: Low prices
        close: Close prices
        period: Lookback period (default 14)

    Returns:
        Williams %R values (-100 to 0)
    """
    highest_high = high.rolling(window=period, min_periods=period).max()
    lowest_low = low.rolling(window=period, min_periods=period).min()

    wr = -100 * (highest_high - close) / (highest_high - lowest_low)

    return wr


# Utility functions for filters

def crossover(series1: pd.Series, series2: pd.Series) -> pd.Series:
    """
    Detect when series1 crosses above series2

    Returns:
        Boolean series where True indicates a crossover
    """
    return (series1 > series2) & (series1.shift(1) <= series2.shift(1))


def crossunder(series1: pd.Series, series2: pd.Series) -> pd.Series:
    """
    Detect when series1 crosses below series2

    Returns:
        Boolean series where True indicates a crossunder
    """
    return (series1 < series2) & (series1.shift(1) >= series2.shift(1))


def above(series1: pd.Series, series2: pd.Series, bars: int = 1) -> pd.Series:
    """
    Check if series1 has been above series2 for N consecutive bars

    Args:
        series1: First series
        series2: Second series
        bars: Number of consecutive bars (default 1)

    Returns:
        Boolean series
    """
    condition = series1 > series2
    if bars == 1:
        return condition
    return condition.rolling(window=bars, min_periods=bars).sum() == bars


def below(series1: pd.Series, series2: pd.Series, bars: int = 1) -> pd.Series:
    """
    Check if series1 has been below series2 for N consecutive bars

    Args:
        series1: First series
        series2: Second series
        bars: Number of consecutive bars (default 1)

    Returns:
        Boolean series
    """
    condition = series1 < series2
    if bars == 1:
        return condition
    return condition.rolling(window=bars, min_periods=bars).sum() == bars
