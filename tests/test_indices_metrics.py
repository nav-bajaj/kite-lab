"""
Comprehensive tests for indices report metric calculations.

Tests all key financial metrics to ensure correct implementation:
- Annualized return (CAGR)
- Annualized volatility
- Maximum drawdown
- Sharpe ratio
- Correlation
- Beta

Run with: python tests/test_indices_metrics.py
"""

import sys
from pathlib import Path

# Add parent directory to path to import modules
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import numpy as np
import pandas as pd

from report_indices import (
    annualized_return,
    annualized_vol,
    max_drawdown,
    sharpe_ratio,
    compute_correlation,
    compute_beta,
    compute_metrics,
)


def assert_approx_equal(actual, expected, tolerance=0.0001, label=""):
    """Assert two values are approximately equal."""
    if np.isnan(expected):
        assert np.isnan(actual), f"{label}: Expected NaN, got {actual}"
    else:
        diff = abs(actual - expected)
        assert diff < tolerance, f"{label}: Expected {expected}, got {actual} (diff: {diff})"
    print(f"✓ {label}: {actual:.6f}")


def test_annualized_return():
    """Test CAGR calculation."""
    print("\n" + "=" * 60)
    print("Testing Annualized Return (CAGR)")
    print("=" * 60)

    # Test 1: Simple doubling over 1 year
    # Starting value: 100, ending value: 200
    # Note: 2020-01-01 to 2021-01-01 is 366 days (leap year)
    # Expected CAGR: (200/100)^(365/366) - 1 = 0.9962
    dates = pd.Series([pd.Timestamp("2020-01-01"), pd.Timestamp("2021-01-01")])
    values = pd.Series([100.0, 200.0])
    cagr = annualized_return(values, dates)
    assert_approx_equal(cagr, 0.9962, tolerance=0.001, label="Test 1: 100% return over leap year")

    # Test 2: Exact 100% return over exactly 365 days
    dates = pd.Series([pd.Timestamp("2021-01-01"), pd.Timestamp("2022-01-01")])
    values = pd.Series([100.0, 200.0])
    cagr = annualized_return(values, dates)
    assert_approx_equal(cagr, 1.0, tolerance=0.001, label="Test 2: Exact 100% return over 365 days")

    # Test 3: 10% annual growth over 5 years
    # Starting: 100, Ending: 100 * 1.1^5 = 161.051
    dates = pd.Series([pd.Timestamp("2020-01-01"), pd.Timestamp("2025-01-01")])
    values = pd.Series([100.0, 161.051])
    cagr = annualized_return(values, dates)
    assert_approx_equal(cagr, 0.10, tolerance=0.002, label="Test 3: 10% CAGR over 5 years")

    # Test 4: Negative return (50% loss over 2 years)
    # Starting: 100, Ending: 50
    # CAGR = (50/100)^(1/2) - 1 = -0.2929 (-29.29%)
    dates = pd.Series([pd.Timestamp("2021-01-01"), pd.Timestamp("2023-01-01")])
    values = pd.Series([100.0, 50.0])
    cagr = annualized_return(values, dates)
    assert_approx_equal(cagr, -0.2929, tolerance=0.002, label="Test 4: -50% over 2 years")

    # Test 5: No change (0% return)
    dates = pd.Series([pd.Timestamp("2021-01-01"), pd.Timestamp("2022-01-01")])
    values = pd.Series([100.0, 100.0])
    cagr = annualized_return(values, dates)
    assert_approx_equal(cagr, 0.0, label="Test 5: 0% return")

    # Test 6: Edge case - single data point (should return NaN)
    dates = pd.Series([pd.Timestamp("2021-01-01")])
    values = pd.Series([100.0])
    cagr = annualized_return(values, dates)
    assert_approx_equal(cagr, np.nan, label="Test 6: Single data point returns NaN")

    print("\n✓ All annualized return tests passed!")


def test_annualized_vol():
    """Test annualized volatility calculation."""
    print("\n" + "=" * 60)
    print("Testing Annualized Volatility")
    print("=" * 60)

    # Test 1: Constant daily returns (0% daily vol)
    # If returns are constant, std should be 0
    returns = pd.Series([0.01] * 252)  # 1% daily return for a year
    vol = annualized_vol(returns)
    assert_approx_equal(vol, 0.0, label="Test 1: Zero volatility (constant returns)")

    # Test 2: Known volatility
    # Create returns with known daily std = 0.01 (1%)
    # Annualized vol = 0.01 * sqrt(252) = 0.1588 (15.88%)
    np.random.seed(42)
    returns = pd.Series(np.random.normal(0, 0.01, 252))
    daily_std = returns.std()
    vol = annualized_vol(returns)
    expected_vol = daily_std * np.sqrt(252)
    assert_approx_equal(vol, expected_vol, tolerance=0.001, label="Test 2: Random returns with known std")

    # Test 3: High volatility example
    # Daily std = 0.03 (3%), annualized = 0.03 * sqrt(252) = 0.4764 (47.64%)
    returns = pd.Series(np.random.normal(0, 0.03, 252))
    vol = annualized_vol(returns)
    expected_vol = returns.std() * np.sqrt(252)
    assert_approx_equal(vol, expected_vol, tolerance=0.001, label="Test 3: High volatility")

    # Test 4: Single return (std = 0)
    returns = pd.Series([0.01])
    vol = annualized_vol(returns)
    # pandas std of single value is NaN
    assert np.isnan(vol) or vol == 0.0, f"Test 4: Single return should be NaN or 0, got {vol}"
    print(f"✓ Test 4: Single return: {vol}")

    print("\n✓ All volatility tests passed!")


