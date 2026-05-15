# OM25 US Retune 2026

## Why

OM25 v3 (Indian production, locked May 2026) degrades on US equities relative to its Indian OOS metrics:

| | Indian OOS 2017-26 | US OOS 2017-26 |
|---|---:|---:|
| CAGR | 44.78% | 34.40% |
| Sharpe | 1.86 | 1.26 |
| Max DD | -36.60% | -41.15% |

Source: `tasks/us_equities_2017/RESULTS.md`. The drop comes from two suspected places:
1. UC/CR composite weights tuned for emerging-market dispersion; US large-cap dispersion is tighter.
2. NIFTY-100-derived regime panel doesn't map cleanly to SPY 100-DMA (US has 29.9% bear days vs an unknown but likely-different Indian share over the same window).

This work retunes OM25's core score and regime overlay on US data, mirroring the methodology in `tasks/oos_retune_2026/PLAN.md` so the result is directly comparable to the Indian v3 retune.

## Methodology

**Inverted IS/OOS** (same shape as Indian retune):

| Window | Period | Length | Role |
|---|---|---|---|
| IS | 2009-09-01 → 2016-12-31 | 7.3y | Tune all hyperparameters here |
| OOS-A | 2017-01-01 → 2019-12-31 | 3y | Trump tax cuts, 2018 Q4 selloff |
| OOS-B | 2020-01-01 → 2022-12-31 | 3y | COVID crash + rally + 2022 Fed cycle |
| OOS-C | 2023-01-01 → 2026-05-13 | 3.4y | AI rally + 2025 mid-cap correction |
| OOS-full | 2017-01-01 → 2026-05-13 | 9.3y | Aggregate |

**Selection criterion:** highest IS Sharpe (NOT IS CAGR). Anti-overfit: do not look at OOS during search. After the winner is chosen, OOS metrics are computed exactly once.

**Pass criteria** (pre-committed, identical to Indian retune):

- IS Sharpe ≥ 1.0
- OOS-full Sharpe ≥ 1.0
- Each of OOS-A / OOS-B / OOS-C Sharpe ≥ 0.7
- OOS-full Max DD ≥ -45%

If no config passes, the strategy is rejected as configured — better than fitting until something passes.

## Search space

**Stage 1 — score base** (matches Indian Stage 1 grid exactly). No regime tilt.

| Param | Values |
|---|---|
| Bull weights (w_uc, w_cr) | 100/0, 70/30, 50/50, 30/70, 0/100 |
| Return filter | on, off |
| Min-obs | 220, 150 |
| Lookback | 252 (fixed) |
| Top-N | 25 (fixed) |
| Exit-buffer | 15 (fixed) |
| Cadence | monthly (fixed) |

= **20 configs**. Pick top 3 by IS Sharpe.

**Stage 2 — execution sensitivity** around each top-3 winner.

| Param | Values |
|---|---|
| Lookback | 126, 189, 252, 378 |
| Top-N × Exit-buffer | (20,10), (20,15), (25,10), (25,20), (30,15), (30,20) |
| Cadence | monthly, biweekly |
| ATR-mult / DD-stop | 0 (off), 4× ATR no-floor, 5× ATR no-floor |

Vary at most 2 dims at a time around each top-3 baseline. ~15 configs/winner × 3 = **~45 configs**.

**Stage 3 — regime tilt overlay** (US-specific addition; only if Stage 2 winner has IS Sharpe ≥ 1.0).

| Param | Values |
|---|---|
| Regime MA window | 50, 100, 150, 200 |
| Regime confirm days | 1, 3, 5 |
| Bear weights (w_uc, w_cr) | (0, 1), (0.25, 0.75), (0.5, 0.5) |

Bull weights inherited from Stage 2 winner. = **4 × 3 × 3 = 36 configs**. Pick best regime config by IS Sharpe.

**Total: ~100 configs.** At ~5-10s each via load-once orchestrator → ~10-15 min wall.

## Files

- `tasks/om25_us_tune_2026/PLAN.md` (this file)
- `tasks/om25_us_tune_2026/_om25_us_retune.py` (new — sweep harness)
- `tasks/om25_us_tune_2026/RESULTS.md` (written after sweeps)

Outputs land in `experiments/oos_retune/<ts>_om25_us/` (gitignored).

## Outcomes

| Outcome | Meaning | Next |
|---|---|---|
| Pass + meaningful lift over locked v3 | US retune is a robust upgrade | Lock as `om25_us_v1`, build runner script |
| Pass but no lift over locked v3 | Locked v3 was already near optimum | Document; keep locked v3 for US use |
| Fail | OM25 thesis may not generalize to US | Document honestly; reconsider whether US needs a different strategy |
