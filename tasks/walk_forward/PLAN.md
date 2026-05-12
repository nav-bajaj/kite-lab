# Walk-Forward 2026 — Rolling 3+1 Robustness Check

## Why this work

The `tasks/oos_retune_2026/` project (May 2026) used a **single anchored split** — IS 2009-2016, OOS 2017-2026 sliced into three sub-windows. OM25 v3 and TL25 v3 were locked in under that split with strong pass-criterion results (OOS Sharpe 1.86 and 1.53 respectively).

That split is rigorous for over-fit detection but answers only one question: *would a 2016 researcher's chosen config hold up across 2017-2026?* It does not answer:

1. **Parameter drift** — would a researcher tuning in 2013 pick the same config as one tuning in 2018? If the IS-optimal config shifts heavily as the IS window slides forward, the "winner" we locked in is regime-dependent rather than timeless.
2. **Cross-universe robustness** — OM25 v3 is locked on Nifty 250, TL25 v3 on NSE 500, L6 momentum on NSE 500. Each strategy was tuned on one universe. Does the locked config still pass on the *other* universes?
3. **Strategy-strategy ranking stability** — on which OOS windows does each strategy lead? Is the ranking consistent or regime-flipping?

A **rolling 3-year IS / 1-year OOS** walk-forward (1-year step) on the full GDF-stitched panel (2009-2026, ~16.7 years) gives ~13 windows — enough to study drift and rank stability with reasonable statistical power. This is complementary to, not a replacement for, the anchored retune.

**Aspirational target:** at least 70% of OOS windows pass the same sub-window criterion as `oos_retune_2026` (Sharpe ≥ 0.7). A locked v3 config that holds up only on the 2017-2026 split but fails when the IS window slides back to 2010-2012 is a regime-tilt artifact, not a timeless strategy.

---

## Methodology

### Window enumeration

Data span: 2009-09-01 → 2026-05-08 (~16.7y on the GDF-stitched panel).

To leave warmup buffer for the longest lookback in any strategy (TL25 persistence = 252 trading days), anchor window 1 IS-start at **2010-09-01**. Rolling 3y IS, 1y OOS, slide by 1 year:

| Window | IS start | IS end | OOS start | OOS end | OOS regime |
|---|---|---|---|---|---|
| W01 | 2010-09-01 | 2013-08-31 | 2013-09-01 | 2014-08-31 | Pre-Modi rally |
| W02 | 2011-09-01 | 2014-08-31 | 2014-09-01 | 2015-08-31 | Modi rally peak |
| W03 | 2012-09-01 | 2015-08-31 | 2015-09-01 | 2016-08-31 | Demonetization bear |
| W04 | 2013-09-01 | 2016-08-31 | 2016-09-01 | 2017-08-31 | Recovery / GST run-up |
| W05 | 2014-09-01 | 2017-08-31 | 2017-09-01 | 2018-08-31 | Smallcap top + IL&FS |
| W06 | 2015-09-01 | 2018-08-31 | 2018-09-01 | 2019-08-31 | Quality-value bear |
| W07 | 2016-09-01 | 2019-08-31 | 2019-09-01 | 2020-08-31 | COVID crash + bounce |
| W08 | 2017-09-01 | 2020-08-31 | 2020-09-01 | 2021-08-31 | Mega rally |
| W09 | 2018-09-01 | 2021-08-31 | 2021-09-01 | 2022-08-31 | Inflation rotation |
| W10 | 2019-09-01 | 2022-08-31 | 2022-09-01 | 2023-08-31 | Range / pause |
| W11 | 2020-09-01 | 2023-08-31 | 2023-09-01 | 2024-08-31 | Smallcap mania |
| W12 | 2021-09-01 | 2024-08-31 | 2024-09-01 | 2025-08-31 | 2025 correction |
| W13 | 2022-09-01 | 2025-08-31 | 2025-09-01 | 2026-05-08 | Recovery (partial, ~8mo) |

**13 windows** (12 full + 1 partial OOS). W13's partial OOS will be reported separately and excluded from any "% of windows passing" denominator.

### Anti-overfit rules (pre-committed)

Same discipline as `tasks/oos_retune_2026/PLAN.md`:

1. **Selection criterion: highest IS Sharpe**, not IS CAGR. Sharpe is more stable.
2. **No look at OOS during search.** Run all per-window sweeps, lock the winner, then evaluate OOS.
3. **Drawdown floor in IS.** Reject any IS config with Max DD worse than -45%.
4. **Min-trades floor.** Reject configs with <40 trades in a 3y IS window (catches degenerate-config silent failures).
5. **Tie-breaker:** Sharpe rounded to 2dp; ties broken by lower IS turnover, then by shorter lookback.
6. **Universe = current snapshot.** Survivorship bias acknowledged, not addressed.

### Per-window pass criteria

For each window the locked-in `v3` config is the **baseline** comparator. The IS-best config is the **challenger**. We report:

- **Pass:** OOS Sharpe ≥ 0.7 (matches `oos_retune_2026` sub-window floor).
- **Challenger > baseline:** IS-best beats baseline on OOS Sharpe by ≥ 0.10 (noise margin).
- **IS→OOS Sharpe degradation:** `(IS_Sharpe - OOS_Sharpe) / IS_Sharpe`. <30% = robust; >50% = overfit.
- **Best/worst noise floor:** OOS Sharpe of IS-best vs IS-worst combo. If the gap < 0.20, the IS ranking carries no signal — flag the window.

### Headline outputs (not "the new winner")

This is a **robustness study, not an optimization.** Headlines we produce:

1. **Drift heatmap** — per strategy, per universe: optimal params per window stacked as a heatmap. Tight clustering = stable; scattered = regime-tilted.
2. **Pass-rate table** — % of windows where the locked v3 config passes Sharpe ≥ 0.7 in OOS, per strategy × universe.
3. **Strategy-rank stability** — which strategy wins OOS in each window? Consistent or flipping?
4. **Cross-universe sensitivity** — does the same strategy hold up across NSE 500 / Nifty 100 / Nifty 250?

We do NOT publish a "new locked config from W13" or similar. The locked v3 configs stay locked. This study informs *confidence* in those configs, not a re-tune.

---

## Scope: strategies × universes × parameter grids

### Strategies (3)

| Strategy | Signal script | Backtest script | Locked v3 universe |
|---|---|---|---|
| L6 momentum | `scripts/build_momentum_signals_flexible.py` | `scripts/backtest_momentum.py` | NSE 500 |
| OM25 | `scripts/build_om25_signals.py` | `scripts/backtest_om25.py` | Nifty 250 |
| TL25 | `scripts/build_trend_leaders_signals.py` | `scripts/backtest_trend_leaders.py` | NSE 500 |

### Universes (3)

`data/static/nse500_universe.csv` (499) · `data/static/nifty250_universe.csv` (250) · `data/static/nifty100_universe.csv` (100).

### Parameter grids (intentionally tight to keep compute manageable)

**Momentum** — 8 combos:
- `lookback_months`: 6, 9
- `rebalance_weeks`: 1, 2
- `min_hold_days`: 0, 8
- Pinned: `top_n=24`, `vol_floor=0.05`, `skip_days=0`, scenario `baseline`

**OM25** — 12 combos:
- `composite_weights` (UC/CR): 70/30, 50/50, 30/70
- `cadence`: weekly, biweekly, monthly
- `drawdown_stop_pct`: 15, 20, 25 → pinned to **20** (locked in v3); sweep weights × cadence only for grid manageability
- Actually: 3 (weights) × 3 (cadence) = **9 combos**. DD stop and return filter pinned.
- Pinned: `top_n=25`, `exit_buffer=20`, `lookback=252`, `min_obs=220`, `return_filter=on`, regime tilt enabled.

**TL25** — 6 combos:
- Score weights (Persistence / DD-Control / Momentum): 40/20/40 (v3 lock), 50/20/30, 30/30/40
- `drawdown_stop_pct`: 15, 20
- Pinned: `top_n=25`, `exit_buffer=20`, biweekly cadence with weekly rank-exit, 200 DMA eligibility.

### Compute budget

Per window per universe: 8 (mom) + 9 (OM25) + 6 (TL25) = **23 IS backtests**.

Plus OOS: per window per universe, 3 strategies × 3 evaluations (IS-best, locked-v3-baseline, IS-worst as noise floor) = 9 OOS backtests.

