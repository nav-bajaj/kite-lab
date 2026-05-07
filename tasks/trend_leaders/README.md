# Trend Leaders 25 — Final Strategy

## Overview

A standalone trend-following portfolio strategy for Indian equities. Designed to be simple, robust, and explainable in 3 sentences.

**Branch:** `trend-leaders-20` (merged into `main`)

> ⚠️ **REBASELINED MAY 2026.** Earlier numbers in this doc reflected a same-day-close → same-day-OHLC/4 lookahead bug in the weekly exit logic. The bug has been fixed in `scripts/backtest_trend_leaders.py`. All numbers below are honest, no-lookahead results.

---

## Strategy (3 sentences)

> Buy the top 25 stocks by trend quality score (equal-weight: MA stacking + persistence + drawdown control + 6-month momentum). Enter bi-weekly. Exit if Close < 200 DMA or 3x ATR trailing stop from peak (min 10% floor).

---

## Configuration

| Parameter | Value |
|-----------|-------|
| Universe | NSE 500 (flagship) / Nifty 250 / Nifty 100 |
| Target holdings | 25 |
| Entry frequency | Bi-weekly (every other Friday signal → Monday execution) |
| Exit checks | Weekly (Friday signal → Monday execution) |
| Exit rule | Close < 200 DMA OR 3x 20-day ATR trailing stop from position peak (min 10% floor) |
| Rank exit | Drop below rank 45 (buffer of 20) |
| Position sizing | Equal weight (1/N), max 7.5% cap |
| Slippage | 20 bps (OHLC/4 pricing on next trading day) |

**Trend Quality Score (equal 25% weights):**
1. MA Structure — binary: Close > 50 > 100 > 200 DMA stacking + slope
2. Trend Persistence — % of last 63 days Close > 100 DMA
3. Drawdown Control — Close / 126-day rolling high
4. 6-Month Momentum — percentile-ranked among eligible stocks

**Eligibility filter:**
- Close > 200 DMA
- 50 DMA > 200 DMA
- 200 DMA today > 200 DMA 20 days ago (slope rising)

**Execution model:**
- All decisions use prior-day's close + indicators (signal date)
- All trades execute at next trading day's OHLC/4 (execution date)
- 20 bps slippage applied to every fill

---

## Honest Performance (Lookahead-Corrected)

| Universe | Cadence | CAGR | Max DD | Sharpe | Calmar | Beta |
|----------|---------|------|--------|--------|--------|------|
| **NSE 500** | **Bi-weekly** | **36.4%** | **-26.2%** | **1.52** | **1.39** | 1.12 |
| NSE 500 | Monthly | 33.2% | -27.6% | 1.54 | 1.21 | 0.97 |
| **Nifty 250** | **Bi-weekly** | **38.8%** | **-23.2%** | **1.79** | **1.67** | 1.09 |
| Nifty 250 | Monthly | 29.3% | -25.4% | 1.46 | 1.16 | 1.00 |
| Nifty 100 | Bi-weekly | 31.9% | -19.8% | 1.71 | 1.61 | 1.05 |
| Nifty 100 | Monthly | 28.1% | -19.5% | 1.58 | 1.44 | 0.99 |

**Period:** 2021-02 to 2026-05 (5.3 years)

### Best risk-adjusted: Nifty 250 Bi-weekly
- 38.8% CAGR, 1.79 Sharpe, 1.67 Calmar, -23.2% max DD
- Better than NSE 500 on every metric except gross CAGR

---

## Lookahead Correction Detail

The original `backtest_trend_leaders.py` used same-day close to decide same-day OHLC/4 execution in the weekly exit check:

```python
# OLD (buggy):
if date in weekly_exit_dates:
    if close_panel.loc[date, sym] < sma_200_panel.loc[date, sym]:
        execute_sell(at trade_panel.loc[date, sym])  # same day, lookahead
```

The fix separates signal date from execution date:

```python
# NEW (clean):
if date in weekly_exec_to_signal:  # date is execution day (e.g. Monday)
    signal_date = weekly_exec_to_signal[date]  # prior signal day (Friday)
    if close_panel.loc[signal_date, sym] < sma_200_panel.loc[signal_date, sym]:
        execute_sell(at trade_panel.loc[date, sym])  # next-day OHLC/4
```

### Inflation removed

| Metric | Old (claimed) | New (clean) | Δ |
|--------|---------------|-------------|---|
| NSE 500 Bi-weekly CAGR | 43.1% | 36.4% | -6.7% |
| NSE 500 Bi-weekly Sharpe | 1.93 | 1.52 | -0.41 |

The lookahead added ~5-7% CAGR by allowing exit decisions to "see" the day's close when executing at the day's OHLC/4. Removing it gives realistic trading expectations.

---

## Parameter Re-validation (with clean engine)

Most locked-in parameter choices held up under proper testing:

| Parameter | Locked-in | Tested alternatives | Verdict |
|-----------|-----------|---------------------|---------|
| Top-N | 25 | 20, 30 | **Keep 25** (clearly best) |
| Exit buffer | 20 | 15, 25, 30 | Marginal: buf 15 slightly better (+0.4% CAGR) |
| ATR multiplier | 3x | 3.5x, 4x | **Keep 3x** (best DD with 10% floor) |
| ATR floor | 10% | 0% (no floor) | **Keep 10%** (clearly better DD) |
| Momentum lookback | 6m | 3m | Marginal: 3m slightly better (+0.5% CAGR) |
| Cadence | Bi-weekly | Monthly | Tied on Sharpe; bi-weekly +3% CAGR |

### Optional refinements (within noise)
- Could change exit buffer 20 → 15 (+0.4% CAGR, +0.02 Sharpe)
- Could change momentum lookback 6m → 3m (+0.5% CAGR, +0.06 Sharpe)

These are marginal and likely just noise. Recommendation: **keep current parameters** to avoid over-tuning.

---

## Strategy Differentiation

| Dimension | Momentum | TL25 | OM25 |
|-----------|----------|------|------|
| Signal | 6m return / vol | Trend structure + 6m mom | Composite capture asymmetry |
| TL25 vs Momentum corr | — | high | — |
| Max DD | -35% | **-26%** | -27% |
| Recent CAGR (clean) | 1% (stagnant) | **36%** | 48% |

TL25 is the **steady trend-follower** that sits between aggressive momentum and the more defensive OM25.

---

## Production Choice

**Flagship: NSE 500 Bi-weekly** — 36.4% CAGR, -26.2% DD, 1.52 Sharpe
- Highest gross CAGR
- Largest universe = most opportunity

**Best risk-adjusted: Nifty 250 Bi-weekly** — 38.8% CAGR, -23.2% DD, 1.79 Sharpe
- Genuinely better Sharpe AND lower DD AND higher CAGR than NSE 500
- Worth promoting to flagship

**Conservative: Nifty 100 Bi-weekly** — 31.9% CAGR, -19.8% DD, 1.71 Sharpe
- Lowest DD, very high Sharpe
- Suitable for risk-averse subscribers

---

## TODO

- [ ] Re-test bi-weekly vs monthly more carefully (Sharpe was tied — could simplify product to monthly only)
- [ ] Sector concentration check
- [ ] Generate updated HTML report with clean numbers
- [ ] Validate Nifty 250 Bi-weekly as the new flagship recommendation
- [ ] Paper trade 3 months before live deployment

---

*Last updated: May 2026 — rebaselined to honest no-lookahead numbers.*
