# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Kite-Lab is a momentum-based quantitative trading system for Indian equities using the Zerodha KiteConnect API. The system fetches NSE 500 market data, generates volatility-adjusted momentum signals, and backtests weekly-rebalanced portfolios with comprehensive performance analytics.

**Current Status (May 2026):**
- **Production portfolios — all built daily by [scripts/run_daily_pipeline.py](scripts/run_daily_pipeline.py):**
  - **OM25 v3** (Nifty 250) — regime-tilt UC/CR composite, bi-weekly entry, weekly exit
  - **TL25 v3** (NSE 500) — 3-component trend score, bi-weekly entry, weekly rank-exit
  - **L6 v2** (NSE 500) — weekly L6 momentum on new `_momentum_engine` (calibrated within 0.4pp CAGR / 0.01 Sharpe of legacy L6)
  - **COMBO Defensive** (NSE 500) — 50-50 L6 + OM25 dedup with 50% bear-regime overlay, bi-weekly Friday→Monday
- **Manual / research portfolios (not in daily pipeline):**
  - Legacy L6-1W via `run_final_momentum_portfolio.py` (Thursday/Friday rebalance helper, NSE 500 / Nifty 100 / Nifty 250 via `--universe`)
- **Production dashboard deployed** (see below) — syncs all 4 production + 3 alt-universe portfolios

## Production Dashboard

A web-based dashboard provides monitoring and control of the momentum portfolio system.

**Production URLs:**
| Service | URL |
|---------|-----|
| Frontend | https://marketworks.in *(custom domain on Vercel; old `kite-lab.vercel.app` 308-redirects here)* |
| Backend API | https://kite-lab-production.up.railway.app *(Railway service name kept as `kite-lab-production`; move to `api.marketworks.in` is a future task)* |
| API Docs | Disabled in production (available locally with DEBUG=true) |

**Tech Stack:**
- **Frontend:** Next.js 16, TypeScript, Tailwind CSS, shadcn/ui, Recharts
- **Backend:** FastAPI, PostgreSQL, SQLAlchemy 2.0, Alembic
- **Hosting:** Vercel (frontend) + Railway (backend + database)
- **Auth:** Google OAuth with email whitelist

**Key Features:**
- Portfolio view with holdings, P&L, allocation pie chart
- **Open Positions** - Live portfolio with real-time Zerodha prices during market hours
- Performance metrics with equity curves and benchmark comparison
- Trade history with search, filter, and CSV export
- Rebalance workflow (Thursday preview, Friday orders)
- Admin panel with job execution and scheduling
- Real-time streaming via SSE (logs and live prices)

**Dashboard Commands:**
```bash
# Run backend locally
cd kite-api && source .venv/bin/activate
uvicorn app.main:app --reload --port 8000

# Run frontend locally
cd kite-dashboard && npm run dev

# Sync local backtest results to production database
cd kite-api
python scripts/sync_to_production.py --full --data-dir /path/to/kite-lab --database-url "postgresql://..."

# One-time upload of local price data to Railway volume
python scripts/upload_price_data.py --api-url https://kite-lab-production.up.railway.app --token "JWT_TOKEN"
```

**API Endpoints:**
- `/api/portfolio` - Holdings and allocation (backtest data)
- `/api/positions` - **Live positions with real-time prices from Zerodha**
- `/api/positions/stream` - SSE for live price updates
- `/api/metrics` - Performance metrics and equity curves
- `/api/trades` - Trade history with pagination
- `/api/rebalance` - Rebalance workflow and orders
- `/api/jobs` - Job execution and logs
- `/api/system` - Health and token status
- `/api/sync` - CSV to database sync + price data upload
- `/api/auth` - JWT token creation and verification

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
# Full pipeline (login + data + signals + sync + backup)
python scripts/run_daily_pipeline.py --with-login

# This runs (actual pipeline as of May 2026):
#  1. Login to Kite API (optional, with --with-login)
#  2. Preflight: Kite token check (<1s)
#  3. Cache instruments list (symbol → token mapping)
#  4. Fetch NSE 500 + indices data (parallel)
#  5. Apply corporate actions to nse500_data/*.csv (idempotent)
#  6. Update Nifty 100 benchmark
#  7. Prepare shared-state cache (close/trade/benchmark/regime panels)
#  8. Build all 7 portfolios + sync DB — delegates to
#       scripts/update_all_portfolios.py
#       (--skip-fetch --skip-corporate-actions --shared-state-file)
#       Portfolios built in this step:
#         Legacy (run_final_momentum_portfolio.py): nse500, nifty100, nifty250
#         v3:                                       OM25 v3, TL25 v3, L6 v2, COMBO Defensive
#       Sync covers all 7 universes + open_positions + corporate-action
#       adjustments.
#  9. Backup price data to /Users/navdeep/Documents/stock_data/
#
# This delegation to update_all_portfolios.py (added May 2026) keeps the
# daily cron and the dashboard's "Update Portfolios" button in lock-step.
# Before, the cron skipped the legacy 3 universes — the dashboard's
# default nse500 view stayed frozen between manual clicks.
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