| Scope | IS runs | OOS runs | Total | Est. time @30s/bt |
|---|---|---|---|---|
| **MVP (NSE 500 only, all strategies, all windows)** | 23 × 13 = 299 | 9 × 13 = 117 | 416 | ~3.5 hr |
| **Phase 2 (add Nifty 100)** | +299 | +117 | +416 | +3.5 hr |
| **Phase 3 (add Nifty 250)** | +299 | +117 | +416 | +3.5 hr |
| **Full** | 897 | 351 | 1,248 | ~10 hr |

Run unattended (overnight). Realistic: MVP confirms the framework end-to-end, then Phases 2 and 3 are launches not new design.

---

## Reuse vs new code

### Reuse as-is (no edits)

- `scripts/multi_window_oos_eval.py` — the per-window metrics + pass-criteria utility. Already returns CAGR/Sharpe/Vol/MaxDD given an equity CSV and window list. Use it for both IS scoring and OOS evaluation.
- `scripts/run_oos_walkthrough.py` — for the **single-pass full-panel sanity check** at the start of every walk-forward run (confirms the production scripts still produce the expected locked-v3 OOS numbers before we start sweeping).
- All three production backtest scripts (`backtest_momentum.py`, `backtest_om25.py`, `backtest_trend_leaders.py`) — backtest engines stay frozen.
- All three signal builders.

### Modify (additive, backward-compatible)

Add `--start-date` and `--end-date` flags to the three signal builders **and** the three backtest scripts.

**Why both?** Signals computed on the full panel (un-truncated) and then sliced at backtest time is *almost* equivalent, but the score normalization in OM25 (`pct_rank` across the eligible universe) and TL25 (cross-sectional rank) is **cross-sectional per date** — so it's already date-local. Date filtering at backtest time alone is sufficient and cleanest. Final decision:

- **Signal builders:** keep un-truncated (signals computed on full panel, no edit needed).
- **Backtest scripts:** add `--start-date` and `--end-date`. Filter the calendar and entry-signal series after they load.

This isolates the change to the backtest layer and avoids recomputing signals per window. Concrete diff locations:

- `backtest_momentum.py` — `run_backtest()` signature gains `start_date`/`end_date` kwargs; filter `entry_signals` and `calendar` immediately after they're built. Sharpe is computed post-hoc from the resulting `momentum_equity.csv` via `multi_window_oos_eval.period_metrics`.
- `backtest_om25.py` and `backtest_trend_leaders.py` — equivalent.

Sharpe is NOT a column in `momentum_metrics.csv` today (verified). Either (a) extend `summarise_metrics` to add it, or (b) compute Sharpe from `*_equity.csv` in the orchestrator using the existing `multi_window_oos_eval.period_metrics`. Choose (b) — keeps production output stable.

### New files

```
scripts/run_walk_forward.py             # NEW — orchestrator
tasks/walk_forward/
  PLAN.md                               # this file
  PROGRESS.md                           # status log (created at execution)
  RESULTS.md                            # findings (created after MVP completes)
  results/                              # generated outputs
    {strategy}_{universe}/
      W{NN}/
        is_sweep.csv                    # per-combo IS Sharpe/CAGR/DD/turnover
        oos_chosen/                     # IS-best applied to OOS, full backtest output
        oos_baseline/                   # locked v3 applied to OOS
        oos_worst/                      # IS-worst applied to OOS (noise floor)
      window_summary.csv                # cross-window summary for this (strategy,universe)
    cross_summary.csv                   # final aggregate across all strategy×universe
    drift_heatmap.png                   # optional, generated post-hoc
```

`scripts/run_walk_forward.py` skeleton:

1. Parse args: `--strategies`, `--universes`, `--windows` (default all), `--limit-combos` for dry-runs, `--dry-run` flag.
2. Sanity gate: run a full-panel backtest of each locked v3 config and assert OOS metrics within tolerance of `tasks/oos_retune_2026/RESULTS.md` (catches data-pipeline drift before we waste hours sweeping).
3. For each `(strategy, universe, window)`: enumerate the strategy's param grid; for each combo invoke the backtest with `--start-date IS_start --end-date IS_end`; parse equity CSV via `multi_window_oos_eval.period_metrics`; apply DD-floor + min-trades filter; rank by Sharpe; pick top-1 and bottom-1.
4. For each `(strategy, universe, window)`: run 3 OOS backtests (chosen / baseline / worst).
5. Write per-window CSVs and the cross summary.
6. Generate the drift heatmap and pass-rate table.