def test_max_drawdown():
    """Test maximum drawdown calculation."""
    print("\n" + "=" * 60)
    print("Testing Maximum Drawdown")
    print("=" * 60)

    # Test 1: No drawdown (monotonic increase)
    values = pd.Series([100, 110, 120, 130, 140])
    dd = max_drawdown(values)
    assert_approx_equal(dd, 0.0, label="Test 1: No drawdown (monotonic increase)")

    # Test 2: Simple 50% drawdown
    # Peak at 200, trough at 100 → -50%
    values = pd.Series([100, 150, 200, 150, 100, 120])
    dd = max_drawdown(values)
    assert_approx_equal(dd, -0.5, label="Test 2: 50% drawdown")

    # Test 3: Multiple drawdowns, largest is -30%
    # Peak 100 → trough 70 = -30%
    # Peak 90 → trough 80 = -11%
    values = pd.Series([100, 90, 80, 70, 75, 90, 85, 80])
    dd = max_drawdown(values)
    assert_approx_equal(dd, -0.3, label="Test 3: Multiple drawdowns, max -30%")

    # Test 4: Recovery after drawdown
    # Peak 200, trough 100 (-50%), recovery to 180 (still down from peak)
    values = pd.Series([100, 200, 150, 100, 150, 180])
    dd = max_drawdown(values)
    assert_approx_equal(dd, -0.5, label="Test 4: Drawdown with partial recovery")

    # Test 5: Constant value (0% drawdown)
    values = pd.Series([100, 100, 100, 100])
    dd = max_drawdown(values)
    assert_approx_equal(dd, 0.0, label="Test 5: Constant value (no drawdown)")

    print("\n✓ All max drawdown tests passed!")


def test_sharpe_ratio():
    """Test Sharpe ratio calculation."""
    print("\n" + "=" * 60)
    print("Testing Sharpe Ratio")
    print("=" * 60)

    # Test 1: Positive excess return with moderate risk
    # CAGR = 15%, Volatility = 10%, Risk-free = 5%
    # Sharpe = (0.15 - 0.05) / 0.10 = 1.0
    sharpe = sharpe_ratio(cagr=0.15, volatility=0.10, risk_free_rate=0.05)
    assert_approx_equal(sharpe, 1.0, label="Test 1: Sharpe = 1.0 (15% return, 10% vol)")

    # Test 2: Higher return, higher risk
    # CAGR = 25%, Volatility = 20%, Risk-free = 5%
    # Sharpe = (0.25 - 0.05) / 0.20 = 1.0
    sharpe = sharpe_ratio(cagr=0.25, volatility=0.20, risk_free_rate=0.05)
    assert_approx_equal(sharpe, 1.0, label="Test 2: Sharpe = 1.0 (25% return, 20% vol)")

    # Test 3: Negative excess return
    # CAGR = 3%, Volatility = 10%, Risk-free = 5%
    # Sharpe = (0.03 - 0.05) / 0.10 = -0.2
    sharpe = sharpe_ratio(cagr=0.03, volatility=0.10, risk_free_rate=0.05)
    assert_approx_equal(sharpe, -0.2, label="Test 3: Negative Sharpe (return below risk-free)")

    # Test 4: Zero volatility (should return NaN)
    sharpe = sharpe_ratio(cagr=0.10, volatility=0.0, risk_free_rate=0.05)
    assert_approx_equal(sharpe, np.nan, label="Test 4: Zero volatility returns NaN")

    # Test 5: High Sharpe scenario (great risk-adjusted return)
    # CAGR = 60%, Volatility = 25%, Risk-free = 5%
    # Sharpe = (0.60 - 0.05) / 0.25 = 2.2
    sharpe = sharpe_ratio(cagr=0.60, volatility=0.25, risk_free_rate=0.05)
    assert_approx_equal(sharpe, 2.2, label="Test 5: High Sharpe = 2.2 (60% return, 25% vol)")

    # Test 6: Different risk-free rate
    # CAGR = 10%, Volatility = 8%, Risk-free = 3%
    # Sharpe = (0.10 - 0.03) / 0.08 = 0.875
    sharpe = sharpe_ratio(cagr=0.10, volatility=0.08, risk_free_rate=0.03)
    assert_approx_equal(sharpe, 0.875, label="Test 6: Custom risk-free rate (3%)")

    print("\n✓ All Sharpe ratio tests passed!")


