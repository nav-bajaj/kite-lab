# OOS Retune 2026 — Robust IS/OOS Rebuild of OM25 and TL25

## Why this work

The current OM25 and TL25 production strategies were tuned on **2020-2026** as the in-sample period. The recent GDF backfill (alt-data branch → main) gave us 2009-2019 history for the first time, and we used that as out-of-sample (OOS).

That OOS testing exposed two issues:

1. **OM25 V2 (May 2026 review)** dropped its trailing stop and positive-return filter. IS CAGR jumped 35% → 50%, but on the GDF-backfilled OOS window:
   - **OOS Sharpe fell 1.46 → 1.08**
   - **OOS Max DD blew out -38% → -55%**
   - The "improvement" was IS-regime-specific.

2. **TL25 V2** is cleaner — it improves OOS too — but production current_best still only delivers OOS Sharpe 1.34 / OOS CAGR 26%. Below the 1.5 / 40% target we believe is needed for a strategy investors can put real money behind.

The strategies are over-tuned to a regime (2020-2026) which itself was a once-in-a-decade smallcap/midcap bull. To break the overfit, we **invert IS and OOS**:

- **IS = 2009-2016** (8 years; ~7 usable after 252-day warmup)
- **OOS = 2017-2026** (10 years; split into 3 sub-windows for multi-regime evaluation)

Goal: a **timeless** OM25 and TL25 — strategies that would have been built in 2016 with 2009-2016 data and held up across the next 10 years.

Aspirational target: **40% CAGR / 1.5 Sharpe** on full OOS, with sub-window Sharpe ≥ 0.7 as a hard pass criterion.

---

## Approach

**Constrained re-tune** — keep the core thesis of each strategy, search hyperparameter space within bounds:

- OM25: Omega ratio composite ranking
- TL25: 3-component trend score (persistence + drawdown + momentum)

No new score components, no universe changes, no new strategies. Pure parameter search with anti-overfit discipline.

### IS / OOS split

| Window | Period | Length | Notes |
|---|---|---|---|
| **IS** | 2009-09-01 → 2016-12-31 | ~7.3y usable | Tune all hyperparameters here |
| **OOS-A** | 2017-01-01 → 2019-12-31 | 3y | Sideways/quality-value bear; IL&FS year |
| **OOS-B** | 2020-01-01 → 2022-12-31 | 3y | COVID crash + mega rally + 2022 inflation rotation |
| **OOS-C** | 2023-01-01 → 2026-05-08 | ~3.4y | Small/mid-cap mania + 2025 correction |

### Pass criterion (per strategy)

The chosen config must satisfy ALL:
- IS Sharpe ≥ 1.0 (sanity check)
- OOS aggregate Sharpe ≥ 1.0
- OOS-A Sharpe ≥ 0.7
- OOS-B Sharpe ≥ 0.7
- OOS-C Sharpe ≥ 0.7
- OOS aggregate Max DD ≥ -45%

The 0.7 floor (vs 1.0 target) acknowledges sub-windows can have unfavorable regimes. If a config is below 0.7 in any sub-window, reject it even if the aggregate is great. Aggregate-only metrics let bad sub-periods hide.

### Anti-overfit rules (pre-committed)

1. **Selection criterion: highest IS Sharpe**, not IS CAGR. CAGR optimization tends to pick lucky configs; Sharpe is more stable.
2. **No look at OOS during search.** Run all sweeps, then look at OOS once. If OOS fails, the strategy is rejected as configured.
3. **At most one re-tune if OOS fails.** Document any second attempt explicitly — and downgrade it to "semi-OOS" status.
4. **Universe = current NSE 500.** Survivorship bias is acknowledged in writeup but not addressed in this round.

---

## Hyperparameter search space

### OM25 — staged search

**Stage 1: score variants (broad).** Fixed: lookback=252, top-N=25, exit-buffer=15, cadence=monthly, no ATR stop.

| Param | Values |
|---|---|
| Composite weights (UC vs CR) | 100/0, 70/30, 50/50, 30/70, 0/100 |
| Return filter | on (V1), off (V2) |
| Min-obs | 220 (default), 150 |

