# Rebalance Page — Plan (v2, decided direction)

> Day-1 plan per `tasks/CONVENTIONS.md`. This supersedes the *direction*
> and *open questions* in `TASKS.md` (the R-1..R-12 backlog) with decisions
> taken on 2026-06-18. The R-item backlog stays as the detailed reference;
> this file is the source of truth for **what we're building and why**.

## Why

`/rebalance` has never worked end-to-end for the four portfolios clients
actually see. It is hardwired to the legacy "weekly Thursday preview /
Friday orders" model:

- `StatusCard` derives its phase from `today.weekday()` — wrong for the
  biweekly v3 strategies.
- `ChangesPreview` / `OrdersTable` read `changes_*.csv` / `orders_*.csv`,
  which only `run_final_momentum_portfolio.py` (legacy) emits. The v3
  runners don't, so those cards show "No changes file found."
- The `Rebalance` DB table is **never written** (confirmed: no producer in
  the codebase), so `signal_date` / `order_date` / history are always
  null/empty.

The real data we already have and can build on:

| Want | Source (already populated) |
|---|---|
| Previous rebalance + its trades | `Trade` table (synced from `momentum_trades.csv`) |
| Current model holdings | `Holding` / `OpenPosition` tables |
| Per-rebalance target ranking | `<strategy>_signals.csv` in each run dir |
| Trading-day calendar / holidays | `market_service.py` (fixed 2026 calendar) |

## Outcome (what "done" looks like)

A **client-informational**, read-only `/rebalance` page, working for all
four production portfolios via the existing universe selector, that shows:

1. **Previous rebalance** — date, stocks added/dropped, turnover %, notional
   traded, and the resulting holdings count. Derived from the `Trade` table
   (latest `trade_date` group) and the last entry date in the signals CSV.
