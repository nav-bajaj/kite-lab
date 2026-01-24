# Zerodha API Historical Data Inconsistency Issue

## Critical Discovery (January 23, 2026)

The Zerodha KiteConnect API returns **inconsistent values for BOTH index and stock data** depending on the date range requested.

## Problem Description

When fetching historical data for indices (NIFTY 50, NIFTY 100, NIFTY BANK, etc.), the API returns different closing prices for the **same date** depending on whether you:
- Fetch a single day
- Fetch a range that includes that day

### Example: NIFTY 100 on 2026-01-23

```python
# Fetch single day only
data = kite.historical_data(
    instrument_token=260617,  # NIFTY 100
    from_date='2026-01-23',
    to_date='2026-01-23',
    interval='day'
)
# Returns: close = 25590.10

# Fetch range including that day
data = kite.historical_data(
    instrument_token=260617,
    from_date='2026-01-19',
    to_date='2026-01-24',
    interval='day'
)
# Returns: close = 25570.50 for 2026-01-23

# Difference: 19.60 points (0.077%)
```

## Scope of Issue

### Affected Instruments

**ALL INDICES** tested show this behavior (large discrepancies):

| Index | Single Day | Range Fetch | Difference |
|-------|-----------|-------------|------------|
| NIFTY 50 | 25064.75 | 25048.65 | 16.10 |
| NIFTY 100 | 25590.10 | 25570.50 | 19.60 |
| NIFTY BANK | 58501.10 | 58473.10 | 28.00 |
| NIFTY MIDCAP 100 | 57184.40 | 57145.65 | 38.75 |
| NIFTY DIV OPPS 50 | 6305.00 | 6307.20 | 2.20 |

**SOME STOCKS** also show this behavior (small discrepancies):

| Stock | Single Day | Range Fetch | Difference |
|-------|-----------|-------------|------------|
| WIPRO | 238.00 | 238.05 | 0.05 |
| ITC | 323.15 | 323.00 | 0.15 |
| TCS | 3157.00 | 3157.00 | 0.00 ✓ |
| INFY | 1672.00 | 1672.00 | 0.00 ✓ |
| RELIANCE | 1387.00 | 1387.00 | 0.00 ✓ |
| HDFCBANK | 915.80 | 915.80 | 0.00 ✓ |
| SBIN | 1028.40 | 1028.40 | 0.00 ✓ |
| BHARTIARTL | 1988.00 | 1988.00 | 0.00 ✓ |

Test date: 2026-01-23

**Conclusion**: While indices have large discrepancies (10-70 points), some stocks also show small discrepancies (0.05-0.15 rupees). The fix must be applied universally.

## Root Cause Hypothesis

Index values likely undergo **end-of-day revisions/adjustments**:

1. **Single-day fetches**: Return preliminary/intraday closing values
2. **Range fetches**: Return finalized/revised closing values
3. **Revision window**: Appears to happen 1-2 days after the trading day

This is standard for index providers who may:
- Adjust for corporate actions
- Correct calculation errors
- Apply weighting adjustments
- Update constituent changes

## Impact on Our System

### Broken Components

1. **`scripts/compute_benchmark.py`**
   - Uses incremental updates (fetches only new dates)
   - Gets preliminary values that are never revised
   - Existing benchmark data has wrong values for recent dates

2. **All backtests using benchmark data**
   - Outperformance calculations are incorrect
   - Portfolio vs benchmark comparisons are wrong
   - Historical analysis is unreliable

3. **Portfolio reports**
   - Daily breakdown shows wrong benchmark returns
   - Comparison metrics are inaccurate

### Example of Corruption

In `data/benchmarks/nifty100.csv` (last 10 days):

| Date | CSV Value | Actual Value | Difference |
|------|-----------|--------------|------------|
| 2026-01-13 | 26278.40 | 26296.75 | -18.35 |
| 2026-01-19 | 26205.75 | 26181.95 | +23.80 |
| 2026-01-21 | 25771.15 | 25701.40 | +69.75 |

3 out of 10 days have wrong data (30% error rate).

## Impact on Our System - COMPLETE SCOPE

### All Affected Components (Fixed)

1. **`data_pipeline/price_client.py`** - Core PriceClient class
   - Used by: compute_benchmark.py, update_prices.py
   - Fix: Added +1 day to end date

2. **`scripts/history_utils.py`** - Utility fetch_history function
   - Used by: Many scripts including fetch_nse500_history.py
   - Fix: Added +1 day to end date

3. **`scripts/fetch_indices_history.py`** - Indices tracking script
   - Fetches NIFTY 50, sectoral indices, commodity indices
   - Fix: Added +1 day AND 30-day rolling window

4. **`scripts/compute_benchmark.py`** - Benchmark (NIFTY 100) updates
   - Critical for portfolio performance metrics
   - Fix: Added +1 day AND 30-day rolling window

5. **`scripts/fetch_history_and_analyse.py`** - Analysis script
   - Fix: Added +1 day to end date

### Portfolio Impact