= ~20 configs. Pick **top-3 by IS Sharpe**.

**Stage 2: execution sensitivity** around top-3 winners.

| Param | Values |
|---|---|
| Lookback | 126, 189, 252, 378 |
| Top-N | 20, 25, 30 |
| Exit-buffer | 10, 15, 20 |
| Cadence | monthly, biweekly |
| ATR trailing stop | off, 4x no floor, 5x no floor |

For each top-3 winner: vary at most 2 dimensions at a time around the stage-1 baseline. Cap at ~15 configs per winner. Total stage 2: ~45 configs.

**OM25 total: ~65 configs × ~10s = ~12 min runtime.**

### TL25 — staged search

**Stage 1: score weights.** Fixed: persistence=252d, drawdown=126d (squared), momentum=63d, top-N=25, buffer=20, biweekly, 5x ATR no floor.

| Variant | Persistence | Drawdown | Momentum |
|---|---|---|---|
| Equal (current) | 1/3 | 1/3 | 1/3 |
| Persist-heavy | 0.50 | 0.25 | 0.25 |
| DD-heavy | 0.25 | 0.50 | 0.25 |
| Mom-heavy | 0.25 | 0.25 | 0.50 |
| 2-comp: P+DD | 0.50 | 0.50 | 0 |
| 2-comp: P+M | 0.50 | 0 | 0.50 |
| 2-comp: DD+M | 0 | 0.50 | 0.50 |

= 7 configs.

**Stage 2: windows + execution** around top-3 weight winners.

| Param | Values |
|---|---|
| Persistence-window | 126, 252, 378 |
| Momentum-window | 21, 63, 126 |
| Drawdown-window | 63, 126, 252 |
| Top-N | 20, 25, 30 |
| Exit-buffer | 15, 20, 25 |
| ATR-mult | 0 (off), 3, 5, 7 |
| Cadence | monthly, biweekly |

Same "vary 2 dimensions at a time" rule. Cap each top-3 winner at ~20 configs. Total stage 2: ~60 configs.

**TL25 total: ~70 configs × ~15s = ~18 min runtime.**

---

## Outcomes & next steps

After running:

| Outcome | What it means | Next step |
|---|---|---|
| **Pass + clears 40% / 1.5 target** | Robust strategy ready for paper-trading window | User sign-off → deploy candidate |
| **Pass but below target** | Robust but lower expected return | Document; discuss whether to deploy at lower numbers or seek improvements |
| **Fail (no config passes pre-committed criteria)** | Strategy thesis may be over-fit to recent regime | Document failure honestly; discuss whether to retire the strategy or try a different IS window |

The fail case is acceptable and informative — better than fitting until something passes.

---

## Files

| File | Purpose | Action |
|---|---|---|
| `scripts/_clean_engine.py` | V2 score + run_strategy backtest engine | Read-only — reuse |
| `scripts/backtest_om25.py` | Production OM25 backtest | Read-only |
| `scripts/backtest_trend_leaders.py` | Production TL25 backtest | Read-only |
| `scripts/build_om25_signals.py` | OM25 signals | Read-only — sweeps go through `_clean_engine.run_strategy` directly with closure-based score functions |
| `scripts/build_trend_leaders_signals.py` | TL25 signals | Read-only — supports needed flags |
| `scripts/run_oos_walkthrough.py` | Existing single-split OOS | Read-only — extract `period_metrics()` |
| `scripts/multi_window_oos_eval.py` | NEW — multi-window slicing utility | Create |
| `tasks/om25/experiments/_om25_oos_retune.py` | NEW — OM25 sweep harness | Create |
| `tasks/trend_leaders/experiments/_tl25_oos_retune.py` | NEW — TL25 sweep harness | Create |
| `tasks/oos_retune_2026/RESULTS.md` | NEW — final writeup | Create |
| `nse500_data_merged/` | Stitched panel | Read-only — already on disk |

Outputs land in `experiments/oos_retune/<timestamp>/` (gitignored).

---

## See also

- `TASKS.md` — implementation checklist
- `RESULTS.md` — written after sweeps complete
- `/Users/navdeep/.claude/plans/sunny-seeking-hartmanis.md` — original plan (pre-approval copy)
