# Nifty 100 Momentum Portfolio

## Overview

This folder contains experiments running the same momentum strategy on the Nifty 100 universe instead of the full NSE 500 universe.

**Purpose:** Compare portfolio performance when constrained to blue-chip large-cap stocks only.

## Universe

**Stocks:** 100 stocks from the Nifty 100 index
**Source:** `data/static/nifty100_universe.csv`
**Data:** Same price data from `nse500_data/` directory

## Configurations Tested

### Configuration 1: L6 + 1-Week (Baseline) ✓
- **Lookback:** 6 months (126 days)
- **Rebalance:** Weekly (Friday signals → Monday trades)
- **CAGR:** 44.86%
- **Max DD:** -19.11%
- **Folder:** `nifty100_portfolio_20260127223454/`

### Configuration 2: L9 + 2-Week
- **Lookback:** 9 months (189 days)
- **Rebalance:** Bi-weekly (every 2 weeks)
- **CAGR:** 38.95%
- **Max DD:** -25.22%
- **Folder:** `nifty100_portfolio_20260127223955/`

**Common Parameters:**
- **Skip days:** 0 (no skip window)
- **Vol floor:** 0.05 (5% daily = 79% annualized)
- **Vol power:** 1.0
- **Top-N:** 24 stocks
- **Initial capital:** ₹1,000,000
- **Slippage:** 0.2% (20 bps)

**Winner:** L6 + 1-Week (higher returns, lower risk)

See `COMPARISON.md` for detailed analysis.

## Performance Comparison

### Nifty 100 Portfolio
- **CAGR:** 44.86%
- **Total return:** 682.0% (₹7,820,005 final value)
- **Max drawdown:** -19.11%
- **Volatility:** (from equity curve)
- **Sharpe ratio:** (calculated)
- **Turnover:** 57.66% annualized
- **Hit rate:** 45.78%
- **Avg holding period:** 52.2 days
- **Trades:** 1,824 total (924 buys, 900 sells)

### NSE 500 Portfolio (for reference)
- **CAGR:** 57.51%
- **Total return:** 1144.7% (₹12,446,536 final value)
- **Max drawdown:** -27.67%
- **Volatility:** 26.02% annualized
- **Sharpe ratio:** 1.71
- **Turnover:** 122.27% annualized
- **Hit rate:** 47.76%
- **Avg holding period:** 38.7 days
- **Trades:** 2,482 total (1,253 buys, 1,229 sells)

## Key Differences

### Returns
- **Nifty 100:** 44.86% CAGR (-12.65% vs NSE 500)
- NSE 500 outperforms by capturing higher-momentum mid/small-caps

### Risk
- **Nifty 100:** -19.11% max DD (8.56% better)
- Lower drawdown due to large-cap stability

### Turnover
- **Nifty 100:** 57.66% annualized (53% lower)
- More stable holdings due to less volatile large-caps
- Longer holding periods (52 vs 39 days)

### Stock Composition
**Overlapping stocks** (in both portfolios as of Jan 2026):
- HINDZINC, VEDL, SHRIRAMFIN, CANBK, HINDALCO
- SBIN, TVSMOTOR, TATASTEEL, JSWSTEEL
- (9 stocks overlap)

**NSE 500 only** (not in Nifty 100):
- HINDCOPPER, ATHERENERG, NATIONALUM, NETWEB
- ASHOKLEY, BANKINDIA, JKTYRE, MUTHOOTFIN
- INDIANB, MCX, M&MFIN, LTF, INDIACEM
- CUB, IDEA, AUBANK, FEDERALBNK, ABCAPITAL, GPIL
- (15 stocks unique to NSE 500)

**Nifty 100 only** (not in NSE 500 top 24):
- EICHERMOT, BANKBARODA, MARUTI, AXISBANK
- TITAN, ADANIPOWER, ASIANPAINT, SBILIFE
- BAJAJ-AUTO, HCLTECH, TECHM, COALINDIA
- TORNTPHARM, LTIM, TATACONSUM
- (15 stocks unique to Nifty 100)

## Insights

### 1. Mid-cap Alpha
NSE 500 portfolio captures significant alpha from mid/small-caps:
- HINDCOPPER, ATHERENERG, NATIONALUM (metal/commodity)
- NETWEB (IT hardware)
- MCX (exchange)
These stocks are not in Nifty 100 but contribute to higher returns.

### 2. Volatility-Return Tradeoff
- Nifty 100: Lower risk (-19% DD) but lower return (45% CAGR)
- NSE 500: Higher risk (-28% DD) but higher return (58% CAGR)
- Risk-adjusted (Sharpe): NSE 500 still wins

### 3. Turnover and Stability
- Nifty 100 has 53% lower turnover
- Large-caps rank more stably over time
- Lower transaction costs due to fewer trades

### 4. Large-cap Defensive Play
Nifty 100 portfolio includes more defensive large-caps:
- TITAN, ASIANPAINT, COALINDIA (stable businesses)
- HCLTECH, TECHM, LTIM (defensive IT)
NSE 500 leans more cyclical/commodity-heavy.

## Use Cases

**Nifty 100 Portfolio:**
- Conservative investors wanting lower volatility
- Portfolios with limited liquidity (large position sizes)
- Tax-efficient (lower turnover = fewer taxable events)
- Risk-averse mandates

**NSE 500 Portfolio:**
- Growth-focused investors
- Higher risk tolerance
- Capturing full market opportunity set
- Smaller portfolio sizes (can access mid-caps)

## Recommendation

**For most retail investors:** NSE 500 portfolio
- Superior risk-adjusted returns (1.71 Sharpe)
- Acceptable drawdown (-27.67%)
- Captures full momentum universe

**For institutional/HNI:** Consider Nifty 100
- Lower drawdown for risk management
- Better liquidity for large sizes
- Still solid 45% CAGR
- Lower transaction costs

## Running the Experiment

```bash
# Generate Nifty 100 momentum portfolio
python scripts/run_final_momentum_portfolio.py --universe nifty100

# Compare with NSE 500
python scripts/run_final_momentum_portfolio.py --universe nse500

# View reports
open nifty_100_tests/nifty100_portfolio_*/report.html
open experiments/final_portfolio/final_portfolio_*/report.html
```

## Files

- `nifty100_symbols.txt` - List of 100 symbols
- `nifty100_portfolio_*` - Timestamped experiment runs
  - `signals/` - Weekly momentum rankings
  - `backtests/baseline/` - Backtest results (trades, equity, metrics)
  - `report.html` - HTML report with charts

---

**Created:** January 2026
**Test Period:** 2020-07-10 to 2026-01-27 (5.5 years)
**Universe:** Nifty 100 (100 large-cap stocks)
**Benchmark:** Nifty 100 Total Return Index
