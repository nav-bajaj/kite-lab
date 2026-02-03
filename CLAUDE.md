# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Kite-Lab is a momentum-based quantitative trading system for Indian equities using the Zerodha KiteConnect API. The system fetches NSE 500 market data, generates volatility-adjusted momentum signals, and backtests weekly-rebalanced portfolios with comprehensive performance analytics.

**Current Status (February 2026):**
- Production portfolio: NSE 500, L6 momentum, weekly rebalance, min-hold 8 days
- Performance: 59.4% CAGR, -30.0% max DD, 1.92 Sharpe (2020-2026)
- Recent optimizations: Min-hold-days 8 (eliminated 0-7d churn), vol floor (0.20 → 0.05)
- Alternative universes: Nifty 100, Nifty 250 via `--universe` argument
- Single portfolio script handles all universes

## Environment Setup

**Python version:** 3.9+

**Virtual environment:**
```bash
source .venv/bin/activate  # Always activate before running scripts
```

**Key dependencies:** kiteconnect, pandas, matplotlib, python-dotenv

Install via:
```bash
pip install kiteconnect pandas matplotlib python-dotenv
```

**Configuration:**
- `.env` contains API credentials (API_KEY, API_SECRET, REDIRECT_URI)
- `access_token.txt` stores daily OAuth2 token (expires daily)
- `session.json` caches session metadata

## Common Commands

### Daily Production Pipeline
```bash
# Full pipeline (login + data + signals + backup)
python scripts/run_daily_pipeline.py --with-login

# This runs:
# 1. Login to Kite API
# 2. Fetch NSE 500 + indices data
# 3. Update Nifty 100 benchmark
# 4. Build momentum signals
# 5. Backup data to /Users/navdeep/Documents/stock_data/
```

### Final Portfolio Generation
```bash
# Generate final NSE 500 portfolio (default universe)
python scripts/run_final_momentum_portfolio.py

# With fresh data fetch
python scripts/run_final_momentum_portfolio.py --with-data --with-login

# Generate Nifty 100 portfolio (large-cap only)
python scripts/run_final_momentum_portfolio.py --universe nifty100

# Generate Nifty 250 portfolio
python scripts/run_final_momentum_portfolio.py --universe nifty250

# Thursday: Generates changes report (adds/drops)
# Friday: Generates order file for execution
# Output varies by universe (see UNIVERSE_DEFAULTS in script)
```

### Manual Data Operations
```bash
# Login (token expires daily)
python scripts/login_and_save_token.py

# Fetch NSE 500 historical data
python scripts/fetch_nse500_history.py

# Fetch indices data
python scripts/fetch_indices_history.py

# Update Nifty 100 benchmark
python scripts/compute_benchmark.py

# Manual backup to external location
python scripts/sync_data_backup.py
```

### Signal Generation & Backtesting
```bash
# Build L6 momentum signals (flexible parameters)
python scripts/build_momentum_signals_flexible.py \
  --prices-dir nse500_data \
  --output signals.csv \
  --lookback-months 6 \
  --rebalance-weeks 1 \
  --top-n 24 \
  --vol-floor 0.05 \
  --skip-days 0

# Run backtest
python scripts/backtest_momentum.py \
  --signals signals.csv \
  --prices-dir nse500_data \
  --benchmark data/benchmarks/nifty100.csv \
  --output-dir results/ \
  --scenario baseline \
  --top-n 24

# Generate HTML report
python scripts/report_backtests.py \
  --runs results/ \
  --output report.html
```

### Testing & Validation
```bash
# Test vol_floor parameter impact
python scripts/test_vol_floor_impact.py \
  --vol-floors 0.01 0.02 0.03 0.04 0.05 \
  --output experiments/vol_floor_test

# Validate signal quality
python scripts/validate_signals.py --signals signals.csv --top-n 24
```

## Architecture

### Data Pipeline (`data_pipeline/`)
Reusable modules for fetching and storing market data:

- **`symbol_resolver.py`**: Maps trading symbols to instrument tokens using cached `data/instruments_full.csv`
- **`price_client.py`**: `PriceClient` wrapper around KiteConnect API with automatic rate limiting
- **`storage.py`**: CSV persistence utilities
- **`qa.py`**: Data quality checks for price data

### Signal Generation
Primary script: `scripts/build_momentum_signals_flexible.py`

