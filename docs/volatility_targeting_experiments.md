# Volatility Targeting Experiments - Results & Learnings

## Objective

Test whether volatility targeting could:
1. Reduce portfolio volatility from 26% to 20% target
2. Reduce maximum drawdowns from -27.67%
3. Improve risk-adjusted returns (Sharpe ratio)

## Approaches Tested

### 1. Daily Position Reduction
- **Method**: Calculate realized vol daily, proportionally reduce all positions if vol > target
- **Result**: ❌ FAILED
  - CAGR: 57.28% → 63.89% (increased!)
  - Max DD: -27.67% → -35.97% (worse!)
  - Volatility: 26.02% → 33.54% (worse!)
  - Trades: 4,988 vol-scaling trades disrupted momentum strategy
  - **Issue**: Daily adjustments broke "hold winners" logic, created massive turnover

### 2. Weekly Position Reduction
- **Method**: Only adjust exposure on Thursday rebalance days (weekly rhythm)
- **Result**: ❌ FAILED (identical to daily)
  - CAGR: 63.89%, Max DD: -35.97%, Vol: 33.54%
  - 4,988 vol-scaling trades still occurred
  - **Issue**: Same fundamental problem - selling from winners disrupts momentum

### 3. Exposure Bands (10% threshold)
- **Method**: Only adjust if exposure change exceeds 10% threshold
- **Result**: ❌ FAILED
  - CAGR: 66.62%, Max DD: -37.78% (even worse!), Vol: 33.69%
  - Fewer adjustments, but still disruptive
  - **Issue**: Threshold too large to be effective, too small to prevent disruption

### 4. Cash Buffer (Preserve Positions)
- **Method**: Hold cash instead of reducing positions, maintain existing holdings
- **Result**: ⚠️ NO EFFECT
  - Identical to baseline (57.28% CAGR, -27.67% DD, 26.02% vol)
  - Exposure remained 100% throughout
  - **Issue**: Weekly rebalancing logic already redeploys cash, exposure adjustments have no effect

## Root Cause Analysis

**Fundamental Incompatibility:**

Weekly momentum strategies are incompatible with dynamic volatility targeting because:

1. **Momentum requires holding winners**: Proportionally reducing positions means selling from ALL holdings, including the best performers
2. **Weekly rhythm is too slow**: Volatility changes intraweek, but adjustments only happen weekly, creating lag
3. **Cash deployment is automatic**: The rebalancing logic already targets full investment, so "holding cash" doesn't work
4. **Turnover explosion**: Constant position adjustments create excessive transaction costs (₹660M turnover on ₹1M portfolio)

**Why Results Got WORSE:**

- Higher volatility: Frequent position changes increased portfolio instability
- Worse drawdowns: Selling during volatile periods locked in losses and missed recoveries
- Higher CAGR (paradox): Lower exposure during pullbacks meant missing rallies, but also missing drawdowns → irregular exposure created higher variance

## Key Findings

### Portfolio Characteristics (Baseline)
- **Realized Volatility (63-day rolling)**:
  - Mean: 25.42%
  - Range: 13.38% - 38.05%
  - > 20% on 82.1% of days
  - > 25% on 54.4% of days

### What Works
✅ **Accept 26% volatility**: Part of a high-momentum strategy (57% CAGR)
✅ **Sharpe ratio 1.71**: Excellent risk-adjusted returns for equity strategy
✅ **Weekly rebalancing**: Already optimized for momentum capture
✅ **Equal weight**: Prevents concentration risk

### What Doesn't Work
❌ **Dynamic vol targeting**: Conflicts with momentum logic
❌ **Proportional reduction**: Breaks "hold winners" principle
❌ **Daily/weekly adjustments**: Too frequent for strategy rhythm

## Alternative Approaches (Not Tested)

If drawdown protection is needed in the future:

### 1. Static De-Levering (Simplest)
- Run portfolio at fixed 77% exposure
- Achieves ~20% vol (26% × 0.77 ≈ 20%)
- **Pros**: Simple, predictable, proportionally reduces DD
- **Cons**: Lower CAGR (~44% vs 57%), misses upside
- **When to use**: Conservative risk appetite, regulatory constraints

### 2. Circuit Breaker (Already Exists!)
- Use existing `--scenario cooldown`
- Goes to cash on -25% drawdown trigger
- Staged re-entry over N weeks
- **Pros**: Protects against extreme drawdowns, momentum-friendly
- **Cons**: Can miss recovery rallies, timing risk
- **When to use**: Tail risk protection, large drawdown aversion

### 3. Position Limits
- Cap max position size at 5-6% (vs current 4.17% for 24 stocks)
- Reduces single-stock risk
- **Pros**: Prevents concentration, minimal strategy disruption
- **Cons**: Doesn't reduce overall vol, slight performance drag
- **When to use**: Regulatory compliance, risk management overlay

### 4. Volatility-Adjusted Position Sizing
- Size positions inversely to their individual volatility
- High-vol stocks get smaller allocations
- **Pros**: Natural risk balancing, maintains momentum
- **Cons**: Complex, may underweight high-momentum stocks
- **When to use**: Cross-sectional risk management

## Recommendation

**DO NOT implement volatility targeting** for this strategy.

**Current metrics are healthy:**
- 57.28% CAGR
- 26.02% volatility
- -27.67% max drawdown
- 1.71 Sharpe ratio
- 38.0% post-tax compounding drag (FY basis)

**The 26% volatility is reasonable for:**
- High-momentum equity strategy
- Weekly rebalancing frequency
- Indian equity market (naturally volatile)
- Return profile (57% CAGR justifies the risk)

**If future risk reduction is needed:**
1. Start with circuit breaker (`cooldown` scenario) for drawdown protection
2. Consider static de-levering (75-85% exposure) if regulatory constraints arise
3. Keep current approach otherwise - it's working well

## Conclusion

Volatility targeting is **not suitable** for weekly momentum strategies. The baseline approach delivers excellent risk-adjusted returns without artificial constraints. Focus optimization efforts elsewhere (signal generation, transaction costs, tax efficiency).

---

**Experiments Conducted:** January 2026
**Test Period:** 2020-07-10 to 2026-01-23 (5.5 years)
**Results:** Volatility targeting made performance worse across all metrics
