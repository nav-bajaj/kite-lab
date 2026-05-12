# Walk-Forward 2026 — Execution Log

**Status:** COMPLETED 2026-05-12. Findings in `RESULTS.md`; HTML report at
`reports/walk_forward_summary.html`.

---

## Timeline

### 2026-05-12 — Planning + scope tightening
- User reviewed original `PLAN.md` and flagged ~10-hour runtime as too long.
- Explored speedup levers: existing OM25/TL25 sweep harnesses already prove
  `_clean_engine.run_strategy()` runs in ~1s per backtest with pre-loaded
  panels. Plan's ~30s/backtest assumed CLI invocations with full panel
  re-load each time.
- User decisions:
  1. Drop L6 momentum (focus on the recently-locked v3 configs)
  2. Skip Modal/cloud for now (local-first with multiprocessing)
  3. Tiny smell test first before committing to full sweep
- Refined plan filed at `~/.claude/plans/sunny-seeking-hartmanis.md`.

### 2026-05-12 — Phase 0 smell test
- Built `scripts/run_walk_forward.py` with load-once + ProcessPoolExecutor.
- Ran TL25 v3 × NSE 500 × 3 windows (W01, W07, W13) × 6 combos = 27 backtests.
- **Wall-clock: 11.6 seconds.** Framework works end-to-end.
- IS-best-vs-IS-worst OOS Sharpe gap: 0.24 / 0.19 / -0.34 across the 3 windows.
  Diagnostic signal: IS Sharpe ranking is weak across these 3 windows but the
  locked-v3 baseline passes all 3.

### 2026-05-12 — Phase 1 production-universe sweep
- TL25 v3 × NSE 500 + OM25 v3 × Nifty 250, all 13 windows, full grids.
- 26 window-runs (2 × 13). 6 workers.
- **Wall-clock: 285 seconds (~5 min).**
- Pass rate: 11/13 = **84.6%** for both strategies on their production universes.
- Failure windows for TL25: W06 (2018-19 IL&FS), W12 (2025 small-cap correction).
- Failure windows for OM25: W12, W13.

### 2026-05-12 — Phase 2 cross-universe sweep
- Both strategies × all 3 universes × all 13 windows = 78 window-runs. 6 workers.
- **Wall-clock: 835 seconds (~14 min).**
- TL25 generalizes well (84.6% on NSE 500 AND Nifty 250, 76.9% on Nifty 100).
- OM25 degrades more outside Nifty 250 (84.6% → 76.9% on Nifty 100 → 69.2% on NSE 500).
- W06, W12, W13 universally hard across all combos.

### 2026-05-12 — Phase 3 report
- Built `scripts/walk_forward_report.py` — 5 charts (pass-rate heatmap, OOS
  trajectory, gap distribution, IS-vs-OOS scatter, drift heatmap) + 4 tables
  + narrative callouts.
- Wrote `RESULTS.md` and `reports/walk_forward_summary.html`.
- Final recommendation: **keep locked v3 configs, no re-tune**.

---

## Compute summary

| Phase | Window-runs | Wall-clock | Notes |
|---|---|---|---|
| Phase 0 (smell test) | 3 | 11.6s | TL25 only, 1 worker, validates framework |
| Phase 1 (production universes) | 26 | 285s | Both strategies, 6 workers |
| Phase 2 (cross universes) | 78 | 835s | Adds Nifty 100 + cross-universe combos, 6 workers |
| Phase 3 (report) | — | <30s | Chart + HTML generation |
| **Total** | **~110** | **~19 min** | vs original plan's ~10 hr (~30× speedup) |

The speedup came from the load-once orchestrator pattern + multiprocessing
across (strategy, window) pairs. Modal/cloud was sketched but not needed.

---

## Outputs

| Path | Contents |
|---|---|
| `tasks/walk_forward/PLAN.md` | Original methodology + execution scope changes |
| `tasks/walk_forward/PROGRESS.md` | This log |
| `tasks/walk_forward/RESULTS.md` | Findings + recommendation |
| `tasks/walk_forward/results/smell_test/` | Phase 0 outputs |
| `tasks/walk_forward/results/phase1/` | Phase 1 outputs (26 window-runs) |
| `tasks/walk_forward/results/phase2/` | Phase 2 outputs (78 window-runs) |
| `reports/walk_forward_summary.html` | Phase 3 visual report (5 charts + tables) |
| `scripts/run_walk_forward.py` | Orchestrator (load-once + multiprocessing) |
| `scripts/walk_forward_report.py` | Report generator |