def test_correlation():
    """Test correlation calculation."""
    print("\n" + "=" * 60)
    print("Testing Correlation")
    print("=" * 60)

    # Test 1: Perfect positive correlation (use more data points for precision)
    values1 = pd.Series(np.arange(100, 200, 10))  # 10 points
    values2 = pd.Series(np.arange(50, 150, 10))   # Same trend
    corr = compute_correlation(values1, values2)
    assert_approx_equal(corr, 1.0, tolerance=0.01, label="Test 1: Perfect positive correlation")

    # Test 2: Perfect negative correlation
    # For returns to be perfectly negatively correlated, when one goes up X%, other goes down X%
    # Start both at 100, then apply opposite returns
    returns = np.array([0.10, -0.05, 0.08, -0.12, 0.15])  # arbitrary returns
    values1 = 100 * (1 + pd.Series(returns)).cumprod()
    values2 = 100 * (1 - pd.Series(returns)).cumprod()  # opposite returns
    values1 = pd.Series([100] + list(values1))  # prepend starting value
    values2 = pd.Series([100] + list(values2))
    corr = compute_correlation(values1, values2)
    assert_approx_equal(corr, -1.0, tolerance=0.01, label="Test 2: Perfect negative correlation")

    # Test 3: Zero correlation (uncorrelated)
    np.random.seed(42)
    values1 = pd.Series(np.random.randn(100))
    values2 = pd.Series(np.random.randn(100))
    corr = compute_correlation(values1, values2)
    # Should be close to 0 but not exactly due to randomness
    assert abs(corr) < 0.2, f"Test 3: Correlation should be near 0, got {corr}"
    print(f"✓ Test 3: Near-zero correlation: {corr:.6f}")

    # Test 4: Constant values (correlation undefined)
    values1 = pd.Series([100, 100, 100, 100])
    values2 = pd.Series([50, 60, 70, 80])
    corr = compute_correlation(values1, values2)
    assert_approx_equal(corr, np.nan, label="Test 4: Constant values return NaN")

    # Test 5: Single data point (should return NaN)
    values1 = pd.Series([100])
    values2 = pd.Series([50])
    corr = compute_correlation(values1, values2)
    assert_approx_equal(corr, np.nan, label="Test 5: Single point returns NaN")

    print("\n✓ All correlation tests passed!")


def test_beta():
    """Test beta calculation."""
    print("\n" + "=" * 60)
    print("Testing Beta")
    print("=" * 60)

    # Test 1: Beta = 1 (same as market)
    # If portfolio moves exactly with market, beta = 1
    market = pd.Series([100, 110, 120, 110, 100, 105])
    portfolio = pd.Series([200, 220, 240, 220, 200, 210])
    beta = compute_beta(portfolio, market)
    assert_approx_equal(beta, 1.0, label="Test 1: Beta = 1 (moves with market)")

    # Test 2: Beta = 2 (twice as volatile as market)
    # Portfolio moves 2x the market
    market = pd.Series([100, 110, 105, 115, 110])
    portfolio = pd.Series([100, 120, 110, 130, 120])
    beta = compute_beta(portfolio, market)
    # Should be approximately 2.0
    assert 1.8 < beta < 2.2, f"Test 2: Beta should be ~2.0, got {beta}"
    print(f"✓ Test 2: Beta ~2.0 (high volatility): {beta:.6f}")

    # Test 3: Beta = 0 (uncorrelated with market)
    np.random.seed(42)
    market = pd.Series(np.random.randn(100))
    portfolio = pd.Series(np.random.randn(100))
    beta = compute_beta(portfolio, market)
    # Should be close to 0
    assert abs(beta) < 0.3, f"Test 3: Beta should be near 0, got {beta}"
    print(f"✓ Test 3: Beta near 0 (uncorrelated): {beta:.6f}")

    # Test 4: Negative beta (inverse relationship)
    # Create portfolio with opposite returns to market
    returns = np.array([0.10, -0.05, 0.08, -0.12, 0.15])
    market = 100 * (1 + pd.Series(returns)).cumprod()
    portfolio = 100 * (1 - pd.Series(returns)).cumprod()
    market = pd.Series([100] + list(market))
    portfolio = pd.Series([100] + list(portfolio))
    beta = compute_beta(portfolio, market)
    # Should be negative
    assert beta < -0.5, f"Test 4: Beta should be significantly negative, got {beta}"
    print(f"✓ Test 4: Negative beta (inverse): {beta:.6f}")

    # Test 5: Constant market (zero variance) → NaN
    market = pd.Series([100, 100, 100, 100])
    portfolio = pd.Series([50, 60, 70, 80])
    beta = compute_beta(portfolio, market)
    assert_approx_equal(beta, np.nan, label="Test 5: Constant market returns NaN")

    print("\n✓ All beta tests passed!")


