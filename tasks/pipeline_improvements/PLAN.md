# Daily Pipeline Improvements — Plan

**Branch:** `pipeline-improvements`
**Started:** 2026-05-15
**Owner:** navdeep
**Status (2026-05-18):** Phases 0, 1, 2, 2.5 (incl. 2.5.6 Railway migration) shipped.
GDF backfill side-task complete (760 stocks / 141 indices stitched).
Phase 3.2 (loader extraction) + 3.3 (latest.json pointers) shipped.
Phase 3.1 (legacy-L6 engine migration) **skipped** —
`run_final_momentum_portfolio.py` is now production-critical (daily cron
refreshes nse500/nifty100/nifty250 through it after the 2026-05-18 fix);
migrating it onto `_clean_engine` would carry production risk for
marginal payoff.

---

## Motivation

The daily pipeline (`scripts/run_daily_pipeline.py`) has accumulated organic
growth across the May 2026 OOS retune (OM25 v3, TL25 v3), the MM-tuning engine
migration (L6 v2), and the DD-reduction product launch (COMBO Defensive). The
result:

- **Four portfolio scripts** each independently reload the full NSE 500 price
  panel, the NIFTY 100 benchmark, and (for OM25/COMBO) the regime panel.
- **Two backtest engines** (`backtest_momentum.py` and `_clean_engine.py`) with
  ~600 LOC overlap — L6 uses the legacy engine, OM25/TL25/COMBO use the new one.
- **Four metrics implementations** with **three different Sharpe formulas**
  (rf=0 in legacy, rf=5% in OM25/TL25 inline, rf=0 in `_clean_engine`).
- **One pipeline step (`build_momentum_signals.py`) writes
  `data/momentum/top25_signals.csv` that nothing downstream consumes** — only
  ad-hoc tools read it.
- **No atomic transaction guard** around `sync_to_database.py` — a mid-pipeline
  portfolio failure can leave partial state in production Postgres.

User decisions captured 2026-05-15:
1. Keep both L6 v2 and COMBO Defensive as permanent production strategies.
2. Investigate `build_momentum_signals.py` orphan first (done — see findings below).
3. Leave `experiments/` folder alone; focus on pipeline/code.
4. Sequence work as **Correctness → Performance → Consolidation** with hard
   validation gates between phases.

---

## Phase 0 — Pre-work (this phase)

### 0.1 Orphan-step investigation — DONE

`scripts/build_momentum_signals.py` writes `data/momentum/top25_signals.csv`
daily. Searched all `.py` files under `scripts/`, `kite-api/`, and
`kite-dashboard/` for runtime consumers. **No production code path reads this
file** — only the following ad-hoc tools open it:

| Consumer | Type |
|---|---|
| `scripts/validate_signals.py` | Manual signal QA |
| `scripts/compare_signals_baseline.py` | Manual comparison tool |
| `scripts/backtest_momentum.py --signals ...` | Legacy backtest CLI |
| `scripts/run_rebalance_sensitivity.py` | Research sensitivity tool |

**Recommendation (decision deferred to user):** remove the step from
`run_daily_pipeline.py`. Saves ~8-12s/day. Manual runs of the consumer tools
can rebuild the signal file on demand.

### 0.2 CLAUDE.md drift fix — DONE

CLAUDE.md updated 2026-05-15:
- "Current Status" now lists all 4 production portfolios (OM25 v3, TL25 v3,
  L6 v2, COMBO Defensive) instead of the stale "NSE 500 L6-1W" description.
