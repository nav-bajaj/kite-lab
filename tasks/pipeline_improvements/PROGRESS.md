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

### Phase 2.5.4 — Google Drive cloud upload — DONE

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
- Operator completed setup 2026-05-16; confirmed 5 subfolders
  visible in `My Drive/kite-lab-backups/`.

## 2026-05-17 — Phase 2.5.6 (Railway-side migration)

User flagged the Mac-cron weakness: Mac isn't always on at 20:00 IST.
Moved both backup steps into the Railway APScheduler so the offsite
chain runs without a local machine.

- Added `daily_db_backup` (20:00 IST) + `daily_cloud_upload`
  (20:30 IST) entries to `kite-api/app/scheduler/tasks.py`.
- Added `db_backup` + `cloud_upload` commands to
  `kite-api/app/services/job_service.py` (so Admin → Jobs can
  trigger them manually).
- OAuth scope narrowed from `drive` to `drive.file`. Required a
  fresh refresh token (the old `drive`-scoped token can't be
  downgraded in place). New token + client secret stored as
  `GDRIVE_REFRESH_TOKEN_JSON` and `GDRIVE_CLIENT_SECRET_JSON`
  env vars on Railway.
- Expanded `scripts/init_persistent_storage.sh` to mkdir + symlink
  `nse500_data_historical`, `nse500_data_gdf_full`,
  `nse500_data_full`, and `indices_data_full` into `/app/`.
- One-time upload of the 2009-2019 backfill to Railway via
  `scripts/upload_price_data.py --target nse500_data_historical`.
  Required fixing the allowlists:
  - Added `nse500_data_historical` (and the GDF/full variants) to
    `scripts/upload_price_data.py:TARGETS` and to
    `kite-api/app/api/sync.py:ALLOWED_UPLOAD_DIRS`.
- Hit and fixed two rollout bugs:
  - `backup_database.py` initially tried
    `postgres.railway.internal` (Railway-internal hostname) from
    the Mac; added a fail-fast probe in `_engine_from_env` with a
    Railway-specific error message pointing at `DATABASE_PUBLIC_URL`.
  - Cloud-upload job failed on Railway with
    `ModuleNotFoundError: No module named 'google'`. Added
    `google-api-python-client==2.196.0`,
    `google-auth-httplib2==0.3.1`, and
    `google-auth-oauthlib==1.3.1` to `kite-api/requirements.txt`.
- `RAILWAY_BACKUP_SETUP.md` written as a 20-minute operator runbook
  (env vars, the JWT token capture, the symlink trick, smoke test).

After Railway redeploy + manual triggers:
- `db_backup` job: ran cleanly, tarball written under
  `/data/db_backups/`, smoke test OK.
- `cloud_upload` job: completed, 7 files visible in
  `kite-lab-backups/` under the new `drive.file`-scoped folder.

### Phase 2.5.6 deliverables

- `kite-api/app/scheduler/tasks.py` (2 new APScheduler entries)
- `kite-api/app/services/job_service.py` (2 new commands)
- `kite-api/app/api/sync.py` (`ALLOWED_UPLOAD_DIRS` expanded)
- `kite-api/requirements.txt` (google-* deps)
- `scripts/init_persistent_storage.sh` (4 new dirs + symlinks)
- `scripts/upload_price_data.py` (`TARGETS` expanded)
- `scripts/backup_database.py` (`_engine_from_env` fail-fast)
- `scripts/upload_to_gdrive.py` (drive.file scope + env-var creds)
- `tasks/pipeline_improvements/RAILWAY_BACKUP_SETUP.md` (new)

## 2026-05-17/18 — GDF deep-backfill side task

User opted to capture the deepest possible price history while GDF
API access was live, as insurance against subscription lapse. Tracked
in `tasks/gdf_full_backfill/`.

- Phase A — probed GDF limits: no per-request bar cap; no 100-symbol
  cap; earliest data ~2009-03-05; 2024-25 gap on most names.
  Decision: cap GDF window at 2023-12-31 and use Kite for 2024+.