### Dashboard Architecture (`kite-api/` and `kite-dashboard/`)

**Backend Services (`kite-api/app/services/`):**
- `portfolio_service.py` - Portfolio data retrieval from CSV (local dev fallback)
- `portfolio_db_service.py` - Portfolio data from PostgreSQL (production)
- `positions_service.py` - Live positions with real-time Zerodha prices
- `metrics_service.py` - Performance calculations (CAGR, Sharpe, DD)
- `trade_service.py` - Trade history queries with pagination
- `rebalance_service.py` - Rebalance workflow (preview, orders)
- `job_service.py` - Job execution with subprocess handling
- `sync_service.py` - CSV to PostgreSQL synchronization
- `quotes_service.py` - Zerodha live price quotes with caching
- `system_service.py` - Health checks, token management, OAuth callback

**Frontend Structure (`kite-dashboard/src/`):**
- `app/(dashboard)/` - Main pages (portfolio, performance, trades, rebalance, admin)
- `components/` - Reusable UI components per feature
- `hooks/` - SWR data fetching hooks
- `lib/` - API client and utilities
- `contexts/` - Universe selector + API auth contexts

**Database Tables:**
- `equity_curve` - Daily portfolio values per universe
- `metrics` - Performance metrics per universe
- `trades` - Trade execution history
- `holdings` - Current position snapshots (backtest)
- `open_positions` - Live portfolio positions (actual holdings)
- `rebalances` - Rebalance action history
- `jobs` - Job execution logs
- `allowed_users` - Email whitelist for dashboard access

**Railway Deployment:**
- Persistent volume mounted at `/data` for price CSVs, tokens, experiments
- `scripts/init_persistent_storage.sh` symlinks `/data` dirs into `/app` at startup
- `scripts/entrypoint.sh` runs storage init as root, then drops to appuser via gosu
- All API endpoints require JWT authentication (except health, login, market-status)

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

### OM25 v3 Production Portfolio (Locked-in May 2026 OOS Retune)
**Location:** `data/om25_v3_portfolios/om25_v3_portfolio_<ts>/` (legacy runs under `data/om25/v3/runs/`)
**Run:** `python scripts/run_om25_v3_portfolio.py --start 2016-01-01`
**Daily pipeline invocation:** `--prices-dir nse500_data --regime-index indices_data/NIFTY_100.csv --start 2020-01-01`

**Parameters:**
- **Universe:** NSE Nifty 250 (250 stocks)
- **Cadence:** Bi-weekly entry (every other Friday) + weekly exit checks
- **Score (bull regime):** 0.5 × pct_rank(UC) + 0.5 × pct_rank(CR)
- **Score (bear regime):** pct_rank(CR) only — defensive tilt
- **Regime signal:** NIFTY 100 close vs 100-day MA, 3-day confirmation hysteresis
- **Lookback:** 252 days, ≥220 obs required
- **Top-N:** 25 stocks, exit-buffer 20 (drop below rank 45)
- **Drawdown stop:** 20% from running peak (weekly check)
- **Sizing:** Equal 1/N, max 7.5%, drift after entry
- **Slippage:** 0.2% (20 bps, OHLC/4 next-day)
- **Initial capital:** ₹1,000,000

**Performance (2016-01-04 to 2026-05-08, 10.4 years):**
- **CAGR:** 39.34%
- **Sharpe ratio:** 1.66 (rf=5%)
- **Max drawdown:** -32.01%
- **Total trades:** 1,414 (729 buys, 685 sells)

**OOS-only validation (2017-2026, 9.3 years):**
- CAGR 44.78% / Sharpe 1.86 / MaxDD -36.6%
- Sub-window Sharpes: 1.57 (2017-19) / 2.10 (2020-22) / 1.80 (2023-26) — all pass

**Use case:**
- Quality-aware momentum with regime-adaptive defensive rotation
- Bull regimes: balanced UC+CR (production identity preserved)
- Bear regimes: rotates to CR-only (low-beta defensive names)
- Always 100% invested — no cash drag

**Full evidence trail:** `tasks/oos_retune_2026/RESULTS.md`

### TL25 v3 Production Portfolio (Locked-in May 2026 OOS Retune)
**Location:** `data/tl25_v3_portfolios/tl25_v3_portfolio_<ts>/`
**Run (production orchestrator):** `python scripts/run_tl25_v3_portfolio.py --start 2020-01-01`
**Report (HTML, research):** `python tasks/trend_leaders/experiments/_tl25_v3_production_report.py`
**Research artifacts:** `tasks/oos_retune_2026/winner_artifacts/tl25_v3_production_*.csv`

