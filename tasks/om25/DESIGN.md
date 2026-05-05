# OM25 — Design & Decisions Log

## Strategy Identity

**Core thesis:** Stocks that participate more in market rallies and less in market selloffs have a structural edge — they compound faster with less pain. This is a different lens from momentum (which just buys the highest returners) and trend-following (which buys stocks in established uptrends).

**What makes it different:**
- Momentum asks: "What went up the most?"
- TL25 asks: "What has the cleanest trend structure?"
- OM25 asks: "What goes up more on good days and falls less on bad days?"

A stock can have high momentum but terrible capture ratio (it went up 100% but crashed 30% on every market dip). A stock can have mediocre momentum but excellent capture ratio (it only went up 40% but participated in every rally and dodged every selloff). OM25 selects the latter.

---

## Evolution of the Signal

### V1: Pure Omega Ratio (Rejected)
- **Signal:** Sum of positive returns / sum of negative returns (threshold = 0)
- **Result:** 35.4% CAGR, 1.59 Sharpe
- **Problem:** 0.92 correlation with momentum. Omega Ratio is essentially momentum restated in distributional terms — if a stock went up a lot, it has more positive daily returns than negative ones. Not differentiated.

### V2: Upside/Downside Capture Ratio (Current)
- **Signal:** (Avg stock return on market-up days / avg market return on up days) / (Avg stock return on market-down days / avg market return on down days)
- **Result:** 32.9% CAGR, 2.20 Sharpe, 0.789 correlation
- **Why it works:** This measures a stock's SENSITIVITY to market direction, not its absolute return. A stock with capture ratio 2.0 goes up 2x the market on good days but only falls 1x on bad days. This is genuinely different from "what went up the most."

