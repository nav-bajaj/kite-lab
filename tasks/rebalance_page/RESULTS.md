# Rebalance Page — Results

Close-out for the `rebalance_page` initiative. Plan of record: `PLAN.md` (v2).
Detailed audit + remediation trail: `AUDIT_2026-07-04.md`.

Status: **shipped.** `/rebalance` works end-to-end for all four production
portfolios (om25_v3, tl25_v3, l6_v2, combo_defensive); the client-informational
page, the EOD engine-readout producer, the DB sync, the read endpoints, and the
16:00 IST scheduled job are all live on marketworks.in, and the post-ship audit's
correctness / UX / ops findings are closed.

## What shipped vs. planned

### Phase 1 — read-only cadence-aware page (PLAN §Phase 1) — shipped as planned
Cadence/date module, previous-rebalance summary from the `Trade` table,
holiday-rolled next-date projection, rebuilt page with the universe selector, and
the dual-cadence weekly-exit surfacing for biweekly strategies. Retired the
`today.weekday()` phase logic and the misleading "No changes file found" state.

### Phase 2 — show the actual rebalance from the engine (PLAN §Phase 2) — shipped as planned
"Read the engine, don't re-implement it": a 16:00 IST producer runs each strategy
on its signal day (placeholder next-bar trick) and reads the membership the engine
decided, writing `proposed_orders_<exec>.csv` + `proposed_regime.json`. New
`ProposedRebalance` table + `sync_proposed_rebalance`, `/api/rebalance/upcoming`
behind `check_universe_access`, the `ActionableTrades` card (SELL-all / BUY-to-
weight / HOLD + client-side ₹ personalisation), and the per-strategy EOD job with
a signal-day gate. All four portfolios wired with their exact production plumbing
(om25_v3 `regime_panel=None`; combo_defensive regime overlay + `bear_exposure=0.5`;
l6_v2 `min_hold_days=8` + Trade-table gate; tl25_v3 weekly rank-exit).

### Post-ship audit remediation (AUDIT_2026-07-04.md) — shipped
A three-lens audit (correctness / UX / ops) confirmed the selection logic was
correct for all four portfolios and surfaced peripheral risks, all now fixed:

- **P0 correctness** — added the missing ad-hoc 15 Jan 2026 NSE holiday + a
  missing-year guardrail; fixed the `/summary` zero-BUY crash; added staleness
  guards (stale flag, panel-freshness backstop, orchestrator abort on failed
  refresh); added an adapter-vs-runner parity test; made the placeholder exec_date
  holiday-aware.
- **P1 client-trust UX** — stopped showing model-scale ₹/shares as the user's;
  per-card "information only" disclaimer; legible portfolio-level regime/drawdown
  strip; zero-activity cycles read as no-action.
- **P1 ops** — EOD dead-man's-switch (fails the wrapper Job on a missing
  producer); fetch-only EOD refresh (dropped the redundant all-7-portfolio
  rebuild); persistence-coverage test for the Railway symlink script.
- **P2 cleanup** — single source of truth for the strategy/universe lists;
  removed the dead legacy `/status`; fixed stale comments; documented the
  edge cases and the (non-reducible) producer warmup.

### Scope changes from the plan
- The plan's earlier "re-implement selection + reconciliation harness" was
  **dropped** before Phase 2 in favour of reading the engine directly (simpler,
  no drift) — recorded in PLAN §Phase 2.
- Deferred (unchanged from PLAN "out of scope"): "tighten my weights to the
  model", admin execution / Kite order-book reconciliation, basket-CSV refresh,
  cross-strategy de-dup, paper-trading, per-stock hover.

## Commits

- **Phase 1 + Phase 2 build:** PRs #6–#21 (`a94aa80` … `6ba312a`) — cadence page,
  proposal formatter, EOD producer, DB table + sync, API, UI card, scheduler job,
  per-portfolio wiring, and the Railway-persistence fixes.
- **Audit P0 + P1:** PR #22 (`a30bb99`) = `c8cca9a` (P0 correctness) +
  `9ce58b0` (P1 UX + ops).
- **Audit P2:** PR #23 = `bdcb72e` (dedup/comments/gitignore) +
  `fce5ece` (remove dead `/status`, empty-state, warmup docs).

## Deferred / not done (intentional)

- **T-19 (O8) — `ProposedRebalance` retention.** Growth is ~a few hundred rows/yr
  and only the latest row per universe is read; left as documented-keep.
- **T-20 (O5) — external cron / persisted jobstore.** The 16:00 job is an
  in-process APScheduler run with a `MemoryJobStore`, so a Railway
  deploy/restart across the run drops that day's proposals. Left gated on the new
  dead-man's-switch: build it only if T-10 starts surfacing real misses. Recovery
  today is a manual `scripts/run_eod_proposed_orders.py --universe <x>` (idempotent
  upsert) or waiting for the next signal day.
- **U13 a11y nit** — history Added/Removed cells still lean on colour + column
  header. Minor.

## Verification log

- **Backend:** `pytest kite-api/tests/` — 679 passed / 1 skipped after the P2
  `/status` removal (was 691 pre-removal; the −12 are the removed endpoint's authz
  cases). New audit tests: holiday table + guardrail, zero-BUY summary, upcoming
  stale flag, EOD dead-man's-switch, persistence coverage, strategy-list drift.
- **Data pipeline:** the EOD guard tests (freshness, adapter-vs-runner parity,
  holiday-aware placeholder) pass. Pre-existing unrelated failures
  (`test_ta_indicators` ModuleNotFound, network-dependent price tests) untouched.
- **Frontend:** `npm run build` + eslint clean on all rebalance components and lib
  changes; `/rebalance` prerenders static.
- **Correctness spot-checks:** all four EOD adapters compared line-by-line against
  their production runners (identical engine config); the L1 (2027 holiday gap →
  found the missing 15 Jan) and L2 (`last_date`) bugs re-verified by hand.
- **Deploy:** P0+P1 (PR #22) deployed to marketworks.in (Vercel) + Railway and
  confirmed working by the founder. P2 (PR #23) merged after review.