---

## Verification gates

Before trusting any walk-forward result:

1. **Date-filter correctness.** For each backtest script: a backtest with `--start-date X --end-date Y` produces an equity curve with first/last date inside [X, Y]. Asserted as a pytest in `tests/test_walk_forward_date_filter.py`.
2. **No future leak.** For each strategy: an IS-only backtest (e.g., 2010-09 → 2013-08) followed by an OOS-only backtest (2013-09 → 2014-08) of the same params produces equity curves whose IS portion exactly equals an IS run, AND whose OOS portion uses no prices/signals from before its start. Specifically: no trade in OOS references a signal date inside IS.
3. **Locked-v3 sanity match.** Re-running each v3 config over the canonical IS+OOS-full window must reproduce the headline numbers in `tasks/oos_retune_2026/RESULTS.md` within ±0.02 Sharpe / ±0.5pp CAGR. If not, something in the data panel or scripts has drifted since the lock-in.
4. **Smoke run.** A 2-window, 1-strategy, 1-universe, 2-combo dry-run completes in <10 min and produces all expected output files.
5. **IS-best vs IS-worst OOS gap.** As an auditable diagnostic: log this gap per window. If many windows have gap < 0.20, the IS Sharpe ranking is noise and the whole study is suspect.

---

## Phased execution plan

### Phase 0 — Infra (1 day, ~4 hours coding + 1 hr verification)
- Add `--start-date` / `--end-date` to all three backtest scripts.
- Write `scripts/run_walk_forward.py` skeleton.
- Pass verification gates 1, 3, 4.

### Phase 1 — MVP on NSE 500 (~4 hours unattended compute)
- Run all 3 strategies × NSE 500 × all 13 windows.
- 416 backtests total.
- Inspect per-window IS-best vs locked-v3 OOS; check verification gate 2 and gate 5.
- Write Phase 1 findings to `tasks/walk_forward/RESULTS.md`.

### Phase 2 — Expand to Nifty 100 and Nifty 250 (~7 hr)
- Same runs on the other two universes (no new code).
- Update `RESULTS.md` with cross-universe pass-rate table and drift heatmap.

### Phase 3 — Narrative report (1 day)
- Markdown report with: drift heatmap, pass-rate table, strategy-rank stability per window, head-to-head OOS plots.
- Recommendation for each locked v3: keep / re-examine / formal re-tune trigger.

### Decision gate after Phase 1

After MVP, decide:
- **Continue to Phase 2** if the framework works and Phase 1 findings are interesting.
- **Stop and re-design** if verification gates 2 or 5 fail consistently.
- **Reduce grid** if any strategy's IS sweep is dominated by one combo (gives no comparison signal).

---

## Open questions for the user

1. **Universe scope.** Confirm "all 3 universes" for each strategy — including running OM25 on NSE 500 and Nifty 100 (it's locked on Nifty 250), and TL25 on Nifty 100/250 (locked on NSE 500). Yes per earlier conversation, but flagging again because cross-universe runs are not light.
2. **Survivorship bias.** Skip historical index composition (per `oos_retune_2026` precedent) — acknowledged in report only. Confirm.
3. **Compute budget.** OK to run unattended overnight for the full 10-hour Phase 1+2+3? Or restrict to NSE 500 only first?
4. **Re-tune trigger.** If a locked v3 fails the pass-rate threshold (e.g., <60% of windows), do we escalate to a formal re-tune project, or just document and keep the lock?

---

## What this plan deliberately does NOT do

- Does not re-tune the locked OM25 v3 or TL25 v3 configs. Walk-forward is a check, not a replacement.
- Does not touch the production signal builders (only the backtest scripts get date flags).
- Does not source point-in-time index composition. Survivor bias acknowledged.
- Does not add Monte Carlo sampling — the chosen grids are tight enough for systematic sweep.
- Does not extract shared helpers (`load_metrics`, etc.) from existing sweep scripts. Walk-forward uses its own helpers; refactor is a separate concern.
- Does not commit anything until you approve the plan and the Phase 0 diff.
