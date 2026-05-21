# COMBO 3-state Breadth Regime — Production Candidate Evaluation

**Goal**: rigorously evaluate a replacement for the production COMBO Defensive
regime gate, swapping the NIFTY-100 close-vs-100dma 2-state for a breadth-
driven 3-state (bull / bear / deep_value) with sticky-deep semantics.

**Status (2026-05-21):** preliminary backtest looks promising. Needs robust
verification before considering for production.

---

## What we're evaluating

Replace production COMBO's regime gate:

| Lever | Production (A_PROD) | Candidate (D_BREADTH) |
|---|---|---|
| Regime signal | NIFTY-100 close vs 100-DMA, 3-day confirm | breadth `avg_dist_from_200dma`, 3-day confirm |
| States | bull / bear | bull / bear / deep |
| Exposure (bull) | 100% | 100% |
| Exposure (bear) | 50% | 50% |
| Exposure (deep) | n/a | 100% (re-deploy at extreme oversold) |
| Bear entries | skipped (`bear_skips_entries=True`) | allowed at scaled weight (`=False`) |
| State machine | n/a | sticky-deep: `bull → bear → deep → bull` (deep exits only to bull) |

Everything else (universes, score, cadence, sizing, slippage) is identical to
production.

## Preliminary backtest summary (2009-09 → 2026-05, single full-span)

|  | A_PROD (status quo) | D_BREADTH (candidate) |
|---|---|---|
| FULL CAGR | 31.88% | **35.13%** |
| FULL Sharpe | 1.552 | 1.548 |
| FULL MaxDD | -25.60% | **-24.43%** |
| FULL Calmar | 1.245 | **1.438** |
| OOS-A Sharpe (IL&FS) | 1.27 | **1.77** |
| OOS-C Sharpe (recent) | **1.61** | 1.55 |
| 2021+ Sharpe | **1.99** | 1.84 |
| End-state holdings | 8 | **24** |
| End-state cash | 81% | **27%** |

The headline tradeoff: D_BREADTH wins on long-term CAGR and Calmar plus the
subscriber-comprehensible 24-stock structure, costs some recent-era Sharpe
and MaxDD (because A_PROD's compounding cash buildup gives stronger drawdown
protection during long bears).

That preliminary result is the starting point — we need to verify it's
robust before pushing it to production.

---

## Test battery (in priority order)

### T1. Walk-forward stress test (the robustness gate)

Same procedure as `walk_forward_2026`: rolling 3-year IS / 1-year OOS slices
across the full timeline. ~78 slices. For each slice, run both A_PROD and
D_BREADTH and record OOS Sharpe / CAGR / MaxDD. Pass criteria:

- D_BREADTH wins OOS Sharpe in ≥50% of slices (no consistent edge for production)
- D_BREADTH wins OOS Sharpe in ≥70% of slices (deployable upgrade)
- D_BREADTH wins OOS Sharpe in ≥85% of slices (strong upgrade)

The OOS-A IL&FS-style years should not be doing all the work. If the win
concentrates in a single 3-year stretch, this is sample-of-one.

### T2. Year-by-year vs A_PROD

Slice the FULL backtest into calendar years. Compare CAGR, Sharpe, MaxDD,
hit rate of monthly returns. Identify:

- Years where D_BREADTH outperforms (and by how much)
- Years where D_BREADTH underperforms (especially the recent ones)
- Whether the OOS-A win is one-off (e.g. just 2018 IL&FS) or recurs

### T3. Differentiation from existing production portfolios

Required before considering as a separate product OR before pitching to
subscribers as an upgrade (subscribers need clarity on what COMBO is doing
vs L6, OM25, TL25).

- Daily-return correlation: D_BREADTH vs L6, OM25, TL25 (per window)
- Holdings overlap (Jaccard at every biweekly Friday) vs L6, OM25, TL25
- Compare against A_PROD's correlations and overlaps for context
- If D_BREADTH looks materially similar to L6 (or OM25), the marketing story
  weakens

### T4. Sensitivity to regime thresholds

