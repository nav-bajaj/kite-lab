# Trend Leaders 25 — Strategy Implementation

## Overview

A standalone trend-following portfolio strategy for Indian equities, designed as a separate subscriber product alongside the existing cross-sectional momentum strategy.

**Strategy philosophy:** Select stocks in the cleanest, most durable uptrends with recent momentum strength. Let winners run with dynamic trailing stops. Auto-raise cash when fewer stocks qualify.

**Branch:** `trend-leaders-20`

**Specification:** `data/trend_leaders_20_backtest_handoff.md`

---

## Current Best Configuration

| Parameter | Value |
|-----------|-------|
| Universe | NSE 500 (also tested on Nifty 250, Nifty 100) |
| Target holdings | 25 |
| Entry frequency | Bi-weekly (every other Friday) |
| Exit frequency | Weekly (every Friday — trailing stop checks) |
| Exit buffer | 20 (keep stock unless rank drops below 45) |
| Position sizing | Equal weight 4% (7.5% cap when fewer stocks qualify) |
| Trailing stop | Dynamic: 200 DMA base; 50 DMA/15% trail if >30% extended; 20% trail if >15% extended |
| Slippage | 20 bps (OHLC/4 pricing) |
| Benchmark | Nifty 100 TRI |

**Trend Quality Score (TQS) — raw weighted average, no distance penalty:**
- 30% Moving Average Structure (Close > 50 > 100 > 200 DMA stacking)
- 30% Trend Persistence (% of 63 days Close > 100 DMA)
- 25% Drawdown Control (proximity to 6-month rolling high)
- 15% Momentum (3-month return, percentile-ranked among eligible stocks)

---

## Performance Results

### Universe Comparison (same config)

| Universe | CAGR | Max DD | Sharpe | Sortino | Calmar | Vol |
|----------|------|--------|--------|---------|--------|-----|
| **NSE 500** | **40.1%** | -25.0% | 1.76 | 2.01 | 1.60 | 22.8% |
| **Nifty 250** | 40.0% | -21.1% | **1.93** | **2.26** | **1.90** | 20.7% |
| Nifty 100 | 32.9% | -17.3% | 1.81 | 2.18 | 1.90 | 18.2% |

**Nifty 250 is the sweet spot** — same CAGR as NSE 500 with 4% less DD and best Sharpe.

### Optimization Journey (NSE 500)

| Iteration | CAGR | Max DD | Sharpe | Calmar | Change |
|-----------|------|--------|--------|--------|--------|
| V1 Base (monthly, with distance penalty) | 20.8% | -18.9% | 1.25 | 1.10 | Starting point |
| + Remove distance penalty | 26.7% | -32.2% | 1.26 | 0.83 | Let winners run |
| + Dynamic trailing stop | 30.0% | -25.7% | 1.52 | 1.17 | Protect extended stocks |
| + 15% momentum component | 36.1% | -26.6% | 1.62 | 1.36 | Prefer recent strength |
| + Top-25 (from Top-20) | 37.2% | -26.2% | 1.72 | 1.42 | More diversification |
| **+ Bi-weekly entry** | **40.1%** | **-25.0%** | **1.76** | **1.60** | Faster trend capture |

### Comparison with Momentum Strategy

| Metric | TL25 (NSE 500) | Momentum L6 | Benchmark |
|--------|----------------|-------------|-----------|
| CAGR | 40.1% | 59.4% | ~15% |
| Max DD | -25.0% | -30.0% | ~-20% |
| Sharpe | 1.76 | 1.92 | ~0.7 |
| Calmar | 1.60 | — | — |
| Monthly Win Rate | 69.4% | — | — |
| Correlation (daily) | — | 0.785 | — |

---

## Implementation

### Scripts

| Script | Purpose |
|--------|---------|
| `scripts/build_trend_leaders_signals.py` | Signal generation: eligibility + TQS ranking (monthly/weekly/bi-weekly) |
| `scripts/backtest_trend_leaders.py` | Backtest engine: dual-frequency, trailing stops, exit hysteresis |
| `scripts/run_trend_leaders_portfolio.py` | Orchestrator: signals + backtests + summary |
| `scripts/report_trend_leaders.py` | HTML report: metrics, charts, holdings, comparison |

### Running the Strategy

```bash
# Generate signals (bi-weekly, top-25, rank output 45 for buffer)
python scripts/build_trend_leaders_signals.py \
  --universe data/static/nse500_universe.csv \
  --rebalance-freq weekly \
  --rank-output 45 --top-n 25 \
  --w-ma 0.30 --w-persistence 0.30 --w-drawdown 0.25 --w-distance 0.0

# Run backtest
python scripts/backtest_trend_leaders.py \
  --signals data/trend_leaders/signals/trend_leaders_signals.csv \
  --prices-dir nse500_data \
  --benchmark data/benchmarks/nifty100.csv \
  --output-dir data/trend_leaders/backtests/current_best \
  --top-n 25 --exit-buffer 20 --variant base

# Generate report
python scripts/report_trend_leaders.py
```

Note: The current best configuration (bi-weekly + momentum component + trailing stop) was developed through inline testing. The scripts support all the building blocks but the full optimized pipeline hasn't been wired into a single orchestrator command yet (see TODO below).

---

## Architecture

