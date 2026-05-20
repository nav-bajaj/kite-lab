# Marketworks

A momentum-based quantitative trading platform for Indian equities, built on the Zerodha KiteConnect API. The directory layout, Railway service, and Vercel deployment are still named `kite-lab` for historical reasons; the user-facing product is Marketworks.

> **Status: Private Beta.** Production lives at <https://marketworks.in>. SEBI Research Analyst registration is currently applied for. All content and functionality is for research and educational purposes; nothing on the platform is investment advice.

## Two halves of the project

1. **Quantitative research toolkit** (Python, `scripts/` + `data_pipeline/`): fetches NSE data via Zerodha KiteConnect, builds momentum signals, backtests strategies, applies corporate actions, runs the daily production pipeline. See the rest of this README for the toolkit's CLI surface.
2. **Web product** (`kite-dashboard/` + `kite-api/`): Next.js 16 + Tailwind frontend on Vercel, FastAPI backend on Railway, Postgres for trade/portfolio data. Authentication via Clerk (Google sign-in, role-gated). Clients see 4 production portfolios (Quality Momentum, Trend Leaders, Core Momentum, Defensive Blend); admins see all 7. Architecture is documented in [`CLAUDE.md`](./CLAUDE.md) and per-task plans live under [`tasks/`](./tasks/).

## Overview

Marketworks provides tools for:
- Secure OAuth2 authentication with Zerodha
- Automated instrument data caching (125K+ securities)
- Historical OHLC data fetching with rate-limiting protection
- Technical analysis with moving averages
- Automated visualization and CSV export

## Features

- **Authentication**: OAuth2-based login with token persistence
- **Data Collection**: Fetch historical market data for NSE, BSE, NFO, BFO, and MF instruments
- **Technical Analysis**: Calculate moving averages (MA50, MA200) and cumulative returns
- **Visualization**: Generate price charts with technical indicators
- **Rate Limiting**: Smart batching to avoid API throttling

## Project Structure

```
kite-lab/
    scripts/
        login_and_save_token.py      # OAuth2 authentication workflow
        cache_instruments.py         # Fetch and cache tradable instruments
        fetch_history_and_analyse.py # Historical data and technical analysis
        fetch_next50_history.py      # Batch downloader for Nifty Next 50 (daily/hourly cached)
        fetch_nse500_history.py      # Batch downloader for NSE 500 universe (daily/hourly cached)
        fetch_indices_history.py     # Fetch 38 tracked indices data (NEW)
        compute_benchmark.py         # Maintain Nifty 100 benchmark series
        build_momentum_signals.py    # Generate weekly momentum rankings
        run_daily_pipeline.py        # Orchestrate daily refresh tasks
        backtest_momentum.py         # Simulate weekly momentum portfolio
        report_backtests.py          # Compare multiple backtest scenarios
        report_indices.py            # Compare portfolio vs all tracked indices (NEW)
        run_l6_grid.py               # L6 grid search (skip/vol-floor/top-N/exit-buffer)
        run_l6_monte_carlo.py        # L6 Monte Carlo (baseline/hysteresis/PnL-hold)
        sample_universe.py           # Sample random subsets of NSE 500
        update_prices.py             # Generic updater using data_pipeline modules
        utils.py                     # Helper utilities for token lookup
    data_pipeline/                   # Reusable components for symbols, prices, and storage
    data/
        static/
            tracked_indices.csv      # List of 38 tracked indices (NEW)
            README_INDICES.md        # Indices tracking documentation (NEW)
        benchmarks/                  # Benchmark indices (e.g., Nifty 100)
    next50_data/                     # Daily cache for Nifty Next 50 (gitignored)
    next50_data_hourly/              # Hourly cache for Nifty Next 50 (gitignored)
    nse500_data/                     # Daily cache for NSE 500 (gitignored)
    nse500_data_hourly/              # Hourly cache for NSE 500 (gitignored)
    indices_data/                    # Daily cache for 38 tracked indices (gitignored, NEW)
    .env                             # API credentials (not tracked)
```

## Setup

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd kite-lab
   ```

2. **Create a virtual environment**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install kiteconnect pandas matplotlib python-dotenv
   ```

