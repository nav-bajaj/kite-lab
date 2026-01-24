# Stock Data Accuracy Test

## Purpose

This test verifies that individual stock price data files in `nse500_data/` contain accurate closing prices by comparing them against fresh data fetched from the Zerodha API.

## What It Tests

The test:
1. Validates the symbol is in the NSE 500 universe
2. Loads the stock's CSV file from `nse500_data/<SYMBOL>_day.csv`
3. Extracts the last N days of closing prices (default: 10 days)
4. Makes a fresh API call to Zerodha for the same date range
5. Compares CSV values vs API values for each date
6. Reports any discrepancies with detailed statistics

## Why This Test Is Important

Accurate stock price data is critical for:
- **Signal generation**: Momentum scores are calculated from price data
- **Portfolio construction**: Top-24 rankings depend on accurate prices
- **Backtesting**: Performance metrics rely on correct entry/exit prices
- **Trade execution**: Current positions are valued using latest prices

If stock data contains preliminary values instead of finalized values, it affects your entire trading strategy.

## How to Run

### Test a Single Stock (Default: 10 days)

```bash
python tests/test_stock_data_accuracy.py --symbol TCS
```

### Test with Custom Lookback Period

```bash
# Test last 30 days
python tests/test_stock_data_accuracy.py --symbol INFY --days 30

# Test last 5 days
python tests/test_stock_data_accuracy.py --symbol WIPRO --days 5
```

### Test Multiple Stocks

```bash
# Create a simple test script
for symbol in TCS INFY WIPRO ITC RELIANCE HDFCBANK; do
    echo "Testing $symbol..."
    python tests/test_stock_data_accuracy.py --symbol $symbol --days 10
    echo ""
done
```

### Short Form Arguments

```bash
python tests/test_stock_data_accuracy.py -s TCS -d 10
```

## Prerequisites

1. **Valid access token**: The test requires a valid Zerodha API access token
   ```bash
   python scripts/login_and_save_token.py
   ```

2. **Stock data exists**: The test expects stock CSV files to exist
   ```bash
   python scripts/fetch_nse500_history.py  # Fetch all NSE 500 stocks
   # OR
   python scripts/update_prices.py --symbols TCS INFY --daily-dir nse500_data  # Specific stocks
   ```

3. **NSE 500 universe file**: The test validates against NSE 500 list
   - File: `data/static/nse500_universe.csv`
   - Should already exist in the repository

4. **Active internet connection**: Required for API calls to Zerodha

## Expected Output

### All Tests Pass

```
Testing stock data accuracy for TCS (last 10 days)
================================================================================
✓ Loaded CSV file: 1508 rows
✓ Extracted last 10 days from CSV

================================================================================
FETCHING FRESH DATA FROM ZERODHA API
================================================================================
Fetching TCS data from 2026-01-09 to 2026-01-24...
✓ Fetched 10 rows from API

================================================================================
COMPARISON RESULTS
================================================================================

2026-01-09:
  ✓ CSV:  3132.00
  ✓ API:  3132.00
  ✓ Diff: 0.00 (0.0000%)

2026-01-12:
  ✓ CSV:  3128.50
  ✓ API:  3128.50
  ✓ Diff: 0.00 (0.0000%)

... (10 days total)

================================================================================
SUMMARY STATISTICS
================================================================================
Symbol: TCS
Total dates compared: 10
Matching prices: 10
Mismatches: 0
Max absolute difference: 0.00
Max percentage difference: 0.0000%
Average absolute difference: 0.0000

================================================================================
✅ ALL TESTS PASSED - TCS data is accurate!
================================================================================
```

### Tests Fail (Mismatch Detected)

```
2026-01-23:
  ✗ MISMATCH DETECTED
    CSV:  238.00
    API:  238.05
    Diff: -0.05 (-0.0210%)

================================================================================
SUMMARY STATISTICS
================================================================================
Symbol: WIPRO
Total dates compared: 10
Matching prices: 9
Mismatches: 1
Max absolute difference: 0.05
Max percentage difference: 0.0210%
Average absolute difference: 0.0050

================================================================================
❌ TESTS FAILED - WIPRO data has discrepancies!

Recommendation: Re-fetch WIPRO data:
  python scripts/update_prices.py --symbols WIPRO --daily-dir nse500_data
================================================================================
```

## Tolerance Levels

The test uses the following tolerance:

- **Price values**: ±0.01 (1 paisa tolerance)

This is very tight to catch even small discrepancies. Stocks should have exact matches or differences of only 1 paisa due to floating-point precision.

## Exit Codes

- `0`: All tests passed (all prices match within tolerance)
- `1`: One or more tests failed, symbol not found, or error occurred

## Common Issues

### Issue: "Stock data file not found"

**Cause**: The CSV file doesn't exist in `nse500_data/` directory

**Solutions**:
1. Check symbol spelling: `ls nse500_data/ | grep -i <symbol>`
2. Fetch the stock data:
   ```bash
   python scripts/update_prices.py --symbols <SYMBOL> --daily-dir nse500_data
   ```