**Algorithm:**
1. **Price panel construction**: Merges daily close prices from `nse500_data/*_day.csv`
2. **Skip window**: Optional (0, 10, or 21 days) to avoid short-term mean reversion
3. **Lookback windows**: L6 (126 days), L9 (189 days), L12 (252 days)
4. **Volatility normalization**:
   - Compute rolling std of daily returns over lookback window
   - Floor volatility at `vol_floor` (default 0.05 = 5% daily)
   - Score = `momentum / max(realized_vol, vol_floor)^power`
5. **Cross-sectional z-scoring**: Standardize scores across all symbols each date
6. **Rebalance frequency**: Weekly or bi-weekly, ranks on last trading day of period

**Output format:** `date, rank, symbol, score, score_6m, mom_6m, vol_6m`

### Backtest Engine
Script: `scripts/backtest_momentum.py`

**Key Features:**
- **Pricing model**: `OHLC/4` average with 0.2% (20 bps) slippage
- **Rebalance timing**: Friday close signals → Monday open execution
- **Position sizing**: Equal-weight across top-N holdings
- **Exit rules**: Baseline (rank-based exit when drops out of top-N)
- **Min hold period**: 8 days default (prevents immediate churn exits)
- **Comprehensive metrics**: CAGR, volatility, Sharpe, max DD, turnover, hit rates

**Output files:**
- `momentum_equity.csv`: Daily portfolio value
- `momentum_trades.csv`: All entry/exit transactions with P&L
- `momentum_holdings.csv`: Current positions
- `momentum_turnover.csv`: Weekly turnover percentage
- `momentum_metrics.csv`: Summary statistics

### Report Generation
Script: `scripts/report_backtests.py`

**Generated HTML report includes:**
- Equity curve with benchmark comparison
- Performance metrics table
- Risk metrics (drawdown, volatility)
- Position-level insights
- Rebalancing behavior analysis
- Trade statistics and hit rates

### Data Backup System
Script: `scripts/sync_data_backup.py`

**Automatic backup to:** `/Users/navdeep/Documents/stock_data/`

**Backed up directories:**
- `nse500_data/` (499 stocks, daily, ~30MB)
- `nse500_data_hourly/` (90 days hourly, ~13MB)
- `indices_data/` (Nifty indices, ~2.5MB)

**Backup strategy:**
- Full directory replacement (not incremental)
- Runs automatically with daily pipeline
- Manual sync: `python scripts/sync_data_backup.py`

## Current Portfolio Configuration

### NSE 500 Production Portfolio (Primary)
**Location:** `data/final_portfolio/`

**Parameters:**
- **Universe:** NSE 500 (499 stocks)
- **Lookback:** 6 months (L6, 126 trading days)
- **Rebalance:** Weekly (Friday signals → Monday trades)
- **Skip days:** 0 (no skip window)
- **Vol floor:** 0.05 (5% daily = 79% annualized)
- **Vol power:** 1.0
- **Top-N:** 24 stocks
- **Min hold days:** 8 (one full rebalance cycle)
- **Initial capital:** ₹1,000,000
- **Slippage:** 0.2% (20 bps)

**Performance (2020-07-10 to 2026-02-02, with min-hold-days 8):**
- **CAGR:** 59.4%
- **Max drawdown:** -30.0%
- **Sharpe ratio:** 1.92
- **Turnover:** 123% annualized
- **Hit rate:** 49.3%
- **Avg holding:** 43.3 days
- **Total trades:** 2,352 (1,188 buys, 1,164 sells)

**Latest holdings (Jan 2026):**
HINDCOPPER, ATHERENERG, NATIONALUM, NETWEB, VEDL, SHRIRAMFIN, ASHOKLEY, HINDZINC, BANKINDIA, JKTYRE, MUTHOOTFIN, INDIANB, MCX, HINDALCO, CANBK, M&MFIN, LTF, INDIACEM, CUB, IDEA, AUBANK, FEDERALBNK, ABCAPITAL, GPIL

### Nifty 100 Alternative Portfolio (Conservative)
**Location:** `nifty_100_tests/`
**Run with:** `python scripts/run_final_momentum_portfolio.py --universe nifty100`

**Parameters:**
- **Universe:** Nifty 100 (100 large-cap stocks)
- **Same parameters as NSE 500** (L6, weekly, vol_floor=0.05, top-N=24, min-hold 8d)

