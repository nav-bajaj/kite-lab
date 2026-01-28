# Daily Breakdown Report Test

## Purpose

This test verifies that the daily breakdown table in portfolio HTML reports displays correctly computed values for:
- Portfolio daily returns (%)
- Portfolio PnL (absolute value)
- Benchmark daily returns (%)
- Outperformance (portfolio return - benchmark return)

## What It Tests

The test:
1. Loads the equity CSV file from the backtest
2. Computes the last 10 days of daily performance using the same logic as `report_backtests.py`
3. Parses the daily breakdown table from the HTML report
4. Compares expected vs. actual values for all metrics

### Formulas Verified

For each day `i`:
- **Portfolio Return**: `(portfolio_value[i] / portfolio_value[i-1]) - 1`
- **Portfolio PnL**: `portfolio_value[i] - portfolio_value[i-1]`
- **Benchmark Return**: `(benchmark[i] / benchmark[i-1]) - 1`
- **Outperformance**: `portfolio_return - benchmark_return`

## How to Run

### Test Latest Portfolio

```bash
python tests/test_daily_breakdown_report.py
```

This uses the default path: `experiments/final_portfolio/final_portfolio_20260123165312`

### Test Specific Portfolio

```bash
python tests/test_daily_breakdown_report.py --portfolio-dir experiments/final_portfolio/final_portfolio_YYYYMMDDHHMMSS
```

## Expected Output

```
Testing daily breakdown for: final_portfolio_20260123165312
================================================================================
✓ Loaded equity data: 1378 rows
✓ Computed trailing 10-day performance: 10 days
✓ Parsed daily breakdown from HTML: 10 rows

================================================================================
VERIFICATION RESULTS
================================================================================

2026-01-09:
  ✓ Portfolio Return: -1.45%
  ✓ Portfolio PnL: -171120
  ✓ Benchmark Return: -0.79%
  ✓ Outperformance: -0.66%

... (10 days total)

================================================================================
✅ ALL TESTS PASSED - Daily breakdown calculations are correct!
================================================================================
```

## Tolerance Levels

The test uses the following tolerances to account for rounding in HTML display:

- **Percentage values**: ±0.005pp (accounts for 2 decimal place rounding in HTML)
- **PnL values**: ±1 rupee (accounts for integer display in HTML)

## Exit Codes

- `0`: All tests passed
- `1`: One or more tests failed or error occurred

## Files Required

The test expects the following files to exist in the portfolio directory:
- `backtests/baseline/momentum_equity.csv` - Equity time series data
- `report.html` - Generated HTML report

## Maintenance

If the HTML report format changes, update the regex pattern in `parse_daily_breakdown_from_html()`:

```python
pattern = r'<tr>\s*<td[^>]*>(\d{4}-\d{2}-\d{2})</td>...'
```

The pattern must match the table row structure in `scripts/report_backtests.py` around line 2015-2021.
