# OM25 — Omega Ratio Stock Portfolio

## Overview

A standalone portfolio strategy that ranks stocks by the quality and asymmetry of their historical daily return distribution using the Omega Ratio. Designed as a third subscriber product alongside Momentum and TL25.

**Core question:** Which stocks have the best upside/downside return asymmetry over the past year?

**Branch:** `om25`

**Specification:** `data/om25_backtest_handoff.md`

---

## Strategy Summary

| Parameter | Value |
|-----------|-------|
| Universe | NSE 500 |
| Target holdings | 25 |
| Sizing | Equal weight 4% per stock (no scale-up) |
| Rebalance | Monthly (1st trading day) |
| Signal | Omega Ratio (sum of gains / sum of losses, threshold = 0%) |
| Lookback | 252 trading days (configurable: 126, 378) |
| Eligibility | Min 220 valid observations + positive 252-day return |
| Omega cap | 10.0 (prevent infinite values) |
| Cash | Remainder when <25 qualify, earns 0% |
| Slippage | 20 bps (OHLC/4 pricing, consistent with other strategies) |
| Exits | Monthly only (no weekly exits in V1) |

---

## How OM25 Differs

| Strategy | Question | Signal | Personality |
|----------|----------|--------|-------------|
| Momentum | Strongest relative performers? | 6m price return | Aggressive growth |
| TL25 | Cleanest sustained uptrends? | MA structure + persistence + trailing stop | Trend-following, defensive |
| **OM25** | **Best upside/downside asymmetry?** | **Omega Ratio of daily returns** | **Quality returns, smoother winners** |

---

## Implementation Phases

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Signal generator (Omega computation + ranking) | Pending |
| 2 | Backtest engine (monthly rebalance, 4% weight, cash tracking) | Pending |
| 3 | Run all 5 variants | Pending |
| 4 | Report generation + comparison vs momentum + TL25 | Pending |
| 5 | Robustness testing (universe sampling) | Pending |

---

## Variants to Test

| # | Name | Lookback | Ranking | Positive Return Filter |
|---|------|----------|---------|------------------------|
| 1 | Pure Omega | 252d | Raw omega_capped | Yes |
| 2 | Omega Quality Score | 252d | 60% omega + 20% return + 20% downside dev | Yes |
| 3 | 126-Day Omega | 126d | Raw omega_capped | Yes |
| 4 | 378-Day Omega | 378d | Raw omega_capped | Yes |
| 5 | No Return Filter | 252d | Raw omega_capped | No |

---

## Scripts (Planned)

| Script | Purpose |
|--------|---------|
| `scripts/build_om25_signals.py` | Omega computation + ranking + audit output |
| `scripts/backtest_om25.py` | Monthly rebalance backtest with 4% sizing |
| `scripts/run_om25_portfolio.py` | Orchestrator |
| `scripts/report_om25.py` | HTML report |

---

## Key Questions to Answer

1. Does raw Omega work as a stock-ranking signal?
2. Is OM25 meaningfully different from momentum and TL25?
3. Does it select "smoother winners" or just low-vol sleepy stocks?
4. Does the positive return filter help or make it too momentum-like?
5. Which lookback (126/252/378) is best?
6. Is turnover reasonable for monthly rebalance?
7. Does Omega Quality Score improve over pure Omega?

---

## Design Principles (from TL25 lessons)

1. **Start simple** — pure Omega ranking first, add complexity only if it helps
2. **Round numbers** — 252 days, 25 stocks, 4% weight, cap at 10
3. **Validate with universe sampling** — don't overfit to specific stocks
4. **Compare honestly** — correlation with existing strategies is the key differentiation test
5. **Avoid overfitting** — resist the urge to tune many dials; the goal is to test whether Omega Ratio IS a signal, not to maximize in-sample CAGR

---

*Created: May 2026*
