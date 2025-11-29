# Kite-Lab

A Python toolkit for Indian stock market analysis using the Zerodha KiteConnect API.

## Overview

Kite-Lab provides tools for:
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
        compute_benchmark.py         # Maintain Nifty 100 benchmark series
        build_momentum_signals.py    # Generate weekly momentum rankings
        validate_signals.py          # QA checks for signal file shape/duplicates
        compare_signals_baseline.py  # Drift check vs frozen baseline signals
        run_daily_pipeline.py        # Orchestrate daily refresh tasks
        backtest_momentum.py         # Simulate weekly momentum portfolio
        report_backtests.py          # Compare multiple backtest scenarios
        run_l6_grid.py               # L6 grid search (vol-floor/top-N/exit-buffer)
        run_l6_monte_carlo.py        # L6 Monte Carlo (baseline/hysteresis/PnL-hold)
        run_rebalance_sensitivity.py # Sweep exit buffer / PnL-hold / cooldown / vol-trigger knobs
        sample_universe.py           # Sample random subsets of NSE 500
        update_prices.py             # Generic updater using data_pipeline modules
        utils.py                     # Helper utilities for token lookup
    data_pipeline/                   # Reusable components for symbols, prices, and storage
    data/                            # Market data and analysis outputs (not tracked)
    next50_data/                     # Daily cache for Nifty Next 50 (gitignored)
    next50_data_hourly/              # Hourly cache for Nifty Next 50 (gitignored)
    nse500_data/                     # Daily cache for NSE 500 (gitignored)
    nse500_data_hourly/              # Hourly cache for NSE 500 (gitignored)
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

### 8. Build weekly momentum rankings

```bash
python scripts/build_momentum_signals.py --prices-dir nse500_data --output data/momentum/top25_signals.csv
```

The script merges NSE 500 price histories, computes 6M/3M volatility-normalized returns (no skip by default), and exports the top 25 symbols for each weekly rebalance.

### 9. Run the full daily pipeline

```bash
python scripts/run_daily_pipeline.py --with-login
```

`--with-login` launches the Kite login workflow first; omit it for routine runs when a fresh access token already exists. Use `--dry-run` to see the command sequence without executing it. The pipeline sequentially refreshes NSE 500 data, updates the Nifty 100 benchmark, and rebuilds the momentum rankings.

### 10. Backtest the momentum strategy

```bash
python scripts/backtest_momentum.py --prices-dir nse500_data \
       --signals data/momentum/top25_signals.csv \
       --benchmark data/benchmarks/nifty100.csv \
       --output-dir data/backtests
```

The backtester uses the weekly top-25 rankings, trades only when holdings change, prices fills at `OHLC/4` with 20 bps slippage, and writes equity and trade logs to `data/backtests/`.

### 11. Generate an HTML comparison report

```bash
python scripts/report_backtests.py --runs data/backtests/baseline \
       data/backtests/cooldown data/backtests/voltrigger \
       --output data/backtests/report.html
```

The report compares every scenario (baseline/cooldown/vol-trigger) with summary metrics, charts, trailing returns, and top/bottom contributors based on realized PnL. Charts require `matplotlib`; if unavailable, tables are still produced.

### 12. L6 grid search (vol floor / top-N / exit buffer)

```bash
python scripts/run_l6_grid.py --skip-days 0 --vol-floor 0.0005 0.001 --top-n 25 20 --exit-buffer 0 5 --scenarios baseline cooldown --limit 10
```

### 13. L6 Monte Carlo (baseline / hysteresis / PnL-hold)

```bash
python scripts/run_l6_monte_carlo.py --runs 20 --sample-size 250 --topn-min 20 --topn-max 30 --skip-days 0 --exit-buffers 0 5 10 --pnl-hold 0.05 0.1 --vol-floor 0.0005 0.001
```

Each run samples a sub-universe, builds L6 signals (depth = top_n + exit_buffer), and runs three scenarios: baseline, hysteresis (exit buffer), and PnL-hold. Results are saved under `experiments/l6_mc_*` with `summary.csv` ranked by CAGR and `report.html`.

### 14. Validate signals

```bash
python scripts/validate_signals.py --signals data/momentum/top25_signals.csv --top-n 25
```

Checks for duplicates, missing ranks, or row overflows per date.

### 15. Compare signals vs baseline

```bash
python scripts/compare_signals_baseline.py --baseline data/momentum/signals_L6_noskip.csv --candidate data/momentum/top25_signals.csv --top-n 25 --output data/momentum/compare.csv
```

Reports overlap ratios and rank drift relative to a frozen snapshot.

### 16. Rebalance sensitivity (turnover/drawdown tuning)

```bash
python scripts/run_rebalance_sensitivity.py --signals data/momentum/top25_signals.csv --exit-buffers 0 5 10 --pnl-hold 0.05 0.1 --cooldown-weeks 1 2 --staged-steps 0.25 0.5 --vol-targets 0.15 0.2 --vol-lookbacks 63
```

Sweeps exit buffer / PnL-hold / cooldown staging / vol-trigger settings across baseline, cooldown, and vol-trigger scenarios. Saves `summary.csv` and `report.html` under `experiments/rebalance_*`.

## Momentum signal methodology (summary)

- Inputs: daily close prices from `nse500_data/`; merged into a `date × symbol` panel, sorted chronologically.
- Skip window: default 21 trading days (configurable) to reduce short-term mean reversion.
- Returns: default L6 (6-month) `R6 = P_{t-21} / P_{t-21-126} - 1`; optional L12/L3 via CLI.
- Volatility: realized vol on the same window; floored (default ε=0.0005) to avoid exploding scores; optionally scaled with a volatility exponent (`--vol-power`, default 1.0; use 0.5 for sqrt-vol).
- Scores: risk-adjusted `S = R / vol^p`, then cross-sectional z-score per date; composite is the average of enabled horizons (default just Z6).
- Ranking: rebalance on the last trading day of each week (`W-FRI`), keep top-N (default 25), write to `data/momentum/top25_signals.csv` with component scores, returns, and vols.

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
