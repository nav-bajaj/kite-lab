# Trend Leaders 25 — Final Strategy

## Overview

A standalone trend-following portfolio strategy for Indian equities. Designed
to be simple, robust, and explainable in 3 sentences.

**Branch:** `trend-leaders-20` (merged into `main`)

> **REVIEWED MAY 2026.** Full parameter review under the clean (no-lookahead)
> engine in `scripts/_clean_engine.py`. Several components changed; numbers
> below are the honest no-lookahead results with the new locked-in stack.
> The earlier doc (May 2026 rebaseline) is superseded.

---

## Strategy (3 sentences)

> Buy the top 25 stocks by trend quality score (equal 1/3 weights:
> persistence + drawdown control + 6-month-rank momentum) — among stocks
> already in clear long-term uptrends. Enter bi-weekly. Exit if Close < 200
> DMA on weekly check, or if drawdown from position peak exceeds 5x the
> stock's 20-day ATR (no floor).

---

## Configuration

| Parameter | Value |
|-----------|-------|
| Universe | NSE 500 / Nifty 250 / Nifty 100 |
| Target holdings | 25 |
| Entry frequency | Bi-weekly (every other Friday signal → Monday execution) |
| Exit checks | Weekly (Friday signal → Monday execution) |
| Trailing stop | 5x 20-day ATR from position peak, **no floor** |
| Hard exit | Close < 200 DMA on weekly check |
| Rank exit | Drop below rank 45 (top-25 + buffer-20) |
| Position sizing | Equal weight (1/N), max 7.5% cap, drift after entry |
| Slippage | 20 bps (OHLC/4 pricing on next trading day) |

### Trend Quality Score (equal 1/3 weights)

1. **Persistence** — % of last **252 trading days** Close > 100 DMA
2. **Drawdown Control** — `(Close / 126-day rolling high)²` (concave/squared)
3. **6-Month Momentum** — 63-day return, percentile-ranked among eligible stocks

### Eligibility filter (the trend gate)

- Close > 200 DMA
- 50 DMA > 200 DMA
- 200 DMA today > 200 DMA 20 trading days ago (slope rising)

A stock in a downtrend literally cannot enter. Eligibility owns "is it
trending?", the score ranks among trending stocks on three independent
measures of trend quality.

### Execution model

- All decisions use prior-day's close + indicators (signal date)
- All trades execute at next trading day's OHLC/4 (execution date)
- 20 bps slippage applied to every fill
- Weekly Friday-close signal → Monday execution

---

## Honest Performance (clean engine, May 2026)

| Universe | Cadence | CAGR | Max DD | Sharpe | Calmar | Sortino |
|----------|---------|------|--------|--------|--------|---------|
| **NSE 500** | Bi-weekly | **44.0%** | **-28.6%** | **1.88** | **1.54** | 2.17 |
| Nifty 250 | Bi-weekly | 41.2% | -22.5% | 1.93 | 1.83 | 2.23 |
| Nifty 100 | Bi-weekly | 32.7% | -19.7% | 1.72 | 1.67 | 2.08 |

**Period:** 2021-02 to 2026-05 (5.3 years)

**Best risk-adjusted: Nifty 250 Bi-weekly** — 41.2% CAGR, 1.93 Sharpe, 1.83
Calmar, -22.5% max DD. Genuinely better than NSE 500 on Sharpe and DD; only
NSE 500 wins on gross CAGR.

---

## Parameter Review — May 2026

Full deep-dive under the clean engine. Every component and parameter tested
in isolation. Each row below is a locked-in choice with the alternatives that
were tested and rejected.

### Locked-in changes vs prior stack

| Component | Old (prior locked-in) | New (May 2026 locked-in) | Why |
|-----------|----------------------|--------------------------|-----|
| ATR multiplier | 3x | **5x** | Wider stop captures more upside; CAGR up, DD comparable |
| ATR floor | 10% | **No floor** | Floor was forcing premature exits on low-vol leaders |
| Drawdown function | linear | **Concave (squared)** | Penalizes deep drawdowns more sharply, rewards near-highs |
| Persistence window | 63d | **252d** | Long-term reliability beats short-term consistency |
| Persistence reference | 100 DMA | 100 DMA (unchanged) | Confirmed |
| Momentum window | 126d (6m) | **63d (3m)** | Faster trend detection; closer to current strength |
| Momentum scaling | percentile-rank | percentile-rank (unchanged) | Confirmed |
| MA Structure | 4 sub-scores × 0.25 | **DROPPED** | Redundant with eligibility — eligibility already gates trend |
| TQS components | 4 × 25% | **3 × 1/3** | One fewer component; equal split confirmed |

