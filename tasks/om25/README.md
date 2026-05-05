# OM25 — Upside/Downside Capture Ratio Portfolio

## Overview

A portfolio strategy that selects stocks with the best asymmetric market sensitivity — stocks that go up more than the market on good days and fall less on bad days.

**Branch:** `om25`

---

## Strategy (3 sentences)

> Rank stocks by their upside/downside capture ratio over the past year. Monthly, buy the top 25 (let existing positions run, exit buffer 15). Every two weeks, exit if Close < 200 DMA or stock has dropped more than 4x its 20-day ATR from peak.

---

## Locked-In Configuration

| Parameter | Value |
|-----------|-------|
| Universe | NSE 500 |
| Signal | Upside/Downside Capture Ratio (252-day) |
| Entry | Monthly (1st trading day), top 25, incremental sizing |
| Exit check | Bi-weekly (every other Friday) |
| Exit rule | Close < 200 DMA OR 4x ATR(20) trailing stop from peak |
| Exit buffer | 15 (keep stock unless rank drops below 40) |
| Sizing | Equal weight (1/N), 7.5% cap |
| Slippage | 20 bps (OHLC/4) |

**Capture Ratio formula:**
```
upside_capture = avg(stock return on market-up days) / avg(market return on up days)
downside_capture = avg(stock return on market-down days) / avg(market return on down days)
score = upside_capture / downside_capture
```

Higher score = stock participates more in rallies, less in selloffs.

---

## Current Results

| Metric | Value |
|--------|-------|
| CAGR | 32.9% |
| Max Drawdown | -19.6% |
| Sharpe | 2.20 |
| Calmar | 1.68 |
| Correlation with momentum | 0.789 |

**Status:** CAGR needs improvement. 32.9% pre-tax/pre-friction may not be compelling enough for an active subscriber product. Target: 40%+.

---

## What We Tested

### Signal variants (all with full rebalance)
| Signal | CAGR | Sharpe | Corr w/ Mom | Verdict |
|--------|------|--------|-------------|---------|
| Pure Omega Ratio | 35.4% | 1.59 | 0.920 | Too correlated with momentum |
| Omega Quality Score | 30.1% | 1.54 | — | Worse on all metrics |
| Consistency (% pos months × return) | 43.8% | 1.81 | 0.904 | High CAGR but still correlated |
| **Capture Ratio** | 33.2% | 1.83 | **0.829** | Most differentiated |

### Trading mechanics (capture ratio, incremental sizing)
| Config | CAGR | Max DD | Sharpe | Calmar |
|--------|------|--------|--------|--------|
| Monthly entry, no stop | 33.2% | -23.6% | 1.83 | 1.41 |
| Monthly entry, 4x ATR weekly | 30.1% | -18.8% | 2.08 | 1.60 |
| **Monthly entry, 4x ATR biweekly** | **32.9%** | **-19.6%** | **2.20** | **1.68** |
| Biweekly entry, weekly exit | 36.1% | -19.8% | 2.16 | 1.82 |
| 20/30/40-day low stop | 33.6% | -23.1% | 1.95 | 1.45 |
| 5x ATR biweekly | 32.4% | -20.9% | 2.06 | 1.55 |

### What didn't work
- Pure Omega Ratio: 0.92 correlation with momentum (just momentum restated)
- N-day low stops: never trigger before 200 DMA (no benefit)
- 6-month lookback: noisier signal, higher correlation
- No positive return filter: identical to with filter (non-binding)
- Full rebalance: excessive turnover, lower CAGR

---

## Exit Analysis

From the 4x ATR weekly stop analysis:
- **ATR stop**: 70% of exits, avg P&L +4.3%, 42% win rate — clips some winners early
- **200 DMA**: 15% of exits, avg P&L -4.3%, 19% win rate — crash protector (correct)
- **Rank drop**: 15% of exits, avg P&L +17.6%, 84% win rate — healthy rotation

Moving to biweekly exit checks reduced ATR exits from 567 → 460 (less noise), improving CAGR by +2.8%.

---

## Differentiation

| Strategy | Signal | Corr with OM25 |
|----------|--------|----------------|
| Momentum | 6m price return | 0.789 |
| TL25 | Trend quality (MA + persistence) | ~0.85 |
| OM25 | Capture ratio (asymmetric market sensitivity) | — |

10/25 stock overlap with TL25 on latest date. Different character: OM25 picks "quality beta" stocks (low downside participation), not necessarily the fastest trends.

---

## TODO: Improve CAGR to 40%+

Ideas to test:
- [ ] Blend capture ratio with 3-month momentum (like TL25's 15% momentum boost)
- [ ] Bi-weekly entry (faster rotation into new high-capture stocks)
- [ ] Reduce to top 20 (more concentrated)
- [ ] Use capture ratio from market UP days only (ignore downside — just pick best upside participators)
- [ ] Combine with TL25 eligibility filter (only pick capture-ratio stocks that are also in uptrends)
- [ ] Test on Nifty 250 (may have better risk-adjusted like TL25)
- [ ] Universe sampling robustness test

---

*Last updated: May 2026*