4. **Configure API credentials**

   Create a `.env` file in the project root:
   ```
   API_KEY=your_api_key
   API_SECRET=your_api_secret
   REDIRECT_URI=http://localhost:8000/callback
   ```

## Usage

### 1. Authenticate with Zerodha

```bash
python scripts/login_and_save_token.py
```

This will:
- Launch a browser for Zerodha login
- Start a local server on port 8000 to capture the OAuth callback
- Save your access token to `access_token.txt`

### 2. Cache Instruments Data

```bash
python scripts/cache_instruments.py
```

This fetches all tradable instruments from Zerodha and saves them to `data/instruments_full.csv`. Run this once daily in the morning.

### 3. Fetch History and Analyze

```bash
python scripts/fetch_history_and_analyse.py
```

By default, this:
- Fetches daily data for INFY (Infosys) from 2020-01-01 to today
- Calculates MA50, MA200, and cumulative returns
- Exports data to `data/INFY_day.csv`
- Generates charts: `data/INFY_ma.png` and `data/INFY_cumret.png`

Edit the script to analyze different symbols or date ranges.


### 4. Download Nifty Next 50 caches

```bash
python scripts/fetch_next50_history.py
```

This script uses `ind_niftynext50list.csv` to download or incrementally update:
- Daily candles in `next50_data/`
- Hourly candles (last 90 days) in `next50_data_hourly/`

Re-run it anytime to keep both datasets fresh.

### 5. Download NSE 500 caches

```bash
python scripts/fetch_nse500_history.py
```

This uses `data/static/nse500_universe.csv` as the universe source and mirrors the incremental daily/hourly caching used for the Next 50 script:
- Daily candles saved under `nse500_data/`
- Hourly candles (last 90 days) saved under `nse500_data_hourly/`

Ensure `data/static/nse500_universe.csv` stays current before running large backfills.

### 6. Run generic price updater

`data_pipeline` modules power a flexible updater for custom universes:

```bash
python scripts/update_prices.py --symbols INFY TCS HDFCBANK --daily-dir custom_data
```

This reuses incremental caching and writes each symbol to `custom_data/<SYMBOL>_day.csv`.

### 7. Refresh Nifty 100 benchmark

```bash
python scripts/compute_benchmark.py
```

This keeps `data/benchmarks/nifty100.csv` updated with daily closes, returns, and cumulative performance for the benchmark used in momentum comparisons.

### 8. Fetch tracked indices data (NEW)

```bash
python scripts/fetch_indices_history.py
```

This fetches daily historical data for **38 tracked indices** across multiple categories:
- **Broad market**: Nifty 50, 100, 500, Next 50, Midcap, Smallcap
- **Factor/Strategy**: Momentum, Alpha, Low Volatility indices
- **Sectoral**: Banking, IT, Auto, Pharma, Energy, FMCG, etc. (23 sectors)
- **Global**: S&P 500, NASDAQ, Dow Jones
- **Commodity**: MCX Gold, Silver

Data is saved to `indices_data/` directory and used for comprehensive portfolio benchmarking.

**See**: `data/static/README_INDICES.md` for detailed documentation on tracked indices and usage.

### 10. Build weekly momentum rankings

```bash
python scripts/build_momentum_signals.py --prices-dir nse500_data --output data/momentum/top25_signals.csv
```

The script merges NSE 500 price histories, applies a 1-month skip, computes 6M/3M volatility-normalized returns, and exports the top 25 symbols for each weekly rebalance.

### 11. Run the full daily pipeline

```bash
python scripts/run_daily_pipeline.py --with-login
```

`--with-login` launches the Kite login workflow first; omit it for routine runs when a fresh access token already exists. Use `--dry-run` to see the command sequence without executing it. The pipeline now sequentially:
1. Refreshes NSE 500 data
2. **Fetches indices data** (NEW)
3. Updates the Nifty 100 benchmark
4. Rebuilds the momentum rankings

### 13. Backtest the momentum strategy

```bash
python scripts/backtest_momentum.py --prices-dir nse500_data \
       --signals data/momentum/top25_signals.csv \
       --benchmark data/benchmarks/nifty100.csv \
       --output-dir data/backtests
```