**Parameters:**
- **Universe:** NSE 500 (499 stocks)
- **Cadence:** Bi-weekly entry + **weekly rank-exit** + weekly DD-stop checks
- **Score weights:** 0.40 × Persistence + 0.20 × Drawdown-Control + 0.40 × Momentum
- **Persistence:** % of 252d where Close > 100 DMA
- **Drawdown-Control:** (Close / 126d rolling high)² (squared/concave)
- **Momentum:** 63-day return, percentile-ranked among eligible
- **Eligibility:** Close > 200 DMA AND 50 DMA > 200 DMA AND 200 DMA rising over 20d
- **Top-N:** 25 stocks, exit-buffer 20 (drop below rank 45)
- **Drawdown stop:** 20% from peak (weekly check), no 200 DMA exit
- **Sizing:** Equal 1/N, max 7.5%, drift after entry
- **Slippage:** 0.2% (20 bps, OHLC/4 next-day)
- **Regime tilt:** None (single config, distinguishes from OM25 v3)

**Performance (2009-09 to 2026-05, 16.7 years full panel):**
- **CAGR:** 32.73%
- **Sharpe ratio:** 1.40 (rf=5%)
- **Max drawdown:** -39.10%

**OOS-only validation (2017-2026, 9.3 years):**
- CAGR 34.86% / Sharpe 1.53 (rf=0) / MaxDD -39.00%
- Sub-window Sharpes: 1.18 (2017-19) / 2.16 (2020-22) / 1.18 (2023-26) — all pass

**Use case:**
- Pure trend-following with no regime tilt
- Diversifier vs OM25 v3 (different signal: trend quality vs capture asymmetry)
- Different universe (NSE 500 vs Nifty 250) → less stock overlap
- Weekly rank-exit provides modest DD reduction over biweekly-only

**Full evidence trail:** `tasks/oos_retune_2026/RESULTS.md` (TL25 v3 section)

### L6 v2 Production Portfolio (Engine migration, May 2026)
**Location:** `data/l6_v2_portfolios/l6_v2_portfolio_<ts>/`
**Run:** `python scripts/run_l6_v2_portfolio.py --prices-dir nse500_data --start 2020-01-01`
**Engine:** `scripts/_momentum_engine.py` atop `scripts/_clean_engine.run_strategy()`

**Parameters (same as legacy L6, no behavioral change):**
- **Universe:** NSE 500 (499 stocks)
- **Score:** `momentum_6m / max(realized_vol, 0.05)^1.0`, cross-sectional z-score
- **Cadence:** Weekly Thursday signal → Friday OHLC/4 execution
- **Top-N:** 24 stocks, equal-weight 1/24, max 7.5%
- **Min hold:** 8 days, **Exit buffer:** 0 (immediate exit when out of top-24)
- **Slippage:** 0.2% (20 bps), **Skip days:** 0
- **No drawdown stop, no regime overlay** (those live in COMBO Defensive sibling)

**Purpose:** Production migration of legacy L6-1W (the script `run_final_momentum_portfolio.py` continues to run as a Thursday/Friday rebalance helper, but `run_l6_v2_portfolio.py` is the engine going forward). Calibrated within 0.4pp CAGR / 0.01 Sharpe of legacy on identical data (verified during MM-tuning calibration). Performance characteristics match the legacy "NSE 500 L6-1W (min-hold 8d)" row in the benchmark table — see legacy L6 figures above.

**Full evidence trail:** `tasks/MM-tuning/PRODUCTIONIZATION.md`

### COMBO Defensive Portfolio (Locked-in May 2026)
**Location:** `data/combo_defensive_portfolios/combo_defensive_portfolio_<ts>/`
**Run:** `python scripts/run_combo_defensive_portfolio.py --prices-dir nse500_data --start 2020-01-01`
**Spec:** `scripts/combo_defensive.py` (LOCKED config), `tasks/MM-tuning/DD_REDUCTION_RESEARCH.md`

**Parameters:**
- **Universe:** NSE 500
- **Composite:** 50% L6 v2 ranks + 50% OM25 v3 ranks, priority dedup
- **Cadence:** Bi-weekly Friday signal → Monday OHLC/4 execution
- **Regime overlay:** NIFTY 100 close vs 100-DMA, 3-day confirmation, **50% allocation cut in bear regime**
- **Top-N / Sizing / Slippage:** inherits from L6 / OM25 component specs

**Purpose:** Drawdown-reduction sibling product. Combines L6 momentum capture with OM25's regime-aware defensive rotation; the 50% bear-regime cut sacrifices some upside for materially lower max DD.