### Entry Logic (bi-weekly)
1. Compute trend eligibility: Close > 200 DMA, 50 DMA > 200 DMA, 200 DMA rising
2. Compute TQS for eligible stocks (MA structure + persistence + drawdown control + 3m momentum)
3. Rank by TQS descending
4. Fill open slots from top-25 (only buy new entrants, no rebalance of continuing positions)

### Exit Logic (weekly)
**Dynamic trailing stop based on how extended the stock is:**
- **All stocks:** Close < 200 DMA → exit
- **Stocks >30% above 200 DMA:** Close < 50 DMA OR 15% off position peak → exit
- **Stocks >15% above 200 DMA:** 20% off position peak → exit

**Monthly rank-based exit:**
- Stock drops below rank 45 (top_n + buffer) → exit

### Key Design Decisions

1. **No distance-from-200 DMA penalty** — lets winners run; the trailing stop provides protection instead
2. **Incremental sizing** — only buy new entrants with freed cash; continuing positions drift
3. **Exit hysteresis (buffer=20)** — prevents churn from rank noise near boundary
4. **Momentum component (15%)** — percentile-ranked 3m return gives preference to stocks with recent strength, without making this a pure momentum strategy
5. **Bi-weekly entry** — catches new trends faster than monthly without weekly noise

---

## Output Structure

```
data/trend_leaders/
  signals/
    trend_leaders_signals.csv             # Current production signals
    persistence_only_signals.csv          # Variant 4 (simpler)
    no_distance_penalty_signals.csv       # No distance penalty signals
  backtests/
    current_best/                         # Latest locked-in config
    base/                                 # Original V1 base
    trailing_stop_b/                      # Trailing stop without bi-weekly
    [other experiment variants...]
  reports/
    trend_leaders_20_report.html          # Comprehensive HTML report
    comparison_summary.md                 # Results summary
```

---

## Experiments Log

### What Worked
- Removing distance-from-200 DMA penalty (+6% CAGR)
- Dynamic trailing stop by extension level (+3% CAGR, -6% DD)
- 15% momentum component (3-month return) (+6% CAGR, +0.10 Sharpe)
- Top-25 instead of Top-20 (+1% CAGR, +0.10 Sharpe, lower DD)
- Bi-weekly entry instead of monthly (+3% CAGR, -1% DD)
- Exit buffer of 20 (vs 10 or 15)

### What Didn't Work
- Weekly rebalance (too much churn, rank noise destroys returns)
- 100 DMA eligibility instead of 200 DMA (too permissive in bear markets, -29.6% DD)
- Full rebalance at each entry (unnecessary turnover — 2696% annualized)
- Percentile-ranked TQS components (amplifies tiny differences, causes rank volatility)
- Hybrid entry/hold signals (selecting "near MA" stocks for entry picked weaker trends)
- Tighter exit buffer (10 or 15 — more churn, worse Sharpe)
- Higher momentum weights (>15% — diminishing returns, slightly worse DD)
- Top-10 or Top-12 concentration (too volatile)

---

## TODO / Future Work

### Strategy Improvements to Test
- [ ] 6-month momentum instead of 3-month (longer lookback may be more stable)
- [ ] ATR-based trailing stop (adapts to each stock's volatility instead of fixed %)
- [ ] Sector diversification cap (max 4-5 stocks from same sector)
- [ ] Minimum volume/liquidity filter (exclude illiquid micro-caps)
- [ ] EMA instead of SMA for faster indicator response
- [ ] Min-hold-days (8 days, like momentum strategy — prevent immediate flip-flops)

### Robustness & Sensitivity
- [ ] Different initial capital (₹10L, ₹50L, ₹1Cr)
- [ ] Slippage sensitivity (10 bps vs 30 bps vs 50 bps)
- [ ] Out-of-sample testing (train on 2021-2023, test on 2024-2026)
- [ ] Monte Carlo simulation of parameter stability
- [ ] Survivorship bias check (use actual historical NSE 500 constituents)

### Production Pipeline
- [ ] Wire optimized config into `run_trend_leaders_portfolio.py` orchestrator
- [ ] Add bi-weekly rebalance date derivation to orchestrator
- [ ] Add momentum component to signal generator CLI (new `--w-momentum` flag)
- [ ] Integrate with dashboard (sync to production DB)
- [ ] Add to daily pipeline (like momentum strategy)
- [ ] Thursday preview / Friday execution workflow

### Product & Reporting
- [ ] Offer as tiered product: Nifty 250 (flagship), Nifty 100 (conservative), NSE 500 (aggressive)
- [ ] Generate subscriber-friendly report (simplified, weekly email)
- [ ] Track live paper portfolio before going to production
- [ ] Combine with momentum for a blended product (50/50 or risk-parity)

---

## Design Documents

- [DESIGN.md](DESIGN.md) — Architecture decisions, lessons learned, V1 assessment
- [phase1_signals.md](phase1_signals.md) — Signal generation implementation (Done)
- [phase2_backtest.md](phase2_backtest.md) — Backtest engine implementation (Done)
- [phase3_variants.md](phase3_variants.md) — Variant testing (Done)
- [phase4_reports.md](phase4_reports.md) — Report generation (Done)
- [phase5_orchestrator.md](phase5_orchestrator.md) — Orchestrator (Done)

---

*Created: May 2026*
*Last updated: May 2026 — Locked in bi-weekly + Top-25 + Mom 15% + trailing stop (40.1% CAGR, 1.76 Sharpe)*