The backtester uses the weekly top-25 rankings, trades only when holdings change, prices fills at `OHLC/4` with 20 bps slippage, and writes equity and trade logs to `data/backtests/`.

### 14. Generate backtest comparison report

```bash
python scripts/report_backtests.py --runs data/backtests/baseline \
       data/backtests/cooldown data/backtests/voltrigger \
       --output data/backtests/report.html
```

The report compares every scenario (baseline/cooldown/vol-trigger) with summary metrics, charts, trailing returns, and top/bottom contributors based on realized PnL. Charts require `matplotlib`; if unavailable, tables are still produced.

### 15. Generate indices comparison report (NEW)

```bash
python scripts/report_indices.py \
       --portfolio data/backtests/momentum_equity.csv \
       --output reports/indices_comparison.html
```

This generates a comprehensive HTML report comparing your portfolio performance against all 38 tracked indices:
- **Summary metrics**: CAGR, volatility, Sharpe ratio, max drawdown for all indices
- **Correlation analysis**: How closely your portfolio correlates with each index
- **Beta analysis**: Portfolio sensitivity to index movements
- **Equity curves**: Normalized performance comparison (base 100)
- **Category-wise analysis**: Separate sections for broad market, sectoral, factor, global, and commodity indices

**Use cases**:
- Benchmark against multiple market segments
- Identify sector concentration risks
- Compare vs other systematic strategies (momentum, low-vol)
- Analyze correlation with global markets
- Evaluate diversification opportunities

### 16. Analyze tax impact on returns (NEW)

```bash
python scripts/analyze_tax_impact.py \
       --equity data/backtests/momentum_equity.csv \
       --initial-capital 1000000 \
       --tax-rate 0.25 \
       --output reports/tax_impact.txt \
       --chart reports/tax_impact_chart.png \
       --csv reports/tax_impact_data.csv
```

Simulates the impact of **25% flat tax** on gains using **Indian Financial Year** (April 1 - March 31) taxation model:
- Applies tax at end of each FY on realized gains
- Deducts tax from portfolio and continues with post-tax amount
- Generates year-by-year breakdown and total impact analysis
- Shows how taxation reduces CAGR and final portfolio value

**Key insights** for 60% CAGR strategy:
- Post-tax CAGR: ~47% (13% reduction)
- Tax drag on compounding: ~38%
- Average annual tax: ₹400K on ₹1M initial capital

**See**: `TAX_ANALYSIS_GUIDE.md` for detailed documentation, use cases, and interpretation guide.

### 17. L6 grid search (skip / vol floor / top-N / exit buffer)

```bash
python scripts/run_l6_grid.py --skip-days 21 10 0 --vol-floor 0.0005 0.001 --top-n 25 20 --exit-buffer 0 5 --scenarios baseline cooldown --limit 10
```

### 13. L6 Monte Carlo (baseline / hysteresis / PnL-hold)

```bash
python scripts/run_l6_monte_carlo.py --runs 20 --sample-size 250 --topn-min 20 --topn-max 30 --skip-days 0 10 21 --exit-buffers 0 5 10 --pnl-hold 0.05 0.1 --vol-floor 0.0005 0.001
```

Each run samples a sub-universe, builds L6 signals (depth = top_n + exit_buffer), and runs three scenarios: baseline, hysteresis (exit buffer), and PnL-hold. Results are saved under `experiments/l6_mc_*` with `summary.csv` ranked by CAGR and `report.html`.

To run specific scenarios only:
```bash
# Run only hysteresis scenario
python scripts/run_l6_monte_carlo.py --scenarios hyst --runs 20

# Run baseline and hysteresis
python scripts/run_l6_monte_carlo.py --scenarios baseline hyst --runs 20
```

### 14. L6 Monte Carlo without vol-floor variation

```bash
python scripts/run_l6_monte_carlo_no_volfloor.py --runs 20 --sample-size 250 --topn-min 20 --topn-max 30 --skip-days 0 10 21 --exit-buffers 0 5 10 --pnl-hold 0.05 0.1
```

This variant uses a fixed vol-floor (default 0.0005) to isolate the impact of other parameters. Results are saved under `experiments/l6_mc_no_volfloor_*`.

