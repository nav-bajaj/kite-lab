# Trend Leaders 25 — Final Strategy

## Overview

A standalone trend-following portfolio strategy for Indian equities. Designed to be simple, robust, and explainable in 3 sentences.

**Branch:** `trend-leaders-20`

---

## Strategy (3 sentences)

> Buy the top 25 stocks by trend quality score (equal-weight: MA stacking + persistence + drawdown control + 6-month momentum). Enter bi-weekly. Exit if Close < 200 DMA or 3x ATR trailing stop from peak.

---

## Configuration

| Parameter | Value |
|-----------|-------|
| Universe | NSE 500 / Nifty 250 / Nifty 100 |
| Target holdings | 25 |
| Entry frequency | Bi-weekly (every other Friday) |
| Exit checks | Weekly (every Friday) |
| Exit rule | Close < 200 DMA OR 3x 20-day ATR trailing stop from position peak (min 10%) |
| Rank exit | Drop below rank 45 (buffer of 20) |
| Position sizing | Equal weight (1/N), max 7.5% cap |
| Slippage | 20 bps (OHLC/4 pricing) |

**Trend Quality Score (equal 25% weights):**
1. MA Structure — binary: Close > 50 > 100 > 200 DMA stacking + slope
2. Trend Persistence — % of last 63 days Close > 100 DMA
3. Drawdown Control — Close / 126-day rolling high
4. 6-Month Momentum — percentile-ranked among eligible stocks

**Eligibility filter:**
- Close > 200 DMA
- 50 DMA > 200 DMA
- 200 DMA today > 200 DMA 20 days ago (slope rising)

---

## Performance (Full Universes)

| Universe | CAGR | Max DD | Sharpe | Sortino | Calmar |
|----------|------|--------|--------|---------|--------|
| NSE 500 | 43.1% | -21.1% | 1.92 | — | 2.04 |
| Nifty 250 | 40.1% | -20.4% | 1.94 | — | 1.97 |
| Nifty 100 | 33.4% | -16.5% | 1.84 | — | 2.02 |

**Period:** 2021-02 to 2026-04 (5.2 years)

---

## Robustness Test (Random Universe Subsets)

Removed 30% of stocks randomly, 10 trials per universe:

| Universe | Subset Size | Median CAGR | Min CAGR | Median Sharpe | Min Sharpe | >25% CAGR |
|----------|-------------|-------------|----------|---------------|------------|------------|
| NSE 500 | 350 / 500 | 42.0% | 35.5% | 1.91 | 1.64 | 10/10 |
| Nifty 250 | 175 / 251 | 39.0% | 33.8% | 1.95 | 1.74 | 10/10 |
| Nifty 100 | 70 / 101 | 32.3% | 23.8% | 1.88 | 1.48 | 9/10 |

**29/30 trials above 25% CAGR. 30/30 trials above 1.0 Sharpe.**

The strategy does not depend on specific stocks — it finds good trends regardless of which names are available.

---

## Comparison with Momentum Strategy

| Metric | TL25 (Nifty 250) | Momentum (NSE 500) |
|--------|-------------------|-------------------|
| CAGR (from Feb 2021) | 40.0% | 26.4% |
| CAGR (from Jan 2024) | 19.7% | 1.1% |
| Max DD | -20.4% | -35.3% |
| Sharpe | 1.94 | 1.19 |
| Daily correlation | 0.84 | — |

Momentum has higher ceiling in bull markets (2020-21: +102%) but has been essentially dead since Jan 2024 (1.1% CAGR). TL25 is more consistent across market regimes.

---

## Design Principles

1. **Simple rules** — the strategy can be described in 3 sentences. No tiered thresholds, no complex conditional logic.
2. **Round numbers** — 3x ATR, 25 stocks, 200 DMA. No precisely tuned parameters.
3. **Robust to universe changes** — works on NSE 500, Nifty 250, Nifty 100, and random subsets.
4. **Let winners run** — no distance-from-MA penalty. The ATR trailing stop adapts to each stock's volatility.
5. **Defensive exits** — weekly trailing stop checks catch trend breaks before they become catastrophic drawdowns.

---

## Scripts

| Script | Purpose |
|--------|---------|
| `scripts/build_trend_leaders_signals.py` | Signal generation |
| `scripts/backtest_trend_leaders.py` | Backtest engine |
| `scripts/run_trend_leaders_portfolio.py` | Orchestrator |
| `scripts/report_trend_leaders.py` | HTML report |

---

## TODO

### Production
- [ ] Wire simplified config into orchestrator as single command
- [ ] Integrate with daily pipeline and dashboard
- [ ] Paper trade for 3 months before live deployment
- [ ] Add to subscriber product (tiered: Nifty 250 flagship, Nifty 100 conservative)

### Further Testing
- [ ] Sector concentration check (is there sector clustering?)
- [ ] Different slippage sensitivity (10 bps, 30 bps, 50 bps)
- [ ] Walk-forward validation (roll forward 6-month windows)
- [ ] Survivorship bias check (historical index constituents)
- [ ] Longer history if data becomes available (2015-2020)

---

*Last updated: May 2026*
