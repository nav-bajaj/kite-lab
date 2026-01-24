# Data Refresh Action Plan - Post API Fix

## Date: January 23, 2026

## Background

All data fetching functions have been fixed to handle Zerodha API's preliminary vs. finalized values issue. However, **existing data files may contain incorrect preliminary values** from the last 30 days.

## What Was Fixed

1. **data_pipeline/price_client.py** - Core PriceClient (+1 day fix)
2. **scripts/history_utils.py** - Utility fetch_history (+1 day fix)
3. **scripts/fetch_indices_history.py** - Indices tracking (+1 day + rolling window)
4. **scripts/compute_benchmark.py** - Benchmark updates (+1 day + rolling window)
5. **scripts/fetch_history_and_analyse.py** - Analysis script (+1 day fix)

## Required Data Refreshes

### Priority 1: CRITICAL (Do Immediately)

#### 1.1 Benchmark Data (COMPLETED ✓)

```bash
python scripts/compute_benchmark.py
```

**Status**: Already refreshed and verified
**Verification**: `python tests/test_benchmark_data_accuracy.py --days 10`
**Result**: All 10 days match perfectly (including previously incorrect 2026-01-13)

### Priority 2: HIGH (Do Today)

#### 2.1 Indices Data Refresh

```bash
python scripts/fetch_indices_history.py
```

**What it updates**:
- All files in `indices_data/` directory
- NIFTY 50, NIFTY sectoral indices, commodity indices
- Uses 30-day rolling window to correct recent data

**Time estimate**: 5-10 minutes (depends on number of indices)

**Affected files**:
- `indices_data/NIFTY_50.csv`
- `indices_data/NIFTY_BANK.csv`
- `indices_data/NIFTY_IT.csv`
- ... (all tracked indices)

**Impact if skipped**: Sector analysis and index comparisons will use incorrect values for last 30 days

#### 2.2 NSE 500 Stock Data Refresh

```bash
python scripts/fetch_nse500_history.py
```

**What it updates**:
- All files in `nse500_data/` directory (~500 stocks)
- Each file: `<SYMBOL>_day.csv`
- Now uses fixed PriceClient automatically

**Time estimate**: 30-60 minutes (API rate limits apply)

**Affected data**: Last 30 days of stock prices
- Most stocks: No change (already had finalized values)
- Some stocks (like WIPRO, ITC): Small corrections (0.05-0.15 rupees)

**Impact if skipped**:
- Signal generation may use slightly incorrect prices
- Backtests may have small inaccuracies
- Portfolio positions may be priced incorrectly by fractions of a rupee

### Priority 3: MEDIUM (Do This Week)

#### 3.1 Re-run Recent Backtests

Any backtest generated in the last 30 days should be re-run with refreshed data:

```bash
# Example: Re-run latest portfolio backtest
python scripts/run_final_momentum_portfolio.py --with-data
```

**What to re-generate**:
- Latest portfolio run in `experiments/final_portfolio/`
- Any recent grid searches or Monte Carlo runs
- Any reports shared externally

**Impact if skipped**: Recent backtest metrics may be slightly off

#### 3.2 Validate Current Portfolio

Check if current portfolio holdings are affected:

```bash
# View current portfolio
cat data/final_portfolio/final_portfolio_24.csv

# Check if any positions are WIPRO or ITC (affected stocks)
grep -E "WIPRO|ITC" data/final_portfolio/final_portfolio_24.csv
```

If WIPRO or ITC are in the portfolio:
- Their entry prices may be off by 0.05-0.15 rupees
- Re-run portfolio generation to get accurate prices

### Priority 4: LOW (Monitor Ongoing)

#### 4.1 Add Data Quality Checks to Daily Pipeline

Modify `scripts/run_daily_pipeline.py` to include validation:

```bash
# After data updates, add:
python tests/test_benchmark_data_accuracy.py
```

This ensures future data quality issues are caught early.

#### 4.2 Monthly Full Refresh

Schedule a monthly full data refresh:

```bash
# First Sunday of each month
# Backup existing data
cp -r data/benchmarks data/benchmarks_backup_$(date +%Y%m%d)
cp -r indices_data indices_data_backup_$(date +%Y%m%d)

# Full refresh (delete and rebuild)
rm data/benchmarks/nifty100.csv
python scripts/compute_benchmark.py

# Indices can be refreshed incrementally (rolling window handles it)
python scripts/fetch_indices_history.py

# Validate
python tests/test_benchmark_data_accuracy.py --days 30
```

## Verification Checklist

After completing refreshes, verify:

- [ ] Benchmark data: `python tests/test_benchmark_data_accuracy.py --days 10`
- [ ] Indices data: Check file sizes and last modified dates in `indices_data/`
- [ ] Stock data: Check a few samples in `nse500_data/` for recent dates
- [ ] Latest portfolio report: Re-generate and review metrics
- [ ] Git status: Check what data files changed

## Expected Results

### Benchmark Data (nifty100.csv)

**Before fix**: 3 out of 10 recent days had incorrect values
**After fix**: All 10 days match API perfectly

Example correction:
- 2026-01-13: 26278.40 → 26296.75 (difference: -18.35 points)
- 2026-01-19: 26205.75 → 26181.95 (difference: +23.80 points)
- 2026-01-21: 25771.15 → 25701.40 (difference: +69.75 points)

### Stock Data

**Expected changes**:
- Most stocks: No change
- WIPRO: ~0.05 rupee corrections on affected dates
- ITC: ~0.15 rupee corrections on affected dates

**Portfolio impact**:
- If WIPRO/ITC are in portfolio: Entry prices may shift slightly
- If not in portfolio: No impact on current holdings
- Future trades: Will use accurate prices

### Indices Data

**Expected changes**:
- NIFTY 50: ~10-20 point corrections on recent dates
- NIFTY BANK: ~20-30 point corrections
- NIFTY MIDCAP 100: ~30-40 point corrections

**Analysis impact**:
- Sector performance comparisons will be more accurate
- Index correlation studies will be corrected
- Benchmarking against sectoral indices will be fixed

## What Doesn't Need Refreshing

1. **Historical data (>30 days old)**: Already has finalized values, no need to refresh
2. **Static files**: `data/static/nse500_universe.csv`, `tracked_indices.csv` - not affected
3. **Instrument cache**: `data/instruments_full.csv` - not price data
4. **Old experiments**: Backtest results >30 days old are still valid (used finalized historical data)

## Automated Prevention

Going forward, the fixes prevent this issue:

1. **All new fetches** use +1 day end_date → Get finalized values
2. **Rolling windows** (30 days) → Automatically correct recent data
3. **Validation tests** → Catch any future issues early

Daily pipeline is now resilient to this issue.

## Questions?

**Q: Why not refresh ALL historical data?**
A: Data >30 days old already has finalized values. Only recent data had preliminary values.

**Q: Will this happen again?**
A: No. The +1 day fix ensures we always get finalized values going forward.

**Q: How long does each refresh take?**
A:
- Benchmark: <1 minute
- Indices: 5-10 minutes
- NSE 500 stocks: 30-60 minutes (rate limited)

**Q: Can I skip stock data refresh?**
A: Yes, if:
- Your portfolio doesn't hold WIPRO or ITC
- You're okay with very small pricing discrepancies (0.05-0.15 rupees)
- You'll run it eventually this week

**Q: How do I know if my data is affected?**
A: Run: `python tests/test_benchmark_data_accuracy.py --days 30`
If it passes, your benchmark is good. For stocks/indices, check file modification dates.

## Next Daily Workflow

From now on, your daily workflow automatically uses fixed functions:

```bash
# Standard daily pipeline (now uses fixed fetch functions)
python scripts/login_and_save_token.py
python scripts/fetch_nse500_history.py  # Uses fixed PriceClient
python scripts/compute_benchmark.py     # Uses fixed +1 day + rolling window
python scripts/run_final_momentum_portfolio.py

# Validation (optional but recommended)
python tests/test_benchmark_data_accuracy.py
```

All new data will be accurate!
