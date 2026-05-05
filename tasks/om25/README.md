# OM25 — Composite Capture Score Portfolio

## Overview

A portfolio strategy that selects stocks with both high upside market participation AND good upside/downside asymmetry. Uses a composite percentile rank of upside capture and capture ratio.

**Branch:** `om25`

---

## Strategy (3 sentences)

> Rank each stock by the average of its upside-capture percentile rank and its capture-ratio percentile rank over the past year. Monthly, buy the top 25 (let winners run, exit buffer 15). Weekly, exit if Close < 200 DMA or 4x ATR trailing stop from peak.

---

## Locked-In Configuration

| Parameter | Value |
|-----------|-------|
| Universe | NSE 500 |
| Signal | Composite: 50% upside capture pct rank + 50% capture ratio pct rank (252d) |
| Entry | Monthly (1st trading day), top 25, incremental sizing |
| Exit check | Weekly (every Friday) |
| Exit rule | Close < 200 DMA OR 4x ATR(20) trailing stop from peak |
| Exit buffer | 15 (keep stock unless rank drops below 40) |
| Sizing | Equal weight (1/N), 7.5% cap |
| Slippage | 20 bps (OHLC/4) |
| Eligibility | 220+ valid return observations, positive 252-day total return |

---

## Performance

| Metric | Value |
|--------|-------|
| CAGR | 53.7% |
| Max Drawdown | -24.1% |
| Sharpe | 2.72 |
| Sortino | 3.40 |
| Calmar | 2.23 |

### Robustness (random 350/500 stock subsets, 10 trials)

| | Min | Median | Max |
|---|---|---|---|
| CAGR | 44.1% | 50.2% | 61.0% |
| Sharpe | 2.21 | 2.53 | 3.04 |
| Max DD | -23.2% | -21.6% | -20.4% |

**10/10 trials above 40% CAGR. 10/10 above 2.0 Sharpe.**

---

## How the Composite Score Works

```
For each stock on each monthly rebalance date:
  1. Compute upside_capture = avg(stock return on market-up days) / avg(market return on up days)
  2. Compute capture_ratio = upside_capture / downside_capture
  3. Percentile-rank both among eligible stocks (0 to 1)
  4. composite_score = 0.5 * upside_pct_rank + 0.5 * ratio_pct_rank
  5. Select top 25 by composite_score
```

**What this selects:** Stocks that score well on BOTH dimensions — high upside participation AND good asymmetry. Filters out:
- Pure high-beta stocks (high upside but also high downside → poor ratio rank)
- Pure defensive stocks (great ratio but low upside → poor upside rank)

**What it keeps:** Stocks that go up aggressively on good days AND have structural downside protection.

---

## Differentiation

| | Momentum | TL25 | OM25 |
|---|---|---|---|
| Signal | 6m price return | Trend structure + persistence | Composite capture score |
| Corr with OM25 | 0.82 | 0.87 | — |
| Character | Aggressive growth | Steady trend followers | Quality upside participators |
| Max DD | -35% | -21% | -24% |
| Recent CAGR (2024+) | 1% | 20% | TBD |

---

## Evolution Log

| Step | Signal | CAGR | Sharpe | DD | Corr | Verdict |
|------|--------|------|--------|-----|------|---------|
| Pure Omega | sum(gains)/sum(losses) | 35.4% | 1.59 | -31.8% | 0.92 | Too correlated with momentum |
| Capture Ratio | upside/downside capture | 32.9% | 2.20 | -19.6% | 0.79 | Good risk-adj but low CAGR |
| Upside-only | upside capture only | 45.2% | 2.04 | -27.3% | 0.76 | High CAGR but high DD |
| **Composite (final)** | **50/50 pct rank blend** | **53.7%** | **2.72** | **-24.1%** | **0.82** | **Best overall** |

---

## Universe & Frequency Matrix

| Universe | Entry | CAGR | Max DD | Sharpe | Calmar |
|----------|-------|------|--------|--------|--------|
| NSE 500 | Monthly | 53.7% | -24.1% | 2.72 | 2.23 |
| **NSE 500** | **Bi-weekly** | **60.0%** | -25.1% | 2.58 | 2.40 |
| Nifty 250 | Monthly | 47.3% | -18.3% | 2.44 | **2.59** |
| Nifty 250 | Bi-weekly | 52.4% | -20.3% | 2.40 | 2.58 |
| Nifty 100 | Monthly | 33.6% | -20.3% | 1.97 | 1.66 |
| Nifty 100 | Bi-weekly | 38.1% | -21.6% | 1.95 | 1.77 |

## Slippage Sensitivity (NSE 500, monthly)

| Slippage | CAGR | Sharpe | CAGR loss |
|----------|------|--------|-----------|
| 10 bps | 55.3% | 2.81 | — |
| 20 bps | 53.7% | 2.72 | -1.6% |
| 30 bps | 51.9% | 2.64 | -3.4% |
| 50 bps | 48.8% | 2.47 | -6.5% |

Even at 50 bps (very conservative), strategy delivers 48.8% CAGR.

## Period Analysis

| Period | OM25 CAGR | Momentum | TL25 |
|--------|-----------|----------|------|
| Full (2021+) | +52.9% | +26.4% | +43.3% |
| 2022+ | +29.8% | +13.3% | +29.9% |
| 2024+ | +25.7% | +1.1% | +15.1% |
| 2025+ | +6.3% | -17.9% | -3.2% |

Hot year: 2023 (+83%) — but unlike momentum, OM25 followed up with 2024 (+57%) and stays positive in 2025.

---

## TODO

- [ ] Generate comprehensive HTML report
- [ ] Paper trade for validation
- [ ] Wire into production scripts
- [ ] Sector concentration analysis

---

*Last updated: May 2026*
