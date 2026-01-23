# Score Filtering Investigation - January 2026

## Summary

After extensive testing, **score-based filtering was found to reduce returns** and should NOT be used in production.

## Investigation Timeline

### Original Implementation (Jan 2026)
- Implemented score filtering with thresholds: min_entry_score=2.5, min_exit_score=1.5
- Initial grid search showed 60.2% CAGR (rank #1)
- Configuration was adopted for production

### Critical Bug Discovery (Jan 22, 2026)
Discovered that the backtest filtering code had a **date mismatch bug**:
- `score_map_by_date` and `rank_map_by_date` were keyed by signal dates (e.g., 2020-07-09)
- But lookups used trade dates (e.g., 2020-07-10)
- **Result**: Score filtering never actually worked - 90.6% of trades violated thresholds
- Bug caused incorrect exit timing, artificially inflating returns

### Bug Fix
Fixed in `backtest_momentum.py` (lines 191-209, 274-276, 291):
- Added `trade_to_signal_map` dictionary to map trade dates → signal dates
- Updated score and rank lookups to use correct signal dates
- All BUY trades now properly respect min_entry_score threshold

### Re-testing with Fixed Code

Tested three distinct approaches:

| Approach | Description | CAGR | Max DD | Trades |
|----------|-------------|------|--------|--------|
| **Pure Baseline** | No filtering, all top-24 stocks | **55.6%** | -27.1% | 2,342 |
| Backtest-Level Filtering | Filter after ranking (entry≥2.5) | 45.9% | -43.3% | 744 |
| Signal-Level Filtering | Filter before ranking (entry≥2.5) | 42.1% | -43.3% | 1,149 |

### Key Findings

1. **Old 60% result was inflated by the bug** (+18pp artificial boost)
2. **Pure baseline outperforms all filtered strategies** by 9-13pp
3. **Score filtering increases drawdowns** (-27% → -43%)
4. **Score filtering reduces hit rates** (48% → 40%)
5. **Lower thresholds perform better** (if filtering is used):
   - Entry=1.5: avg 46.5% CAGR
   - Entry=2.0: avg 40.6% CAGR
   - Entry=2.5: avg 43.6% CAGR
   - Entry=3.0: avg 35.7% CAGR

## Why Filtering Reduces Returns

1. **Reduced diversification**: Fewer positions → higher concentration risk
2. **Missed opportunities**: Stocks with low scores can still deliver returns
3. **False positives**: High momentum scores don't guarantee future performance
4. **Increased volatility**: Concentrated portfolios have deeper drawdowns

## Production Configuration

**Recommended Settings:**
```bash
python scripts/run_final_momentum_portfolio.py \
  --min-entry-score None \
  --min-exit-score None \
  --top-n 24 \
  --lookback-months 6 \
  --vol-floor 0.2
```

**Expected Performance:**
- CAGR: ~55.6%
- Max Drawdown: ~27%
- Trades: ~2,340 over backtest period

## Lessons Learned

1. **Always verify filtering is actually working** - The bug went undetected because results "looked good"
2. **Simpler is often better** - Pure momentum ranking outperforms complex filtering
3. **Diversification matters** - Concentrated strategies (fewer positions) have worse risk-adjusted returns
4. **Test infrastructure before parameters** - Fix bugs before optimizing

## Grid Search Results

Complete results saved in:
- `experiments/score_grid_FIXED_20260122190329/summary.csv`
- `experiments/score_grid_FIXED_20260122190329/comparison_report.html`

Old buggy results (for reference only):
- `experiments/score_grid_20260120154509/` - DO NOT USE (inflated by bug)
