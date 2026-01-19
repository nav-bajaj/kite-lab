# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Kite-Lab is a momentum-based quantitative trading system for Indian equities using the Zerodha KiteConnect API. The system fetches NSE 500 market data, generates volatility-adjusted momentum signals, and backtests weekly-rebalanced portfolios with hysteresis and PnL-hold exit rules.

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

### Authentication & Data Collection
```bash
# Login (required daily, token expires)
python scripts/login_and_save_token.py

# Cache instrument list (run once daily in morning)
python scripts/cache_instruments.py

# Fetch NSE 500 historical data (daily + hourly)
python scripts/fetch_nse500_history.py

# Update benchmark (Nifty 100)
python scripts/compute_benchmark.py

# Run full daily pipeline
python scripts/run_daily_pipeline.py --with-login
```

### Signal Generation & Backtesting
```bash
# Build L6 momentum signals (weekly rebalance)
python scripts/build_momentum_signals.py --prices-dir nse500_data --output data/momentum/top25_signals.csv --skip-days 21 --lookbacks 6 --top-n 25

# Run backtest
python scripts/backtest_momentum.py --prices-dir nse500_data --signals data/momentum/top25_signals.csv --benchmark data/benchmarks/nifty100.csv --output-dir data/backtests --scenario baseline

# Generate HTML report
python scripts/report_backtests.py --runs data/backtests/run1 data/backtests/run2 --output report.html
```

### Monte Carlo & Grid Search
```bash
# L6 Monte Carlo (baseline vs hysteresis vs PnL-hold)
python scripts/run_l6_monte_carlo.py --runs 20 --sample-size 250 --topn-min 20 --topn-max 30 --skip-days 0 10 21 --exit-buffers 0 5 10 --pnl-hold 0.05 0.1 --vol-floor 0.0005 0.001

# L6 grid search
python scripts/run_l6_grid.py --skip-days 21 10 0 --vol-floor 0.0005 0.001 --top-n 25 20 --exit-buffer 0 5 --scenarios baseline

# Lookback & rebalance frequency experiments
python scripts/run_lookback_rebalance_mc.py --runs 20 --sample-size 250 --lookback-months 6 9 12 --rebalance-weeks 1 2 3 4
```

### Final Portfolio (Production)
```bash
# Generate final portfolio (runs on Thu/Fri for weekly rebalance)
python scripts/run_final_momentum_portfolio.py --with-data --with-login

# Generate portfolio report
python scripts/report_final_portfolio.py
```

### Testing
```bash
# No unified test runner; pytest not installed
# Individual test files exist in tests/ but must be run manually
python tests/test_ta_indicators.py
```

## Architecture

### Data Pipeline (`data_pipeline/`)
Reusable modules for fetching and storing market data:

- **`symbol_resolver.py`**: Maps trading symbols to instrument tokens using cached `data/instruments_full.csv`. Uses `find_instrument(symbol, exchange_priority=["NSE", "BSE"])` to resolve symbols across exchanges.
- **`price_client.py`**: `PriceClient` wrapper around KiteConnect API. Handles chunked historical data fetching with automatic date-range splitting to avoid rate limits.
- **`storage.py`**: Simple CSV persistence utilities.
- **`qa.py`**: Data quality checks for price data.

All data pipeline modules expect `data/instruments_full.csv` to exist (run `cache_instruments.py` first).

### Signal Generation
Implemented in `scripts/build_momentum_signals.py`:

1. **Price panel construction**: Merges daily close prices from `nse500_data/*_day.csv` into a `date × symbol` DataFrame
2. **Skip window**: Default 21-day (1 month) skip to avoid short-term mean reversion
3. **Lookback windows**: L6 (6-month = 126 days), L12 (252 days), L3 (63 days)
4. **Volatility normalization**:
   - Compute rolling std of daily returns over lookback window
   - Floor volatility at epsilon (default 0.0005) to prevent explosion
   - Score = `return / volatility^p` (default p=1.0)
5. **Cross-sectional z-scoring**: For each date, z-score all symbols to make scores comparable
6. **Weekly rebalance**: Ranks symbols on last trading day of each week (W-FRI), selects top-N

Output format: `date, rank, symbol, composite_score, score_6m, mom_6m, vol_6m`

### Backtest Engine
Implemented in `scripts/backtest_momentum.py`:

- **Pricing model**: Fills at `OHLC/4` average with 20 bps slippage
- **Rebalance**: Weekly (Friday close), trades execute on Monday open
- **Position sizing**: Equal-weight across top-N holdings
- **Exit scenarios**:
  - **Baseline**: Exit when symbol drops out of top-N
  - **Hysteresis**: Exit buffer (e.g., top-25 → exit at rank 30) to reduce churn
  - **PnL-hold**: Defer exits if unrealized PnL exceeds threshold (e.g., 5%)
- **Metrics**: CAGR, max drawdown, turnover, hit rate, cost drag, holding period

Outputs:
- `equity.csv`: Daily portfolio NAV
- `trades.csv`: All entry/exit transactions
- `turnover.csv`: Weekly turnover percentage
- `momentum_metrics.csv`: Summary statistics

### Monte Carlo Framework
Primary tool: `scripts/run_l6_monte_carlo.py`

