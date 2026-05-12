# Walk-Forward Robustness Study — Results

**Status:** Phases 1-4 completed 2026-05-12. Locked v3 configs validated; no re-tune.

**Scope:** OM25 v3 and TL25 v3, three universes (NSE 500, Nifty 250, Nifty 100), 13 rolling 3y-IS / 1y-OOS windows from 2010-09 to 2026-05. **78 OOS validations total.**

**HTML report:** `reports/walk_forward_summary.html` (charts + interactive tables).

---

## Pass-rate matrix (locked v3 baseline OOS Sharpe ≥ 0.7)

| Strategy | NSE 500 | Nifty 250 | Nifty 100 |
|---|---|---|---|
| **TL25 v3** | **84.6%** (★) | 84.6% | 76.9% |
| **OM25 v3** | 69.2% | **84.6%** (★) | 76.9% |

★ = production universe.

## Headline findings

1. **Both locked v3 configs survive walk-forward stress testing.** 84.6% pass rate on their respective production universes is meaningful — these aren't curve-fits to the 2017-2026 OOS window.

2. **TL25 v3 is more universe-robust** than OM25 v3 (84.6% on TWO universes vs OM25's 84.6% on one). The trend-quality signal is more universally applicable than capture-asymmetry, which needs universe breadth to work.

3. **IS Sharpe ranking is weak signal** — mean gap between IS-best and IS-worst OOS Sharpe is +0.37 for OM25 (modest signal) and **−0.08 for TL25 (pure noise)** across 39 windows each. Picking the IS-best config gives you nothing on average for TL25 and only a small edge for OM25 — and the locked v3 baseline already beats both.

4. **Failure windows are universal regime tails:**
   - **W06** (OOS 2018-09 → 2019-08): IL&FS-driven quality-value bear, hostile to momentum/trend
   - **W12** (OOS 2024-09 → 2025-08): 2025 small-cap correction
   - **W13** (OOS 2025-09 → 2026-05): partial recovery; insufficient data window
   These are not fixable via re-tuning; they're characteristic drawdowns of the strategy class.

## Phase 4 — Alternative IS metrics (added after Phase 1-3)

Question raised: would picking by an alternative IS metric (Calmar, multi-criteria, Sharpe+Calmar composite) instead of IS Sharpe give better OOS predictions?

**Method:**
- Phase 4a: cheap re-rank — for each window, compute IS-top-1 under each metric using existing `is_sweep.csv` data. Many new top-1 picks happen to be one of {challenger, baseline, worst} for which we already have OOS data.
- Phase 4b: focused re-run — for OM25 windows where Calmar picks a config we don't have OOS for, run those OOS backtests (14 missing combos, ~30s).

**Result (full unbiased sample, OM25 v3, n=39 windows across 3 universes):**

| Metric | Mean OOS Sharpe | vs locked baseline | Pass rate |
|---|---|---|---|
| Sharpe (current) | 1.729 | +0.093 | 76.9% |
| Calmar (alternative) | 1.743 | +0.108 | 76.9% |
| **Δ** | **+0.014** | **+0.015** | **0** |

The Phase 4a hint of +0.188 advantage for Calmar was **selection bias** — it came from comparing on sub-samples where Calmar's pick happened to overlap with one of three configs we'd already evaluated OOS. The Phase 4b unbiased comparison shrinks the advantage to +0.014, which is well within window-to-window noise.

**Conclusion:** alternative IS selection metrics do NOT meaningfully improve OOS performance for either strategy. This *strengthens* the original recommendation — locked v3 configs are robust not only to a single IS selection metric, but across multiple plausible alternatives.

For TL25 v3, no Phase 4b was needed; Phases 1-2 already showed the noise-floor (mean Δ vs baseline ≈ 0 regardless of selection metric).

## Recommendation

**Do not re-tune OM25 v3 or TL25 v3.** The locked configs from `tasks/oos_retune_2026/` hold up under walk-forward stress, **and** the choice of IS Sharpe (vs Calmar, multi-criteria, or composite) is not load-bearing — alternative metrics give statistically indistinguishable OOS results.

Manage W06-style and W12-style drawdowns at the portfolio level (position sizing, risk overlay), not at the strategy-config level.

## Methodology recap

- **Windows:** 13 rolling 3y-IS / 1y-OOS, step 1y, starting IS=2010-09-01 (warmup buffer).
- **Param grids:** TL25 = 6 combos (3 weight × 2 DD stops); OM25 = 9 combos (3 UC/CR weights × 3 cadences). Tighter than original plan grids — sufficient for robustness measurement.
- **Anti-overfit floors:** IS Max DD must be shallower than -45%; minimum 40 round-trip trades in 3y IS.
- **No CLI flag changes** to production backtest scripts. Orchestrator calls `_clean_engine.run_strategy()` directly with pre-loaded panels (~1s per backtest).
- **Total compute:** Phase 1 (26 window-runs) ran in 285s on M-series Mac with 6 workers; Phase 2 (78 window-runs) in 835s; Phase 4a (alt-metric re-rank from existing CSVs) <1s; Phase 4b (14 missing OM25 OOS runs for Calmar) 34s. **Combined: ~20 min wall-clock** for the entire study.

## Files

| Path | Purpose |
|---|---|
| `scripts/run_walk_forward.py` | Orchestrator (load-once, multiprocessing) |
| `scripts/walk_forward_report.py` | This report generator |
| `tasks/walk_forward/PLAN.md` | Original methodology doc |
| `tasks/walk_forward/results/phase1/cross_summary.csv` | Phase 1 results (26 rows) |
| `tasks/walk_forward/results/phase2/cross_summary.csv` | Phase 2 results (78 rows — includes Phase 1) |
| `reports/walk_forward_summary.html` | HTML summary with charts |
| `tasks/walk_forward/RESULTS.md` | This file |

Per-window detail (each `(strategy, universe, window)` subdir):
- `is_sweep.csv` — all combos with IS metrics
- `oos_results.csv` — challenger / baseline / worst on OOS
- `oos_{role}_equity.csv` — OOS equity curve per role