- "Daily Production Pipeline" comment block expanded from 9 steps to the
  actual 12 (adds: apply_corporate_actions, L6 v2, COMBO Defensive, and
  flags the orphan step #6).
- OM25 v3 output dir corrected to `data/om25_v3_portfolios/...`
  (CLAUDE.md still said the deprecated `data/om25/v3/runs/` path).
- New CLAUDE.md sections added for L6 v2 and COMBO Defensive.
- Footer updated to point at this PLAN.md.

### 0.3 Golden-master snapshot — IN PROGRESS

Build `scripts/snapshot_pipeline_outputs.py`:
- Discovers the latest `<universe>_portfolio_<ts>/` dir for each of the 4
  production portfolios (matches `sync_service.py` glob logic).
- For each portfolio reads its dashboard-schema CSVs
  (`momentum_equity.csv`, `momentum_trades.csv`, `momentum_holdings.csv`,
  `momentum_metrics.csv`) and `top25_signals.csv` for the legacy step.
- Computes per-file:
  - Row count
  - SHA256 of normalized content (sorted, deterministic float formatting)
  - Numeric column-wise summary: min/max/mean/last-value for key columns
    (portfolio_value, drawdown for equity; price, shares for trades)
- Writes JSON to `tasks/pipeline_improvements/golden_master_<ts>.json`

This file is the **regression oracle**:
- After Phase 1 (correctness): metrics will change (rf unification);
  equity/trades/holdings must remain bit-identical.
- After Phase 2 (perf): all outputs must remain bit-identical.
- After Phase 3 (consolidation): L6 v2 equity/trades may drift within
  defined tolerance bands (1 bps daily equity, ≥99% trade match).

---

## Phase 1 — Correctness

### 1.1 Unify metrics
Create `scripts/metrics_common.py`:
```python
def compute_portfolio_metrics(equity_df, trades_df, exits_df,
                              initial_capital, rf_rate, benchmark=None) -> dict:
    """Single source of truth: CAGR, vol, Sharpe (rf-aware), Sortino,
    MaxDD, turnover (annualized), hit rate, avg holding days."""
```

Replacements:
- `scripts/run_om25_v3_portfolio.py` — inline metrics in `write_dashboard_outputs()`
- `scripts/run_tl25_v3_portfolio.py` — inline metrics
- `scripts/run_l6_v2_portfolio.py` — inline metrics
- `scripts/run_combo_defensive_portfolio.py` — inline metrics
- `scripts/_clean_engine.py:compute_metrics()` — delegate
- `scripts/backtest_momentum.py:summarise_metrics()` — delegate

**Standardize Sharpe rf rate at 5%** (matches current OM25/TL25 published
performance and the dashboard's existing displays). Document in CLAUDE.md.

### 1.2 Transactional safety on sync
Refactor `scripts/sync_to_database.py`:
- Stage all CSVs in a dry-run validation pass (row counts, date monotonicity,
  equity ≥ 0, holdings.shares ≥ 0, etc.) before any DB writes.
- Wrap each universe's sync in a single SQLAlchemy transaction.
- Halt before sync if any portfolio script failed earlier in the pipeline.
- Add a `--validate-only` flag for safety drills.

### 1.3 Token-expiry preflight
Add to `run_daily_pipeline.py`:
- Cheap KiteConnect probe (e.g., `kite.profile()`) before fetch steps.
- Fail-fast with a clear "run `--with-login`" message.

### Validation Gate 1
- Re-snapshot golden master.
- Diff vs Phase 0 baseline:
  - **Expected to change:** `momentum_metrics.csv` Sharpe values (rf=0→5% shifts
    Sharpe by ~0.25 for typical strategies). Document expected magnitude.
  - **Must remain bit-identical:** equity, trades, holdings, signals.
- Manual sanity check: dashboard metrics on staging should display unified
  Sharpe values across all 4 universes.

---

## Audit corrections (post-Phase-1)

Three concerns the user raised on 2026-05-15 turned out to be already
correctly handled by existing code:

1. **Schedule 7am IST Mon-Fri** — already configured at
   [`kite-api/app/scheduler/tasks.py:23-26`](../../kite-api/app/scheduler/tasks.py#L23-L26)
   with `hour=7, minute=0, day_of_week="mon-fri"`. Scheduler tz is set to
   `Asia/Kolkata` at
   [`scheduler.py:18`](../../kite-api/app/scheduler/scheduler.py#L18) and passed
   to APScheduler. If the schedule appears not to fire at 7am IST in
   practice, the cause is runtime (Railway container restart wiping the
   in-memory jobstore, scheduler service crashed, etc.) — **not config**.
   We add a runtime verification step in Phase 2.5.1.

2. **Incremental fetch** — already incremental at
   [`history_utils.py:178-195`](../../scripts/history_utils.py#L178-L195).
   Reads the existing CSV, picks `fetch_start = last_date + 1 day`, and
   skips the API call entirely if `fetch_start >= end_ts`. Mid-day reruns
   and recovery-from-failure paths already benefit.

3. **Incremental backup** — already incremental by default at
   [`sync_data_backup.py:172`](../../scripts/sync_data_backup.py#L172).
   `--full` is an explicit opt-in override; default behaviour copies only
   changed files.

The perception of "lots of refetching" most likely comes from the per-stock
CSV-read overhead (500 files opened just to check last_date even when no new
data exists, ~5s wall-clock). Phase 2's load-once orchestrator pattern
eliminates that overhead.

## Phase 2 — Performance

### 2.1 Orchestrator-level data load
Refactor `run_daily_pipeline.py` to call Python entry points rather than
subprocess-launching scripts. New module `scripts/pipeline_core.py` exposes
`load_shared_state()` that returns a frozen dataclass:
```python
@dataclass(frozen=True)
class PipelineState:
    price_panel_close: pd.DataFrame
    price_panel_ohlc: dict[str, pd.DataFrame]
    benchmark: pd.Series
    regime_panel: pd.Series
    universes: dict[str, list[str]]
```

### 2.2 Portfolio scripts accept pre-loaded panels
Each portfolio script grows:
```python
def main(state: PipelineState | None = None):
    if state is None:
        state = load_shared_state()  # backward-compat for standalone runs
    ...
```

CLI invocation continues to work unchanged.

### 2.3 Timing instrumentation
Add per-step `start_ms / end_ms` logging. Baseline target: ≥ 30s reduction
total wall-clock.

### Validation Gate 2
- Re-snapshot golden master.
- Diff vs Phase 1 baseline: **bit-identical across all files**. This phase
  changes only data flow, not logic.
- Confirm each portfolio script still works standalone via CLI.
- Confirm timing improvement ≥ 30s.

---

## Phase 2.5 — Data redundancy & resilience

The single biggest data-loss risk today is a Railway outage or DB
corruption: the Postgres tables `trades`, `trade_matches`,
`open_positions`, `rebalances`, and `jobs` have no offsite backup. The
local price-data backup at `~/Documents/stock_data/` also lives on the
same Mac as the source — single physical device risk.

### 2.5.1 Live schedule verification

Add `scripts/check_schedule.py` that queries the production
`/api/schedule` endpoint and prints next-fire times for each registered
job. Confirms the 7am IST Mon-Fri trigger is live, the scheduler is
running, and the in-memory jobstore was repopulated on the most recent
container start.

If a runtime gap is found, switch the APScheduler jobstore from
`MemoryJobStore` to `SQLAlchemyJobStore` against the existing Postgres
DB. Schedules then survive container restarts without relying on the
`register_default_tasks` startup hook.

### 2.5.2 Postgres offsite backup

Add `scripts/backup_database.py`:

- `pg_dump` of the Railway Postgres into a timestamped compressed file
  under `data/db_backups/`
- Rotation: keep last 14 daily + last 12 weekly (Sunday) + last 12
  monthly (1st of month)
- Tables backed up explicitly enumerated; halts if a new table appears
  unrecognised (forces a conscious choice on whether to back it up)
- Smoke test on every run: `pg_restore --list` against the new file
  must succeed before the previous day's file is purged by rotation

Schedule this as a separate **20:00 IST daily** job (after market
close, well before the next morning's 7am pipeline) via the same
APScheduler config in `tasks.py`.

### 2.5.3 Critical-data git audit

One-time review pass:

- Confirm `data/corporate_actions.json` is committed (it drives the
  corporate-action adjustments in `apply_corporate_actions.py` and
  `sync_to_database.py`).
- Confirm `data/static/*.csv` (universe definitions) are tracked.
- Confirm locked strategy configs (`scripts/om25_v3.py`,
  `scripts/tl25_v3.py`, `scripts/combo_defensive.py`,
  `scripts/_momentum_engine.py:BASELINE`) are tracked.
- The `nse500_data_historical/` 2009-2019 backfill (GDF-sourced, not
  refetchable from Zerodha) lives only on the Mac. Decide: commit via
  git-lfs, upload to cloud as part of 2.5.4, or document as a
  manual-rebuy-only artifact.

Output: a markdown checklist `tasks/pipeline_improvements/CRITICAL_DATA.md`.

### 2.5.4 Cloud-redundancy upload (optional)

If 2.5.2 lands cleanly, extend it to upload the Postgres dump and
critical-data tarball to a second location (Google Drive via the
existing OAuth in the dashboard, or a free-tier S3 bucket). Off-Mac,
off-Railway — survives loss of either.

Requires creds + small SDK call; deferred until 2.5.1-2.5.3 are green
so credential-setup risk is scoped.

### 2.5.5 Recovery runbook

Document the disaster-recovery procedure in
`tasks/pipeline_improvements/RECOVERY.md`:

- "Railway DB is gone": restore from latest `data/db_backups/*.sql.gz`
- "Local repo lost": clone from GitHub + restore prices from
  `~/Documents/stock_data/`
- "Mac lost (no local backups)": clone from GitHub + Phase 2.5.4 cloud
  restore + manual GDF re-purchase for the 2009-2019 backfill
- Test the runbook by doing a dry-run restore into a scratch directory

### Validation Gate 2.5

- `check_schedule.py` reports daily-pipeline next-fire as
  `<next weekday> 07:00:00 IST`.
- A dry-run of `backup_database.py` produces a non-empty compressed
  dump that `pg_restore --list` reads back successfully.
- `CRITICAL_DATA.md` checklist is fully green.
- `RECOVERY.md` exists and a dry-run restore from the latest backup
  into a scratch DB succeeds end-to-end.

### Phase 2.5.6 — Move backup cron to Railway (added 2026-05-17)

Mac-local 21:00 cron is fragile — the laptop isn't always on at that
time. Move the two backup steps into the same APScheduler instance
that runs the 7am pipeline, so daily redundancy doesn't depend on a
laptop being awake.

Scope:

- Add `daily_db_backup` (20:00 IST) + `daily_cloud_upload` (20:30 IST)
  jobs to `kite-api/app/scheduler/tasks.py`.
- Add `db_backup` and `cloud_upload` commands to
  `kite-api/app/services/job_service.py` so they're triggerable from
  Admin → Jobs.
- Backup writes into `/data/db_backups/` on the Railway volume; cloud
  upload mirrors that plus per-day tarballs of `/data/nse500_data`,
  `/data/nse500_data_hourly`, `/data/indices_data`, and
  `/data/nse500_data_historical` to Google Drive.
- Switch Drive OAuth scope from `drive` → `drive.file` (Railway app
  only sees files it itself created — narrower blast radius).
- One-time push of the 2009-2019 GDF backfill to the Railway volume
  via `scripts/upload_price_data.py --target nse500_data_historical`
  so the daily cloud upload picks it up going forward.
- Documented in `RAILWAY_BACKUP_SETUP.md` (operator runbook).

Operator-side bugs encountered during rollout:

- `nse500_data_historical` was missing from
  `scripts/upload_price_data.py:TARGETS` and from
  `kite-api/app/api/sync.py:ALLOWED_UPLOAD_DIRS`; both fixed.
- Mac initially pointed `DATABASE_URL` at `postgres.railway.internal`
  (Railway-only hostname). Added fail-fast probe in
  `backup_database.py:_engine_from_env` with a Railway-specific error
  pointing at `DATABASE_PUBLIC_URL`.
- `init_persistent_storage.sh` didn't `mkdir`/symlink
  `nse500_data_historical` / `nse500_data_gdf_full` /
  `nse500_data_full` / `indices_data_full`; added.
- `cloud_upload` failed with `ModuleNotFoundError: No module named
  'google'` because `google-api-python-client` etc. weren't in
  `kite-api/requirements.txt`. Added the three google-* deps.

### Phase 2.5.7 — GDF deep backfill (side task, see `tasks/gdf_full_backfill/`)

While GDF API access was live, captured the deepest possible history
across NSE 500 + indices in case the subscription lapses. End state:

- `~/Documents/stock_data/nse500_data_full/` — **760 stocks**, GDF
  (2009 → 2023-12-31) + Kite (2020 → present) stitched with the
  rescale-anchored anchor in `scripts/stitch_gdf_kite.py`. 265
  symbols that were blank in GDF were gap-filled from Kite via
  `scripts/fetch_missing_from_kite.py` (258 succeeded; 7 = 5 dummies
  + PFOCUS + STLTECH unavailable).
- `~/Documents/stock_data/indices_data_full/` — **141 indices**,
  comprehensive 2010-present, stitched via `scripts/stitch_gdf_indices.py`.
- 22 corporate-action rescale outliers logged but correctly handled
  by the rescale-anchored stitch.

Status: **complete**. Both directories are now part of the daily
Drive cloud upload via the Railway-side `daily_cloud_upload` job
(symlinked into `/data/` by `init_persistent_storage.sh`).

---

## Phase 3 — Engine consolidation

### 3.1 Retire `backtest_momentum.py` for L6 path
- L6 v2 (`run_l6_v2_portfolio.py`) already runs on `_clean_engine`.
- Legacy L6 (`run_final_momentum_portfolio.py` → `backtest_momentum.py`) is
  the only remaining caller of the legacy engine.
- Decision needed: either migrate legacy L6 to `_clean_engine` and delete
  `backtest_momentum.py`, or leave legacy script as-is (its Thursday/Friday
  rebalance helper is independent of the daily pipeline).

### 3.2 Consolidate loaders
- Move `load_price_panels`, `load_benchmark` into `data_pipeline/loaders.py`.
- Collapse 3 universe loaders into one.
- Delete duplicate definitions.

### 3.3 Latest-pointer files
- After each portfolio run, write `data/<universe>/latest.json` with
  `{"path": "...", "timestamp": "...", "git_sha": "..."}`.
- `sync_service.py` reads `latest.json` instead of globbing `202*`.

### Validation Gate 3 (heaviest)
- Full historical re-run of L6 (2020-2026) on `_clean_engine`.
- Diff equity curve vs Phase 2 baseline:
  - Equity daily values must match within **1 bps**.
  - Trade list must match **≥ 99%** (allowing minor float-precision reordering
    on tied scores).
- If divergence exceeds tolerance: do not delete `backtest_momentum.py`;
  document the divergence in RESULTS.md and revisit.

---

## Testing strategy

1. **Golden-master regression** — JSON snapshot diffed at each gate.
2. **Unit tests** for new shared modules:
   - `scripts/tests/test_metrics_common.py` — synthetic equity curve →
     known CAGR/Sharpe/DD; synthetic trades → known turnover/hit-rate.
   - `scripts/tests/test_loaders.py` — synthetic price dir → expected
     pivot shape, ffill behavior, universe filtering.
3. **Smoke test** — `scripts/run_pipeline_smoke.py`:
   - 30-day window, runs full pipeline against frozen test data, asserts
     all artifacts exist and pass schema validation.
   - Wire into a pre-commit hook on `pipeline-improvements` branch.
4. **Dry-run mode** — extend `--dry-run` in orchestrator to print the full
   computed call plan + load-once data summary without executing.

---

## Out of scope (deferred)

- `experiments/` folder cleanup (user opted out).
- Backup folder consolidation (`nse500_data_merged/`, `nse500_data_historical/`).
- Railway volume audit / backup of `trade_matches` table.
- Hourly data pipeline (currently stale).
- Removing `build_momentum_signals.py` from the pipeline — pending user confirm
  of the Phase 0 finding.

---

## Open items pending decision

1. **Remove `build_momentum_signals.py` from daily pipeline?** Investigation
   confirms it's orphaned within the pipeline. Manual research tools that read
   `data/momentum/top25_signals.csv` continue to work unchanged.
2. **Migrate legacy `run_final_momentum_portfolio.py` to `_clean_engine`** in
   Phase 3, or leave the legacy Thursday/Friday helper standalone? L6 v2
   already covers the daily-pipeline path; the legacy script is only used
   manually for rebalance preview.