**ALL stock price data** in `nse500_data/` directory is potentially affected:
- Scripts using `PriceClient` or `history_utils.fetch_history` were fetching preliminary values
- This affects signal generation, backtests, and all portfolio calculations
- While discrepancies are small for individual stocks (0.05-0.15), they compound across 24 positions

**ALL index data** in `indices_data/` directory is affected:
- Larger discrepancies (10-70 points)
- Affects benchmarking, sector analysis, and comparison metrics

## Solutions

### Short-Term Fix (Immediate) - COMPLETED

**Always add +1 day to end_date when calling Zerodha API**:

```python
# BAD: Single day fetch (gets preliminary value)
data = kite.historical_data(token, '2026-01-23', '2026-01-23', 'day')

# GOOD: Range fetch (gets finalized value)
data = kite.historical_data(token, '2026-01-20', '2026-01-24', 'day')
```

### Long-Term Fix (Recommended)

1. **Modify `compute_benchmark.py`**:
   - Instead of incremental updates (fetch only new dates)
   - Always fetch **last N days** (e.g., 10 days) on every run
   - Overwrite recent data with finalized values

2. **Add validation**:
   - Compare recent benchmark data against fresh API fetches
   - Alert if discrepancies exceed threshold (e.g., 10 points)

3. **Periodic full refresh**:
   - Re-fetch entire benchmark history monthly
   - Catches any historical revisions

### Implementation Plan

#### Step 1: Fix compute_benchmark.py

```python
# Current (BROKEN):
start = existing["date"].max() + pd.Timedelta(days=1)  # Only fetch new dates
fetched = client.fetch_history(SYMBOL, start, end, interval="day")

# Fixed (CORRECT):
# Always re-fetch last 30 days to get finalized values
lookback_days = 30
start = max(
    pd.Timestamp("2020-01-01"),
    existing["date"].max() - pd.Timedelta(days=lookback_days)
)
fetched = client.fetch_history(SYMBOL, start, end, interval="day")

# Merge with existing, preferring new data for overlaps
combined = pd.concat([existing, fetched]).drop_duplicates(subset=['date'], keep='last')
```

#### Step 2: Add Data Validation

Create `scripts/validate_benchmark_data.py`:
- Fetch last 10 days from API
- Compare against CSV
- Alert if differences > threshold

#### Step 3: Full Revalidation

Run one-time full refresh:
```bash
# Backup current file
cp data/benchmarks/nifty100.csv data/benchmarks/nifty100_backup.csv

# Delete and rebuild from scratch
rm data/benchmarks/nifty100.csv
python scripts/compute_benchmark.py
```

## Testing

Created `tests/test_benchmark_data_accuracy.py` to:
- Compare last N days of CSV against fresh API data
- Report discrepancies
- Can be run anytime to validate data quality

## Lessons Learned

1. **Never trust incremental updates for index data**
2. **Always validate recent data against fresh fetches**
3. **Index data has revision periods - fetch ranges, not single days**
4. **This issue only affects indices, not stocks**
5. **Data quality issues can be subtle and systemic**

## Recommendations

1. **Immediate**: Run full benchmark refresh
2. **Short-term**: Fix compute_benchmark.py to use rolling window
3. **Long-term**: Add automated validation to daily pipeline
4. **Monitoring**: Include benchmark validation in daily checks

## Next Steps - Data Refresh Required

### Critical Actions

1. **Refresh benchmark data** (COMPLETED)
   ```bash
   python scripts/compute_benchmark.py
   ```
   - 30-day rolling window automatically corrected recent bad data
   - Verified with: `python tests/test_benchmark_data_accuracy.py --days 10`

2. **Refresh all indices data** (RECOMMENDED)
   ```bash
   python scripts/fetch_indices_history.py
   ```
   - Will re-fetch last 30 days with corrected values
   - Affects: all files in `indices_data/` directory

3. **Refresh NSE 500 stock data** (RECOMMENDED)
   ```bash
   python scripts/fetch_nse500_history.py
   ```
   - Will automatically use fixed PriceClient
   - Only recent data (last 30 days) needs correction

4. **Re-run recent backtests** (RECOMMENDED)
   - Any backtest run in the last 30 days may have incorrect recent data
   - Re-run with refreshed data to get accurate metrics

5. **Monitor daily updates**
   - Daily pipeline now uses fixed fetch functions
   - Future data will be accurate
   - Test periodically: `python tests/test_benchmark_data_accuracy.py`

### Data Quality Notes

- **Historical data (>30 days old)**: Likely accurate (values finalized long ago)
- **Recent data (<30 days)**: May have preliminary values, needs refresh
- **Today's data**: Will be preliminary until tomorrow, rolling window will correct it

## References

- Issue discovered during portfolio testing: 2026-01-23
- Test: `tests/test_benchmark_data_accuracy.py`
- Fixed scripts: All data fetching utilities (see "All Affected Components" above)
- Documentation: `docs/benchmark_data_fix_summary.md` for executive summary
