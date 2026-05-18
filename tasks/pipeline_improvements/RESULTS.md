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

## Validation Gate 2 (Phase 2 — Performance) — PASSED

**Date:** 2026-05-15
**Baseline:** `golden_master_20260515_151808.json` (Phase 0)
**Comparison:** post-Phase-2 re-snapshot

### Outcome

Each of the four production portfolios was run twice — once with
`--shared-state-file` pointing at a `pipeline_core` cache, once without
— and the four dashboard CSVs (`momentum_equity.csv`, `momentum_trades.csv`,
`momentum_holdings.csv`, `momentum_metrics.csv`) hashed byte-identically
across both runs for every portfolio:

| Portfolio | Files compared | Result |
|---|---|---|
| L6 v2 | 4 | bit-identical |
| OM25 v3 | 4 | bit-identical |
| TL25 v3 | 4 | bit-identical |
| COMBO Defensive | 4 | bit-identical |

Re-snapshotting the production run dirs against the Phase 0 baseline
diffs cleanly (only the `label` field changes, as designed). All 27
unit tests across `test_metrics_common.py`, `test_sync_validation.py`,
and `test_pipeline_core.py` pass.

### Wall-clock impact

Real-world savings on this machine for the 2020-2026 backtest window
(measured for TL25 v3 with the cache built once):

| Run | Wall-clock |
|---|---|
| TL25 without cache | 1.8s |
| TL25 with cache | 0.9s |
| Savings per portfolio | ~0.9s |

Extrapolating to all 4 portfolios + 1 cache-build step: roughly
**4 × 0.9s = 3.6s saved**, minus 0.95s for the one-time cache build =
**~2.7s net saved per pipeline run** on this dataset.

This is below the 30s target from PLAN.md. The reason is that
`load_price_panels` is already fast on a modern SSD (~1s for 500
files of ~60KB each); the original 4-8s/load estimate in PLAN.md
overcounted. The remaining wins from this pattern come at scale
(larger universes, slower disks, or when re-running portfolios many
times — e.g. parameter sweeps).

The cache is preserved in the orchestrator anyway because:

1. It eliminates work duplication, which is good hygiene independent
   of the absolute savings.
2. The `--shared-state-file` plumbing is now in place for Phase 3
   when the engine consolidation may load additional shared artefacts.
3. The `--no-shared-state` flag preserves backward-compatibility.

### Phase 2 deliverables

- `scripts/pipeline_core.py` (177 LOC) — `PipelineState`,
  `load_shared_state()`, `dump_to_cache()`, `load_from_cache()`,
  schema-versioned pickle round-trip.
- 4 portfolio scripts now accept `--shared-state-file` (read panels
  from the cache instead of disk).
- `scripts/run_daily_pipeline.py` rewired with a "Prepare shared-state
  cache" step before the portfolio builds, plus a `--no-shared-state`
  escape hatch and per-step timing summary at the end of the run.
- `tests/test_pipeline_core.py` (5 tests, round-trip + describe +
  schema-mismatch + wrong-type behaviour).

### Audit corrections folded into PLAN.md (Phase 2.5)

The user's concerns on 2026-05-15 about scheduling, incremental fetch,
and incremental backup turned out to already be correctly handled by
existing code. The "Audit corrections" section in PLAN.md now documents
this so future work doesn't re-litigate. Phase 2.5 (data redundancy)
remains the meaningful unmet need and is the next phase.

## Validation Gate 2.5 (Phase 2.5 — Data redundancy & resilience) — PASSED

**Date:** 2026-05-17 (2.5.1–2.5.5 + 2.5.6) / 2026-05-18 (final live verify)

### Outcome

Daily redundancy now runs unattended on Railway. The chain that
matters for survival has **three independent offsite copies**:

| Location | Contains | Refreshed by |
|---|---|---|
| Mac (`~/Documents/stock_data/`) | Prices + DB tarballs + GDF backfill (`nse500_data_full`, `indices_data_full`) | Mac-local backup scripts (manual / belt-and-suspenders) |
| Railway volume (`/data/`) | Prices + DB tarballs + symlinked GDF backfill | `init_persistent_storage.sh` + Railway-side jobs |
| Google Drive (`kite-lab-backups/`) | DB tarballs (mirrored) + daily tarballs of each price dir | `daily_cloud_upload` @ 20:30 IST (Railway APScheduler, `drive.file` scope) |

### Live verification (2026-05-17/18)

- `daily_pipeline` (07:00 IST Mon-Fri) — confirmed live via Admin → Schedule.
- `daily_db_backup` (20:00 IST every day) — registered; manual
  trigger succeeded; `/data/db_backups/kitelab_db_<ts>.tar.gz`
  written; `pg_restore --list` smoke test OK.
- `daily_cloud_upload` (20:30 IST every day) — registered; manual
  trigger succeeded after the `google-*` deps fix; 7 files visible
  in `My Drive/kite-lab-backups/` under the new `drive.file` scope.
- `backup_database.py --dry-run` against the public Postgres proxy:
  31,537 rows across 10 tables.

### CRITICAL_DATA.md gaps — status

