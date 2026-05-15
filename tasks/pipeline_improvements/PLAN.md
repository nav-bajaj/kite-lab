# Daily Pipeline Improvements — Plan

**Branch:** `pipeline-improvements`
**Started:** 2026-05-15
**Owner:** navdeep
**Status:** Phase 0 in progress

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
