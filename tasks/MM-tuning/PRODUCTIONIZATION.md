# L6 Engine Migration + COMBO Defensive Productionization

**Status:** PLAN — pending implementation.

**Context:** MM-tuning workstream surfaced a Defensive product candidate
(COMBO 50-50 + Regime, biweekly Fri→Mon, see `DD_REDUCTION_RESEARCH.md`).
Putting it into production benefits from first migrating L6 to the new
`_momentum_engine`-based path — both strategies will then share the same
engine, making the wiring cleaner.

Decision sequence agreed:
1. **L6 engine migration FIRST** (with parallel-run verification)
2. **COMBO Defensive productionization SECOND** (after L6 migrated)
3. **TL25 v3 stays as-is** in production; improvements done off-pipeline
4. **OM25 v3 stays as-is** — already productionized in prior session

---

## Phase 1: L6 engine migration (parallel-run, then cutover)

### Why migrate

The new `_momentum_engine.py` (atop `_clean_engine.run_strategy`):
- Calibrated to legacy within **0.4pp CAGR / 0.01 Sharpe** on same data source
- Faster (~1s vs ~10-15s per backtest) — useful for research, not daily
- Code consistency with OM25 v3, TL25 v3, and the new COMBO strategy
- Already includes the delisting bug fix; legacy script also has it now

### Parallel-run approach

Both engines run daily for ~5-7 trading days. Output diffed each day.
Cutover after verification window if outputs are stable.

### Implementation steps

1. **Create `scripts/run_l6_v2_portfolio.py`** — orchestrator mirroring
   `run_om25_v3_portfolio.py`:
   - Uses `_momentum_engine.BASELINE` (Thursday signal, weekly, top_n=24,
     min_hold=8, vol_floor=0.05, etc. — matches current production)
   - Output dir: `data/l6_v2_portfolios/l6_v2_portfolio_<YYYYMMDD>_<HHMMSS>/`
   - Dashboard CSVs at `<run>/backtests/baseline/momentum_*.csv` (same
     schema as OM25 v3 / TL25 v3)
   - Native CSVs at run dir root for strategy-aware tooling
   - CLI flags for prices-dir, start date, output dir overrides

2. **Add `l6_v2` to dashboard backend:**
   - `kite-api/app/config.py:UNIVERSES` — new entry, `data_dir: nse500_data`,
     `universe_file: data/static/nse500_universe.csv`,
     `portfolio_dir: data/l6_v2_portfolios`
   - Extend `UniverseId` Literal
   - `kite-api/app/services/sync_service.py:get_latest_experiment_dir` —
     new branch for `l6_v2`
   - `kite-api/app/services/sync_service.py:sync_all_universes` — append `l6_v2`
   - `kite-api/app/services/positions_service.py` — extend regex pattern
     for `l6_v2_portfolio_*`, add experiments_dir branch
   - `scripts/sync_to_database.py` — CLI help + default-sync list

3. **Daily pipeline integration (parallel-run mode):**
   - `scripts/run_daily_pipeline.py` — add a NEW step `"Build L6 v2 portfolio"`
     positioned AFTER `"Build momentum rankings"` (which builds the legacy
     output) but before the OM25/TL25 steps
   - Both legacy AND v2 produce daily outputs during parallel-run period
   - Dashboard initially shows LEGACY L6 to subscribers; v2 is read-only
     for internal verification

4. **Verification harness** — new script
   `scripts/_l6_engine_parallel_diff.py`:
   - Runs nightly (or as a separate step in daily pipeline)
   - Loads legacy holdings (`data/final_portfolio/final_portfolio_24.csv` or
     latest `experiments/final_portfolio/` dir)
   - Loads v2 holdings (`data/l6_v2_portfolios/.../momentum_holdings.csv`)
   - Computes diff: how many symbols match, how many differ
   - Reports symbol-level delta, weight-level delta, expected trade list
     differences
   - Acceptance criteria: ≥80% holding overlap; positions that differ should
     have rank-tie or boundary explanations

5. **Cutover** (after 5-7 trading days of clean diffs):
   - Swap the dashboard `nse500` universe entry's `portfolio_dir` to point
     at `data/l6_v2_portfolios/`
   - Remove the legacy "Build momentum rankings" + "Generate final portfolio"
     pipeline steps (or downgrade them to research-only)
   - Keep the legacy infrastructure intact as a fallback for ~1 month
   - Update CLAUDE.md to reflect the new engine path

### Critical files

| File | Action |
|---|---|
| `scripts/_momentum_engine.py` | Read-only — already done |
| `scripts/_clean_engine.py` | Read-only |
| `scripts/run_l6_v2_portfolio.py` | **NEW** — orchestrator |
| `scripts/_l6_engine_parallel_diff.py` | **NEW** — verification |
| `kite-api/app/config.py` | Edit — UNIVERSES + UniverseId |
| `kite-api/app/services/sync_service.py` | Edit — get_latest_experiment_dir + rotation |
| `kite-api/app/services/positions_service.py` | Edit — regex + experiments_dir |
| `scripts/sync_to_database.py` | Edit — CLI |
| `scripts/run_daily_pipeline.py` | Edit — add v2 step |

