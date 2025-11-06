# Momentum Portfolio Roadmap

This document tracks the incremental build-out of the NSE 500 momentum strategy with a Nifty 100 benchmark. Each section lists the deliverables and key validation steps needed before moving onward.

## Phase 0 — Foundations
- [x] Check in authoritative NSE 500 universe CSV under `data/static/`
- [x] Add integrity tests (row count, checksum) for universe files
- [x] Confirm Nifty 100 index symbol/token is present in `data/instruments_full.csv`

## Phase 1 — Instrument & Data Layer
- [x] Implement `data_pipeline/symbol_resolver.py` to map symbols ➝ metadata/token (with caching)
- [x] Build `data_pipeline/price_client.py` wrapper for Kite historical API (handles incremental fetch, timezone normalization)
- [x] Create `data_pipeline/storage.py` to persist prices as partitioned Parquet/CSV (`data/prices/{symbol}/{frequency}.parquet`)
- [x] Script `scripts/update_prices.py` to refresh daily & weekly bars for NSE 500 and benchmark
- [x] Add QA checks: missing trading days, zero/negative prices, extreme gaps
- [x] Unit tests covering resolver, client error paths, and incremental merge logic

## Phase 2 — Momentum Engine
- [ ] Implement configurable momentum ranking (e.g., 12M/6M lookback with 1M skip, volatility-adjusted scores)
- [ ] Introduce liquidity filters and tradability checks
- [ ] Develop weekly rebalance scheduler based on Indian trading calendar
- [ ] Produce holdings selection limited to top 20 names with turnover reporting
- [ ] Integration test using fixture data to validate rankings & rebalance output

## Phase 3 — Risk Management & Benchmarking
- [ ] Simulate equity curve with 25% max drawdown enforcement (move to cash or reduce exposure)
- [ ] Capture benchmark comparison metrics (active return, information ratio, tracking error)
- [ ] Support configurable transaction costs & slippage placeholders
- [ ] Generate performance reports (tables + charts) saved to `reports/`
- [ ] Tests confirming drawdown guard triggers and benchmark stats correctness

## Phase 3.5 — Technical Analysis Toolkit
- [ ] Implement modular library for common indicators (EMA, RSI, MACD, ATR)
- [ ] Provide vectorized functions compatible with pandas & backtest engine
- [ ] Allow indicator configuration via strategy parameters (lookbacks, thresholds)
- [ ] Add unit tests comparing against reference calculations (e.g., TA-Lib samples)
- [ ] Integrate selected indicators into momentum ranking experiments (e.g., filter by RSI, volatility measures)

## Phase 4 — Validation & Tooling
- [ ] End-to-end regression test (mini backtest) covering data load → rebalance → reporting
- [ ] CLI commands or Make targets to run data QA, backtests, and report generation
- [ ] Documentation updates (README usage, configuration guides)
- [ ] Optional: CI integration to run tests and linting on push

## Phase 5 — Enhancements (Future Ideas)
- [ ] Sector/industry exposure limits
- [ ] Position sizing via volatility targeting or risk parity overlay
- [ ] Multi-frequency momentum composites (daily vs. weekly inputs)
- [ ] Live signal export connectors (broker API, Slack alerts)

Use this checklist to drive future sessions. Update statuses and add detail as work progresses.
