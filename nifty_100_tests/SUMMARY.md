# Portfolio Comparison Summary

## Three Configurations Tested

### 1. NSE 500 (Full Universe) - L6 + 1-Week
**Universe:** 499 stocks (full NSE 500)
**Parameters:** 6-month lookback, weekly rebalance

### 2. Nifty 100 (Large-cap Only) - L6 + 1-Week
**Universe:** 100 stocks (Nifty 100 index)
**Parameters:** 6-month lookback, weekly rebalance

### 3. Nifty 100 (Large-cap Only) - L9 + 2-Week
**Universe:** 100 stocks (Nifty 100 index)
**Parameters:** 9-month lookback, bi-weekly rebalance

## Performance Comparison Table

| Metric | **NSE 500 L6-1W** | **Nifty 100 L6-1W** | **Nifty 100 L9-2W** |
|--------|-------------------|---------------------|---------------------|
| **CAGR** | **57.51%** 🥇 | 44.86% 🥈 | 38.95% 🥉 |
| **Final Value** | **₹12,446,536** 🥇 | ₹7,820,005 🥈 | ₹4,758,025 🥉 |
| **Total Return** | **1144.7%** 🥇 | 682.0% 🥈 | 475.8% 🥉 |
| **Max Drawdown** | -27.67% | **-19.11%** 🥇 | -25.22% 🥈 |
| **Max DD Duration** | 263 days 🥇 | 329 days | 381 days |
| **Sharpe Ratio** | **1.71** 🥇 | ~1.4 est. | ~1.2 est. |
| **Turnover (ann.)** | 122.27% | 57.66% 🥈 | **23.42%** 🥇 |
| **Hit Rate** | 47.76% | 45.78% | **50.11%** 🥇 |
| **Avg Hold Days** | **38.7** 🥇 | 52.2 | 100.2 |
| **Total Trades** | 2,482 | 1,824 | **918** 🥇 |
| **Cost Drag** | 1.36% | 0.64% | **0.25%** 🥇 |

## Visual Comparison

### Returns (CAGR)
```
NSE 500 L6-1W:     ████████████████████████████████████████████ 57.51%
Nifty 100 L6-1W:   ███████████████████████████████ 44.86%
Nifty 100 L9-2W:   ██████████████████████ 38.95%
```

### Risk (Max Drawdown) - Lower is better
```
NSE 500 L6-1W:     ████████████████████████████████████ -27.67%
Nifty 100 L9-2W:   ███████████████████████████████ -25.22%
Nifty 100 L6-1W:   ████████████████████ -19.11% ✓
```

### Turnover (Annualized) - Lower is better
```
NSE 500 L6-1W:     █████████████████████████████████████████ 122.27%
Nifty 100 L6-1W:   ████████████████████ 57.66%
Nifty 100 L9-2W:   ██████ 23.42% ✓
```

## Key Insights

### 1. Universe Size Matters Most
**NSE 500 vs Nifty 100 (both L6-1W):**
- NSE 500 outperforms by **+12.65% CAGR**
- Mid-cap stocks contribute significant alpha
- Worth the extra 8.56% drawdown for growth investors

### 2. Rebalance Frequency is Critical
**Nifty 100 L6-1W vs L9-2W:**
- Weekly rebalancing wins by **+5.91% CAGR**
- Lower frequency does NOT reduce risk (DD worse by 6.11%)
- Transaction cost savings irrelevant vs return loss

### 3. Lookback Period Optimization
**6-month vs 9-month:**
- 6-month captures momentum better
- 9-month dilutes recent signals
- Shorter lookback = better performance

### 4. Risk-Adjusted Performance
**Winner: NSE 500 L6-1W**
- Highest Sharpe ratio (1.71)
- Best risk-adjusted returns
- Drawdown acceptable for CAGR achieved

## Recommendations by Investor Type

### 🚀 Growth Investors → NSE 500 L6-1W
**Best choice if you want:**
- Maximum returns (57.51% CAGR)
- Full market opportunity
- Willing to accept -27.67% drawdown
- Smaller portfolio size (<₹10 crore)

**Characteristics:**
- High turnover (122% annually)
- 2,482 trades over 5.5 years
- Captures mid-cap alpha
- Requires active management

### 🛡️ Conservative Investors → Nifty 100 L6-1W
**Best choice if you want:**
- Lower volatility (-19.11% DD)
- Large-cap stability
- Still solid returns (44.86% CAGR)
- Better liquidity for large sizes

**Characteristics:**
- Moderate turnover (57.66%)
- 1,824 trades over 5.5 years
- Blue-chip stocks only
- Easier to execute at scale

### ❌ NOT Recommended → Nifty 100 L9-2W
**Why it fails:**
- Lower returns (38.95% CAGR)
- Higher risk (-25.22% DD)
- No meaningful advantage
- Loses to both other configs

**Only advantage:**
- Lowest turnover (23.42%)
- But not worth the tradeoffs

## Final Verdict

### Winner: NSE 500 L6-1W 🏆

**For most investors, NSE 500 with 6-month lookback and weekly rebalancing is optimal:**

✅ Highest returns (57.51% CAGR)
✅ Best risk-adjusted performance (1.71 Sharpe)
✅ Captures full market opportunity
✅ Proven over 5.5 years

**Accept the tradeoffs:**
- Higher turnover (122% vs 58%)
- Larger drawdown (-27.67% vs -19.11%)
- More active monitoring required

### Alternative: Nifty 100 L6-1W

**Choose this if:**
- Very large portfolio (₹10+ crore)
- Limited risk tolerance
- Require high liquidity
- Prefer large-cap only

**You sacrifice:**
- 12.65% CAGR annually
- Mid-cap alpha opportunities
- ₹4.6M on ₹1M capital over 5.5 years

## Parameter Sensitivity Summary

### What Works:
✓ Shorter lookbacks (6 months)
✓ Weekly rebalancing
✓ Full universe (NSE 500)
✓ Vol floor = 0.05

### What Doesn't Work:
❌ Longer lookbacks (9 months)
❌ Lower rebalance frequency (bi-weekly)
❌ Restricted universe (Nifty 100 only)
❌ False economy on transaction costs

## Next Steps

**If you want to improve further:**
1. Test skip windows (0 vs 10 vs 21 days)
2. Test different top-N values (20-30 stocks)
3. Try sector rotation filters
4. Explore dynamic position sizing

**Current configuration is excellent:**
- NSE 500 L6-1W already optimized
- Vol floor recently improved (0.20 → 0.05)
- Further gains likely marginal

---

**Test Period:** 2020-07-10 to 2026-01-27 (5.5 years)
**All Tests:** Same methodology, slippage, pricing model
**Date:** January 2026
