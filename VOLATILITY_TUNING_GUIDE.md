# Volatility Tuning Guide

This guide explains the momentum model's volatility adjustments in plain terms and shows you what each knob does.

## The Core Problem

When ranking stocks by momentum (price return), we face a dilemma:
- **High volatility stocks** can have big returns but are risky
- **Low volatility stocks** have smaller returns but are steadier
- We want to **reward returns while penalizing excessive volatility**

## The Formula (Simplified)

```
Score = Return / (Volatility ^ Power)
```

Then we z-score across all stocks to rank them.

## The Knobs You Can Turn

### 1. Skip Window (`--skip-days`)
**Default: 21 days (≈1 month)**

**What it does:**
- Creates a "gap" between TODAY and when we measure momentum
- Measures momentum from `(today - skip)` back to `(today - skip - lookback)`

**Why it matters:**
- Short-term reversals: Stocks that went up a lot last week often pull back
- The skip window avoids buying stocks that just had a big pop

**Impact:**
```
skip = 0:   Uses very recent prices → catches short-term momentum but higher reversal risk
skip = 21:  Skips last month → balances momentum and mean reversion
skip = 63:  Skips 3 months → very conservative, might miss active trends
```

**When to increase:** If you see high turnover and trades that reverse quickly
**When to decrease:** If you're missing strong trending stocks

---

### 2. Volatility Floor (`--vol-floor`)
**Default: 0.0005 (0.05% daily)**

**What it does:**
- Sets a minimum volatility value so we never divide by near-zero
- Prevents scores from exploding for very stable stocks

**Why it matters:**
- Without a floor, a stock with 0.1% vol and 5% return gets a score of 50
- With floor of 0.05%, that same stock's score is capped lower
- Prevents "boring" low-vol stocks from dominating the rankings

**Impact:**
```
vol_floor = 0.0001:  Very permissive → low-vol stocks can rank very high
vol_floor = 0.0005:  Moderate → default balance
vol_floor = 0.002:   Strict → only normal/high vol stocks can top-rank
```

**When to increase:** If you're getting too many low-volatility "sleeper" stocks
**When to decrease:** If you want to allow stable growers to rank higher

---

### 3. Volatility Power (`--vol-power`)
**Default: 1.0 (linear penalty)**

**What it does:**
- Controls HOW MUCH we penalize volatility
- Power < 1: Gentler penalty (square root dampens large vols)
- Power = 1: Linear penalty (default)
- Power > 1: Harsh penalty (squares amplify large vols)

**Why it matters:**
- This is the MAIN DIAL for risk preference
- Lower power = "I'm okay with volatility, just show me returns"
- Higher power = "I really hate volatility, strongly prefer stable stocks"

**Impact:**
Example: Stock with 10% return and 2% daily volatility:

```
vol_power = 0.5:   Score = 10 / (2^0.5)  = 10 / 1.41  = 7.07   (gentle penalty)
vol_power = 1.0:   Score = 10 / (2^1.0)  = 10 / 2     = 5.00   (linear penalty)
vol_power = 1.5:   Score = 10 / (2^1.5)  = 10 / 2.83  = 3.54   (harsh penalty)
vol_power = 2.0:   Score = 10 / (2^2.0)  = 10 / 4     = 2.50   (very harsh)
```

**When to increase:** If portfolio feels too volatile, lots of whipsaw
**When to decrease:** If portfolio feels too conservative, missing big winners

---

### 4. Lookback Period (`--lookbacks`)
**Default: 6 months (L6)**

**What it does:**
- How far back we measure the momentum
- Options: 3, 6, or 12 months (can combine multiple)

**Why it matters:**
- Short lookback (3M): Captures recent trends, more reactive
- Medium lookback (6M): Balance of trend and stability
- Long lookback (12M): Slower, captures mega-trends

**Impact:**
```
L3 (3 months):   Fast signal, high turnover, catches short trends
L6 (6 months):   Sweet spot for Indian markets (current default)
L12 (12 months): Slow signal, low turnover, only mega winners
Combined:        Averages all enabled horizons
```

**When to change:** This is more strategic - L6 is well-tested for this use case

---

### 5. Top-N (`--top-n`)
**Default: 25 stocks**

**What it does:**
- How many stocks we hold in the portfolio
- More stocks = more diversification, less concentration

**Impact:**
```
top_n = 10:   Concentrated, higher variance, bigger winners/losers
top_n = 25:   Balanced diversification (default)
top_n = 50:   Highly diversified, smoother but diluted alpha
```