def test_compute_metrics_integration():
    """Test the full compute_metrics function with realistic data."""
    print("\n" + "=" * 60)
    print("Testing compute_metrics() Integration")
    print("=" * 60)

    # Create realistic portfolio data: 60% CAGR, 25% volatility over 3 years
    # Starting value: 100, ending value: 100 * 1.6^3 = 409.6
    dates = pd.date_range(start="2020-01-01", end="2023-01-01", freq="D")
    np.random.seed(42)

    # Generate daily returns with target annualized metrics
    target_daily_return = (1.60 ** (1 / 252)) - 1  # Daily return for 60% annual
    target_daily_vol = 0.25 / np.sqrt(252)  # Daily vol for 25% annual

    daily_returns = np.random.normal(target_daily_return, target_daily_vol, len(dates))
    values = 100 * (1 + pd.Series(daily_returns)).cumprod()
    values.index = dates

    metrics = compute_metrics(values, pd.Series(dates))

    print(f"\nComputed metrics for realistic portfolio:")
    print(f"  CAGR: {metrics['cagr']:.2%}")
    print(f"  Volatility: {metrics['volatility']:.2%}")
    print(f"  Sharpe Ratio: {metrics['sharpe']:.3f}")
    print(f"  Max Drawdown: {metrics['max_drawdown']:.2%}")
    print(f"  Total Return: {metrics['total_return']:.2%}")

    # Sanity checks (not exact due to randomness - wide ranges expected)
    assert 0.20 < metrics['cagr'] < 2.50, f"CAGR out of expected range: {metrics['cagr']}"
    assert 0.10 < metrics['volatility'] < 0.40, f"Volatility out of expected range: {metrics['volatility']}"
    assert 0.2 < metrics['sharpe'] < 8.0, f"Sharpe out of expected range: {metrics['sharpe']}"
    assert -0.7 < metrics['max_drawdown'] < 0, f"Max DD should be negative: {metrics['max_drawdown']}"

    print("\n✓ Integration test passed!")


def test_sharpe_old_vs_new():
    """Test to demonstrate the bug in the old Sharpe calculation."""
    print("\n" + "=" * 60)
    print("OLD vs NEW Sharpe Ratio Calculation")
    print("=" * 60)

    # Create test data: 30% CAGR, 20% volatility
    dates = pd.date_range(start="2020-01-01", end="2023-01-01", freq="D")
    np.random.seed(42)

    target_daily_return = (1.30 ** (1 / 252)) - 1
    target_daily_vol = 0.20 / np.sqrt(252)
    daily_returns = np.random.normal(target_daily_return, target_daily_vol, len(dates))
    values = 100 * (1 + pd.Series(daily_returns)).cumprod()

    returns = values.pct_change().fillna(0)
    cagr = annualized_return(values, pd.Series(dates))
    volatility = annualized_vol(returns)

    # OLD (WRONG) formula: returns.mean() * 252
    old_annualized_return = returns.mean() * 252
    old_sharpe = (old_annualized_return - 0.05) / volatility

    # NEW (CORRECT) formula: proper CAGR
    new_sharpe = sharpe_ratio(cagr, volatility, 0.05)

    print(f"\nComparison:")
    print(f"  Actual CAGR: {cagr:.2%}")
    print(f"  Old annualized return (mean * 252): {old_annualized_return:.2%}")
    print(f"  Difference: {(old_annualized_return - cagr):.2%}")
    print(f"\n  Old Sharpe: {old_sharpe:.3f} (WRONG)")
    print(f"  New Sharpe: {new_sharpe:.3f} (CORRECT)")
    print(f"  Difference: {(new_sharpe - old_sharpe):.3f}")

    # The old method underestimates returns due to ignoring compounding
    print("\n✓ Old formula demonstrated to be incorrect!")


def run_all_tests():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("INDICES METRICS COMPREHENSIVE TEST SUITE")
    print("=" * 70)

    try:
        test_annualized_return()
        test_annualized_vol()
        test_max_drawdown()
        test_sharpe_ratio()
        test_correlation()
        test_beta()
        test_compute_metrics_integration()
        test_sharpe_old_vs_new()

        print("\n" + "=" * 70)
        print("✓✓✓ ALL TESTS PASSED! ✓✓✓")
        print("=" * 70)
        return 0

    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(run_all_tests())
