# OM25 — Composite Capture Score Portfolio

## Overview

A portfolio strategy that selects stocks with both high upside market participation AND good upside/downside asymmetry. Uses a composite percentile rank of upside capture and capture ratio.

**Branch:** `om25`

**Status:** Production strategy with two tiers (Monthly + Bi-weekly).

---

## Strategy (3 sentences)

> Rank each stock by the average of its upside-capture percentile rank and its capture-ratio percentile rank over the past year. Buy the top 25 (let winners run, exit buffer 15). Weekly, exit if Close < 200 DMA or 4x ATR trailing stop from peak.

Same signal, two cadences.

---

## Two Production Variants

OM25 is offered as **two tiers** that share the exact same signal but differ on rebalance cadence. The signal picks the same kinds of stocks; the cadence determines deployment speed and consequently risk profile.

### Tier 1 — Monthly (Conservative)
> Entry: Monthly (1st trading day) | Exit: Weekly (4x ATR or Close < 200 DMA)

| Metric | Value |
|--------|-------|
| CAGR | 54.4% |
| Max Drawdown | -24.0% |
| Sharpe | **2.76** |
| Sortino | **3.44** |
| Calmar | 2.27 |
| Volatility | 19.7% |
| Beta | 0.82 |
| Avg Cash | 21.4% |

