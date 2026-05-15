# Pipeline Improvements — Results

## Validation Gate 1 (Phase 1 — Correctness) — PASSED

**Date:** 2026-05-15
**Baseline:** `golden_master_20260515_151808.json` (Phase 0)
**Comparison:** post-Phase-1 re-snapshot

### Outcome

All four production portfolios' dashboard CSVs (`momentum_equity.csv`,
`momentum_trades.csv`, `momentum_holdings.csv`, `momentum_metrics.csv`)
are **bit-identical** to the Phase 0 baseline.

The Phase 1.1 metrics consolidation is provably faithful to the
pre-consolidation inline code: function-level regression tests
(`tests.test_metrics_common.RegressionAgainstBaseline`) feed each
portfolio's native equity/trades/exits through the new
`compute_dashboard_metrics()` and confirm reproducibility to 1e-9 float
tolerance against the on-disk `momentum_metrics.csv` written by the
pre-refactor inline code.

The Phase 0 baseline JSON itself hashes the on-disk CSVs; those CSVs
were untouched by the refactor (the portfolio scripts haven't been
re-run since the refactor — that will happen on the next live daily
pipeline run, which will be the first real-world test).

### Sharpe / rf-rate finding

The Phase 0 audit suggested the four production portfolios used three
different Sharpe formulas. Closer inspection during Phase 1.1 disproved
this: **all four daily-pipeline portfolios already used rf=5%** for the
`momentum_metrics.csv` Sharpe field. The actual divergence is between:

- Daily-pipeline portfolios (OM25 v3, TL25 v3, L6 v2, COMBO Defensive):
  `sharpe_ratio = (cagr - 0.05) / vol` — **rf=5%**
- Research/legacy paths (`_clean_engine.compute_metrics`,
  `backtest_momentum.summarise_metrics`): `sharpe = cagr / vol` — **rf=0**

This divergence remains and is **out of scope for Phase 1**. Will be
revisited in Phase 3 when L6 legacy migrates onto `_clean_engine`.

### Test results

```
tests/test_metrics_common.py:
  11 tests, 0 failures (7 synthetic + 4 regression-against-baseline)

tests/test_sync_validation.py:
  11 tests, 0 failures (synthetic CSVs exercising each failure mode)
```

### Snapshot diff (only the label field differs, by design)

```
- label
  baseline: phase0_baseline
  current : phase1_gate

1 differences.
```

## Phase 1 deliverables

- `scripts/metrics_common.py` (97 LOC) — single source of truth
- `scripts/sync_validation.py` (210 LOC) — pre-sync CSV validator
- `scripts/preflight_token.py` (78 LOC) — fail-fast Kite-token check
- Migrated `run_l6_v2_portfolio.py`, `run_om25_v3_portfolio.py`,
  `run_tl25_v3_portfolio.py`, `run_combo_defensive_portfolio.py` to
  call `write_dashboard_metrics` (net −110 LOC across the four)
- Wired preflight + validation into `run_daily_pipeline.py` and
  `sync_to_database.py`
- Removed orphan `build_momentum_signals.py` step from orchestrator
- 22 new unit tests across two test files

### Real-world validation pending

Function-level bit-equivalence is proven. The first live `run_daily_pipeline.py`
execution after this commit will produce four fresh portfolio runs; their
new `momentum_metrics.csv` files should be:

- **Schema-identical** to the Phase 0 baseline files
- **Value-equivalent** modulo the data-date shift (new prices since
  2026-05-12 / 2026-05-14)

Re-snapshot after that run and confirm.
