# Handover Notes for Claude Code

## Vision
Kite-Lab aims to build **the world's best momentum portfolio engine** for Indian equities—robust enough for production use, yet
transparent for research. The goal is to deliver a repeatable, data-driven workflow that (1) ingests and cleans high-quality
price/benchmark data, (2) constructs momentum signals with clear, configurable parameters, (3) backtests rebalancing and
risk-controls across market regimes, and (4) produces human-friendly reports and dashboards for decision support.

Efforts to date toward this vision include:
- Establishing reliable data ingestion and caching for NSE universes (NSE500, Next50) with daily and hourly histories to
  minimize drift and accelerate experiments.
- Locking in a baseline 6-month momentum specification (skip window, z-scored returns/volatility, top-25 selections) and
  documenting the methodology to keep research reproducible.
- Building backtesting scripts that explore rebalance cadence, turnover, cooldowns, and volatility triggers, plus grid/Monte
  Carlo runners to probe L6 hyperparameters.
- Adding reporting utilities that consolidate multiple runs into comparison views to spot performance/turnover trade-offs.
- Capturing pending roadmap items (drawdown guards, richer ranking filters, reporting/dashboard UI, CI/regression coverage) to
  guide the next iterations toward a production-ready portfolio engine.

This repository contains **Kite-Lab**, a Python toolkit for Indian stock market analysis built on the Zerodha KiteConnect API. It includes CLI scripts for authentication, data collection, momentum signal construction, backtesting, and reporting, plus early UI design assets.

## Project snapshot
- Purpose: fetch/caches NSE instruments and OHLCV data, compute momentum signals, run portfolio backtests, and produce reports/plots. 【README.md†L1-L93】【README.md†L97-L151】
- Tech stack: Python 3.9+, KiteConnect, pandas, matplotlib, python-dotenv; Node/Vite scaffold under `design_ideas/` for future dashboard work. 【README.md†L93-L111】【design_ideas/README.md†L1-L11】
- Data locations: CSV/Parquet caches under `data/`, `nse500_data/`, `next50_data/`, and hourly variants; benchmarks in `data/benchmarks/`; momentum outputs in `data/momentum/`. (Large data dirs are gitignored.) 【README.md†L17-L54】【runbook.md†L5-L74】

## Key workflows
- **Authentication & instruments:** `scripts/login_and_save_token.py` writes `access_token.txt`; `scripts/cache_instruments.py` refreshes `data/instruments_full.csv`. 【runbook.md†L5-L18】
- **Data refresh:** `scripts/fetch_nse500_history.py` and `scripts/fetch_next50_history.py` build daily + 90-day hourly caches; `scripts/update_prices.py` supports ad-hoc symbol updates. 【runbook.md†L19-L38】
- **Benchmark:** `scripts/compute_benchmark.py` maintains `data/benchmarks/nifty100.csv`. 【runbook.md†L37-L43】
- **Signals & QA:** `scripts/build_momentum_signals.py` generates weekly top-25 rankings with configurable skip/lookbacks; `validate_signals.py` and `compare_signals_baseline.py` perform sanity checks and drift analysis. Methodology is documented in `docs/momentum_signals_methodology.md`. 【runbook.md†L45-L69】【docs/momentum_signals_methodology.md†L1-L43】
- **Backtesting:** `scripts/backtest_momentum.py` simulates portfolios (baseline/cooldown/vol-trigger) with turnover and hit-rate metrics; grid/MC runners (`run_l6_grid.py`, `run_l6_monte_carlo.py`) explore L6 hyperparameters; `run_rebalance_sensitivity.py` sweeps rebalance knobs. 【runbook.md†L71-L108】
- **Reporting:** `scripts/report_backtests.py` merges multiple runs into an HTML comparison. 【runbook.md†L106-L108】
- **Pipelines:** `scripts/run_daily_pipeline.py` chains login → fetch NSE500 → benchmark → signals (supports `--dry-run`). 【runbook.md†L110-L114】

## Documentation & planning
- **Runbook:** quick CLI reference for all scripts/flags. 【runbook.md†L1-L114】
- **Methodology:** momentum signal inputs (skip window, returns/vol, z-scoring) and composite ranking logic. 【docs/momentum_signals_methodology.md†L1-L43】
- **Roadmap:** progress tracked across phases—data layer is complete; momentum engine/risk/reporting tasks remain open (rebalance logic, drawdown guard, indicator toolkit, QA/CI). 【ROADMAP.md†L1-L52】【ROADMAP.md†L53-L96】
- **Phase-2 checklist:** operational to-dos for data freshness, signal verification, backtest features, and reporting upgrades. 【docs/momentum_phase2.md†L1-L32】
- **UI concept:** Vite/React scaffold under `design_ideas/` corresponds to a Stock Analysis Dashboard Figma; run `npm i` then `npm run dev`. 【design_ideas/README.md†L1-L11】

## Working notes for Claude
- Environment: create a Python venv, install deps from README, and keep `.env`, `access_token.txt`, `session.json` out of git (tokens expire daily). 【README.md†L55-L93】【README.md†L113-L120】
- Data hygiene: rerun instrument cache daily; ensure `data/static/nse500_universe.csv` stays authoritative before bulk fetches. Momentum builders expect weekly `W-FRI` scheduling and top-25 outputs. 【README.md†L113-L151】【docs/momentum_signals_methodology.md†L33-L43】
- Experiments: L6 (6-month) momentum is the locked baseline; grid/MC scripts save summaries under `experiments/`. Preserve historical snapshots for drift checks. 【ROADMAP.md†L76-L87】【runbook.md†L71-L101】
- Outstanding focus areas: implement configurable momentum ranking and filters, enforce drawdown guard and risk metrics, expand reporting/dashboard UI, and add regression/CI coverage per roadmap. 【ROADMAP.md†L53-L96】【docs/momentum_phase2.md†L17-L32】
- Handoff tip: keep methodology docs in sync when adjusting parameters; update runbook after adding new scripts or flags to ease future automation.
