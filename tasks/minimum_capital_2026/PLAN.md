# minimum_capital_2026 — PLAN

## Why the work started

Two product questions, asked 2026-09-06 ahead of publishing guidance for
the momentum portfolios:

1. What capital should we suggest a client needs to follow them —
   Rs 1-5L or Rs 5-10L?
2. What should we suggest as a SIP — an initial lumpsum plus a monthly
   contribution?

Neither is a matter of taste. Position size in an equal-weight 24/25-stock
book is `capital / N`, so a share priced above that position cannot be
bought at all, and DP charges are a flat per-scrip-per-sale cost that
only capital dilutes. Both are measurable from repo data.

## How the scope grew

Answering (1) surfaced the real constraint: the production books hold
names — POWERINDIA at Rs 34,190, APARINDS at Rs 16,856, NEULANDLAB at
Rs 23,301 — that are unbuyable at a Rs 20-40k position. That produced a
follow-on question the founder asked directly: what would it cost to
exclude high-priced names outright? So the task has two halves:

- **Phase 1 — capital and SIP sizing.** What is the true minimum, and
  what lumpsum + SIP should we advertise.
- **Phase 2 — price-cap study.** What a Rs 4,000 per-share entry ceiling
  would have cost OM25 v3, L6 v2 and COMBO Defensive.

Phase 2 changes the answer to Phase 1, which is why they live together.

## Outcome

A defensible suggested-capital and SIP figure, plus a decision-ready
answer on whether to adopt a price cap per portfolio.

## Scope boundary

- Analysis only. **No production config or strategy code was changed.**
- The cap is an entry-eligibility filter, not a re-tune: score, cadence,
  top-N, exit buffer, drawdown stop and slippage all stay at LOCKED
  values in every arm.
- TL25 v3 was not run through the cap study (see TASKS.md, open items).

## Design decision that matters — where the cap is injected

The cap is applied to **entry eligibility only**, and the injection point
differs per strategy because each selects names differently:

| strategy | injection point | why |
|---|---|---|
| OM25 v3 | `membership_fn` | Score is doubly cross-sectional (`market_ret` is the equal-weight mean over candidate columns; UC and CR are pct-ranked across them). Capping `candidate_fn` would change every surviving stock's score and confound "restricted buy list" with "different score". |
| L6 v2 | `membership_fn` | Score is a monotone cross-sectional z-score, so the same approach is safe. |
| COMBO | wrap each component `score_fn` | `make_combo_score_fn` truncates EACH component to its top-12 and emits exactly 24 names. A membership-level cap would let expensive names consume component slots and then be filtered out by `_relevant_ranking`, leaving the book holding **fewer than 24 names** — an under-invested portfolio, not a fair test. Component scores are computed first and filtered after, so scores stay identical to production. |

Wrapping `membership_fn` also gets the economically right exit behaviour
for free: the engine's grandfather rule (`_relevant_ranking` retains
`s in holdings`) keeps a holding that appreciates through the cap instead
of force-selling it. COMBO cannot do this — see RESULTS_PRICE_CAP.md.

## Critical files

- `scripts/om25_v3.py` — OM25 LOCKED config and score factory
- `scripts/_momentum_engine.py` — L6 BASELINE, score factory, `run_momentum`
- `scripts/combo_defensive.py` — COMBO LOCKED config, `make_combo_score_fn`
- `scripts/_clean_engine.py` — `run_strategy`, membership + grandfather logic
- `scripts/universe_membership.py` — `resolve_universe`
- `scripts/run_{om25_v3,l6_v2,combo_defensive}_portfolio.py` — the
  production runners each harness mirrors

## Validation requirement

Every uncapped arm must reproduce its production run before any capped
arm is believed. Achieved — see RESULTS_PRICE_CAP.md, all three within
0.2pp CAGR with Sharpe and MaxDD matching to 0.03.