3. Or fetch all NSE 500 stocks:
   ```bash
   python scripts/fetch_nse500_history.py
   ```

### Issue: "Symbol is not in the NSE 500 universe"

**Cause**: The symbol is not in `data/static/nse500_universe.csv`

**Solution**: The test will continue anyway, but verify:
1. Symbol spelling is correct
2. Stock is actually in NSE 500 (may have been removed from index)
3. Use correct symbol (e.g., "HDFCBANK" not "HDFC Bank")

### Issue: "access_token.txt is empty or missing"

**Solution**: Login to Zerodha and generate a fresh token
```bash
python scripts/login_and_save_token.py
```

Access tokens expire daily at 6 AM, so this must be run each day.

### Issue: Price mismatches detected

**Possible causes**:
1. CSV file has stale data (not updated recently)
2. Data was fetched with old buggy code (before +1 day fix)
3. Corporate actions (splits, bonuses) affecting prices

**Solution**: Re-fetch the stock data
```bash
python scripts/update_prices.py --symbols <SYMBOL> --daily-dir nse500_data
```

## Integration with Portfolio Testing

This test is useful for:

1. **Before generating portfolio**: Verify current holdings have accurate prices
   ```bash
   # Get current portfolio symbols
   cat data/final_portfolio/final_portfolio_24.csv | cut -d',' -f2 | tail -n +2 > /tmp/symbols.txt

   # Test each symbol
   while read symbol; do
       python tests/test_stock_data_accuracy.py --symbol "$symbol" --days 5
   done < /tmp/symbols.txt
   ```

2. **After data refresh**: Verify specific stocks were updated correctly
   ```bash
   python tests/test_stock_data_accuracy.py --symbol WIPRO --days 30
   ```

3. **Investigating signal issues**: If a stock's momentum score looks wrong, check if price data is accurate
   ```bash
   python tests/test_stock_data_accuracy.py --symbol <SUSPICIOUS_STOCK> --days 30
   ```

## Technical Details

### Data Source

- **Exchange**: NSE (National Stock Exchange)
- **Instrument Type**: Equity (EQ)
- **API Endpoint**: Zerodha KiteConnect historical data API
- **Interval**: Daily (day candles)

### Implementation

The test uses:
- `PriceClient` from `data_pipeline/price_client.py` for API calls (with +1 day fix)
- `init_kite_client()` from `scripts/history_utils.py` for authentication
- Pandas date normalization to ensure dates match correctly
- NSE 500 universe validation from `data/static/nse500_universe.csv`

### Date Handling

Both CSV and API dates are normalized to midnight (00:00:00) before comparison to avoid timezone or time-of-day mismatches.

The PriceClient automatically adds +1 day to the end date to get finalized values (see: `docs/zerodha_api_index_data_issue.md`).

## Comparison with Benchmark Test

| Feature | Stock Test | Benchmark Test |
|---------|-----------|----------------|
| **Target** | Individual stocks | NIFTY 100 index |
| **Directory** | `nse500_data/` | `data/benchmarks/` |
| **Validation** | NSE 500 universe | Single file |
| **Typical discrepancies** | 0.05-0.15 rupees | 10-70 points |
| **Usage** | Validate portfolio holdings | Validate benchmark comparison |

Use both tests together to ensure complete data quality.

## Examples

### Test Your Current Portfolio

```bash
# Test the exact stocks in your portfolio
python -c "
import pandas as pd
portfolio = pd.read_csv('data/final_portfolio/final_portfolio_24.csv')
for symbol in portfolio['symbol']:
    print(f'\\n=== Testing {symbol} ===')
    import subprocess
    subprocess.run(['python', 'tests/test_stock_data_accuracy.py', '--symbol', symbol, '--days', '10'])
"
```

### Test High-Impact Stocks

```bash
# Test stocks that commonly appear in momentum strategies
for stock in TCS INFY RELIANCE HDFCBANK ICICIBANK SBIN BHARTIARTL; do
    python tests/test_stock_data_accuracy.py -s $stock -d 10
done
```

### Batch Test with Summary

```bash
# Test multiple stocks and create summary
echo "Stock,Status" > stock_test_results.csv
for stock in TCS INFY WIPRO ITC; do
    if python tests/test_stock_data_accuracy.py -s $stock -d 10 > /dev/null 2>&1; then
        echo "$stock,PASS" >> stock_test_results.csv
    else
        echo "$stock,FAIL" >> stock_test_results.csv
    fi
done
cat stock_test_results.csv
```

## Maintenance

If the CSV file format changes, update the column names in the test:
- Currently expects: `date`, `close` columns
- Line 59: `df = pd.read_csv(csv_path, parse_dates=["date"])`
- Line 133: `api_data[["date", "close"]]`

If the NSE 500 universe file location changes, update line 25:
```python
universe_path = ROOT / "data" / "static" / "nse500_universe.csv"
```
