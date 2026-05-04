# Phase 5: Orchestrator Script

**File:** `scripts/run_trend_leaders_portfolio.py`

**Status:** Done

**Depends on:** Phases 1-4

---

## Objective

Create a single orchestrator script that runs the full pipeline: signal generation, all backtest variants, and report generation. Follows the pattern of `scripts/run_final_momentum_portfolio.py`.

---

## Tasks

- [ ] **5.1** Create orchestrator with CLI arguments (universe, top-n, variants to run, etc.)
- [ ] **5.2** Implement `UNIVERSE_DEFAULTS` dictionary (initially NSE 500 only)
- [ ] **5.3** Wire signal generation step (calls `build_trend_leaders_signals.py` logic)
- [ ] **5.4** Wire backtest execution for selected variants
- [ ] **5.5** Wire report generation
- [ ] **5.6** Wire momentum comparison (if momentum equity data available)
- [ ] **5.7** Add summary output to console (key metrics per variant)
- [ ] **5.8** Test full end-to-end pipeline

---

## CLI Interface

```bash
# Run full pipeline (all variants)
python scripts/run_trend_leaders_portfolio.py

# Run specific variant only
python scripts/run_trend_leaders_portfolio.py --variant base

# Run with different parameters
python scripts/run_trend_leaders_portfolio.py --top-n 25 --max-weight 0.06

# Skip report generation (faster iteration)
python scripts/run_trend_leaders_portfolio.py --no-report

# Run with fresh data (if data pipeline is integrated)
python scripts/run_trend_leaders_portfolio.py --with-data
```

---

## Pipeline Steps

```
1. Load universe (data/static/nse500_universe.csv)
2. Build composite signals → data/trend_leaders/signals/trend_leaders_signals.csv
3. Build persistence-only signals → data/trend_leaders/signals/persistence_only_signals.csv
4. Run Variant 1: Base → data/trend_leaders/backtests/base/
5. Run Variant 2: Market Filter → data/trend_leaders/backtests/market_filter/
6. Run Variant 3: Monthly Only → data/trend_leaders/backtests/monthly_only/
7. Run Variant 4: Persistence Only → data/trend_leaders/backtests/persistence_only/
8. Generate strategy report → data/trend_leaders/reports/trend_leaders_20_report.html
9. Generate momentum comparison → data/trend_leaders/reports/comparison_vs_momentum.html
10. Print summary table to console
```

---

## Console Summary Output

```
=== Trend Leaders 20 — Backtest Summary ===

Date range: 2020-08-03 to 2026-05-02

| Variant          | CAGR    | Max DD  | Sharpe | Sortino | Turnover | Avg Cash |
|------------------|---------|---------|--------|---------|----------|----------|
| Base             |         |         |        |         |          |          |
| Market Filter    |         |         |        |         |          |          |
| Monthly Only     |         |         |        |         |          |          |
| Persistence Only |         |         |        |         |          |          |
| Momentum (ref)   | 59.4%   | -30.0%  | 1.92   |         | 123%     | 0%       |
| Benchmark        | ~15%    | ~-20%   | ~0.7   |         | 0%       | 0%       |

Correlation with momentum: X.XX (daily), X.XX (monthly)
Reports saved to: data/trend_leaders/reports/
```

---

## Future Extensions

- `--universe nifty100` / `--universe nifty250` support
- Integration with daily pipeline (`run_daily_pipeline.py`)
- Dashboard sync (like momentum strategy's `sync_to_production.py`)
- Thursday/Friday workflow (Thursday preview, Friday signals)
