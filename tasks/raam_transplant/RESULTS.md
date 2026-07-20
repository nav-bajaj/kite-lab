# raam_transplant — Results

**Outcome:** conclusive — 2 validated candidates held for a productization
decision; 1 engine shipped to kite-api (dashboard wiring deferred); several
negative sub-results documented.
**Closed (research phase):** 2026-07-20

Transplanted ideas from Giordano's *Ranked Asset Allocation Model* (2018
Charles H. Dow Award) into the NSE-500 stock-momentum line, weekly cadence,
following the repo's diagnostic-first, pre-registered-gate methodology.

## What was actually done (vs PLAN.md)

PLAN proposed: diagnose crowding (Phase 0) → E1 crowding-penalised selection
→ E2 breadth throttle → E3 RC25 composite → optional insight gauge. Actual
path, after each checkpoint with the founder:

- **Data refreshed** to 2026-07-20 (fetch-only pipeline; no production
  writes). Surfaced a local stale-index footgun (see Open follow-ups).
- **Phase 0.2** — reproduced the L6 v2 baseline through the production engine
  to validate the harness (`baseline_l6.py`).
- **Phase 0.3/0.4 (G0 gate)** — built the residual-crowding instrument
  (`residuals.py`) and diagnostic (`crowding_diagnostic.py`).
- **E1** — crowding-penalised selection (`e1_l6div.py`) + robustness
  (`e1_robustness.py`). **Qualified pass.**
- **E2** — refuted at the diagnostic stage (never backtested); breadth is
  U-shaped, not monotone.
- **E-LV** (founder-requested) — low-vol as a conservative sleeve
  (`lv_revisit.py`) + robustness (`lv_robustness.py`). **Viable.**
- **E-T** (founder-requested) — trend as a soft contributor (`t_trend.py`).
  Paper's mechanic failed; a gentle DMA-distance tilt modestly helped.
- **Crowding gauge** — TDD engine shipped to `kite-api/app/insights/crowding.py`
  (+ `test_insights_crowding.py`). Dashboard wiring **deferred**.
- **E3 (RC25 composite)** — not run.

## Headline numbers (net of 20bps, out-of-sample)

**E1 — L6-DIV (crowding-penalised L6, λ=1.0):** vs L6 across OOS-A/B/C —
CAGR +0.2/+3.3/+1.7pp (gains in all four windows incl. 2021-era), Calmar
better in 2/3, drawdown shallower in 3/4. Robust across λ∈[0.5,1.5] and
crowd-window 42/63/126 (not a knife-edge). ~90% holdings overlap with L6
(swaps 2-3 of 24 names/week). Cost gate trips only on a scale-ambiguous
turnover measure; canonical cost_drag +~0.3pp/yr, absorbed in net CAGR.

**E-LV — low-vol conservative sleeve (best config: realized-252 vol + trend
gate + monthly + top-30):** FULL 2009-2026 Sharpe ~1.00 at ~2.4%/yr cost;
weekly/top-24 reference Sharpe 0.82, vol 12.6% (~half L6), MaxDD −32%, ~4%
holdings overlap with L6. Beats NIFTY 100 buy-hold on return, vol, drawdown
and Sharpe; beats it on rolling 1-yr return 69% / drawdown 70% of windows.
Lags in large-cap bull years (2021, 2025); vs a 60/40 wins return+Sharpe but
not drawdown (still equity-sized) — a defensive-equity sleeve, not a bond sub.

**Meta-finding:** the paper's *ideas* transplant; its *literal mechanics*
don't. Our simpler tooling beat the paper's instrument three times —
residual crowding > its correlation math, DMA-distance > its ATR breakout,
realized-252 vol > its EWMA(0.94). Good idea generator, not a recipe.

## Decision

- **No production change made.** Two validated candidates are held for a
  separate productization decision:
  1. **Crowding-aware L6 (E1)** — a modest, robust upgrade to the live Core
     Momentum strategy, or an opt-in variant.
  2. **Defensive low-vol sleeve (E-LV)** — a genuinely different fifth-product
     candidate for a conservative investor.
- **Crowding gauge engine** is in kite-api (TDD-green) but not wired to any
  route/panel — no live surface yet.
- **Do not retry** (see `docs/failed_experiments.md`): the bottom-up breadth
  throttle, the ATR/Donchian breakout trend state, and EWMA vol over realized.

## Open follow-ups

- **Crowding gauge Step B** — swap the primary metric to own-history
  percentile (null-vs-random saturates for momentum books), add a loader that
  reconstructs L6's crowding history, expose one admin endpoint.
- **If productizing E-LV** — run the monthly/realized/top-30 config through the
  full OOS gate suite as a formal strategy proposal; assign a stable universe
  ID + display name (`docs/portfolios.md`, `kite-dashboard/src/lib/universes.ts`).
- **If productizing E1** — decide: change live L6, or ship as an opt-in
  "de-crowded" variant.
- **RC25 composite (E3)** — unrun; low prior it clears the om25_alt
  differentiation bar. Only worth it to formally close "is a 5th momentum
  portfolio warranted?".
- **Data hygiene (independent of this task)** — the local strategy regime path
  `indices_data_historical/NIFTY_100.csv` is stale (2026-05-08); the
  insight-engine path (`Documents/indices_data_full`) is fresh. Railway is
  unaffected. Local OM25/COMBO backtests with the regime overlay would use a
  stale index until this is synced.

## Reusable artifacts (by-products)

- `residuals.py` — beta-residual return panel (beta 252d vs NIFTY 100).
- `kite-api/app/insights/crowding.py` — TDD'd crowding engine (7 spec tests).
- `crowding_diagnostic.py` — book-crowding vs forward-outcome harness.
- `explainer.html` — plain-English one-pager (published as an artifact).

## Commit log

```
56b2c1a open task — PLAN with pre-registered gates, phased TASKS
8ebdd99 Phase 0.2 — reproduce L6 v2 baseline harness
5416dea Phase 0.3/0.4 — crowding diagnostic, G0 verdict
d47898e Phase 1 — E1 L6-DIV crowding-penalised selection
491cb2e Phase 1 — E1 robustness confirms qualified pass
81694a1 crowding engine (TDD) — book_crowding + null percentile
5647352 plain-English progress explainer (one-page HTML)
ee6fea9 E-LV — low-vol as a conservative sleeve (VIABLE)
de10078 E-T — trend as soft contributor to L6
ae9dac0 E-LV robustness — survives and improves under stress
```