- Phase B — `scripts/gdf_full_backfill.py` fetched a 765-symbol
  universe (Nifty 500 + Microcap 250 + dropped names) into
  `~/Documents/stock_data/nse500_data_gdf_full/`.
- Phase C — `scripts/stitch_gdf_kite.py` refactored to accept
  `--gdf-dir/--kite-dir/--out-dir`; stitched output landed in
  `nse500_data_full/`. Indices similarly via
  `scripts/stitch_gdf_indices.py` → `indices_data_full/`. GDF index
  fetch returned "Data for requested exchange is disabled" for non-
  stock exchanges; worked around by discovering the existing
  `indices_data_historical/` already had comprehensive 2010-present
  coverage.
- Phase D — `scripts/gdf_backfill_validate.py` produced
  `coverage_report.csv`. Found 265 stocks with zero GDF history.
  `scripts/fetch_missing_from_kite.py` gap-filled 258 of those from
  Kite live (7 unavailable: 5 dummies + PFOCUS + STLTECH).
- Final stitched panel: **760 stocks**, **141 indices**, both in
  `~/Documents/stock_data/`. 22 corporate-action rescale outliers
  (CGCL +300%, METROPOLIS +300%, VEDL -66%) handled correctly by
  the rescale-anchored anchor.
- The `_full` directories are picked up automatically by the
  Railway-side cloud upload (per Phase 2.5.6 symlinks).

### Validation Gate 2.5 — PASSED

- `daily_pipeline` next-fire = next weekday 07:00 IST (verified via
  Admin → Schedule).
- `daily_db_backup` and `daily_cloud_upload` registered, both
  triggered manually with success.
- `backup_database.py --dry-run` against Railway via the public
  proxy: 31,537 rows across 10 tables.
- `pg_restore` smoke test on the produced tarball succeeds; first
  real backup written and stored.
- `CRITICAL_DATA.md` checklist: 4 of 5 gaps resolved (smallcap
  universe tracked, rebalances empty by design, single-Mac risk
  closed by Drive + Railway upload, historical-backfill risk closed
  by `nse500_data_full/`). One gap deferred to operator:
  `DATABASE_PUBLIC_URL` password-manager entry.
- `RECOVERY.md` exists; quarterly dry-run test scheduled as an
  ongoing operator item.

### Final state of offsite copies (3 independent locations)

1. Mac: `~/Documents/stock_data/` (rsync + Mac-local backup scripts)
2. Railway volume: `/data/` (persistent, survives container rebuild)
3. Google Drive: `kite-lab-backups/` (drive.file scoped, Railway-driven)

A failure of any single one of these doesn't take down the chain.

## 2026-05-18 — Documentation refresh + status review

User requested a status review. Folder contents reconciled with
live state; PLAN.md now lists Phase 2.5.6 + GDF side-task; PROGRESS.md
extended through 2026-05-18 (this entry); RESULTS.md gained a
Gate 2.5 record.

## 2026-05-18 — Production bug: daily cron didn't refresh dashboard's nse500 view

User flagged: positions and trades only updated after clicking "Update
Portfolios" — daily cron never refreshed them despite running cleanly.

**Root cause:** `run_daily_pipeline.py` built the 4 v3 portfolios (OM25/TL25/L6 v2/COMBO)
but skipped the legacy `run_final_momentum_portfolio.py --universe {nse500,nifty100,nifty250}`.
`sync_to_database.py` looped over all 7 universes but the legacy 3
were syncing yesterday's stale CSVs. Dashboard defaults to `nse500`
(legacy) → looked frozen.

**Evidence:** Latest `experiments/final_portfolio/` was 5/12; latest
`data/l6_v2_portfolios/` was 5/14. Five-day age gap between cron-only
and manual-button outputs.

**Fix:**
- Extended `scripts/update_all_portfolios.py` to build all 7 portfolios
  (3 legacy + 4 v3). Added `--skip-fetch`, `--skip-corporate-actions`,
  `--shared-state-file` flags so the cron can call it without
  duplicating earlier pipeline steps.