The chosen thresholds `(bear_entry, bear_exit, deep_entry) = (0.00, 0.05, -0.10)`
come from the breadth atlas. Verify the result isn't a knife-edge:

- Sweep `bear_entry` ∈ {-0.05, 0.00, 0.05}
- Sweep `bear_exit` ∈ {0.00, 0.05, 0.10}
- Sweep `deep_entry` ∈ {-0.15, -0.10, -0.05}

Goal: D_BREADTH's edge over A_PROD should hold across reasonable threshold
variations. If it only works at one specific config, that's overfitting.

### T5. Sensitivity to breadth metric

The atlas had 6 candidate metrics. `avg_dist_from_200dma` was the OM25-3state
winner. Verify the COMBO result is consistent:

- Re-run with `pct_above_200dma` (binary cousin)
- Re-run with `net_new_highs_pct` (asymmetric, independent ρ=0.73)
- Re-run with `mcclellan_sum` (slow flow)

If only `avg_dist_from_200dma` works, the result is metric-dependent and
fragile.

### T6. Sensitivity to bear exposure level

Currently 50%. Sweep ∈ {0.3, 0.5, 0.7}. The "right" defensive level might
not be 50% — could be the difference between matching and beating A_PROD
on recent-era Sharpe.

### T7. Live-state snapshot

What does D_BREADTH hold today on the same Kite data as live production?
- List current 24 holdings
- Compare against what A_PROD currently holds (5-8 names)
- Identify overlap and divergence

Helps quantify the "user-visible change" if we deploy this.

### T8. Risk attribution (deferred to after T1-T3 pass)

If D_BREADTH passes the gates, dig into where the drawdowns come from:
- Position concentration during bear → deep transitions
- Sector tilts (if breadth crashes coincide with specific sectors hit)
- Per-position contribution to peak-to-trough during the larger drawdowns

This is for understanding the strategy, not for blocking deployment.

---

## Pass / fail criteria for production replacement

D_BREADTH replaces A_PROD if **all** of the following hold:

1. **T1 walk-forward**: D_BREADTH wins ≥70% of OOS slices on Sharpe
2. **T2 year-by-year**: no calendar year shows D_BREADTH catastrophically worse than A_PROD (max year-spread within -10pp)
3. **T4 threshold sensitivity**: D_BREADTH's edge holds across all 27 threshold combinations (3³ sweep), no single config is doing the work
4. **T3 differentiation**: D_BREADTH's daily-return correlation with L6 stays below 0.85 (production COMBO is currently around 0.78), holdings overlap with L6 stays below 50%
5. **T7 live snapshot**: D_BREADTH's current holdings make sense (not obviously broken)

Soft considerations (don't block but worth thinking about):
- T5 metric robustness: nice if 2+ metrics give similar results, OK if only `avg_dist_from_200dma` works
- T6 bear-exposure sweep: if 0.6 or 0.7 dominates 0.5, change the parameter

---

## File index

```
tasks/breadth_atlas/combo_3state/
  PLAN.md                       # this file
  RESULTS.md                    # final writeup (after tests complete)
  combo_regime_diagnostic.py    # A_PROD vs B_BEAR_ENTRIES vs C_ALWAYS_100 (the discovery work)
  combo_breadth_3state.py       # A vs B vs D_BREADTH (the candidate)
  walkforward.py                # T1 (to be written)
  yearly.py                     # T2 (to be written)
  diff_existing.py              # T3 (to be written)
  sensitivity.py                # T4 + T5 + T6 (to be written)
  live_snapshot.py              # T7 (to be written)
```

Run outputs land under `runs/<ts>/` and are gitignored (regenerable).

---

## Order of execution

T1 first. If walk-forward fails the 70% bar, everything else is moot.
T2 + T3 next (they're cheap once T1 is set up).
T4-T6 only if T1-T3 pass.
T7 anytime — it's a quick live-data snapshot.

Walk-forward backtest will take longest (~78 IS-OOS slices × 2 variants × ~30s each = ~80 min). Worth running in background.
