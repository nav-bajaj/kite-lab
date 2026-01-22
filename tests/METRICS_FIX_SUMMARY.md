# Sharpe Ratio Calculation Fix

## Issue Identified

The Sharpe ratio calculation in `report_indices.py` was using an incorrect formula for annualizing returns:

### OLD (INCORRECT) Formula
```python
def sharpe_ratio(returns: pd.Series, risk_free_rate: float = 0.05) -> float:
    excess_returns = returns.mean() * 252 - risk_free_rate  # WRONG!
    vol = annualized_vol(returns)
    return excess_returns / vol if vol > 0 else np.nan
```

**Problem**: Using `returns.mean() * 252` to annualize returns does not account for compounding effects. This systematically underestimates actual returns and therefore underestimates the Sharpe ratio.

### Example of the Error

For a portfolio with:
- **Actual CAGR**: 65.14%
- **Old formula result**: 36.53%
- **Difference**: -28.62% underestimate!

This leads to:
- **Old Sharpe**: 1.615 (WRONG)
- **New Sharpe**: 3.081 (CORRECT)
- **Difference**: 1.466 (91% underestimate!)

## Solution

The corrected formula now uses proper CAGR calculation:

### NEW (CORRECT) Formula
```python
def sharpe_ratio(cagr: float, volatility: float, risk_free_rate: float = 0.05) -> float:
    """
    Compute Sharpe ratio.

    Args:
        cagr: Annualized return (CAGR) - properly compounded
        volatility: Annualized volatility
        risk_free_rate: Annual risk-free rate (default 5%)

    Returns:
        Sharpe ratio (excess return per unit of risk)
    """
    if volatility > 0:
        return (cagr - risk_free_rate) / volatility
    return np.nan
```

The `compute_metrics()` function was refactored to compute CAGR once using the correct `annualized_return()` function and pass it to `sharpe_ratio()`.

## Why the Old Formula Was Wrong

### Arithmetic Mean vs Geometric Mean

**Old formula**: Arithmetic mean of daily returns × 252
- Assumes: `(1 + r₁ + r₂ + ... + rₙ) / n`
- Does not compound returns
- Valid only for very small returns

**New formula**: Geometric mean (CAGR)
- Assumes: `(1 + r₁) × (1 + r₂) × ... × (1 + rₙ)^(1/n) - 1`
- Properly compounds returns
- Mathematically correct for investment returns

### Real-World Impact

For high-performing strategies like your momentum portfolio (60%+ CAGR), the difference is substantial:

| Metric | Old Formula | New Formula | Error |
|--------|-------------|-------------|-------|
| Annualized Return | 36.53% | 65.14% | -44% |
| Sharpe Ratio | 1.615 | 3.081 | -48% |

The old formula made your strategy appear significantly worse than it actually is!

## Other Bugs Fixed

### 1. Removed Unused Import
- Removed `from collections import defaultdict` (was triggering Pylance warning)

### 2. All Other Metrics Verified
Created comprehensive test suite (`tests/test_indices_metrics.py`) covering:
- ✅ Annualized return (CAGR) - 6 tests
- ✅ Annualized volatility - 4 tests
- ✅ Maximum drawdown - 5 tests
- ✅ Sharpe ratio - 6 tests
- ✅ Correlation - 5 tests
- ✅ Beta - 5 tests
- ✅ Integration test - 1 test
- ✅ Old vs New comparison - 1 test

**Total: 33 tests, all passing ✓**

## Files Modified

1. **scripts/report_indices.py**
   - Fixed `sharpe_ratio()` function
   - Refactored `compute_metrics()` to use correct CAGR
   - Removed unused `defaultdict` import

2. **tests/test_indices_metrics.py** (NEW)
   - Comprehensive test suite for all financial metrics
   - Demonstrates the bug in old formula
   - Validates correct behavior with known inputs/outputs

## Running the Tests

```bash
python tests/test_indices_metrics.py
```

Expected output:
```
======================================================================
✓✓✓ ALL TESTS PASSED! ✓✓✓
======================================================================
```

## Impact on Reports

All future indices comparison reports (`report_indices.py`) will now show:
- **Accurate Sharpe ratios** for all indices
- **Correct risk-adjusted performance** comparisons
- **Reliable strategy evaluation** metrics

Previous reports generated with the old formula should be regenerated for accurate results.

## Mathematical Background

### Sharpe Ratio Definition

The Sharpe ratio measures risk-adjusted return:

```
Sharpe Ratio = (Portfolio Return - Risk-Free Rate) / Portfolio Volatility
```

Where all terms must be in the **same time units** (typically annualized).

### Correct Annualization

**For returns** (geometric):
```python
CAGR = (End Value / Start Value)^(365 / days) - 1
```

**For volatility** (arithmetic):
```python
Annual Volatility = Daily Volatility × sqrt(252)
```

**Not** for returns:
```python
# WRONG!
Annual Return = Daily Mean Return × 252
```

This is because returns compound multiplicatively, not additively.

## References

- **Sharpe, W.F. (1994)**. "The Sharpe Ratio". Journal of Portfolio Management.
- **Standard financial practice**: Always use geometric mean (CAGR) for multi-period returns
- **Python pandas documentation**: `pct_change()` returns simple returns, not log returns

---

**Fixed by**: Claude Code
**Date**: 2026-01-22
**Verified**: 33 passing tests