**Performance (2020-07-10 to 2026-01-27):**
- **CAGR:** 44.86% (-12.65% vs NSE 500)
- **Total return:** 682.0% (₹7,820,005 final value)
- **Max drawdown:** -19.11% (+8.56% better than NSE 500)
- **Volatility:** 20.51% annualized
- **Sharpe ratio:** 1.69
- **Turnover:** 57.66% annualized (-53% vs NSE 500)
- **Hit rate:** 45.78%
- **Avg holding:** 52.2 days
- **Total trades:** 1,824 (924 buys, 900 sells)

**Use case:**
- Risk-averse investors wanting lower volatility
- Large portfolios requiring better liquidity
- Preference for blue-chip large-caps only
- Lower turnover for tax efficiency

**Latest holdings (Jan 2026):**
HINDZINC, VEDL, SHRIRAMFIN, CANBK, HINDALCO, EICHERMOT, SBIN, TVSMOTOR, BANKBARODA, MARUTI, AXISBANK, TATASTEEL, JSWSTEEL, TITAN, ADANIPOWER, ASIANPAINT, SBILIFE, BAJAJ-AUTO, HCLTECH, TECHM, COALINDIA, TORNTPHARM, LTIM, TATACONSUM

## Key Data Directories

**Price data:**
- `nse500_data/` - Daily OHLC for NSE 500 (~500 files, gitignored)
- `nse500_data_hourly/` - Hourly data (90 days, gitignored)
- `indices_data/` - Index data (Nifty 50, 100, 500, etc.)

**Universe definitions:**
- `data/static/nse500_universe.csv` - NSE 500 stock list
- `data/static/nifty100_universe.csv` - Nifty 100 stock list
- `data/static/nifty250_universe.csv` - Nifty 250 stock list

**Benchmarks:**
- `data/benchmarks/nifty100.csv` - Nifty 100 Total Return Index

**Production outputs:**
- `data/final_portfolio/final_top24_signals.csv` - Latest NSE 500 signals
- `data/final_portfolio/final_portfolio_24.csv` - Current holdings snapshot

**Experiments:**
- `experiments/final_portfolio/` - Timestamped NSE 500 runs
- `nifty_100_tests/` - Nifty 100 experiments and comparisons

**Backup location (external):**
- `/Users/navdeep/Documents/stock_data/` - Automatic backup of all price data

## Critical Workflows

### Daily Production Workflow
**Run once per day (morning):**
```bash
python scripts/run_daily_pipeline.py --with-login
```

This automatically:
1. Logs in to Kite API
2. Fetches latest NSE 500 price data
3. Fetches latest indices data
4. Updates Nifty 100 benchmark
5. Builds momentum signals
6. Syncs backup to external location

### Weekly Portfolio Rebalance
**Thursday (review day):**
```bash
python scripts/run_final_momentum_portfolio.py
# Review: experiments/final_portfolio/final_portfolio_*/changes_YYYY-MM-DD.csv
# Shows: Stocks to add, stocks to drop, reasons
```

**Friday (execution day):**
```bash
python scripts/run_final_momentum_portfolio.py
# Review: experiments/final_portfolio/final_portfolio_*/orders_YYYY-MM-DD.csv
# Execute orders via Kite Console or API
```

### Parameter Testing Workflow
1. **Test new configuration:**
   ```bash
   python scripts/run_final_momentum_portfolio.py --universe nifty100 --lookback-months 9 --rebalance-weeks 2
   ```

2. **Compare results:**
   - Review `report.html` for equity curves
   - Check `momentum_metrics.csv` for CAGR, DD, Sharpe
   - Compare turnover and hit rates

3. **Document findings:**
   - Add to `docs/failed_experiments.md` for experiment results
   - Update summary tables

## Recent Optimizations (January 2026)

### 1. Vol Floor Parameter Optimization
**Changed:** `vol_floor` from 0.20 → 0.05

**Rationale:**
- Actual stock volatilities: 1.5-3.3% daily (15-52% annualized)
- Old value 0.20 (317% annualized) was absurdly high
- New value 0.05 (79% annualized) clips all stocks equally (pure momentum)

**Impact:**
- Performance: +0.23% CAGR improvement (57.51% vs 57.28%)
- Final value: +₹102,570 on ₹1M capital over 5.5 years
- Stock selection: Identical (both above actual vols)
- Benefit: More meaningful parameter value