### Acceptance criteria

- v2 produces output every day matching the same schema as OM25 v3 / TL25 v3
- 80%+ holding overlap with legacy on any given snapshot
- CAGR/Sharpe delta < 1pp on the production-window comparison
- After cutover: dashboard reads from v2 path only; legacy held as fallback

---

## Phase 2: COMBO Defensive productionization

### Strategy spec (locked)

| Parameter | Value |
|---|---|
| Composition | COMBO 50-50 (L6 + OM25 v3, L6 priority dedup) |
| L6 picks | Top 12 from NSE 500 (using `_momentum_engine.BASELINE`) |
| OM25 picks | Top 12 from Nifty 250 (using `OM25_LOCKED`), backfilled non-overlapping with L6's 12 |
| Cadence | Bi-weekly entry |
| Signal day | Friday close |
| Execution day | Monday OHLC/4 |
| Top-N | 24 (12 + 12) |
| Position sizing | Equal-weight 1/24, max 7.5% per stock, drift after entry |
| Min hold days | 8 |
| Slippage | 0.2% (20 bps) |
| Regime overlay | NIFTY 100 vs 100-DMA, 3-day confirm |
| Bear exposure | 50% (when bear regime confirmed) |
| Bull exposure | 100% |

### Implementation steps

1. **Create `scripts/combo_defensive.py`** — strategy module with locked
   defaults dict and the priority-dedup score factory:
   - `LOCKED` dict mirroring the spec above
   - `make_combo_score_fn(l6_score_fn, om25_score_fn, n_per=12, priority_order)`
     — the dedup logic from research scripts, productionized

2. **Create `scripts/run_combo_defensive_portfolio.py`** — orchestrator:
   - Loads price panels + L6 panels + OM25 returns + regime panel
   - Builds combined score_fn
   - Calls `run_strategy` with biweekly Friday entry, 100-DMA regime,
     bear=50%
   - Dual output: native `combo_*.csv` at run dir root + dashboard
     `momentum_*.csv` at `backtests/baseline/`
   - Output dir: `data/combo_defensive_portfolios/combo_defensive_portfolio_<YYYYMMDD>_<HHMMSS>/`

3. **Wire to dashboard backend:**
   - `kite-api/app/config.py:UNIVERSES` — new entry `combo_defensive`
   - Extend `UniverseId` Literal
   - `sync_service.get_latest_experiment_dir` + `sync_all_universes`
   - `positions_service` regex + branch
   - `sync_to_database.py` CLI

4. **Daily pipeline integration:**
   - `scripts/run_daily_pipeline.py` — add step AFTER OM25 v3 (so OM25
     panels can be re-used; and order matches dependency)
   - Step name: `"Build COMBO Defensive portfolio"`

5. **Verification:**
   - Smoke test: run from CLI, verify outputs land correctly
   - DB sync test: `python scripts/sync_to_database.py --universe combo_defensive`
   - Verify positions show up in dashboard (or at least that the
     positions_service can find them)

### Critical files

| File | Action |
|---|---|
| `scripts/combo_defensive.py` | **NEW** — strategy module |
| `scripts/run_combo_defensive_portfolio.py` | **NEW** — orchestrator |
| `kite-api/app/config.py` | Edit |
| `kite-api/app/services/sync_service.py` | Edit |
| `kite-api/app/services/positions_service.py` | Edit |
| `scripts/sync_to_database.py` | Edit |
| `scripts/run_daily_pipeline.py` | Edit |

### Test plan

Same end-to-end checks as TL25 v3 productionization:
1. Standalone smoke test: `python scripts/run_combo_defensive_portfolio.py --start 2017-01-01`
2. CSV schema verification (holdings has correct columns)
3. `get_latest_experiment_dir('combo_defensive')` returns the right dir
4. `PositionsService.sync_from_csv('combo_defensive')` syncs N positions
5. `sync_to_database.py --universe combo_defensive` completes successfully
6. `run_daily_pipeline.py --dry-run` shows the new step in correct position

---

## Out of scope (explicitly)

- **TL25 v3 changes**: stays running as-is in production. Improvements to TL25
  happen off-pipeline (research branch); no production touches.
- **Frontend (kite-dashboard)**: adding universe-selector options for
  `l6_v2` and `combo_defensive` is a separate Next.js codebase change;
  backend will return the data, UI exposure is a follow-up.
- **Customer-facing renames**: "Aggressive / Defensive / Set-and-forget"
  product names are positioning, not technical config. Branding decisions
  separate from this implementation.

## Decision log

- 2026-05-14: Plan written. Sequence: L6 engine migration first (parallel-run
  for 5-7 days, then cutover), COMBO Defensive productionization second.
  TL25 v3 stays in production unchanged. OM25 v3 already productionized.
