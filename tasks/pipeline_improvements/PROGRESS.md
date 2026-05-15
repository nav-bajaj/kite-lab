# Daily Pipeline Improvements — Progress Log

## 2026-05-15 — Phase 0 kickoff

- Branched off main as `pipeline-improvements`.
- Ran three-agent audit (pipeline orchestration, portfolio scripts, data
  topology). Findings consolidated in PLAN.md.
- Confirmed via grep that `scripts/build_momentum_signals.py` step is
  effectively orphaned within the daily pipeline — its output
  `data/momentum/top25_signals.csv` (last modified 2026-05-12) has no
  pipeline-downstream readers, only ad-hoc research tools.
- Verified actual portfolio output directory conventions:
  - `data/om25_v3_portfolios/om25_v3_portfolio_<ts>/`
    (legacy runs still in `data/om25/v3/runs/<ts>/`)
  - `data/tl25_v3_portfolios/tl25_v3_portfolio_<ts>/`
  - `data/l6_v2_portfolios/l6_v2_portfolio_<ts>/`
  - `data/combo_defensive_portfolios/combo_defensive_portfolio_<ts>/`
- Verified `scripts/sync_to_database.py` and `kite-api/app/services/sync_service.py`
  sync these 7 universes:
  `nse500, nifty100, nifty250, om25_v3, tl25_v3, l6_v2, combo_defensive`.
- Updated CLAUDE.md: status header, daily pipeline comment, OM25 v3 location,
  added L6 v2 + COMBO Defensive sections, updated footer.
- Created `tasks/pipeline_improvements/PLAN.md`.

### Open questions awaiting user decision
- Remove `build_momentum_signals.py` step from daily pipeline?
- Migrate `run_final_momentum_portfolio.py` to `_clean_engine` in Phase 3?

- Built `scripts/snapshot_pipeline_outputs.py` (deterministic SHA256 over
  normalized DataFrames, 10dp float rounding; ignores `captured_at` /
  `run_mtime` / `size_bytes` in diffs).
- Captured **Phase 0 baseline** at
  `tasks/pipeline_improvements/golden_master_20260515_151808.json`.
  Row counts:
  - om25_v3: equity=1326, trades=868, holdings=25
  - tl25_v3: equity=1354, trades=1737, holdings=21
  - l6_v2: equity=1449, trades=2207, holdings=24
  - combo_defensive: equity=1443, trades=1925, holdings=5
  - legacy signals: 7650 rows
- Verified **idempotency** by re-snapshotting against the latest run dirs
  and diffing — zero content differences (only the optional `label` tag
  diverged on the second run, as expected).

### Phase 0 complete

All three Phase 0 deliverables done. Ready to begin Phase 1 (correctness)
pending user confirm on the two open items in PLAN.md (orphan-step removal,
legacy L6 script migration scope).

### Next
- Get user decision on the two open items.
- Phase 1.1: build `scripts/metrics_common.py` and unify Sharpe definitions.
- Phase 1.2: transactional safety on `sync_to_database.py`.
- Phase 1.3: token-expiry preflight in orchestrator.
- Re-snapshot at Validation Gate 1.

## 2026-05-15 — Phase 1 complete

User decisions received: remove orphan step, scope Phase 3 to include
legacy L6 migration.

- **Orphan removal:** `build_momentum_signals.py` step deleted from
  `run_daily_pipeline.py` (with explanatory comment pointing at PLAN.md).
  The script itself is preserved for manual / research use.

- **Phase 1.1 — unified metrics:**
  - Built `scripts/metrics_common.py` with `compute_dashboard_metrics()`
    and `write_dashboard_metrics()` (97 LOC).
  - Refactored all four production portfolio scripts to use it;
    ~30 LOC of inline-metrics deleted per file, ~110 LOC total.
  - Notable correction to earlier audit: all four daily-pipeline
    portfolios already used rf=5% consistently; the Sharpe divergence
    is only between daily-pipeline (rf=5%) and the
    research/legacy engines (rf=0). Documented in RESULTS.md.
  - Added 11 unit tests (7 synthetic + 4 regression-against-baseline).
    Regression tests prove function-level bit-equivalence with the
    pre-consolidation inline implementations.

- **Phase 1.2 — pre-sync CSV validation:**
  - Built `scripts/sync_validation.py` (210 LOC) checking file presence,
    required columns, equity monotonicity, non-positive values, bad
    trade sides, positive max-drawdown (impossible), non-finite Sharpe,
    schema-correctness on the metrics row.
  - Wired into `sync_to_database.py` with `--validate-only` and
    `--skip-validation` flags; failure aborts with exit-code 2 before
    any DB write.
  - Scoped to the four daily-pipeline portfolios only; the legacy
    nse500/nifty100/nifty250 outputs have a different metrics schema
    (no `sharpe_ratio` column) and remain out of scope.
  - Added 11 unit tests using a tempdir + patched RUN_DIR_GLOBS to
    exercise each failure mode.

- **Phase 1.3 — token-expiry preflight:**
  - Built `scripts/preflight_token.py` — cheapest possible KiteConnect
    call (`kite.profile()`), fails in <1s with a clear "re-run with
    --with-login" message if the token is missing/expired.
  - Wired into `run_daily_pipeline.py` immediately after the optional
    login step, before instruments cache + parallel fetch.
  - Verified end-to-end: the current real-world expired token is
    correctly rejected with the right exit code.

- **Validation Gate 1 — PASSED.**
  - Re-snapshot diffed against Phase 0 baseline: only the `label` field
    differs (by design). All four portfolios' equity/trades/holdings/metrics
    hashes are bit-identical. The portfolio scripts haven't been re-run
    since the refactor, so the on-disk CSVs are unchanged — the real
    end-to-end validation happens at the next live `run_daily_pipeline.py`
    execution.
  - All 22 unit tests pass.

### Phase 1 deliverables (commit-ready)

- `scripts/metrics_common.py`, `scripts/sync_validation.py`,
  `scripts/preflight_token.py` (new modules)
- `scripts/run_l6_v2_portfolio.py`, `scripts/run_om25_v3_portfolio.py`,
  `scripts/run_tl25_v3_portfolio.py`,
  `scripts/run_combo_defensive_portfolio.py` (migrated to metrics_common)
- `scripts/run_daily_pipeline.py` (orphan removal + preflight wiring)
- `scripts/sync_to_database.py` (validation wiring + new flags)
- `tests/test_metrics_common.py`, `tests/test_sync_validation.py` (new tests)
- `tasks/pipeline_improvements/RESULTS.md` (Validation Gate 1 record)

### Next — Phase 2 (Performance)

Awaiting user go-ahead. First step: refactor `run_daily_pipeline.py` to
call Python entry points instead of subprocess-launching scripts, so the
price panel / benchmark / regime can be loaded once and shared across all
four portfolio builds. Target wall-clock improvement: ≥30s.