### 15. Build momentum signals with TA filters

```bash
python scripts/build_momentum_signals_with_ta.py --ta-filter rsi_neutral --output data/momentum/signals_rsi.csv
```

Test whether technical analysis filters improve momentum strategy performance. Available filters:
- `none`: Baseline (no filter)
- `rsi_neutral`: Exclude RSI < 30 or > 70
- `rsi_bullish`: Require RSI > 50
- `trend_ema20/ema50`: Require price above EMA
- `adx_trending`: Require ADX > 25
- `macd_positive`: Require MACD histogram > 0
- `combined_conservative/aggressive`: Multiple filters

### 16. Run TA filter experiments

```bash
python scripts/run_ta_filter_experiments.py --runs 10 --sample-size 250
```

Systematically tests all TA filters against baseline L6 momentum. Results show average performance by filter type in `experiments/ta_filters_*/summary_by_filter.csv`.

### 17. Lookback and Rebalance Frequency Monte Carlo

```bash
python scripts/run_lookback_rebalance_mc.py --runs 20 --sample-size 250 --lookback-months 6 9 12 --rebalance-weeks 1 2 3 4
```

Tests combinations of lookback periods (6, 9, 12 months) and rebalance frequencies (1-4 weeks). Each run samples top-N, exit-buffer, and PnL-hold parameters. Results include aggregated statistics by lookback period, rebalance frequency, and their combinations in `experiments/lookback_rebal_mc_*/summary_by_config.csv`.

### 18. Final Momentum Portfolio (Production)

```bash
python scripts/run_final_momentum_portfolio.py --with-data --with-login
```

The final portfolio runner is the production-ready daily script that:
- Rebuilds L6 weekly signals using optimal parameters (skip-days=0, vol-floor=0.2, top-n=24)
- **Applies score filtering by default**: entry threshold 2.5, exit threshold 1.5, incremental allocation mode
- Generates dated snapshots under `experiments/final_portfolio/`
- Publishes latest signals to `data/final_portfolio/final_top24_signals.csv`
- Publishes latest holdings to `data/final_portfolio/final_portfolio_24.csv`
- On Thursdays: generates a changes report showing next rebalance trades
- On Fridays: generates orders file for execution
- Produces comprehensive HTML report with performance analytics

**Score Filtering Benefits** (vs baseline):
- +3.98% CAGR improvement (60.17% vs 56.19%)
- Similar drawdown (-28.60% vs -27.11%)
- 13% fewer trades (lower transaction costs)
- Lower turnover (27.31% vs 29.64%)

**Options:**
- `--with-data`: Refresh NSE500 prices and benchmark before generating signals
- `--with-login`: Login to Kite before data refresh
- `--min-entry-score`: Override entry threshold (default: 2.5)
- `--min-exit-score`: Override exit threshold (default: 1.5)
- `--score-rebalance-mode`: Choose `incremental` (default, recommended) or `full` rebalance
- `--dry-run`: Preview what would be executed without making changes

To disable score filtering, set both thresholds to 0:
```bash
python scripts/run_final_momentum_portfolio.py --min-entry-score 0 --min-exit-score 0
```

### 19. Enhanced Portfolio Reporting

The reporting system generates comprehensive HTML reports with advanced analytics:

**Completed Features:**
- **Drawdown Analysis**: Dual-panel chart showing equity curve and drawdown timeline, top 5 worst periods with recovery stats, current underwater status
- **Rolling Metrics**: 6-month rolling Sharpe, multi-window volatility, rolling beta/correlation vs benchmark, 1-year rolling max drawdown
- **Calendar Performance**: Monthly returns heatmap with color coding, quarterly performance table, seasonality analysis, best/worst months
- **Enhanced Holdings Table**: 10-day trailing performance vs benchmark, day-by-day breakdown, unrealized PnL, position sizing

