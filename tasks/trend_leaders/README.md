# Trend Leaders 20 — Strategy Implementation

## Overview

A standalone trend-following portfolio strategy for Indian equities, designed as a separate subscriber product alongside the existing cross-sectional momentum strategy.

**Strategy philosophy:** Select stocks in the cleanest, most durable uptrends — not the highest returns. Auto-raise cash when fewer stocks qualify. Calmer and more defensive than momentum.

**Branch:** `trend-leaders-20`

**Specification:** `data/trend_leaders_20_backtest_handoff.md`

---

## Strategy Summary

| Parameter | Value |
|-----------|-------|
| Universe | NSE 500 |
| Target holdings | 20 |
| Entry frequency | Monthly (1st trading day of month) |
| Exit frequency | Weekly (last trading day of week) |
| Exit rule | Close < 200 DMA |
| Exit buffer | 20 (keep stock unless rank drops below 40) |
| Position sizing | Equal weight 5% (7.5% cap when <14 stocks) |
| Cash | Remainder when <20 stocks qualify, earns 0% |
| Slippage | 20 bps (OHLC/4 pricing, matching momentum engine) |
| Benchmark | Nifty 100 TRI |

**Trend Quality Score (TQS) — raw weighted average (NOT percentile-ranked):**
- 30% Moving Average Structure (Close > 50 > 100 > 200 DMA stacking)
- 30% Trend Persistence (% of 63 days Close > 100 DMA)
- 20% Distance from 200 DMA (penalized outside 5-35% ideal zone)
- 20% Drawdown Control (proximity to 6-month rolling high)

---

## V1 Backtest Results (2021-02 to 2026-04)

| Metric | Base | Market Filter | Monthly Only | Persistence | Momentum (ref) |
|--------|------|---------------|--------------|-------------|----------------|
| CAGR | 20.8% | 17.9% | 20.0% | 23.4% | 59.4% |
| Max DD | -18.9% | -17.8% | -20.8% | -29.6% | -30.0% |
| Sharpe | 1.25 | 1.20 | 1.18 | 1.16 | 1.92 |
| Sortino | 1.52 | 1.44 | 1.42 | 1.37 | - |
| Calmar | 1.10 | 1.01 | 0.97 | 0.79 | - |
| Turnover | 530% | 493% | 530% | 520% | 123% |
| Avg Hold | 63d | 64d | 64d | 61d | 43d |
| Avg Cash | 2.1% | 11.8% | 1.2% | 2.3% | 0% |

**Correlation with momentum:** 0.785 daily, 0.746 monthly

**Status:** V1 complete. CAGR needs improvement — 20.8% is not compelling enough for an active subscriber product alongside momentum at 59.4%.

---

## Implementation Phases

| Phase | Description | Task File | Status |
|-------|-------------|-----------|--------|
| 1 | Signal generation (eligibility + TQS ranking) | [phase1_signals.md](phase1_signals.md) | **Done** |
| 2 | Backtest engine (dual-frequency rebalance loop) | [phase2_backtest.md](phase2_backtest.md) | **Done** |
| 3 | Run all 4 backtest variants and validate | [phase3_variants.md](phase3_variants.md) | **Done** |
| 4 | Report generation and momentum comparison | [phase4_reports.md](phase4_reports.md) | **Done** |
| 5 | Orchestrator script | [phase5_orchestrator.md](phase5_orchestrator.md) | **Done** |

**Design decisions and architectural notes:** [DESIGN.md](DESIGN.md)

---

## Output Directory Structure

```
data/trend_leaders/
  signals/
    trend_leaders_signals.csv             # Top-40 ranked per month (for exit buffer)
    trend_scores_by_rebalance.csv         # Full audit: all 500 stocks, all scores
    persistence_only_signals.csv          # Variant 4 signals
  backtests/
    base/                                 # Variant 1: monthly entry + weekly exit
    market_filter/                        # Variant 2: + Nifty 500 < 200 DMA caps at 50%
    monthly_only/                         # Variant 3: no weekly exit checks
    persistence_only/                     # Variant 4: simpler persistence-only ranking
  reports/
    comparison_summary.md                 # Full results comparison
```

Each backtest variant directory contains:
```
tl20_equity.csv       — daily portfolio value, cash, drawdown, exposure
tl20_trades.csv       — all trades with reason (entry/monthly_exit/weekly_exit)
tl20_holdings.csv     — position snapshot per monthly rebalance
tl20_turnover.csv     — turnover per rebalance period
tl20_metrics.csv      — summary performance metrics
```

---

## New Scripts

| Script | Purpose |
|--------|---------|
| `scripts/build_trend_leaders_signals.py` | Signal generation: eligibility filter + TQS ranking |
| `scripts/backtest_trend_leaders.py` | Backtest engine with dual-frequency rebalance + exit hysteresis |
| `scripts/run_trend_leaders_portfolio.py` | Orchestrator: signals + 4 variants + summary in ~5 seconds |

---

## Existing Code Reused

| Source | What we reuse |
|--------|---------------|
| `scripts/backtest_momentum.py` | `load_price_panels()`, `load_benchmark()`, `map_signal_to_trade()` |
| `ta_indicators.py` | `sma()` for all moving average computations |
| `scripts/build_momentum_signals_flexible.py` | `load_price_panel()` pattern for loading close prices |

---

## Key Differentiation from Momentum Strategy

| Dimension | Momentum | Trend Leaders 20 |
|-----------|----------|-------------------|
| Signal type | Cross-sectional return momentum | Time-series trend structure |
| Entry frequency | Weekly | Monthly |
| Exit trigger | Rank drops out of top-N | Close < 200 DMA |
| Cash allocation | Always fully invested | Holds cash when <20 qualify |
| Actual turnover | 123% annualized | 530% (needs reduction) |
| Max DD | -30.0% | -18.9% (11% better) |
| Correlation | — | 0.785 daily |

---

## Known Issues / Next Steps

1. **CAGR too low (20.8%)** — not compelling enough alongside momentum's 59.4%. Needs strategy improvements.
2. **Turnover too high (530%)** — for a "calmer" strategy, should be closer to 200%. Possible fixes: min-hold-days, wider buffer, smoothed indicators.
3. **Rankings volatile in bull markets** — many stocks cluster at near-identical TQS scores (~0.98-0.99), causing excessive rank shuffling near the top-20 boundary.

---

*Created: May 2026*