- **Sampling**:
  - Universe: Random subset of NSE 500 (default 250 stocks)
  - Parameters: top-N (20-30), exit-buffer (0-10), PnL-hold (0-0.1), skip-days (0/10/21), vol-floor (0.0005/0.001)
- **Scenarios**: Baseline, hysteresis (exit-buffer), PnL-hold
- **Output**: `experiments/l6_mc_*/summary.csv` (ranked by CAGR) and `report.html`

Use `--scenarios` flag to run specific scenarios (e.g., `--scenarios hyst` for hysteresis only).

### Technical Analysis
`ta_indicators.py` provides vectorized TA functions:

- **Trend**: `ema()`, `sma()`, `macd()`, `adx()`
- **Momentum**: `rsi()`, `momentum()`, `roc()`, `stochastic_oscillator()`, `williams_r()`
- **Volatility**: `atr()`, `bollinger_bands()`
- **Utilities**: `crossover()`, `crossunder()`, `above()`, `below()`

All functions accept pandas Series and return same-indexed Series. Used in `build_momentum_signals_with_ta.py` for filtering experiments (RSI, EMA trend, ADX, MACD).

### Final Portfolio (Production)
Current settings (as of Jan 2026):
- **Signal file**: `data/final_portfolio/final_top24_signals.csv`
- **Holdings snapshot**: `data/final_portfolio/final_portfolio_24.csv`
- **Parameters**: L6 (6-month lookback), skip-days=0, vol-floor=0.2, top-N=24, exit-buffer=0, pnl-hold=0
- **Source experiment**: `experiments/l6_mc_20260117172537/`

`run_final_momentum_portfolio.py`:
- Rebuilds L6 signals from NSE 500 data
- Generates dated snapshot in `experiments/final_portfolio/`
- On Thursday: produces changes report (adds/drops)
- On Friday: generates order file for execution
- Publishes latest signals/holdings to `data/final_portfolio/`
- Creates HTML report with backtest metrics

## Key Data Directories

- **`data/instruments_full.csv`**: Cached instrument list from Kite API (125K+ securities)
- **`nse500_data/`**: Daily OHLC for NSE 500 universe (`<SYMBOL>_day.csv`)
- **`nse500_data_hourly/`**: Last 90 days of hourly data (`<SYMBOL>_60minute.csv`)
- **`data/benchmarks/nifty100.csv`**: Nifty 100 daily closes for comparison
- **`data/momentum/`**: Generated signal files (rankings)
- **`data/backtests/`**: Backtest output folders (equity, trades, metrics)
- **`experiments/`**: Monte Carlo and grid search results
- **`data/final_portfolio/`**: Current production portfolio snapshots

Data directories (`nse500_data/`, `nse500_data_hourly/`, `next50_data/`, `next50_data_hourly/`) are gitignored.

## Critical Workflows

### Daily Production Workflow
1. Login: `python scripts/login_and_save_token.py`
2. Fetch data: `python scripts/fetch_nse500_history.py`
3. Update benchmark: `python scripts/compute_benchmark.py`
4. Generate portfolio: `python scripts/run_final_momentum_portfolio.py`
   - Thursday: Review changes report
   - Friday: Review orders file before execution

### Parameter Tuning Workflow
1. Sample universe: `python scripts/sample_universe.py --size 250`
2. Run Monte Carlo: `python scripts/run_l6_monte_carlo.py --runs 20`
3. Analyze `experiments/l6_mc_*/summary.csv` (sorted by CAGR)
4. Review `report.html` for equity curves and metrics
5. Validate top configurations with full-universe backtest

### Adding New Stocks
1. Ensure symbol is in `data/static/nse500_universe.csv`
2. Fetch history: `python scripts/update_prices.py --symbols <SYMBOL> --daily-dir nse500_data`
3. Signals will automatically include new symbol on next run

## Rate Limiting & API Constraints

- Zerodha API: 3 requests/second limit
- Historical data: Max 60-day chunks for intraday, 1900 days for daily
- Access tokens expire daily at 6 AM
- `PriceClient` auto-chunks large date ranges to avoid rate limits
- Incremental updates: Scripts detect last fetched date and only fetch new data

## Code Conventions

- **Price data format**: CSV with columns `[date, open, high, low, close, volume]`
- **Trade pricing**: Use `OHLC/4` average (not close) to simulate realistic fills
- **Date format**: ISO 8601 (`YYYY-MM-DD`), pandas Timestamps internally
- **Symbols**: Trading symbols are uppercase (e.g., "INFY", "TCS")
- **Returns**: Log returns for internal calculations, simple returns for reporting
- **Rebalance day**: Friday close → Monday open execution

## Notes

- **No mid-week rebalancing**: Final runner (`run_final_momentum_portfolio.py`) disables mid-week trades to match weekly schedule
- **Signal file format**: Must contain `date, rank, symbol` at minimum; backtest engine expects `rank` for hysteresis
- **Volatility floor**: Essential to prevent division-by-zero and extreme scores for low-vol stocks
- **Skip window**: Reduces short-term reversal impact; 21 days ≈ 1 month empirically optimal
- **Universe stability**: NSE 500 list changes rarely; manual updates to `data/static/nse500_universe.csv` required when stocks are added/removed from index
