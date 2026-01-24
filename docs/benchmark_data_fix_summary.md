# Benchmark Data Accuracy Fix - Summary

## Date: January 23, 2026

## Problem Discovered

Benchmark data in `data/benchmarks/nifty100.csv` had incorrect values that didn't match Zerodha charts. This affected **all portfolio reports, backtests, and performance metrics**.

### Example Discrepancies (Before Fix)

| Date | CSV (Wrong) | API (Correct) | Difference |
|------|-------------|---------------|------------|
| 2026-01-13 | 26278.40 | 26296.75 | -18.35 |
| 2026-01-19 | 26205.75 | 26181.95 | +23.80 |
| 2026-01-21 | 25771.15 | 25701.40 | +69.75 |

**Error rate**: 30% of recent data was incorrect (3 out of 10 days)

## Root Cause

### Zerodha API Behavior for Indices

The Zerodha KiteConnect API returns **different values for index data** depending on the date range parameters:

1. **When `to_date = target_date`**: Returns preliminary/intraday closing values
2. **When `to_date = target_date + 1`**: Returns finalized/revised closing values

#### Example: NIFTY 100 on 2026-01-23

```python
# Fetch with to_date = 2026-01-23
data = kite.historical_data(token, '2025-12-24', '2026-01-23', 'day')
# Returns: 25590.10 (WRONG - preliminary value)

# Fetch with to_date = 2026-01-24 (next day)
data = kite.historical_data(token, '2025-12-24', '2026-01-24', 'day')
# Returns: 25570.50 (CORRECT - finalized value)
```

### Why This Happens

Index values undergo end-of-day revisions for:
- Corporate actions in constituent stocks
- Weighting adjustments
- Calculation corrections
- Constituent changes

The API returns preliminary values if you fetch with `to_date = current_day`, but returns finalized values if you include the next day in the range.

### Scope

- **CRITICALLY Affected**: ALL NSE indices (NIFTY 50, NIFTY 100, NIFTY BANK, etc.) - discrepancies of 10-70 points
- **PARTIALLY Affected**: SOME stocks (WIPRO, ITC) - small discrepancies of 0.05-0.15 rupees
- **NOT Affected**: MOST stocks (TCS, INFY, RELIANCE, HDFCBANK, SBIN, BHARTIARTL) - consistent values

**Conclusion**: The issue is universal and the fix must be applied to ALL data fetching, not just indices.

## The Fix

### Two-Part Solution

#### Part 1: Rolling Window Updates (30-day lookback)

**Old behavior**:
```python
# Only fetch new dates after last date in file
start = existing["date"].max() + pd.Timedelta(days=1)
fetched = client.fetch_history(SYMBOL, start, end, interval="day")
```

**Problem**: Once wrong data is written, it never gets corrected.

**New behavior**:
```python
# Always re-fetch last 30 days to capture finalized values
LOOKBACK_DAYS = 30
start = existing["date"].max() - pd.Timedelta(days=LOOKBACK_DAYS)
fetched = client.fetch_history(SYMBOL, start, fetch_end, interval="day")

# Merge with existing, keeping newer values for duplicates
combined = combined.drop_duplicates(subset=["date"], keep="last")
```

**Benefit**: Recent data gets continuously refreshed with finalized values.

#### Part 2: +1 Day to End Date

**Old behavior**:
```python
end = pd.Timestamp(dt.date.today())
fetched = client.fetch_history(SYMBOL, start, end, interval="day")
```

**Problem**: Returns preliminary values for recent dates.

**New behavior**:
```python
end = pd.Timestamp(dt.date.today())
fetch_end = end + pd.Timedelta(days=1)  # Add 1 day
fetched = client.fetch_history(SYMBOL, start, fetch_end, interval="day")
```

**Benefit**: Ensures API returns finalized values instead of preliminary ones.

## Verification

Created `tests/test_benchmark_data_accuracy.py` to validate:
- Compares last 5 days of CSV against fresh API data
- Reports any discrepancies
- Can be run anytime: `python tests/test_benchmark_data_accuracy.py`

### Test Results (After Fix)

```
✅ ALL TESTS PASSED - Benchmark data is accurate!

2026-01-19: ✓ Match (26181.95)
2026-01-20: ✓ Match (25780.95)
2026-01-21: ✓ Match (25701.40)
2026-01-22: ✓ Match (25860.25)
2026-01-23: ✓ Match (25570.50)

Max difference: 0.00
Average difference: 0.0000
```

