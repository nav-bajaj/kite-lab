# Momentum Engine (Phase 2) To-Do

This document tracks the work required to deliver the weekly momentum portfolio for the NSE 500 universe with a Nifty 100 benchmark.

## Data Preparation
- [ ] Ensure `scripts/compute_benchmark.py` is run daily to keep `data/benchmarks/nifty100.csv` current
- [ ] Maintain NSE 500 daily caches via `scripts/fetch_nse500_history.py`
- [ ] Add validation step comparing benchmark returns against external references (spot checks)

## Signal Construction
- [ ] Verify `scripts/build_momentum_signals.py` produces expected top-25 lists (check sample weeks)
- [ ] Experiment with lookback parameters (e.g., 12M/6M) and alternate weighting schemes
- [ ] Integrate technical indicators (EMA slope, RSI) as optional filters once the toolkit is ready
- [ ] Store historical rankings and metadata for auditability

## Backtesting Engine
- [ ] Implement weekly rebalance simulator (equal-weight and volatility-weight options)
- [ ] Model transaction costs and slippage assumptions
- [ ] Enforce 25% max drawdown guard (shift to cash when triggered)
- [ ] Record turnover, exposure, and tracking error relative to Nifty 100

## Reporting & QA
- [ ] Generate benchmark vs strategy performance charts and tables
- [ ] Add unit tests for ranking logic, rebalance outputs, and drawdown enforcement
- [ ] Create automated checks for missing data or extreme returns in the momentum signal file
- [ ] Document runbooks for data refresh, signal generation, and backtest execution

### Reporting Enhancements
- [ ] Replace the placeholder HTML report with a robust dashboard (sections for performance summary, peaks/lows, best/worst contributors, turnover)
- [ ] Integrate a richer charting library (matplotlib already available; consider Plotly or Altair for interactive visuals)
- [ ] Catalog required visuals: normalized equity curves, rolling drawdown, rolling returns, contribution bar charts, cumulative turnover
- [ ] Add tables highlighting top/bottom stocks per period, biggest gainers/losers, and streaks
- [ ] Ensure reports capture metadata (strategy params, run timestamp, data range) for auditability

Update this checklist as tasks move from planning to completion.