2. **Next rebalance** — the upcoming rebalance date + countdown + a plain-
   language cadence rule ("Biweekly · Fridays · weekly rank-exit · 20%
   drawdown stop"). Computed from the engine's *own* schedule, not a
   re-derived parity, then rolled off NSE holidays/weekends.
3. **Upcoming changes / trades** — the trades the strategy intends to take at
   the next rebalance, computed accurately by an **EOD run on T‑1** (after
   the 15:30 IST close) from the engine's selection logic. Shown
   informationally (which stocks enter/exit, target weights, turnover),
   labelled with the data-as-of date and "finalises at T‑1 close."
4. **Regime & drawdown-stop status** — for om25_v3 / tl25_v3 / combo: current
   bull/bear regime and distance from the 20%-from-peak stop. These change
   what a rebalance does, so they belong on this page.
5. **History** — a timeline of recent rebalances with turnover per event.

## Decisions (resolving the backlog's open questions)

- **Audience: client-informational, read-only.** No "execute" button, no
  client-facing order CSV. Endpoints go behind the existing
  `check_universe_access` client-read pattern — **no new `/api/system` or
  admin-mutation surface**, so the auth invariants in `CLAUDE.md` are
  untouched. Admin execution / reconciliation (backlog R-7, R-8) stays a
  separate, later, admin-only concern — out of scope here.
- **Signal-day EOD report, read from the engine (not predicted).** The
  rebalance membership is fixed by the signal-day close, so a new scheduled job
  at **16:00 IST** (after NSE close *and* Zerodha's adjusted closes) runs the
  strategy and reads the rebalance the engine just decided. No re-implementation
  of selection, no reconciliation harness — the engine is the source of truth.
  (Superseded the earlier "re-implement the selection + verify it" plan, which
  was the source of avoidable complexity.)
- **"Current holdings" source of truth (backlog Q1): the model portfolio**
  (reconstructed `momentum_holdings.csv` / `Holding`), not a live Zerodha
  account. Clients see the strategy's model book; live-account divergence is
  an admin/execution concern for later.
- **Action scope: membership changes only.** Subscribers act on **full exits**
  (sell the entire position — universal, no math) and **new entries** (buy to
  the model's target weight). Continuing holdings show **HOLD / no action** —
  we deliberately do *not* ask subscribers to rebalance drifted weights every
  cycle (different start dates → different weights; forcing it means per-
  subscriber trades, cost, and tax for marginal benefit, and momentum wants
  winners to run). "Tighten my weights to the model" is a deferred, optional
  advanced feature (needs the subscriber's actual holdings).
- **Express the model in *weights + membership*, not shares.** The model is one
  notional book; subscribers have different rupee bases, so model share counts
  are meaningless. Target weights come from the model's **actual** weights
  (`momentum_holdings.csv:contribution_pct`), not assumed 1/N — this naturally
  represents the bear-regime cash that om25_v3 / combo_defensive hold (weights
  sum to <100%).
- **Optional ₹ personalization, client-side only.** A single "your portfolio
  value (₹)" input, stored in the browser and **never sent to the server**,
  translates each BUY's target weight into an indicative ₹ amount + rounded
  share count at the latest close (clearly caveated). Exits never need it
  ("sell all"). Without the input the page still works in weights/percent.
  The EOD artifact still carries absolute shares/notional for the admin
  executor; the client view derives ₹ locally.
- **Cadence: read it from the engine, don't hardcode.** Derive the next date
  from the gap between the last entry dates in the signals CSV; store a
  human-readable label per portfolio in `config.UNIVERSES` for display only.

## Scope boundary

**In scope**
- Rebuild `rebalance_service` to derive from `Trade` / `Holding` / signals +
  a cadence/date module; drop the dependence on the empty `Rebalance` table
  and legacy-only CSVs.
- New client-informational page + components + hooks + types; add the
  universe selector.
- Engine: a "proposed next-rebalance orders" output in each v3 runner,
  computed from the engine's own scoring/selection.
- A new EOD scheduled job + a new DB table for proposed orders + sync + a
  `/api/rebalance/upcoming` read endpoint.
- Regime / drawdown-stop status surfaced via the runner → DB → API.

**Out of scope (deferred, tracked in `TASKS.md`)**
- "Tighten my weights to the model" — optional advanced rebalance of drifted
  continuing holdings; needs the subscriber's actual current holdings.
- Admin execution feedback / Kite order-book reconciliation (R-7).
- Kite basket CSV format refresh (R-8).
- Cross-strategy de-dup view (R-11), paper-trading mode (R-12), per-stock
  hover context (R-10), multi-strategy capital allocation (backlog Q2).
- Legacy nse500/nifty100/nifty250 rebalance UI parity (these aren't client-
  facing; keep current behaviour, don't regress).

## Phased approach

### Phase 1 — Read-only page from data we already have (low risk) — SHIPPED
Maps to backlog R-2, R-4, R-9. Shipped on `claude/dashboard-market-rebalancing-issues-y90ald`
(cadence-aware summary + history from the Trade table, holiday-rolled next-date
projection, rebuilt page). Follow-up also shipped: **dual cadence** — biweekly
strategies surface the weekly exit check (`has_weekly_exit` + `exit_check_date`)
in addition to the biweekly entry date.
1. **Cadence/date module** (`rebalance_service` or new `rebalance_schedule.py`):
   `last_rebalance_date(universe)` and `next_rebalance_date(universe)` from
   the signals CSV gap, rolled off holidays via `market_service`. **TDD**:
   spec tests first (weekly vs biweekly, holiday roll, year-boundary).
2. **Previous-rebalance summary** from the `Trade` table (latest `trade_date`
   group): adds/drops, turnover %, notional, holdings count.
3. **Rewrite `get_rebalance_status`** to be cadence-aware (previous + next +
   phase) instead of `today.weekday()`; add a `rebalance_cadence` +
   display label to `config.UNIVERSES`.
4. **Rebuild the page**: universe selector, "Previous / Next" cards, cadence
   rule card, history timeline. Retire the legacy Thu/Fri assumptions and
   the misleading "No changes file found" empty state.
5. New/updated API: `/api/rebalance/summary` (previous + next + cadence);
   keep `/history`.

### Phase 2 — Show the actual rebalance (read from the engine at EOD on the signal day)
Maps to backlog R-1 (reframed), R-3, R-5, R-6.

**Approach (simplified 2026-06-19).** We do NOT predict or re-implement the
strategy's stock selection. The rebalance *membership* (which names in/out) is
fully determined by the signal-day close, so we run the engine after that close
and read the decision it has already made. This deleted the earlier
re-implementation (`select_target_membership` / `propose_next_rebalance`) and the
whole reconciliation harness — there is nothing to "verify" when the engine is
the source of truth. The pure membership-only *formatter* (`build_proposal` in
`data_pipeline/rebalance_proposal.py`) is kept: it turns "current holdings vs
engine target book" into SELL-all / BUY-to-weight / HOLD + optional ₹ sizing.

1. **EOD run on the signal day → read the engine's rebalance.** *Producer
   shipped (om25_v3, tl25_v3) — scheduler / DB / API still to do.* A new
   scheduled job at **16:00 IST** (after NSE close 15:30 *and* after Zerodha
   publishes the adjusted official closes — important, the existing 07:00 run
   uses the prior day's close and can't do this). On each strategy's signal
   weekday it fetches the day's adjusted data and runs that strategy. The
   engine normally waits for the next bar before recording a rebalance; a thin
   wrapper feeds it a placeholder next-day bar (signal-day close as the fill)
   so it computes the signal-day rebalance now — the *membership* is exact,
   only the fill price is a stand-in (irrelevant, we size by weight). The
   wrapper writes `proposed_orders_<exec_date>.csv` (entries/exits + target
   weights from the engine's resulting holdings) + a `proposed_regime.json`
   summary (regime, drawdown_from_peak, data_as_of) into
   `<run-dir>/backtests/baseline/`. Membership-only: partial trims on
   continuing holdings are not surfaced (derived from net-share transitions
   via `data_pipeline.engine_readout.partition_membership_by_date`).
   Implementation: `data_pipeline/eod_proposal.py` (producer module),
   `scripts/run_eod_proposed_orders.py` (CLI entry),
   `data_pipeline/engine_readout.py` (pure membership helper, 13 tests).
   Verified via `tasks/rebalance_page/verify_eod_producer.py` — 5/5 past
   signal dates produce identical membership to the real-bar engine run.
2. **DB table** (`ProposedRebalance` or similar) + alembic migration +
   `sync_service` function, keyed by `universe` + `exec_date`, with a
   `data_as_of` timestamp. Read via the (refreshed) `latest.json` pointer.
   *Shipped:* `ProposedRebalance` in `kite-api/app/models/models.py`,
   alembic `0005_add_proposed_rebalances`, `sync_proposed_rebalance` in
   `sync_service.py` (called from `sync_all`). The producer now writes
   into the latest `<strategy>_portfolio_<ts>/backtests/baseline/` next to
   `momentum_*.csv` so no new pointer is needed. 6 unit tests cover happy
   path, missing JSON (soft-skip), unknown universe, malformed JSON, and
   idempotent re-sync.
3. **API**: `/api/rebalance/upcoming` → exec date, exits + new entries +
   weights, regime + drawdown status, `data_as_of`. *Shipped:* read endpoint
   in `kite-api/app/api/rebalance.py` behind `check_universe_access` (no new
   admin/mutation surface). Returns `available: false` with empty lists
   when no proposal has been produced yet (for strategies whose EOD
   producer isn't wired up), so the UI doesn't 404. Wired into
   `test_clerk_authz.py` (12 new test cases — client-allowed universes
   get 200; client-forbidden universes get 403; anon gets 401).
4. **UI — "Actionable trades" card** (membership-only, weight-based):
   - **SELL (exit fully)** — "sell your entire position." Universal.
   - **BUY (new positions)** — name + model target weight; with the optional
     "your portfolio value" input, also ≈₹ amount and ≈ shares (caveated).
   - **HOLD** — continuing names, collapsed, "no action."
   - Plain-English one-liner + a **Regime / risk** line (regime, drawdown).
   - Off-week exit-check days are first-class: usually SELL-only or empty.
   *Shipped:* `ActionableTrades` card in
   `kite-dashboard/src/components/rebalance/actionable-trades.tsx`, wired
   into `/rebalance` page above the existing Previous/Next cards. Subscriber
   capital is stored in `localStorage` per universe (key
   `rebalance.portfolio_value.<universe>`) via `useSyncExternalStore` —
   never sent to the server. BUYs re-derive ₹ via `weight × clientCapital`
   on the client (mirrors `build_proposal`), falling back to the producer's
   model-scale numbers when no capital is set. HOLDs collapsed by default.
   Renders a "no upcoming rebalance produced yet" empty state when the API
   returns `available: false` (so unsupported strategies don't 404 the UI).
   `tsc` + `eslint` clean on touched files.

### Phase 2 step 5 — 16:00 IST scheduled job (SHIPPED)

A new `eod_proposed_orders` entry in `kite-api/app/scheduler/tasks.py` fires
Mon–Fri at 16:00 IST. The wrapper `run_eod_proposed_orders` iterates
`EOD_STRATEGIES = ("om25_v3", "tl25_v3")` and asks `_is_eod_signal_day` per
strategy — signal-day gate anchored on the engine's most recent signal date
(latest row of `<strategy>_signals.csv`) projected forward via
`rebalance_service.project_next_signal` (already cadence-aware and
holiday-rolled in Phase 1). Off-week exit-check Fridays are deliberately
skipped: the producer only fires on entry-cadence Fridays. Each strategy
that passes the gate gets its own `JobService` job so a producer failure on
one doesn't block the other. The producer script (`scripts/run_eod_proposed_orders.py`)
gained a `--universe` alias to `--strategy` so the job-service's uniform
`--universe` arg works without special-casing. 7 unit tests cover the gate
across the matrix: signal Friday ✓, off-week Friday ✗, weekday non-Friday ✗,
NSE holiday ✗, missing run dir ✗, missing signals CSV ✗, holiday-rolled
anchor (Thursday) handled cleanly.

l6_v2 (Core Momentum) wired 2026-07-02: reuses `_momentum_engine.build_momentum_panels`
+ `make_momentum_score` (same BASELINE the daily runner uses) with weekly
Thursday cadence. Verified byte-identical membership vs real-bar engine on
2 past Thursdays. Same commit refactored `_is_eod_signal_day` to anchor on
the Trade table (most recent BUY exec_date) rather than a per-strategy
signals CSV — l6_v2 never emits a signals CSV so the old CSV-based gate
silently returned False and the cron never fired for it.

combo_defensive (Defensive Blend) wired 2026-07-04: reuses
`combo_defensive.make_combo_score_fn` on the same L6 + OM25 v3 composition,
biweekly Friday cadence, and the portfolio-level regime overlay
(`bear_exposure=0.5`) — the piece that makes it "defensive". Unlike
om25_v3 (`regime_panel=None`), this strategy DOES pass `regime_panel` to
the engine because the defensive scale-down is part of the strategy
definition. Verified byte-identical membership on 2 past biweekly
Fridays.

## Key technical notes / risks

- **Read from the engine, don't re-implement it.** The rebalance must come from
  the engine's own output (via the placeholder-bar EOD run), not a copy of its
  selection logic — the latter drifts (stops / re-entry / min-hold) and would
  mislead clients. This is why Phase 2 runs the engine rather than scoring in
  the API/service.
- **EOD timing.** Run at **16:00 IST** so the membership reflects Zerodha's
  *adjusted* closing prices (published after 15:30), not intraday/raw levels.
  Only run on each strategy's signal weekday, and skip NSE holidays.
- **Scheduler.** Adding an EOD job to the in-process APScheduler is fine
  (confirmed reliable in production). Make it holiday-aware so it doesn't
  emit stale proposals on closed days.
- **No new mutation/admin surface** — keeps us clear of the `require_admin`
  / CSP / `/api/system` invariants. A `security-reviewer` pass is still
  warranted for the new read endpoints (they touch `kite-api/app/api/**`).
- **Don't regress the stale-pointer fix.** Phase 2's new artifacts live in
  the same run dirs that `latest.json` points at; the sync must read them
  via the (now-refreshed) pointer, not re-glob independently.

## Critical files

**Backend**
- `kite-api/app/services/rebalance_service.py` — rebuild around real data.
- `kite-api/app/api/rebalance.py` — new `summary` / `upcoming` endpoints.
- `kite-api/app/services/sync_service.py` — sync proposed-orders artifact.
- `kite-api/app/models/models.py` — new proposed-orders table; `Trade`,
  `Holding` already exist.
- `kite-api/app/services/market_service.py` — trading-day / holiday roll.
- `kite-api/app/config.py` — `UNIVERSES`: cadence + display label.
- `kite-api/app/scheduler/tasks.py` — EOD job.
- `kite-api/alembic/versions/` — migration for the new table.

**Engine / scripts**
- `scripts/run_om25_v3_portfolio.py`, `run_tl25_v3_portfolio.py`,
  `run_l6_v2_portfolio.py`, `run_combo_defensive_portfolio.py` — emit
  proposed orders + regime/stop summary.
- `scripts/_clean_engine.py` — `fridays` / `biweekly_fridays`, `run_strategy`
  (reuse selection logic; do **not** re-anchor the live schedule).
- `scripts/om25_v3.py` — regime panel / score fn (reuse for the preview).
- `scripts/update_all_portfolios.py`, `scripts/sync_to_database.py`.

**Frontend**
- `kite-dashboard/src/app/(dashboard)/rebalance/page.tsx`
- `kite-dashboard/src/components/rebalance/*` (rebuild)
- `kite-dashboard/src/lib/{hooks,api-client,types}.ts`
- `kite-dashboard/src/contexts/universe-context.tsx`,
  `components/shared/universe-selector.tsx` (reuse)

## Verification plan

- TDD specs for the cadence/date module and the proposed-orders diff/sizing.
- Backend `pytest kite-api/tests/`; new tests for `rebalance_service` summary
  and the schedule module.
- Reconcile a known past rebalance: the page's "previous rebalance" must
  match the actual `Trade` rows for that date.
- For Phase 2: run the EOD step on a recent trading day and confirm the
  proposed set matches what the next real rebalance produced (within the
  documented T‑1 vs execution-open gap).
- Frontend `npm run build` + `tsc` + `eslint` clean before any merge.

## Open items still needing a human call (smaller)

1. **EOD job time** — 16:00 IST assumed; confirm vs when Kite EOD data is
   reliably available.
2. **Regime/stop display granularity** — show exact drawdown-from-peak %, or
   just a bull/bear + "stop armed/triggered" badge? (Leaning: show the %.)
3. **History depth** — how many past rebalances on the timeline (default 12).