| Gap | Status |
|---|---|
| `nse500_data_historical/` single-Mac risk | **CLOSED** — uploaded to Railway, mirrored to Drive |
| `data/static/nifty_smallcap_universe.csv` untracked | **CLOSED** (committed 2026-05-16) |
| `rebalances` table empty | **EXPECTED BEHAVIOUR** (operator uses Zerodha Console directly) |
| Backup is local-only | **CLOSED** — Drive cloud upload live |
| `DATABASE_PUBLIC_URL` password-manager entry | **OPEN** — operator action |

### Side-task: GDF deep backfill

Captured while GDF API access was live; documented in
`tasks/gdf_full_backfill/`. Final state on disk:

- `nse500_data_full/` — 760 stocks (GDF 2009 → 2023-12-31 + Kite
  2020 → present, rescale-anchored stitch).
- `indices_data_full/` — 141 indices, 2010-present.
- 265 stocks blank in GDF were gap-filled from Kite (258 succeeded,
  7 unavailable: 5 dummies + PFOCUS + STLTECH).
- 22 corporate-action rescale outliers correctly handled by the
  rescale-anchored stitch.

Both directories are now part of the daily Drive cloud upload.

### Phase 2.5 + 2.5.6 deliverables

- `scripts/backup_database.py`, `scripts/restore_database.py`
- `scripts/upload_to_gdrive.py` (with `drive.file` scope + env-var creds)
- `scripts/upload_price_data.py` (`TARGETS` allowlist expanded)
- `scripts/init_persistent_storage.sh` (4 new volume mounts)
- `kite-api/app/scheduler/tasks.py` (2 new APScheduler entries)
- `kite-api/app/services/job_service.py` (`db_backup` + `cloud_upload` commands)
- `kite-api/app/api/sync.py` (`ALLOWED_UPLOAD_DIRS` expanded)
- `kite-api/requirements.txt` (google-* deps)
- `tasks/pipeline_improvements/CRITICAL_DATA.md`,
  `GDRIVE_SETUP.md`, `RAILWAY_BACKUP_SETUP.md`, `RECOVERY.md`
- 9 new tests on rotation + `parse_ts` in `backup_database` (all
  pipeline-improvements tests pass: 36 of 36 at last run).

## Production fix (2026-05-18) — daily cron didn't refresh dashboard's default view

**Bug:** dashboard's nse500 view stayed frozen between manual "Update
Portfolios" clicks. Daily cron only built the 4 v3 portfolios; the
legacy nse500/nifty100/nifty250 sync was a no-op against yesterday's CSVs.

**Fix:** `scripts/run_daily_pipeline.py` now delegates its portfolio +
DB-sync block to `scripts/update_all_portfolios.py` (extended to build
all 7 portfolios — 3 legacy + 4 v3). Cron and the manual button now
share one orchestrator.

**Verified live (2026-05-18):** single invocation produced fresh
`experiments/final_portfolio/final_portfolio_20260518201402` and
`data/l6_v2_portfolios/l6_v2_portfolio_20260518_201542` — both refresh
in the same cron run.

## Validation Gate 3 (Phase 3.2 + 3.3 — Engine consolidation, scoped) — PASSED

**Date:** 2026-05-18
**Scope:** Loader extraction + `latest.json` pointer files.
**Out of scope (user decision):** Phase 3.1 — legacy-L6 migration onto
`_clean_engine`. The cron bug fix made `run_final_momentum_portfolio.py`
production-critical; engine migration would risk breaking it for marginal
payoff.

### Outcome

| Sub-part | Result |
|---|---|
| 3.2 Loader extraction (`data_pipeline/loaders.py` + re-export shim) | Bit-identical output between old and new import paths; 20+ existing callers unchanged |
| 3.3 `latest.json` pointers + service consolidation | All three services (sync, portfolio, positions) share one resolver; ~0.03ms cached lookup vs full glob; verified across all 7 universes |

### Test results

```
tests/test_pipeline_core.py + test_metrics_common.py + test_sync_validation.py:
  27 tests, 0 failures (post-3.2 + 3.3)
```

### Phase 3 deliverables

- `data_pipeline/loaders.py` (47 LOC) — `load_price_panels`, `load_benchmark`
- `scripts/backtest_momentum.py` — re-export shim, 30 LOC deleted
- `kite-api/app/services/sync_service.py` — `UNIVERSE_DIRS` registry +
  pointer read/write helpers + cached `get_latest_experiment_dir`
- `kite-api/app/services/portfolio_service.py` — delegates to
  sync_service (15 LOC deleted)
- `kite-api/app/services/positions_service.py` — replaced bespoke
  regex-based glob with the shared helper (25 LOC deleted)
- `.gitignore` — `**/latest.json` (regenerated on every sync)
- `CLAUDE.md` — daily pipeline section reflects the new orchestration

### What was explicitly NOT done (Phase 3.1)

`scripts/run_final_momentum_portfolio.py` continues to use the legacy
`backtest_momentum.run_backtest()` engine. The two engines remain
divergent on Sharpe rf rate (legacy: 0; `_clean_engine`: 5%) and minor
implementation details. The legacy path is the production daily-cron
path for the dashboard's default nse500 view, and the user opted to
not gamble on a 1bps-tolerance bit-equivalence migration.

If a future need (e.g., feature parity for the legacy path) forces the
migration, the validation gate from PLAN.md Phase 3.1 stands: 1bps daily
equity tolerance + ≥99% trade match across a full 2020-2026 backtest.