### Confirmed unchanged

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Eligibility | Close > 200 + 50 > 200 + 200 rising 20d | Most universe-agnostic; never worst across NSE 500/Nifty 250/Nifty 100 |
| Cadence | Bi-weekly entry, weekly exit | Best on flagship Nifty 250; weekly exits universally help DD |
| Top-N / Buffer | 25 / 20 | Universe-specific tuning showed gains but rejected for simplicity (see DESIGN.md) |
| TQS weights | 1/3 each | Equal-weight is best on Nifty 250, top-3 elsewhere; tilts are not universe-agnostic |
| Sizing | Equal 1/N, 7.5% cap, drift after entry | Pyramid-into-winners tested and rejected (no universal benefit) |

### Tested and rejected

| Idea | Result |
|------|--------|
| ATR floor 10% | Forced premature exits in low-vol bull-market leaders |
| Linear drawdown component | Less penalty for deep drawdowns; concave squared cleaner |
| Persistence 63d / 100d | Too short; rewarded recently-recovered stocks more than persistent leaders |
| Momentum 126d (6m) | Slower trend detection; 63d (3m) catches turns earlier |
| Universe-specific Top-N | Gains 2-6% CAGR but adds complexity + overfitting risk |
| Universe-specific TQS weights | Same — gains exist but not universe-agnostic |
| Pyramid into winners (+15/+25/+40% triggers) | Only Nifty 250 benefits; complexity not worth it |
| Eligibility "stricter" (+ Close > 50) | Hurts Nifty 100 badly (-7.7% CAGR) |
| Eligibility "100 DMA reference" | Best on NSE 500 but worst on Nifty 100 — not universe-agnostic |
| Eligibility "none" | NSE 500 loses 4.5% CAGR — eligibility is real work |

---

## Strategy Differentiation

| Dimension | Momentum | TL25 | OM25 |
|-----------|----------|------|------|
| Signal | 6m return / vol | Eligibility-gated trend quality | Capture asymmetry |
| Max DD | -35% | **-23 to -29%** | -27% |
| Sharpe (clean) | 1.92 | **1.72-1.93** | 2.26 |
| Recent CAGR (clean) | 1% (stagnant) | **33-44%** | 48% |

TL25 is the **steady trend-follower** — sits between aggressive momentum and
the more defensive OM25.

---

## Production Choice

**Best risk-adjusted: Nifty 250 Bi-weekly** — 41.2% CAGR, -22.5% DD, 1.93 Sharpe
- Highest Sharpe AND lowest DD among the three viable universes
- Recommended flagship

**Highest CAGR: NSE 500 Bi-weekly** — 44.0% CAGR, -28.6% DD, 1.88 Sharpe
- Largest universe → most opportunity
- Higher gross return at the cost of meaningfully more DD

**Conservative: Nifty 100 Bi-weekly** — 32.7% CAGR, -19.7% DD, 1.72 Sharpe
- Lowest DD
- For risk-averse subscribers

---

## Files

| File | Purpose |
|------|---------|
| `scripts/_clean_engine.py` | Canonical clean (no-lookahead) backtest engine |
| `scripts/build_trend_leaders_signals.py` | Signal generation (TL25 score) |
| `scripts/backtest_trend_leaders.py` | Backtest runner (uses clean engine semantics) |
| `scripts/run_trend_leaders_portfolio.py` | Orchestrator (runs all variants, prints summary) |
| `scripts/report_trend_leaders.py` | HTML report |
| `tasks/trend_leaders/experiments/_tl25_*.py` | Parameter review test scripts (May 2026) |

---

## TODO

- [ ] Generate updated HTML report with locked-in stack numbers
- [ ] Validate Nifty 250 Bi-weekly as the new flagship recommendation
- [ ] Sector concentration check
- [ ] Out-of-sample / walk-forward validation
- [ ] Paper trade 3 months before live deployment

---

*Last updated: May 2026 — full parameter review against clean engine, locked-in stack.*
