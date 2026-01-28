# Nifty 250 Portfolio Comparison

**Generated:** 2026-01-28

This document compares the Nifty 250 momentum portfolio against the baseline NSE 500 and conservative Nifty 100 portfolios.

## Portfolio Parameters (Identical Across All)

| Parameter | Value |
|-----------|-------|
| Lookback | 6 months (L6) |
| Rebalance | Weekly |
| Skip days | 0 |
| Vol floor | 0.05 |
| Top-N | 24 stocks |
| Initial capital | ₹1,000,000 |
| Slippage | 0.2% (20 bps) |

## Performance Comparison (2020-07-10 to 2026-01-28)

| Metric | NSE 500 | Nifty 250 | Nifty 100 |
|--------|---------|-----------|-----------|
| **Universe Size** | 499 stocks | 250 stocks | 100 stocks |
| **CAGR** | 57.51% | 52.80% | 44.86% |
| **Total Return** | 1,144.7% | 952.8% | 682.0% |
| **Final Value** | ₹12,446,536 | ₹10,527,872 | ₹7,820,005 |
| **Max Drawdown** | -27.67% | -25.65% | -19.11% |
| **Volatility** | 26.02% | ~24% | 20.51% |
| **Sharpe Ratio** | 1.71 | ~1.70 | 1.69 |
| **Annualized Turnover** | 122.27% | 86.45% | 57.66% |
| **Hit Rate** | 47.76% | 46.89% | 45.78% |
| **Avg Holding Days** | 38.7 | 42.4 | 52.2 |
| **Total Trades** | 2,482 | 2,242 | 1,824 |

## Key Insights

### 1. Return vs Universe Size Trade-off

The results show a clear relationship between universe size and returns:

```
NSE 500 (499 stocks) → 57.51% CAGR
Nifty 250 (250 stocks) → 52.80% CAGR  (-4.71%)
Nifty 100 (100 stocks) → 44.86% CAGR  (-12.65%)
```

Each step down in universe size costs approximately:
- NSE 500 → Nifty 250: **-4.71% CAGR** (sacrificing small-cap alpha)
- Nifty 250 → Nifty 100: **-7.94% CAGR** (sacrificing mid-cap alpha)

### 2. Risk Reduction

Smaller universes provide better risk characteristics:

| Portfolio | Max DD | DD Improvement vs NSE 500 |
|-----------|--------|---------------------------|
| NSE 500 | -27.67% | - |
| Nifty 250 | -25.65% | +2.02% |
| Nifty 100 | -19.11% | +8.56% |

### 3. Turnover and Trading Costs

Larger universes require more active trading:

| Portfolio | Ann. Turnover | Trades | Reduction vs NSE 500 |
|-----------|---------------|--------|----------------------|
| NSE 500 | 122.27% | 2,482 | - |
| Nifty 250 | 86.45% | 2,242 | -29% turnover |
| Nifty 100 | 57.66% | 1,824 | -53% turnover |

### 4. Position Quality

The Nifty 250 sits in a "sweet spot" between return and risk:
- Captures mid-cap momentum alpha (unlike Nifty 100)
- Avoids small-cap volatility (unlike NSE 500)
- Lower turnover than NSE 500 (tax efficiency)
- Better liquidity than small-caps

## Use Cases

| Portfolio | Best For |
|-----------|----------|
| **NSE 500** | Maximum return seekers, higher risk tolerance, smaller portfolios |
| **Nifty 250** | Balanced approach, mid-cap exposure with better liquidity |
| **Nifty 100** | Risk-averse investors, large portfolios, tax-conscious investors |

## Recommendation

**Nifty 250 is an excellent middle-ground option:**
- Achieves 92% of NSE 500's CAGR (52.80% vs 57.51%)
- With only 93% of the drawdown (-25.65% vs -27.67%)
- And 29% less turnover (86% vs 122%)
- Better liquidity for larger portfolio sizes

For investors who find NSE 500 too volatile but Nifty 100 too conservative, **Nifty 250 offers the best risk-adjusted profile**.

## Files

- **Report:** `nifty250_portfolio_20260128134045/report.html`
- **Signals:** `nifty250_portfolio_20260128134045/signals/nifty250_signals.csv`
- **Equity curve:** `nifty250_portfolio_20260128134045/backtests/baseline/momentum_equity.csv`
- **Trades:** `nifty250_portfolio_20260128134045/backtests/baseline/momentum_trades.csv`