**Character:** More defensive. Avg cash of 21% acts as natural shock absorber. Sees fewer drawdowns (11 significant DDs vs bi-weekly's 17), but each takes longer to recover (~80 days avg vs 32 days for bi-weekly).

### Tier 2 — Bi-weekly (Aggressive)
> Entry: Every other Friday | Exit: Weekly (4x ATR or Close < 200 DMA)

| Metric | Value |
|--------|-------|
| CAGR | **60.6%** |
| Max Drawdown | -25.1% |
| Sharpe | 2.61 |
| Sortino | 3.06 |
| Calmar | **2.42** |
| Volatility | 23.2% |
| Beta | 1.04 |
| Avg Cash | 10.0% |

**Character:** More aggressive. Higher deployment, faster drawdown recoveries. More drawdowns but each one shorter. Captures bull rallies more fully.

### Why Both?

Different subscriber profiles:
- **Conservative subscribers** — those who lose sleep over drawdowns, want smoother equity curves → Monthly
- **Aggressive subscribers** — those optimizing for compound growth, can tolerate more volatility → Bi-weekly

The two strategies are highly correlated (0.95 monthly returns) since they hold the same kinds of stocks. They differ mainly in **deployment level**, not in stock selection.

---

## Key Insight: Beta Decomposition

Cross-correlation analysis revealed a counter-intuitive truth:

| Measurement | Monthly | Bi-weekly | Gap |
|-------------|---------|-----------|-----|
| Headline beta | 0.82 | 1.04 | +0.22 |
| Stock-portion beta (cash removed) | 1.20 | 1.21 | +0.005 |

**98% of the beta gap is cash drag, not stock selection.** Both tiers pick stocks with the same ~1.20 deployed beta. Monthly's "lower beta" comes from holding 21% cash on average vs bi-weekly's 10%.

This is why both tiers can be marketed honestly:
- They use **identical stock selection** (same signal, same composite score)
- They differ only in **how often cash gets redeployed**
- Cash itself functions as the risk modulator

---

## Performance — Multi-Period Analysis

### Yearly Returns

| Year | Monthly | Bi-weekly | Diff (Bi - Monthly) |
|------|---------|-----------|---------------------|
| 2022 | +0.2% | +11.7% | +11.5% (bi-weekly redeploys post-correction faster) |
| 2023 | +83.0% | +106.1% | +23.2% (bull captured better) |
| 2024 | +57.2% | +60.1% | +2.9% |
| 2025 | -4.4% | -8.7% | -4.3% (monthly's cash buffer helps) |
| 2026 YTD | +18.1% | +12.0% | -6.1% |

### Period CAGR

| Period | Monthly | Bi-weekly | Winner |
|--------|---------|-----------|--------|
| Full (2021+) | 53.6% | 59.9% | Bi-weekly |
| From 2022 | 30.6% | 34.9% | Bi-weekly |
| From 2023 | 42.2% | 43.8% | Bi-weekly |
| From 2024 | 27.0% | 22.5% | **Monthly** |
| From 2025 | 8.3% | 0.7% | **Monthly** |

**Bi-weekly wins clean bulls. Monthly wins choppy/down markets.**

---

## How the Composite Score Works

```
For each stock on each rebalance date:
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

## Differentiation From Other Strategies

| | Momentum | TL25 | OM25 (Monthly) | OM25 (Bi-weekly) |
|---|---|---|---|---|
| Signal | 6m price return | Trend structure + persistence | Composite capture score | Same |
| Corr with Momentum | 1.00 | 0.89 | 0.82 | 0.87 |
| Corr with TL25 | 0.89 | 1.00 | 0.87 | 0.88 |
| Character | Aggressive growth | Steady trend followers | Quality upside participators | Same, more deployed |
| Max DD | -35% | -21% | -24% | -25% |
| Recent CAGR (2024+) | 1% | 20% | 27% | 22.5% |

---

## Trading Activity

| | Monthly | Bi-weekly |
|---|---------|-----------|
| Trades / year | 281 | 367 |
| Annualized turnover | 536% | 712% |
| Cost drag (5y total) | 60% | 103% |
| Avg holding | 49 days | 43 days |

Bi-weekly trades 30% more, costing ~42% more in slippage over 5 years.

---

## Robustness (Random Universe Subsets)

Random 350/500 NSE 500 stock subsets, 10 trials, on monthly variant:

| Metric | Min | Median | Max |
|--------|-----|--------|-----|
| CAGR | 44.1% | 50.2% | 61.0% |
| Sharpe | 2.21 | 2.53 | 3.04 |
| Max DD | -23.2% | -21.6% | -20.4% |

10/10 trials above 40% CAGR. Strategy doesn't depend on a few specific stocks.

---

## Universe Variants

| Universe | Entry | CAGR | Max DD | Sharpe | Calmar |
|----------|-------|------|--------|--------|--------|
| **NSE 500** | Monthly | 54.4% | -24.0% | 2.76 | 2.27 |
| **NSE 500** | Bi-weekly | 60.6% | -25.1% | 2.61 | 2.42 |
| Nifty 250 | Monthly | 47.3% | -18.3% | 2.44 | 2.59 |
| Nifty 250 | Bi-weekly | 52.4% | -20.3% | 2.40 | 2.58 |
| Nifty 100 | Monthly | 33.6% | -20.3% | 1.97 | 1.66 |
| Nifty 100 | Bi-weekly | 38.1% | -21.6% | 1.95 | 1.77 |

---

## Slippage Sensitivity (NSE 500, Monthly)

| Slippage | CAGR | Sharpe |
|----------|------|--------|
| 10 bps | 55.3% | 2.81 |
| 20 bps (current) | 53.7% | 2.72 |
| 30 bps | 51.9% | 2.64 |
| 50 bps | 48.8% | 2.47 |

Robust to higher real-world execution costs.

---

## Risk-Off Mechanisms — Tested and Rejected

We tested four explicit risk-off filters on top of bi-weekly to see if we could systematically reduce drawdowns. All were rejected.

| Mechanism | CAGR | Max DD | Verdict |
|-----------|------|--------|---------|
| Baseline (no filter) | 60.6% | -25.1% | — |
| V1: Index < 200 DMA → 50% exposure | 55.3% | -19.1% | Loses 5.3% CAGR, 200 DMA too coarse |
| V2: Breadth <30% → 50% exposure | 58.9% | -19.1% | Quietly defensive, but barely activated when needed (2025) |
| V3: Skip entries when index < 50 DMA | 53.8% | -16.6% | Best DD reduction but cost 12% YTD in 2026 (skipped recovery) |
| V4: Half-exit on weekly stops | 55.6% | -23.3% | More trades, worse Sharpe (whipsaw) |

### Why We Rejected Them

- **The baseline already has internal protection** — 4x ATR trailing stop + 200 DMA exit handle most stock-specific risk
- **Drawdown character matters more than depth** — baseline's -25% DD recovers in <1 year. V3's lower DD comes with sluggish 50 DMA filter that misses sharp recoveries
- **Compound speed > drawdown reduction** — losing 12% YTD recovery in 2026 (V3) is the kind of gap that compounds badly over years
- **Cash drag is already implicitly providing risk management** in the monthly variant — no need to add another layer
- **Filter complexity invites overfitting** — every threshold (30% breadth, 50 DMA, etc.) is another parameter to fit to the past

The strategy is left clean. Both monthly and bi-weekly stand on their own merits.

---

## Evolution Log

| Step | Signal | CAGR | Sharpe | DD | Corr | Verdict |
|------|--------|------|--------|-----|------|---------|
| Pure Omega | sum(gains)/sum(losses) | 35.4% | 1.59 | -31.8% | 0.92 | Too correlated with momentum |
| Capture Ratio | upside/downside capture | 32.9% | 2.20 | -19.6% | 0.79 | Good risk-adj but low CAGR |
| Upside-only | upside capture only | 45.2% | 2.04 | -27.3% | 0.76 | High CAGR but high DD |
| **Composite Monthly** | **50/50 pct rank blend** | **54.4%** | **2.76** | **-24.0%** | **0.82** | **Production: conservative** |
| **Composite Bi-weekly** | **Same signal, faster cadence** | **60.6%** | **2.61** | **-25.1%** | **0.87** | **Production: aggressive** |

---

## TODO

- [ ] Generate comprehensive HTML reports for both tiers
- [ ] Paper trade for validation (separate paper portfolios for each tier)
- [ ] Wire into production scripts
- [ ] Sector concentration analysis
- [ ] Decide on naming for subscriber-facing products

---

*Last updated: May 2026*
