# Runbook

Quick reference for the CLI scripts in this repo. Assumes `.env` has `API_KEY`, `API_SECRET`, `REDIRECT_URI`, and you have a fresh `access_token.txt` (run login first).

## Authentication & instruments
- `python scripts/login_and_save_token.py`
  - Opens browser for Kite login; auto-writes `access_token.txt` and `session.json`.
  - No flags.
- `python scripts/cache_instruments.py`
  - Refreshes `data/instruments_full.csv` from Kite instruments API.
  - No flags (run after login).

## Data collection
- `python scripts/fetch_nse500_history.py`
  - Pulls daily + last-90d hourly OHLC for NSE 500 into `nse500_data/` and `nse500_data_hourly/`.
  - No flags.
- `python scripts/fetch_next50_history.py`
  - Same as above for Nifty Next 50; uses `ind_niftynext50list.csv`.
  - No flags.
- `python scripts/update_prices.py --symbols INFY TCS --daily-dir nse500_data --interval day`
  - Incrementally updates given symbols from 2020-01-01 to today.
  - Flags: `--symbols` (required, space-separated), `--daily-dir` (default `nse500_data`), `--interval` (default `day`, supports intraday like `60minute`).
- `python scripts/compute_benchmark.py`
  - Updates `data/benchmarks/nifty100.csv` with close/return/cumret series for NIFTY 100.
  - No flags.

## Signal building & QA
- `python scripts/build_momentum_signals.py --prices-dir nse500_data --output data/momentum/top25_signals.csv --skip-days 21 --lookbacks 12 6 3 --top-n 25 [--universe-file path.csv]`
  - Builds weekly momentum rankings; lookbacks are months mapped to trading days.
  - Flags: `--prices-dir` (default `nse500_data`), `--output` (default `data/momentum/top25_signals.csv`), `--skip-days` (default 21), `--lookbacks` (choices 3/6/12, default `12 6 3`), `--top-n` (default 25), `--universe-file` (CSV with `Symbol` column to filter universe).
- `python scripts/validate_signals.py --signals data/momentum/top25_signals.csv --top-n 25`
  - Checks ranking file for duplicates, excess rows per date, missing scores.
- `python scripts/compare_signals_baseline.py --baseline data/momentum/signals_L6_noskip.csv --candidate data/momentum/top25_signals.csv --top-n 25`
  - Compares a candidate signal file to a frozen baseline snapshot; reports overlap and rank drift, optionally writes a CSV summary.
  - Flags: `--signals` (default `data/momentum/top25_signals.csv`), `--top-n` (default 25).

## Backtesting & reporting
- `python scripts/backtest_momentum.py --prices-dir nse500_data --signals data/momentum/top25_signals.csv --benchmark data/benchmarks/nifty100.csv --output-dir data/backtests --initial-capital 1000000 --top-n 25 --slippage 0.002 --scenario {baseline,cooldown,vol_trigger} [--cooldown-weeks 1] [--staged-step 0.25] [--vol-lookback 63] [--target-vol 0.15] [--exit-buffer 10] [--pnl-hold-threshold 0.05]`
  - Runs a momentum portfolio backtest with optional drawdown cooldown or volatility targeting. `--exit-buffer` adds hysteresis to exits (requires signals containing ranks up to `top_n + buffer`), and `--pnl-hold-threshold` defers exits while unrealized PnL exceeds the threshold.
  - Outputs include equity/trade/turnover CSVs plus `momentum_metrics.csv` (CAGR, drawdown depth/duration, turnover, cost drag, holding period, hit-rate by quintile, trade counts and avg trades per week/month/year).
- (removed) `run_backtest_scenarios.py` — superseded by the L6 grid/MC runners.
- (removed) `run_monte_carlo.py` — superseded by the L6-only Monte Carlo runner.
- `python scripts/run_l6_monte_carlo.py --runs 20 --sample-size 250 --topn-min 20 --topn-max 30 --skip-days 0 10 21 --exit-buffers 0 5 10 --pnl-hold 0.05 0.1 --vol-floor 0.0005 0.001 [--scenarios baseline hyst pnl_hold] [--dry-run]`
  - L6-only Monte Carlo: samples skip window, exit buffer, PnL-hold threshold, top-N, and volatility floor; builds sampled-universe signals and runs baseline vs hysteresis vs PnL-hold backtests. Writes `summary.csv` and `report.html` under `experiments/l6_mc_*`.
  - Use `--scenarios` to run only specific scenarios (e.g., `--scenarios hyst` for hysteresis only).
- `python scripts/run_l6_monte_carlo_no_volfloor.py --runs 20 --sample-size 250 --topn-min 20 --topn-max 30 --skip-days 0 10 21 --exit-buffers 0 5 10 --pnl-hold 0.05 0.1 [--scenarios baseline hyst pnl_hold] [--dry-run]`
  - Same as above but uses a fixed vol-floor (0.0005) to isolate impact of other parameters. Results saved under `experiments/l6_mc_no_volfloor_*`.
- `python scripts/run_l6_grid.py [--skip-days 21 10 0] [--vol-floor 0.0005 0.001] [--top-n 25 20] [--exit-buffer 0 5] [--scenarios baseline cooldown] [--limit 10]`
  - Grid search focused on L6 (6-month) signals; varies skip window, volatility floor, top-N, exit buffer, and scenario. Saves signals, backtests, and `summary.csv` under `experiments/l6_grid_*`.
- `python scripts/run_rebalance_sensitivity.py --signals data/momentum/top25_signals.csv --exit-buffers 0 5 10 --pnl-hold 0.05 0.1 --cooldown-weeks 1 2 --staged-steps 0.25 0.5 --vol-targets 0.15 0.2 --vol-lookbacks 63`
  - Sweeps rebalance knobs (exit buffer, PnL-hold, cooldown staging, vol-trigger targets) for baseline/cooldown/vol-trigger scenarios. Saves ranked `summary.csv` and `report.html` under `experiments/rebalance_*`.
- `python scripts/report_backtests.py --runs data/backtests/run1 data/backtests/run2 --output data/backtests/report.html`
  - Merges multiple backtest folders into a single HTML report (charts require matplotlib installed).
- (removed) `run_churn_experiments.py` — churn variants now covered via `run_l6_monte_carlo.py` (baseline / hysteresis / PnL-hold).

## Utilities
- `python scripts/run_daily_pipeline.py [--with-login] [--dry-run]`
  - Chains login (optional) → fetch NSE500 → compute benchmark → build signals.
- `python scripts/sample_universe.py --source data/static/nse500_universe.csv --size 250 --seed 42 --output data/static/sample.csv`
  - Samples a subset of the NSE 500 list for experiments.
- `python scripts/fetch_history_and_analyse.py`
  - One-off demo for a single symbol; edit constants inside for symbol/dates/interval. Writes CSV and MA/cumret plots.