**Documentation:** `docs/vol_floor_optimization.md`

**Testing:** Comprehensive tests of 0.01-0.05 range showed:
- Below 0.03: 49-52% CAGR (worse performance)
- 0.04-0.05: 57% CAGR (optimal, pure momentum)
- Above 0.05: No change (all converge)

### 2. Nifty 100 Portfolio Testing
**Created:** Alternative portfolio for risk-averse investors

**Configurations tested:**
1. **L6 + 1-week:** 44.86% CAGR, -19.11% DD (WINNER)
2. **L9 + 2-week:** 38.95% CAGR, -25.22% DD (worse on all metrics)

**Key findings:**
- Nifty 100 has 8.56% lower drawdown vs NSE 500
- NSE 500 adds +12.65% CAGR from mid-cap alpha
- Lower rebalance frequency does NOT reduce risk
- Weekly rebalancing optimal for momentum strategies

**Documentation:** `nifty_100_tests/SUMMARY.md`, `COMPARISON.md`

### 3. Data Backup System
**Added:** Automatic backup to external location

**Benefits:**
- Redundancy outside repository
- Protection against data corruption
- Easy recovery if needed
- Runs automatically with daily pipeline

**Documentation:** `docs/data_backup.md`

### 4. Report Optimizations
**Removed:** Bloated sections that slowed generation

**Improvements:**
- Faster HTML report generation
- Focused on key metrics
- Better position-level insights
- Enhanced benchmark comparisons

## Parameter Insights

### What Works (Proven):
✅ **Lookback:** 6 months (L6) optimal for NSE markets
✅ **Rebalance:** Weekly frequency captures momentum best
✅ **Vol floor:** 0.05 (clips all stocks, pure momentum ranking)
✅ **Skip days:** 0 (no skip window needed)
✅ **Top-N:** 24 stocks (diversification vs concentration balance)
✅ **Universe:** Full NSE 500 (captures mid-cap alpha)
✅ **Min hold days:** 8 (eliminates 0-7d churn, +3.2% CAGR, +0.05 Sharpe)

### What Doesn't Work (Tested):
❌ **Longer lookbacks:** 9-month (L9) underperforms 6-month
❌ **Lower frequency:** Bi-weekly worse than weekly (lower returns, higher DD)
❌ **Restricted universe:** Nifty 100 sacrifices 12.65% CAGR
❌ **Low vol floor:** <0.04 allows over-weighting low-vol, low-return stocks
❌ **High vol floor:** >0.05 conceptually wrong (no benefit)
❌ **Volatility targeting:** Dynamic position sizing disrupts momentum strategy
❌ **Volume-weighted scoring:** Dollar-volume and OBV blends both trail pure momentum
❌ **PnL-hold exit filter:** Freezes portfolio, kills momentum rotation
❌ **Consecutive weeks entry filter:** Delays re-entry after corrections, explodes drawdowns
❌ **Entry rank threshold:** Prevents good entries as much as bad ones

See `docs/failed_experiments.md` for detailed experiment logs.

## Branch Structure

**Active branches:**
- `main` - Stable production code
- `consolidate-portfolio-scripts` - Unified `--universe` argument, min-hold-days
- `fix-pnl-hold-logic` - Backtest experiment features (min-hold, entry filters)
- `nifty100-portfolio` - Nifty 100 testing and comparisons
- `momentum-volume` - Volume-weighted scoring experiments (abandoned)
- `volatility-targeting` - Failed volatility targeting experiments (archived)

**Recommended workflow:**
- Create feature branches for new experiments
- Document findings in `docs/` or experiment folders
- Commit with detailed messages including Co-Authored-By
- Push to GitHub for review

## Code Conventions

**Price data format:** CSV with `[date, open, high, low, close, volume]`

**Trade pricing:** Use `OHLC/4` average (not close) for realistic fills

**Date format:** ISO 8601 (`YYYY-MM-DD`), pandas Timestamps internally

**Symbols:** Uppercase trading symbols (e.g., "INFY", "TCS")

**Returns:**
- Daily returns for volatility calculations
- CAGR for performance reporting
- Sharpe uses arithmetic mean returns

**Rebalance timing:**
- Signals generated: Thursday/Friday close
- Trades execute: Following Monday open
- Weekly schedule: Friday → Monday