**Planned Features** (see `REPORTING_IMPROVEMENTS.md` for details):
- Score filtering metrics (filtered stocks, early exits, effectiveness analysis)
- Detailed trade analytics (win rate by holding period, profit factor, best/worst trades)
- Position-level insights (concentration risk, HHI, correlation matrix)
- Comprehensive risk metrics (Sortino, Calmar, Alpha, Information Ratio, VaR, CVaR)
- Rebalancing behavior analysis (turnover patterns, trade clustering, churn rate)
- Enhanced benchmark comparison (relative strength, up/down capture ratios, tracking error)
- Watch lists (stocks near entry/exit thresholds)
- Forward-looking section (next rebalance preview, expected turnover)
- System health indicators (data freshness, missing data warnings)

Reports are generated automatically by:
```bash
python scripts/report_backtests.py --runs <backtest_dir> --output report.html
```

Charts require `matplotlib`; if unavailable, tables are still produced. Report size is typically 500-700KB with embedded PNG charts.

## Momentum Strategy Methodology

The momentum signal generation implemented in `scripts/build_momentum_signals.py` follows a structured approach:

### Data Inputs
- Daily close prices for the NSE 500 universe (CSV files in `nse500_data/`)
- Prices are merged into a single `date × symbol` panel and sorted chronologically
- A 21-trading-day "skip window" (≈1 month, configurable) is applied to reduce short-term mean reversion effects

### Momentum Metrics

For each symbol and date:

1. **Price relatives**
   - Default focus: L6 return `R6 = P_{t-21} / P_{t-21-126} - 1` (6-month lookback)
   - Optional variants: 12M `R12 = P_{t-21} / P_{t-21-252} - 1`, 3M `R3 = P_{t-21} / P_{t-21-63} - 1`

2. **Volatility estimates** use daily returns (with the same 21-day skip) over matching windows, floored at epsilon to avoid exploding scores:
   - `σ6 = max(std(returns_{t-21-126 : t-21}), ε)` (default ε = 0.0005)
   - Optional: `σ12`, `σ3` when those horizons are enabled

3. **Risk-adjusted scores**
   - `S6 = R6 / σ6^p` where `p` is a volatility exponent (default 1.0; use 0.5 for sqrt-vol scaling)
   - Optional `S12` / `S3` match their windows

4. **Cross-sectional normalization**
   - For each date, z-score each enabled score across all symbols to make them comparable

5. **Composite score**
   - Default: `Composite = Z6`
   - If multiple horizons are enabled: average of all enabled z-scored horizons

### Ranking & Output
- Rebalance dates: last trading day of each week (`W-FRI` schedule)
- On each rebalance date, rank symbols by composite score (descending) and keep the top 25
- Output columns per row: date, rank, symbol, composite score, component scores (`score_12m/6m/3m`), raw returns (`mom_12m/6m/3m`), and vol estimates (`vol_12m/6m/3m`)
- Results are saved to `data/momentum/top25_signals.csv` for downstream consumption by the backtest engine

When modifying parameters (lookbacks, weights, skip length) or adding filters (RSI, EMA slope), update the script and configuration documentation accordingly.

## Technical Analysis Toolkit

The `ta_indicators.py` module provides vectorized, pandas-compatible technical indicators:

**Trend Indicators:**
- `ema()`, `sma()`: Moving averages
- `macd()`: Moving Average Convergence Divergence
- `adx()`: Average Directional Index (trend strength)

**Momentum Indicators:**
- `rsi()`: Relative Strength Index (0-100)
- `momentum()`, `roc()`: Rate of change
- `stochastic_oscillator()`: %K and %D
- `williams_r()`: Williams %R

**Volatility Indicators:**
- `atr()`: Average True Range
- `bollinger_bands()`: Volatility bands

**Utility Functions:**
- `crossover()`, `crossunder()`: Detect signal crossings
- `above()`, `below()`: Check position relative to threshold

All functions operate on pandas Series/DataFrames and return the same shape. See `tests/test_ta_indicators.py` for usage examples.

## Requirements

- Python 3.9+
- Zerodha KiteConnect API credentials
- Active Zerodha trading account

## Key Dependencies

- `kiteconnect`: Official Zerodha API client
- `pandas`: Data manipulation and analysis
- `matplotlib`: Visualization
- `python-dotenv`: Environment variable management

## Security Notes

- Never commit `.env`, `access_token.txt`, or `session.json` to version control
- Access tokens expire daily and need to be refreshed
- Store API credentials securely

## License

MIT
