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
- **T‑1 trades: accurate, via a post-close EOD run.** A new scheduled job
  runs after 15:30 IST; the runner emits a *proposed orders* artifact from
  the engine. This is the only way the preview matches the real rebalance
  (it reuses top-N + exit-buffer + regime tilt + drawdown-stop + weekly
  rank-exit instead of re-implementing them in the API).
- **"Current holdings" source of truth (backlog Q1): the model portfolio**
  (reconstructed `momentum_holdings.csv` / `Holding`), not a live Zerodha
  account. Clients see the strategy's model book; live-account divergence is
  an admin/execution concern for later.
- **Sizing for clients: target *weights* and turnover %, not absolute share
  counts** (clients deploy different capital). Absolute shares are an admin-
  executor concern; the EOD artifact will carry both, the client view shows
  weights.
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
- Admin execution feedback / Kite order-book reconciliation (R-7).
- Kite basket CSV format refresh (R-8).
- Cross-strategy de-dup view (R-11), paper-trading mode (R-12), per-stock
  hover context (R-10), multi-strategy capital allocation (backlog Q2).
- Legacy nse500/nifty100/nifty250 rebalance UI parity (these aren't client-
  facing; keep current behaviour, don't regress).

## Phased approach

### Phase 1 — Read-only page from data we already have (low risk)
Maps to backlog R-2, R-4, R-9.
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

### Phase 2 — Accurate T‑1 proposed trades + regime/stop status
Maps to backlog R-1 (reframed), R-3, R-5, R-6.
1. **Engine: proposed-orders output.** In each v3 runner, after the backtest,
   score the universe as of the last data date, apply the *same* selection
   (top_n + exit_buffer + regime tilt + active drawdown-stop), diff vs the
   reconstructed current holdings → `proposed_orders_<next_date>.csv`
   (symbol, side, target_weight, est_shares, est_notional) + a `regime`
   and `drawdown_from_peak` summary. **TDD** the diff + sizing.
2. **EOD scheduled job** (`scheduler/tasks.py`): ~16:00 IST, **holiday-aware**
   (skip via `market_service`), and it only needs to compute a proposal when
   the next trading day is a rebalance day. Reuses the existing job runner.
3. **New DB table** (`ProposedRebalance` or similar) + alembic migration +
   `sync_service` function, keyed by `universe` + `target_date`, with a
   `data_as_of` timestamp.
4. **API**: `/api/rebalance/upcoming` → next date, proposed adds/drops +
   weights + turnover, regime + drawdown-stop status, `data_as_of`.
5. **UI**: "Upcoming changes" + "Regime / risk" sections; clearly labelled
   "indicative, finalises at T‑1 close."

## Key technical notes / risks

- **T‑1 timing is the whole point.** The existing pipeline runs 07:00 IST
  (pre-open) and therefore can't produce an end-of-T‑1 list during the day.
  The new EOD run uses T‑1 *close* data → exact for a T‑1-close decision.
  The usual signal→execution gap (execute at next open) still applies and
  will be stated in the UI.
- **Accuracy requires engine reuse.** The proposal must come from the
  runner's own score/selection path; a re-implementation in the API would
  drift from the real rebalance and mislead clients. This is why Phase 2
  touches the runners, not just the service.
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