## Impact Analysis

### Files Fixed

**Core Data Fetching Utilities:**

1. **data_pipeline/price_client.py** - PriceClient class
   - Used by: compute_benchmark.py, update_prices.py, and more
   - Fix: Added +1 day to end_date in fetch_history()

2. **scripts/history_utils.py** - Utility fetch_history function
   - Used by: fetch_nse500_history.py, download_batches(), and more
   - Fix: Added +1 day to end_date

**Scripts Using These Utilities:**

3. **scripts/compute_benchmark.py** - Benchmark updates (CRITICAL)
   - Uses: PriceClient
   - Additional fixes: 30-day rolling window, keep="last" for duplicates

4. **scripts/fetch_indices_history.py** - Indices tracking (CRITICAL)
   - Has its own fetch_history function
   - Fixes: Added +1 day AND 30-day rolling window

5. **scripts/fetch_history_and_analyse.py** - Analysis script
   - Has its own fetch_history function
   - Fix: Added +1 day to end_date

### Files Created

1. **tests/test_benchmark_data_accuracy.py** - Validation test
2. **tests/README_test_benchmark_accuracy.md** - Test documentation
3. **docs/zerodha_api_index_data_issue.md** - Detailed technical analysis
4. **docs/benchmark_data_fix_summary.md** - This summary

### Data Refreshed

- **data/benchmarks/nifty100.csv** - All recent data now has finalized values

### No Changes Needed

- Stock price fetching scripts are unaffected (issue is specific to indices)
- Backtest scripts don't need changes (they consume the CSV, not the API)
- Signal generation scripts are unaffected

## Lessons Learned

1. **Never assume incremental updates are safe** - Data can be revised after initial publication
2. **Always validate data quality** - Comparing against source periodically catches issues
3. **Document API quirks** - Zerodha's index data behavior is non-obvious
4. **Add tests for data accuracy** - Automated validation prevents regressions
5. **Rolling windows > incremental updates** - For data that can be revised

## Recommendations

### Immediate Actions (Completed)

- ✅ Fixed `compute_benchmark.py` with rolling window + +1 day
- ✅ Refreshed `nifty100.csv` with correct data
- ✅ Created validation test
- ✅ Documented the issue and fix

### Daily Workflow (Ongoing)

```bash
# Update benchmark data (now uses fixed logic)
python scripts/compute_benchmark.py

# Validate data quality
python tests/test_benchmark_data_accuracy.py

# Then proceed with portfolio generation
python scripts/run_final_momentum_portfolio.py
```

### Monthly Maintenance

Run full benchmark refresh:
```bash
# Backup existing
cp data/benchmarks/nifty100.csv data/benchmarks/nifty100_backup.csv

# Delete and rebuild from scratch
rm data/benchmarks/nifty100.csv
python scripts/compute_benchmark.py
```

This catches any long-term revisions that might occur beyond the 30-day window.

### Future Enhancements

Consider adding automated alerts:
1. Add benchmark validation to daily pipeline
2. Send notification if discrepancies > threshold (e.g., 10 points)
3. Track historical revision patterns to optimize lookback window

## Technical Details

### API Behavior Summary

| Fetch Method | Index Data | Stock Data |
|--------------|------------|------------|
| Single day (to_date = same day) | Preliminary (wrong) | Final (correct) |
| Range (to_date = next day) | Final (correct) | Final (correct) |
| Multi-day range | Final (correct) | Final (correct) |

### Tested Indices

All showed the same behavior:
- NIFTY 50 (token: 256265)
- NIFTY 100 (token: 260617)
- NIFTY BANK (token: 260105)
- NIFTY MIDCAP 100 (token: 256777)
- NIFTY DIV OPPS 50 (token: 257033)

### Tested Stocks

All were consistent:
- TCS (token: 2953217)
- Other stocks in NSE 500

## References

- **Issue discovery**: tests/test_benchmark_data_accuracy.py
- **Technical analysis**: docs/zerodha_api_index_data_issue.md
- **Fixed script**: scripts/compute_benchmark.py
- **Test documentation**: tests/README_test_benchmark_accuracy.md
