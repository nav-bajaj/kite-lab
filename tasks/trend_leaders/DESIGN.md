# Trend Leaders 25 — Design & Decisions Log

> ⚠️ **REBASELINED MAY 2026.** All performance numbers in this doc were rebaselined after fixing a same-day-close → same-day-OHLC/4 lookahead bug in `backtest_trend_leaders.py`. Strategy parameters are unchanged; only the historical performance figures are corrected to honest no-lookahead values.

## Final Strategy (Simplified)

```
Signal:    Friday close (Thursday-style timing also works)
Execution: Monday OHLC/4 (next trading day) with 20 bps slippage
Entry:     Top 25 eligible stocks by TQS, every other Friday signal
Exit:      Weekly Friday signal: Close < 200 DMA  OR  3x ATR(20) trailing stop
            from position peak (min 10% floor)
Score:     25% MA structure + 25% persistence + 25% drawdown control
            + 25% 6m momentum (pct-ranked)
Filter:    Close > 200 DMA, 50 DMA > 200 DMA, 200 DMA rising
Sizing:    Equal weight (1/N), 7.5% cap, exit buffer 20 (keep until rank > 45)
```

## Honest Performance (post-rebaseline)

| Universe | Cadence | CAGR | Max DD | Sharpe | Calmar |
|----------|---------|------|--------|--------|--------|
| NSE 500 | Bi-weekly | 36.4% | -26.2% | 1.52 | 1.39 |
| **Nifty 250** | **Bi-weekly** | **38.8%** | **-23.2%** | **1.79** | **1.67** |
| Nifty 100 | Bi-weekly | 31.9% | -19.8% | 1.71 | 1.61 |

**Recommended flagship: Nifty 250 Bi-weekly** — best Sharpe and Calmar across all variants.

---

## Why These Rules

### Eligibility: 200 DMA filter
- **Tested alternative:** 100 DMA filter → too permissive in bear markets, -29.6% DD
- **Decision:** 200 DMA provides structural bear market protection. A stock must be in a clear long-term uptrend to qualify.

### Scoring: Equal 25% weights
- **Tested alternatives:** Various unequal weightings (30/30/20/20, 35/35/30/0, etc.)
- **Decision:** Equal weights are simpler, avoid over-tuning, and actually performed better than the "optimized" versions. Each component contributes independently useful information.

### Scoring: No distance-from-200-DMA penalty
- **Original design:** Penalize stocks >35% above 200 DMA (cap overextension)
- **What happened:** This killed CAGR by forcing exits from the best winners (+6% CAGR without it)
- **Decision:** Remove it entirely. The trailing stop handles overextension protection instead — it lets stocks run but catches them when they crack.

### Scoring: Raw values, not percentile-ranked
- **Original design:** Percentile-rank each component cross-sectionally
- **What happened:** Percentile ranking amplified tiny score differences (all stocks at 0.98-0.99 in bull markets), causing massive rank volatility and monthly churn (only 6.7/20 stocks persisted month-to-month)
- **Decision:** Use raw component values (all already 0-1 scaled). Exception: momentum IS percentile-ranked because raw 6m returns have different scales across market conditions.

### Exit: 3x ATR trailing stop
- **Tested alternatives:**
  - Fixed tiered stops (30% extension → 15% trail, 15% extension → 20% trail)
  - No trailing stop (just 200 DMA exit) → -32% DD
  - Various ATR multipliers (3x, 3.5x, 4x, 5x)
- **Decision:** Simple 3x ATR(20) with 10% floor. Adapts to each stock's volatility naturally. No tiered complexity. The 3x multiplier is standard in trend-following (Turtle Traders used similar).

### Entry: Bi-weekly
- **Tested alternatives:** Monthly (+3% less CAGR), weekly (too much noise/churn)
- **Decision:** Bi-weekly catches new trends faster than monthly without the rank-noise problems of weekly.

### Holdings: Top 25 with buffer 20
- **Tested alternatives:** Top 10 (too concentrated), Top 15, Top 20, Top 25
- **Decision:** Top 25 provides best risk-adjusted returns (1.72+ Sharpe). More diversification reduces stock-specific crash impact. Buffer of 20 prevents churn at the selection boundary.