- Simplified `scripts/run_daily_pipeline.py` to a single subprocess
  call to `update_all_portfolios.py --skip-fetch --skip-corporate-actions
  --shared-state-file`. Removed the four v3 portfolio commands and the
  inline `sync_to_database.py` step — they now live inside
  `update_all_portfolios.py`.
- Updated `CLAUDE.md` "Daily Production Pipeline" section.
- Verified end-to-end: live run produced fresh
  `final_portfolio_20260518201402` and
  `l6_v2_portfolio_20260518_201542` in the same invocation.

Net effect: daily cron and the manual "Update Portfolios" button are
now in lock-step. The button is preserved as a manual override.

## 2026-05-18 — Phase 3.2 + 3.3 (engine consolidation, scoped down)

User decision: do 3.2 + 3.3 only, skip 3.1 — `run_final_momentum_portfolio.py`
is now production-critical (per the cron bug fix above), and migrating
it onto `_clean_engine` carries production risk for marginal payoff.

### Phase 3.2 — loader extraction — DONE

- Created `data_pipeline/loaders.py` (47 LOC) housing `load_price_panels`
  and `load_benchmark`, lifted verbatim from `scripts/backtest_momentum.py`.
- `scripts/backtest_momentum.py` now re-exports both names from
  `data_pipeline.loaders` so the 20+ existing callers
  (`pipeline_core.py`, `run_om25_v3_portfolio.py`, every research
  script, etc.) keep working with zero import changes.
- Validated bit-identical output: loading nse500_data through both
  import paths returns `DataFrame.equals() == True`.
- All 27 pipeline-improvements unit tests still pass.

### Phase 3.3 — latest.json pointers — DONE

- `kite-api/app/services/sync_service.py` now keeps a single
  `UNIVERSE_DIRS` dict (parent dir + glob pattern per universe) — the
  only place that knows the on-disk layout.
- `get_latest_experiment_dir(universe)` prefers reading
  `<parent_dir>/latest.json`. If the pointed-at run dir still has its
  holdings CSV, returns it immediately (one stat, ~0.03ms/lookup).
  Otherwise falls back to the timestamp glob and lazily writes
  `latest.json` for the next caller.
- `portfolio_service.py` and `positions_service.py` now import
  `get_latest_experiment_dir` from `sync_service` — all three services
  share the pointer cache, so they can't disagree about which run is
  latest.
- `positions_service.sync_from_csv` lost its bespoke regex-based glob
  (15+ LOC) in favour of the shared helper.
- `**/latest.json` added to `.gitignore` — these files are
  per-deployment caches, not source-of-truth.
- Verified live across all 7 universes: each resolves to the right
  timestamped dir on first call, then writes `latest.json` into its
  parent.

### Phase 3 deliverables

- `data_pipeline/loaders.py` (new)
- `scripts/backtest_momentum.py` (loaders → re-export shim)
- `kite-api/app/services/sync_service.py` (UNIVERSE_DIRS + pointer
  read/write helpers + cached `get_latest_experiment_dir`)
- `kite-api/app/services/portfolio_service.py` (delegates to
  sync_service)
- `kite-api/app/services/positions_service.py` (replaced bespoke
  glob with shared helper)
- `.gitignore` (latest.json line)
- `CLAUDE.md` (daily-pipeline section reflects new orchestration)

### Validation Gate 3 — PASSED

- All 27 unit tests still pass.
- Bit-identical loader output between old and new import paths.
- Three services resolve to the same run dir per universe.
- Live `update_all_portfolios.py` end-to-end run succeeded with the
  refactored sync path.

### Remaining work — open

1. **Phase 3.1 (legacy-L6 engine migration)** — SKIPPED by user
   decision. Legacy script kept on `backtest_momentum.run_backtest`.
   Revisit only if the engine divergence (rf=0 vs rf=5%) becomes a
   problem.
2. **Operator items (recurring):**
   - `DATABASE_PUBLIC_URL` password-manager entry (CRITICAL_DATA.md gap)
   - Quarterly DR dry-run restore (RECOVERY.md)

Pipeline-improvements project is now **fully shipped**. The remaining
items are durability / hygiene polish, not coding work.