**Full evidence trail:** `tasks/MM-tuning/DD_REDUCTION_RESEARCH.md`

### Walk-Forward Robustness Study (May 2026)

Independent stress test of locked OM25 v3 and TL25 v3 across 13 rolling
3y-IS / 1y-OOS windows × 3 universes = **78 OOS validations**. Built as a
robustness check, never a re-tune.

**Headline:** Both locked v3 configs achieve **84.6% pass rate** (Sharpe ≥ 0.7
floor) on their production universes. TL25 v3 also holds 84.6% on Nifty 250
(more universe-robust than OM25). Three windows fail universally — W06
(2018-19 IL&FS), W12 (2025 small-cap correction), W13 (partial 2025-26) — these
are regime tails not fixable via tuning.

**Key finding:** IS Sharpe ranking carries little predictive signal at 3y
windows (mean gap +0.37 for OM25, **−0.08 for TL25**). The locked v3 baselines
match or beat IS-best challengers on average. **Don't re-tune.**

**Compute:** ~19 min total local wall-clock (vs ~10 hr in the original plan).
Speedup from load-once orchestrator pattern + multiprocessing —
`scripts/run_walk_forward.py` calls `_clean_engine.run_strategy()` directly
with pre-loaded panels (~1s per backtest).

**Files:**
- `scripts/run_walk_forward.py` — orchestrator (Phases 0/1/2)
- `scripts/walk_forward_report.py` — Phase 3 HTML/markdown report
- `tasks/walk_forward/PLAN.md` — methodology + scope changes
- `tasks/walk_forward/RESULTS.md` — findings + recommendation
- `tasks/walk_forward/PROGRESS.md` — execution log
- `reports/walk_forward_summary.html` — visual report (5 charts + tables)

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
1. Logs in to Kite API (with --with-login)
2. Caches instruments list
3. Fetches latest NSE 500 + indices data (parallel)
4. Updates Nifty 100 benchmark
5. Builds momentum signals
6. Syncs data to database
7. Backs up to external location

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
- `main` - Stable production code (deployed to Railway + Vercel)
- `refinement` - Current repo cleanup and polish

**Legacy branches** (kept for reference, not actively developed):
- Various experiment branches (`momentum-volume`, `volatility-targeting`, `nifty100-portfolio`, etc.)

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

## Performance Benchmarks

### Momentum L6-1W family (2020-2026, IS-only tuning)

| Portfolio | CAGR | Max DD | Sharpe | Turnover | Use Case |
|-----------|------|--------|--------|----------|----------|
| **NSE 500 L6-1W (min-hold 8d)** | 59.4% | -30.0% | 1.92 | 123% | Growth investors |
| **NSE 500 L6-1W (no min-hold)** | 56.2% | -27.7% | 1.87 | 122% | Baseline reference |
| **Nifty 100 L6-1W** | 44.86% | -19.11% | 1.69 | 58% | Risk-averse |
| **Nifty 100 L9-2W** | 38.95% | -25.22% | 1.45 | 23% | Not recommended |
| **Nifty 100 Index** | ~15% | -20% | ~0.7 | 0% | Buy & hold |

### OOS-validated v3 strategies (2017-2026 OOS, tuned on 2009-2016)

| Portfolio | OOS CAGR | OOS Max DD | OOS Sharpe | Signal | Use Case |
|-----------|---------|------------|-----------|--------|----------|
| **OM25 v3** (Nifty 250) | 44.78% | -36.6% | 1.86 (rf=0) | Capture asymmetry + regime tilt | Quality momentum, regime-adaptive |
| **TL25 v3** (NSE 500) | 34.86% | -39.0% | 1.53 (rf=0) | 3-component trend quality | Pure trend-following, diversifier |

**Key insight:** Momentum L6-1W is IS-tuned for 2020-2026 (no OOS validation). OM25 v3 and TL25 v3 are tuned on 2009-2016 and OOS-validated on 2017-2026 — pick these for "timeless" robustness; pick L6 for highest recent CAGR.

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

**Last updated:** May 2026 (pipeline-improvements branch)
**Production portfolios (built daily):** OM25 v3 (Nifty 250), TL25 v3 (NSE 500), L6 v2 (NSE 500), COMBO Defensive (NSE 500)
**Manual / alt portfolios:** Legacy L6-1W via `run_final_momentum_portfolio.py` (NSE 500 / Nifty 100 / Nifty 250)
**Dashboard:** https://marketworks.in *(formerly kite-lab.vercel.app — 308-redirects to apex)*
**Backend:** https://kite-lab-production.up.railway.app (persistent volume at /data)
**Status:** Production-ready with full security hardening, DB sync pipeline, and persistent storage. Active refactor: see `tasks/pipeline_improvements/PLAN.md`.