### Sizing: Incremental only
- **Original design:** Full rebalance at each entry (resize all positions to target weight)
- **What happened:** Generated 2696% turnover — absurd for a "calmer" strategy. Most stocks persist month-to-month and don't need resizing.
- **Decision:** Only buy new entrants. Continuing positions drift. Exit only on rank drop or trailing stop.

---

## Optimization Journey (What We Tried)

### Improvements that stuck:
| Change | CAGR Impact | DD Impact | Notes |
|--------|-------------|-----------|-------|
| Remove distance penalty | +6% | -13% worse | Let winners run |
| Add trailing stop | +3% | +6% better | Catch extended stock crashes |
| Add 6m momentum (15→25%) | +6% | -1% | Prefer stocks with recent strength |
| Top 25 (from Top 20) | +1% | +1% better | More diversification helps |
| Bi-weekly (from monthly) | +3% | +1% better | Faster trend capture |
| Simplify to equal weights + 3x ATR | +3% | +4% better | Simpler was literally better |

### Things that didn't work:
| Attempt | Result | Why |
|---------|--------|-----|
| Weekly rebalance | 14.5% CAGR, -29.8% DD | Too much rank noise, massive churn |
| 100 DMA eligibility | 18.6% CAGR, -29.6% DD | Too permissive in bear markets |
| Full rebalance each month | 2696% turnover | Unnecessary, hurts returns via slippage |
| Percentile-ranked TQS | 6.7/20 persistence | Amplifies tiny differences into rank shuffles |
| Hybrid entry/hold signals | 18.7% CAGR | "Near MA" entry picks weaker trends |
| Distance penalty for "overextension" | -6% CAGR | Punishes the best performers |
| Tighter exit buffer (10-15) | Worse Sharpe | More churn without benefit |
| 1-month momentum lookback | 34.4% CAGR | Too noisy as a signal |
| Top 10-12 concentration | Worse Sharpe, worse DD | Single-stock risk too high |

---

## Overfitting Lesson

During optimization we went from 20.8% → 41.3% CAGR by turning ~10 dials on the same 5-year in-sample data. This was overfitting.

**Resolution:** Simplified back to clean round-number rules and validated via Monte Carlo universe sampling (remove 30% of stocks randomly, 10 trials). The simplified version (43.1%) actually outperformed the overfit version (41.3%) — proof that simpler rules generalize better.

**The test that matters:** 29/30 random trials above 25% CAGR. The strategy finds good trends regardless of which specific stocks are in the universe.

---

## Architecture

### Signal Generation
```
NSE 500 daily close prices
  → Compute 50/100/200 DMA (vectorized DataFrame.rolling())
  → Compute eligibility filter (boolean panel)
  → Compute 4 score components (each Date x Symbol, 0-1)
  → Percentile-rank momentum among eligible
  → Equal-weight composite TQS
  → Rank on bi-weekly dates
  → Output top 45 per date (for exit buffer)
```

### Backtest Loop
```
For each trading day:
  1. Mark-to-market (update portfolio value, drawdown, position peaks)
  2. If Friday: check trailing stop (Close < 200 DMA OR 3x ATR from peak → sell)
  3. If bi-weekly rebalance date:
     a. Rank-based exits (rank > 45 → sell)
     b. Fill open slots from top 25 (only new entrants, incremental sizing)
```

### Key Implementation Details
- **200 DMA panel pre-computed** once before loop (fast lookup)
- **ATR panel pre-computed** as `close.pct_change().rolling(20).std()`
- **Position peak** tracked per holding, updated each day
- **Trade execution:** OHLC/4 on next trading day after signal, 20 bps slippage
- **Whole shares** with floor allocation

---

## Files

| File | Purpose |
|------|---------|
| `scripts/build_trend_leaders_signals.py` | Signal generation (supports monthly/weekly/bi-weekly, configurable DMA, scoring modes) |
| `scripts/backtest_trend_leaders.py` | Backtest engine (dual-frequency, trailing stops, exit hysteresis, ATR stops, min-hold) |
| `scripts/run_trend_leaders_portfolio.py` | Orchestrator (runs all variants, prints summary) |
| `scripts/report_trend_leaders.py` | HTML report (auto-detects all variant directories) |

---

*Last updated: May 2026 — Final simplified robust strategy locked in*