**Trade-off:** More stocks = lower volatility but also lower excess returns

---

## Backtest Scenario Knobs

These control the **rebalancing behavior**, not the signal generation:

### 6. Exit Buffer (`--exit-buffer`)
**Default: 0**

**What it does:**
- Adds "hysteresis" - stocks must fall to rank (top_n + buffer) before selling
- Example: top_n=25, buffer=5 → sell only if stock drops below rank 30

**Impact:**
```
buffer = 0:   Strict rebalance, high turnover
buffer = 5:   Hold longer, reduces churn by ~20-40%
buffer = 10:  Very sticky holdings, lowest turnover
```

**When to increase:** High transaction costs, want to reduce trading
**When to decrease:** Want to be more responsive to rankings

---

### 7. PnL-Hold Threshold (`--pnl-hold-threshold`)
**Default: None (disabled)**

**What it does:**
- Defers selling a position if it's profitable above this threshold
- Example: 0.05 = hold if position has unrealized gain > 5%

**Impact:**
```
threshold = None:    Sell whenever ranked out (strict)
threshold = 0.05:    Hold winners longer, "let winners run"
threshold = 0.10:    Very sticky, only sell big losers
```

**When to use:** If you want to implement "let profits run" behavior

---

### 8. Cooldown Weeks (`--cooldown-weeks`)
**Scenario: cooldown only**

**What it does:**
- After a drawdown, scales back into the market gradually
- staged_step controls how fast (0.25 = 25% per week)

**Impact:**
- Reduces exposure after losses
- Takes 1/staged_step weeks to get back to full exposure

---

### 9. Vol-Trigger Parameters (`--target-vol`, `--vol-lookback`)
**Scenario: vol_trigger only**

**What it does:**
- Dynamically adjusts exposure based on recent market volatility
- If market vol > target_vol → reduce exposure
- If market vol < target_vol → increase exposure

**Impact:**
- Automatically de-risks in choppy markets
- Re-risks in calm markets

---

## Quick Start: What to Tune First

### If your backtest has...

**High turnover (>200% annually):**
1. Increase `--exit-buffer` to 5 or 10
2. Or add `--pnl-hold-threshold 0.05`

**Too volatile (big drawdowns):**
1. Increase `--vol-power` from 1.0 to 1.5
2. Or increase `--vol-floor` from 0.0005 to 0.001

**Too conservative (missing winners):**
1. Decrease `--vol-power` from 1.0 to 0.5
2. Or decrease `--vol-floor` from 0.0005 to 0.0002

**Short-term reversals:**
1. Increase `--skip-days` from 21 to 30 or 40

**Missing recent trends:**
1. Decrease `--skip-days` from 21 to 10 or 5

---

## Testing Strategy

**Step 1: Baseline**
```bash
python scripts/build_momentum_signals.py --skip-days 21 --vol-floor 0.0005 --vol-power 1.0
python scripts/backtest_momentum.py --scenario baseline
```

**Step 2: Reduce turnover**
```bash
# Same signals, but add exit buffer
python scripts/backtest_momentum.py --scenario baseline --exit-buffer 5
```

**Step 3: Adjust risk preference**
```bash
# Try different vol-power values
python scripts/build_momentum_signals.py --vol-power 1.5  # More risk-averse
python scripts/build_momentum_signals.py --vol-power 0.5  # More aggressive
```

**Step 4: Compare**
```bash
python scripts/report_backtests.py --runs data/backtests/* --output comparison.html
```

---

## Mental Model

Think of it like a car:

- **vol_power**: How sensitive your brake pedal is (high = very sensitive)
- **vol_floor**: Minimum braking force (prevents coasting)
- **skip_days**: How far ahead you look (rearview vs immediate)
- **exit_buffer**: How slow you are to change lanes (hysteresis)
- **pnl_hold**: "Don't exit the highway if you're making good time"

---

## Common Patterns

| Goal | Signal Knobs | Backtest Knobs |
|------|-------------|----------------|
| Lower turnover | No change | exit_buffer=5-10 |
| Lower volatility | vol_power=1.5, vol_floor=0.001 | scenario=vol_trigger |
| Higher returns (risky) | vol_power=0.5, skip_days=10 | exit_buffer=0 |
| Balanced | vol_power=1.0, skip_days=21 | exit_buffer=5, pnl_hold=0.05 |

The defaults are already pretty good. Start with exit_buffer and vol_power as your main levers.
