# Benchmark Data Accuracy Test

## Purpose

This test verifies that the benchmark data file (`data/benchmarks/nifty100.csv`) contains accurate closing prices by comparing them against fresh data fetched from the Zerodha API.

## What It Tests

The test:
1. Loads the benchmark CSV file (`nifty100.csv`)
2. Extracts the last N days of closing prices (default: 5 days)
3. Makes a fresh API call to Zerodha to fetch NIFTY 100 historical data for the same dates
4. Compares CSV values vs API values for each date
5. Reports any discrepancies with detailed statistics

## Why This Test Is Important

Accurate benchmark data is critical for:
- **Backtest reliability**: Portfolio performance is measured against the benchmark
- **Outperformance calculation**: Daily outperformance = portfolio return - benchmark return
- **Report accuracy**: HTML reports display benchmark returns and comparison metrics

If benchmark data is stale or incorrect, all performance metrics become unreliable.

## How to Run

### Test Last 5 Days (Default)

```bash
python tests/test_benchmark_data_accuracy.py
```

### Test Custom Number of Days

```bash
python tests/test_benchmark_data_accuracy.py --days 10
```

## Prerequisites

1. **Valid access token**: The test requires a valid Zerodha API access token
   ```bash
   python scripts/login_and_save_token.py
   ```

2. **Benchmark file exists**: The test expects `data/benchmarks/nifty100.csv` to exist
   ```bash
   python scripts/compute_benchmark.py  # Run this first if file doesn't exist
   ```

3. **Active internet connection**: Required for API calls to Zerodha

## Expected Output

### All Tests Pass

```
Testing benchmark data accuracy for last 5 days
================================================================================
✓ Loaded benchmark file: 1378 rows
✓ Extracted last 5 days from CSV

================================================================================
FETCHING FRESH DATA FROM ZERODHA API
================================================================================
Fetching NIFTY 100 data from 2026-01-19 to 2026-01-24...
✓ Fetched 5 rows from API

================================================================================
COMPARISON RESULTS
================================================================================

2026-01-19:
  ✓ CSV:  26205.75
  ✓ API:  26205.75
  ✓ Diff: 0.00 (0.0000%)

2026-01-20:
  ✓ CSV:  25780.95
  ✓ API:  25780.95
  ✓ Diff: 0.00 (0.0000%)

... (5 days total)

================================================================================
SUMMARY STATISTICS
================================================================================
Total dates compared: 5
Matching prices: 5
Mismatches: 0
Max absolute difference: 0.00
Max percentage difference: 0.0000%
Average absolute difference: 0.0000

================================================================================
✅ ALL TESTS PASSED - Benchmark data is accurate!
================================================================================
```

### Tests Fail (Mismatch Detected)

```
2026-01-20:
  ✗ MISMATCH DETECTED
    CSV:  25780.95
    API:  25790.50
    Diff: -9.55 (-0.0370%)

================================================================================
SUMMARY STATISTICS
================================================================================
Total dates compared: 5
Matching prices: 4
Mismatches: 1
Max absolute difference: 9.55
Max percentage difference: 0.0370%
Average absolute difference: 1.9100

================================================================================
❌ TESTS FAILED - Benchmark data has discrepancies!

Recommendation: Run 'python scripts/compute_benchmark.py' to refresh benchmark data
================================================================================
```

## Tolerance Levels

The test uses the following tolerance:

- **Price values**: ±0.01 (1 paisa tolerance for floating point precision)

This is stricter than the daily breakdown test because benchmark data should be exact.

## Exit Codes

- `0`: All tests passed (all prices match within tolerance)
- `1`: One or more tests failed or error occurred

## Common Issues

### Issue: "access_token.txt is empty or missing"

**Solution**: Login to Zerodha and generate a fresh token
```bash
python scripts/login_and_save_token.py
```

Access tokens expire daily at 6 AM, so this must be run each day.

### Issue: "Benchmark file not found"

**Solution**: Generate the benchmark file first
```bash
python scripts/compute_benchmark.py
```

### Issue: "Some dates missing from API data"

**Cause**: API might not have data for recent dates (e.g., weekends, holidays, or market closed)

**Solution**: This is expected behavior. The test will show a warning but may still pass for dates where data exists.

### Issue: Price mismatches detected

**Possible causes**:
1. CSV file is stale (not updated recently)
2. Data quality issue in original fetch
3. Corporate actions (splits, bonuses) affecting index values
4. Different data sources (rare for NIFTY 100)

**Solution**: Refresh the benchmark data
```bash
python scripts/compute_benchmark.py
```

## Integration with Daily Workflow

This test should be run:
1. **Before generating portfolio reports** - Ensures benchmark comparison is accurate
2. **After updating benchmark data** - Verifies the update succeeded
3. **When performance metrics look suspicious** - Rules out benchmark data issues

Example workflow:
```bash
# Daily update workflow
python scripts/login_and_save_token.py
python scripts/compute_benchmark.py
python tests/test_benchmark_data_accuracy.py  # Verify update worked
python scripts/run_final_momentum_portfolio.py
```

## Technical Details

### Data Source

- **Symbol**: "NIFTY 100" (NSE exchange)
- **Instrument Type**: Index
- **API Endpoint**: Zerodha KiteConnect historical data API
- **Interval**: Daily (day candles)

### Implementation

The test uses:
- `PriceClient` from `data_pipeline/price_client.py` for API calls
- `init_kite_client()` from `scripts/history_utils.py` for authentication
- Pandas date normalization to ensure dates match correctly (removes time component)

### Date Handling

Both CSV and API dates are normalized to midnight (00:00:00) before comparison to avoid timezone or time-of-day mismatches.

## Maintenance

If the benchmark symbol or data source changes:

1. Update `SYMBOL` constant in the test (currently "NIFTY 100")
2. Update `preferred_exchange` if moving to different exchange
3. Update tolerance if data precision requirements change
