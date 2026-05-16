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

## 2026-05-15 — Phase 2 complete

User decisions received:
- Performance first, then redundancy (Phase 2 → Phase 2.5)
- Postgres backups land in `~/Documents/stock_data/db_backups/`
- Cloud target is Google Drive

User also raised three concerns that turned out to already be correctly
handled by existing code:
- **Schedule 7am IST Mon-Fri:** correctly configured in
  `kite-api/app/scheduler/tasks.py:23-26` with scheduler tz=Asia/Kolkata.
- **Incremental fetch:** already incremental in
  `scripts/history_utils.py:178-195` (reads existing CSV last-date,
  fetches only newer; skips API call if up-to-date).
- **Incremental backup:** already incremental by default in
  `scripts/sync_data_backup.py:172` (`--full` is an explicit override).

Documented as the "Audit corrections" block at the top of PLAN.md.

### Phase 2.1 — orchestrator-level data load

Chose the subprocess-preserving pickle-cache approach over going in-process
to keep the diff small and preserve crash isolation between portfolios.

- Built `scripts/pipeline_core.py` with:
  - `PipelineState` frozen dataclass (close_panel, trade_panel, benchmark,
    optional regime_panel, provenance fields, schema_version=1)
  - `load_shared_state()` — reads all panels from disk in one pass
  - `dump_to_cache()` / `load_from_cache()` — pickle round-trip with
    schema-version + type guards
  - `describe()` — one-line summary for logs
  - CLI: `python scripts/pipeline_core.py --prices-dir ... --benchmark
    ... --regime-index ... --output ...` writes the cache
- Fixed a pickle-qualname bug discovered in testing: the CLI block now
  re-imports `PipelineState` through `scripts.pipeline_core` instead of
  using the local `__main__` symbol, so other processes can unpickle.

Each of the four production portfolio scripts (`run_om25_v3_portfolio`,
`run_tl25_v3_portfolio`, `run_l6_v2_portfolio`,
`run_combo_defensive_portfolio`) now accepts `--shared-state-file <path>`.
When set, they:

- Load `close_panel`, `trade_panel`, `benchmark` from the cache instead
  of calling `load_price_panels` and `load_benchmark` on disk.
- Reindex `cached_regime` to the local calendar for OM25/COMBO,
  bypassing the in-script `build_regime_panel_confirmed` calls.
- Fall back to the original on-disk path when the flag is absent
  (standalone CLI behaviour preserved).

### Phase 2.3 — orchestrator wiring + timing

`scripts/run_daily_pipeline.py` was restructured:

- New "Prepare shared-state cache" step runs `pipeline_core.py` after
  benchmark and corporate-action steps, writing to
  `/tmp/pipeline_state_<ts>.pkl`. `atexit` cleans up the file.
- The four portfolio commands now have `--shared-state-file` appended.
- New `--no-shared-state` flag falls back to per-portfolio loads (escape
  hatch).
- End-of-run timing table prints OK/FAIL + duration per step.

### Validation Gate 2 — PASSED

Ran each portfolio twice (with and without `--shared-state-file`) on
identical inputs. All four dashboard CSVs (`momentum_equity.csv`,
`momentum_trades.csv`, `momentum_holdings.csv`, `momentum_metrics.csv`)
hashed byte-identically for every portfolio.

Re-snapshot vs Phase 0 baseline: only the `label` field differs.

Wall-clock impact was smaller than projected:
- TL25 without cache: 1.8s
- TL25 with cache: 0.9s
- Savings/portfolio: ~0.9s
- Net pipeline savings: ~2.7s (not the projected 30s)

Reason: `load_price_panels` is already fast on a modern SSD; the
PLAN.md projection of 4-8s/load was too high. The cache is still
worth keeping for hygiene, future scale-ups, and the unified plumbing
it provides for Phase 3.

### Phase 2 deliverables

- `scripts/pipeline_core.py` (new, 177 LOC)
- `scripts/run_daily_pipeline.py` (rewired)
- 4 portfolio scripts (each gained `--shared-state-file` + 10-15 LOC)
- `tests/test_pipeline_core.py` (5 new tests)
- Updated `RESULTS.md` with Validation Gate 2 record
- Updated `PLAN.md` with audit-correction block

### Next — Phase 2.5 (Data redundancy & resilience)

Awaiting go-ahead. Five sub-items per PLAN.md:
1. `scripts/check_schedule.py` — runtime verification of the
   APScheduler 7am-IST job, with optional Postgres-jobstore migration.
2. `scripts/backup_database.py` — pg_dump with 14d/12w/12m rotation,
   landing in `~/Documents/stock_data/db_backups/`.
3. Critical-data git audit (`CRITICAL_DATA.md`).
4. Cloud upload to Google Drive (uses existing OAuth).
5. `RECOVERY.md` disaster-recovery runbook with dry-run verification.

## 2026-05-16 — Phase 2.5 in progress

### Phase 2.5.1 — skipped per operator decision

Operator confirmed scheduling is working in production (live 7am IST
run completed cleanly on 2026-05-15). No script needed.

### Phase 2.5.2 — Postgres backup — DONE

- `scripts/backup_database.py`: SQLAlchemy + pandas (no pg_dump dep),
  dumps each of the 10 known tables to CSV.gz inside one timestamped
  tarball. 14d + 12w + 12m rotation gated on smoke-test success.
- `scripts/restore_database.py` companion with `--dry-run` and
  `--truncate` modes.
- 9 new unit tests for rotation + parse_ts. All 36 pipeline-improvements
  tests pass.
- First live --dry-run against Railway initially hit
  `postgres.railway.internal` (the internal hostname). Fixed by adding
  a fail-fast probe in `_engine_from_env` with a Railway-specific
  error pointing at `DATABASE_PUBLIC_URL`. Second --dry-run via the
  public proxy succeeded: 31,537 rows captured across 10 tables.
- First real backup written and smoke-tested OK. Offsite-on-Mac is
  now closed.

### Phase 2.5.3 — Critical-data audit — DONE

- `CRITICAL_DATA.md` inventories what's replaceable vs irreplaceable.
- Confirmed all locked strategy configs + universe CSVs + corporate
  actions are git-tracked.
- Committed `data/static/nifty_smallcap_universe.csv` (250 stocks)
  that was on disk but untracked.
- Resolved 2 of the 5 gaps surfaced (smallcap untracked, rebalances
  empty). Three remain pending or moved into 2.5.4 / RECOVERY: the
  2009-2019 GDF backfill (HIGH risk, single-Mac), the
  password-manager entry, and the cloud-redundancy gap.

### Phase 2.5.5 — Recovery runbook — DONE

- `RECOVERY.md` covers three failure scenarios (Railway DB dead /
  Mac gone / GitHub repo lost). Each has explicit restore commands
  and a quarterly dry-run test.

### Phase 2.5.4 — Google Drive cloud upload — READY FOR OPERATOR

- `scripts/upload_to_gdrive.py` written. Uses
  google-api-python-client (installed into local .venv).
- Strategy:
  - `db_backups/` mirrored file-by-file (md5 dedup; preserves every
    tarball that ever existed in Drive)
  - `nse500_data/`, `nse500_data_historical/`, `nse500_data_hourly/`,
    `indices_data/` snapshotted as one daily tarball each, with
    7-day retention in Drive
- `auth`, `upload`, `status` sub-commands.
- `GDRIVE_SETUP.md` is a 10-min runbook covering the Google Cloud
  Console OAuth setup + first auth + first upload.
- Pending: operator runs through GDRIVE_SETUP.md and confirms the
  first upload lands in `My Drive/kite-lab-backups/`.