### Why capture ratio is more differentiated than omega:
- Omega is absolute (measures the stock's own return distribution)
- Capture ratio is relative to the market (measures asymmetric beta)
- Two stocks can have identical omega but very different capture ratios if one rallies independently while the other amplifies market moves

---

## Current Locked-In Configuration

```
Signal:     Upside/Downside Capture Ratio, 252-day lookback
Entry:      Monthly (1st trading day), top 25, incremental (no rebalance of continuing)
Exit:       Bi-weekly check: Close < 200 DMA OR 4x ATR(20) trailing stop from peak
Buffer:     Keep stock unless rank drops below 40 (exit buffer 15)
Sizing:     Equal weight (1/N), 7.5% cap
Slippage:   20 bps (OHLC/4 on next trading day)
Eligibility: 220+ valid return observations, positive 252-day total return
```

**Results:** 32.9% CAGR, -19.6% max DD, 2.20 Sharpe, 1.68 Calmar, 0.789 corr with momentum

---

## Trading Mechanics Decisions

### Why monthly entry (not bi-weekly or weekly)
- Capture ratio uses a 252-day lookback — the signal changes slowly
- Bi-weekly entry was tested: 36.1% CAGR with weekly exits but correlation jumped to 0.81
- Monthly entry keeps the strategy calmer and more distinct
- The trailing stop handles risk management between entries

### Why bi-weekly exit checks (not weekly)
- Weekly 4x ATR stop was too tight: 30.1% CAGR (clipped winners on normal noise)
- Bi-weekly gives positions 2 weeks to breathe before next check
- Reduces ATR stop triggers from 567 to 460 (-19%), improving CAGR by +2.8%
- The stocks in this portfolio are "quality" names that tend to recover from short dips

### Why 4x ATR (not 3x, 5x, or N-day low)
- 3x ATR: too tight (25.9% CAGR, stops on normal vol)
- 4x ATR: sweet spot (32.9% CAGR, 2.20 Sharpe, -19.6% DD)
- 5x ATR: too loose (worse Sharpe and DD than 4x)
- N-day low (20/30/40): identical to 200 DMA only — never triggers before DMA does
- The 4x multiplier adapts to each stock's volatility without needing a fixed floor

### Why incremental sizing (not full rebalance)
- Full rebalance (resize all positions to 4% monthly) generated excessive turnover
- Winners that grow to 6-7% of portfolio should be left alone — that's the strategy working
- Incremental: only buy new entrants with freed cash, let continuing positions drift

### Why exit buffer 15 (not 10 or 20)
- Buffer 15 means stocks stay unless rank drops below 40
- Prevents month-to-month rank noise from causing unnecessary selling
- 10 was too tight (more churn), 20 was tested but similar results for this strategy

---

## Exit Analysis (from ATR weekly test)

| Exit Reason | % of Exits | Avg P&L | Win Rate | Character |
|-------------|-----------|---------|----------|-----------|
| ATR trailing stop | 70% | +4.3% | 42% | Protective but clips some winners |
| Close < 200 DMA | 15% | -4.3% | 19% | Crash protector (correct behavior) |
| Rank drop | 15% | +17.6% | 84% | Healthy rotation of mature winners |

The ATR stop fires most often because capture-ratio stocks are "quality beta" — they participate in market moves, which means they also participate in corrections (just less than the market). The stop catches those that overcorrect.

---

## Differentiation from Other Strategies

| Dimension | Momentum | TL25 | OM25 |
|-----------|----------|------|------|
| What it measures | Absolute price return | Trend structure quality | Market sensitivity asymmetry |
| Corr with OM25 | 0.789 | ~0.85 | — |
| Holdings overlap | ~40% | ~40% | — |
| DD behavior | -35% (holds through crashes) | -21% (trailing stop on extended) | -19.6% (4x ATR adaptive) |
| CAGR (recent) | Deteriorating since 2022 | 40%+ consistent | 32.9% (needs improvement) |
| Best in | Strong directional bull markets | Any trending market | Asymmetric/quality-driven markets |

---

## CAGR Improvement Plan

**Goal:** Push from 32.9% to 40%+ without importing momentum/trend signals.

### Ideas that stay within the "asymmetric sensitivity" thesis:

**1. Upside capture only (drop denominator)**
- Instead of upside/downside ratio, just rank by upside capture alone
- Picks the most aggressive market-rally participators
- Trailing stop handles downside protection independently
- Hypothesis: the downside penalty may be excluding some great stocks that just happen to be volatile

**2. Dual-lookback: 252d eligibility, 63d ranking**
- Use 252d capture ratio > 1.0 as eligibility filter (structural quality)
- Rank by 63d capture ratio for selection (who is capturing upside NOW)
- Hypothesis: capture ratio improves before price does — stocks whose capture is rising are about to rally

**3. Larger portfolio (top 30)**
- More names = more chances to catch a big winner
- Capture ratio may be a weaker per-stock signal but stronger in aggregate
- Lower concentration risk

**4. Remove positive return filter**
- Allow stocks with negative 252d return but high capture ratio
- These could be quality names that sold off but still go up more than the market on up days
- Hypothesis: beaten-down high-capture stocks are contrarian value picks

**5. Score-weighted sizing**
- Instead of equal weight, allocate proportional to capture ratio score
- Top 5 stocks (highest capture) get 5-6% each, bottom 5 get 2-3%
- Hypothesis: the signal has predictive power — higher score = higher expected return

### Test order:
1. Upside capture only (simplest change, biggest potential impact)
2. Dual-lookback (252d filter + 63d rank)
3. Score-weighted sizing
4. Larger portfolio (top 30)
5. Remove positive return filter

---

## Robustness Concerns

### What could go wrong:
- **Capture ratio is backward-looking** — a stock's market sensitivity can change (management change, sector rotation, liquidity shift)
- **Market regime dependence** — in a prolonged bear market, "high upside capture" stocks have fewer up-days to capture
- **Survivorship bias** — we're using current NSE 500 constituents for the full history
- **252-day lookback is long** — slow to react to regime changes

### What gives confidence:
- 0.789 correlation (genuinely different from momentum)
- The signal is structural (beta asymmetry) not just return-based
- 2.20 Sharpe suggests the signal has real predictive power
- -19.6% max DD is well-controlled

---

## Files

| File | Purpose |
|------|---------|
| `scripts/build_om25_signals.py` | Signal computation (omega + capture ratio) |
| `scripts/backtest_om25.py` | Backtest engine (monthly rebalance, equal weight) |
| `tasks/om25/README.md` | Summary and results |
| `tasks/om25/DESIGN.md` | This file — decisions and improvement plan |

---

*Last updated: May 2026*
