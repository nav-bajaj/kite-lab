# raam_transplant — task breakdown

Owners: 🤖 agent, 👤 Navdeep. Every phase ends with a 👤 checkpoint —
results reviewed and direction confirmed before the next phase starts.

## Phase 0 — Diagnostics (no strategy changes)

| # | Task | Owner | Risk |
|---|---|---|---|
| 0.1 | Data audit: panel depth, membership coverage, NIFTY 100 source freshness, symbol-rename gaps (TATAMOTORS/ZOMATO class) | 🤖 | data-gap |
| 0.2 | Reproduce L6 v2 baseline on the four windows with the standard engine config; confirm metrics match `docs/portfolios.md` within tolerance | 🤖 | lookahead |
| 0.3 | Build residual-correlation panel (beta 252d vs NIFTY 100, residual pairwise corr 63d); reconstruct rolling internal correlation of the actual L6 book 2017→now | 🤖 | compute-cost |
| 0.4 | Diagnostic study: internal corr quantiles vs forward 20/40/60d portfolio DD and return; momentum-breadth (share of top-40 with positive 126d momentum) vs same forwards | 🤖 | multiple-comparisons |
| 0.5 | 👤 checkpoint: review diagnostic report, G0 go/no-go, finalize C parameters | 👤 | — |

## Phase 1 — E1: correlation-penalized selection (L6-DIV)

| # | Task | Owner | Risk |
|---|---|---|---|
| 1.1 | Implement greedy corr-penalized scorer as a `score_fn` probe in this folder | 🤖 | lookahead |
| 1.2 | Tune λ on IS only; run OOS-A/B/C + 2021+ era, net of slippage | 🤖 | overfit |
| 1.3 | Judge against pre-registered E1 gate; sensitivity check on corr window | 🤖 | — |
| 1.4 | 👤 checkpoint: E1 verdict + direction | 👤 | — |

## Phase 2 — E2: bottom-up breadth throttle

| # | Task | Owner | Risk |
|---|---|---|---|
| 2.1 | Implement breadth-throttle exposure panel (float regime_panel) | 🤖 | lookahead |
| 2.2 | Tune floor on IS only; rolling-window T1-style battery vs bare L6 | 🤖 | overfit |
| 2.3 | Judge against pre-registered E2 gate; calendar-year DD table | 🤖 | — |
| 2.4 | 👤 checkpoint: E2 verdict + direction | 👤 | — |

## Phase 3 — E3: RC25 standalone (stretch, gated on E1 or E2 passing)

| # | Task | Owner | Risk |
|---|---|---|---|
| 3.1 | Full ranked-composite scorer (M + C + additive T, per-slot cash) | 🤖 | complexity |
| 3.2 | Four-window run; differentiation metrics vs L6/OM25/TL25/COMBO | 🤖 | overfit |
| 3.3 | Judge against om25_alt differentiation bar | 🤖 | — |
| 3.4 | 👤 checkpoint: portfolio-lineup decision | 👤 | product |

## Phase 4 — Close-out

| # | Task | Owner | Risk |
|---|---|---|---|
| 4.1 | RESULTS.md: decision, by-products, verification log | 🤖 | — |
| 4.2 | Failed branches → `docs/failed_experiments.md` | 🤖 | — |
| 4.3 | Optional: crowding-gauge productisation proposal for insight engine (TDD-scoped, separate approval) | 🤖 | scope-creep |
| 4.4 | 👤 checkpoint: merge/archive decision | 👤 | — |