**File naming:**
- Timestamped experiments: `YYYYMMDDHHMMSS`
- Signals: `*_signals.csv`
- Portfolio snapshots: `portfolio_YYYY-MM-DD.csv`

## Important Notes

### Vol Floor Parameter
**Current value:** 0.05 (5% daily standard deviation)

**Purpose:** Prevents extreme scores from very low volatility stocks

**How it works:**
```python
score = momentum / max(realized_volatility, vol_floor)
```

**Current behavior:**
- All NSE 500 stocks have volatility < 5% daily
- Vol floor clips all stocks equally
- Effectively creates pure momentum ranking
- No volatility penalty applied

**Don't change unless:** Testing different momentum formulations

### Signal File Requirements
Must contain minimum columns: `date, rank, symbol`

**Additional columns for analysis:**
- `score` - Composite momentum score
- `score_6m` - 6-month score component
- `mom_6m` - Raw 6-month momentum
- `vol_6m` - Realized volatility

### Rebalance Day Logic
**Thursday:** Not a rebalance day (signals only)
- Generates changes report
- Shows adds/drops for preview

**Friday:** Rebalance day (signals + orders)
- Generates order file for execution
- Trade execution happens Monday open

**Script automatically detects day** and generates appropriate outputs.

### Stock Universe Updates
NSE 500 composition changes rarely (1-2 times per year).

**When index changes:**
1. Update `data/static/nse500_universe.csv`
2. Fetch price history: `python scripts/update_prices.py --symbols <NEW_SYMBOL>`
3. Signals will include new stock automatically

### Rate Limiting
- Zerodha API: 3 requests/second
- `PriceClient` handles automatic throttling
- Historical data auto-chunks large date ranges
- Access token expires daily at 6 AM

### Backup and Recovery
**Automatic backup:** Runs with daily pipeline

**Manual recovery:**
```bash
# If repo data corrupted, restore from backup
cp -r /Users/navdeep/Documents/stock_data/nse500_data ./
cp -r /Users/navdeep/Documents/stock_data/indices_data ./
```

**Backup contents updated daily** with latest price data.

## Performance Benchmarks (2020-2026)

| Portfolio | CAGR | Max DD | Sharpe | Turnover | Use Case |
|-----------|------|--------|--------|----------|----------|
| **NSE 500 L6-1W (min-hold 8d)** | 59.4% | -30.0% | 1.92 | 123% | Growth investors |
| **NSE 500 L6-1W (no min-hold)** | 56.2% | -27.7% | 1.87 | 122% | Baseline reference |
| **Nifty 100 L6-1W** | 44.86% | -19.11% | 1.69 | 58% | Risk-averse |
| **Nifty 100 L9-2W** | 38.95% | -25.22% | 1.45 | 23% | Not recommended |
| **Nifty 100 Index** | ~15% | -20% | ~0.7 | 0% | Buy & hold |

**Key insight:** NSE 500 L6 with weekly rebalancing and min-hold 8 days is optimal for most investors.

## Troubleshooting

**Access token expired:**
```bash
python scripts/login_and_save_token.py
```

**Missing price data:**
```bash
python scripts/fetch_nse500_history.py
```

**Signal validation errors:**
```bash
python scripts/validate_signals.py --signals <path> --top-n 24
```

**Backtest fails:**
- Check signal file has required columns
- Verify price data exists for all symbols
- Ensure dates align between signals and prices

## Documentation

**Comprehensive docs in `docs/` folder:**
- `failed_experiments.md` - Backtest experiments log (volume, pnl-hold, entry filters, min-hold)
- `vol_floor_optimization.md` - Vol floor parameter analysis
- `data_backup.md` - Backup system documentation
- `rebalance_trade_report.md` - Trade execution reporting
- `volatility_targeting_experiments.md` - Volatility targeting experiments (lessons learned)

**Experiment summaries:**
- `nifty_100_tests/SUMMARY.md` - Portfolio comparison
- `nifty_100_tests/COMPARISON.md` - Parameter sensitivity
- `nifty_100_tests/README.md` - Nifty 100 overview

---

**Last updated:** February 2026
**Production portfolio:** NSE 500 L6-1W + min-hold 8d (59.4% CAGR, 1.92 Sharpe)
**Alternative portfolio:** Nifty 100 L6-1W (44.86% CAGR, -19.11% DD)
**Status:** Optimized and production-ready
