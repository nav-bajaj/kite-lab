# Rebalance Page — Backlog

> **See `PLAN.md` for the decided direction (2026-06-18).** The page will be
> rebuilt as a **client-informational** view (previous + next rebalance,
> cadence, history) with accurate upcoming trades from a **post-close EOD
> T‑1 run**. PLAN.md resolves the "open questions" below and reframes the
> R-items into Phase 1 / Phase 2. This backlog stays as the detailed
> reference for individual R-items.

## Current state

The `/rebalance` page exists in the dashboard (frontend at
`kite-dashboard/src/app/(dashboard)/rebalance/page.tsx` and supporting
components under `kite-dashboard/src/components/rebalance/`; backend at
`kite-api/app/services/rebalance_service.py` exposed via
`kite-api/app/api/rebalance.py`). **It has never been fully functional
end-to-end.** Today, after the May 2026 follow-up commits:

- Status, preview, orders, history endpoints exist
- All 7 universes resolve to a real signals directory
- Legacy portfolios (Broad / Mid-Cap / Large-Cap Momentum) render
  preview + orders **only when the legacy
  `run_final_momentum_portfolio.py` script has been run recently and
  written `changes_<date>.csv` + `orders_<date>.csv` to its experiment
  dir**
- v3 portfolios (Quality / Trend Leaders / Core / Defensive Blend)
  show "No changes file found" gracefully because the v3 runners emit
  a different file format

Goal: make `/rebalance` actually useful for all 7 portfolios.

---

## Must-fix (page becomes useful)

### R-1. v3 strategies emit nothing the rebalance UI can read

The v3 runner scripts produce `<strategy>_signals.csv`,
`_exits.csv`, `_trades.csv`, `_equity.csv`, `metrics.json` — but no
`changes_<date>.csv` or `orders_<date>.csv`. Pick one path:

- **Path A:** Modify each v3 runner
  (`scripts/run_om25_v3_portfolio.py`, `run_tl25_v3_portfolio.py`,
  `run_l6_v2_portfolio.py`, `run_combo_defensive_portfolio.py`) to
  also write `changes_<date>.csv` (adds/drops from previous run) and
  `orders_<date>.csv` (target weight × portfolio value / current
  price → shares). Reuses the legacy file format. **Recommended** —
  smaller blast radius, no rebalance-service changes.
- **Path B:** Teach
  `rebalance_service.get_rebalance_preview` /
  `get_rebalance_orders` to derive adds/drops by diffing
  `<strategy>_signals.csv` from the latest run against the previous
  run, and compute shares from `<strategy>_equity.csv` + current
  prices. More decoupled but bigger surface.

### R-2. Rebalance cadence is hardcoded to weekly Thu/Fri

`rebalance_service.get_rebalance_status` uses `today.weekday()` to set
`current_phase` to `"preview"` on Thursday, `"ready"` on Friday,
`"waiting"` otherwise. This is wrong for the v3 strategies:

- OM25 v3 (Quality Momentum): bi-weekly entry + weekly exit checks
- TL25 v3 (Trend Leaders): bi-weekly entry + weekly rank-exit
- COMBO Defensive: bi-weekly Fri signal → Mon execution
- L6 v2 (Core Momentum): weekly Thu/Fri (matches legacy)
- Legacy (Broad / Mid-Cap / Large-Cap): weekly Thu/Fri

Action: encode the cadence per universe (in `config.py` UNIVERSES dict
add `rebalance_cadence: "weekly_thu_fri"` | `"biweekly_fri_mon"`),
then derive `current_phase` from the cadence + last
`metrics.json["last_run"]` timestamp instead of just weekday.

### R-3. Order quantities need a portfolio-value source

To produce `orders_*.csv` with share quantities, we need to know
"how much capital am I deploying?" The legacy script uses
`--initial-capital ₹1,000,000` and tracks via backtest. For LIVE
execution we want one of:

- (a) Read current Zerodha portfolio value from `/api/positions`
  and compute shares as `target_weight × current_value / current_price`
- (b) Use a user-configured "target capital per strategy" stored in
  DB or env

Both work. (a) couples rebalance to live positions which is the
realistic ask; (b) keeps the system pluggable.

### R-4. Empty-state message is misleading for v3 strategies

`get_rebalance_preview` returns
`"No changes file found. Run portfolio generation to create one."` for
the v3 portfolios. That's misleading — running their generators
*won't* produce a changes file. Two options:

- Quick: branch the message by `universe.startswith` so v3 strategies
  show "Rebalance UI not yet wired for this strategy — see Performance
  for activity history" and legacy shows the current message.
- Right: closes once R-1 lands. v3 strategies will then have changes
  files.

---

## Should-fix (UI hygiene)

### R-5. Status component doesn't know about regime overlay

OM25 v3 and COMBO Defensive have a regime overlay (NIFTY 100 vs
100-DMA, 3-day confirmation). In bear regime, OM25 v3 switches to
CR-only and COMBO Defensive cuts allocation by 50%. Today the
`/rebalance` page doesn't surface "current regime: bull/bear" or what
the overlay is doing to today's allocation.

Action: add `regime_state` to the status response
(`bull` | `bear` | `unknown`) and render it on the
`status-card.tsx` component for strategies that use it.

### R-6. Drawdown-stop signals invisible

OM25 v3 and TL25 v3 do weekly drawdown-stop checks — if equity drops
20% from peak, they exit ad-hoc between regular rebalances. Today
there's no UI surface for "DD stop triggered last Wednesday; here's
what got sold." User would only see it via the trades log.

Action: add an "Ad-hoc exits" section to the changes preview when
`<strategy>_exits.csv` has rows since the last regular rebalance.

### R-7. No "executed" feedback

After Friday's orders are placed, there's no way in the UI to mark
"yes, I executed these via Kite Console." The status sits at
`"ready"` indefinitely. Two paths:

- Manual: an "I executed" button that writes to the `Rebalance` DB
  table.
- Automatic: poll Zerodha's order book and reconcile against
  `orders_*.csv`. Tighter loop but needs Zerodha order-book API
  integration.

### R-8. CSV export format vs Kite Console current format

`export_orders_csv` writes a Kite basket-order format from circa
when the original audit was written. Kite Console's basket upload
schema may have changed. Action: open a recent basket from Kite,
download the template, diff against `export_orders_csv` output.

---

## Nice-to-have (polish)

### R-9. Rebalance history not rendered

`get_rebalance_history` returns past rebalances from the DB but no
frontend component renders it. Add a "History" tab or table showing
the last N rebalances with turnover %, # adds, # drops, signal date.

### R-10. Per-stock context in preview

When the preview shows "ADD: ASHOKLEY at rank 18", a hover tooltip
or a side panel with the stock's 6m momentum / current price / 50/200
DMA crossover would help the user trust the signal before clicking
through to Kite.

### R-11. Cross-strategy de-duplication view

If you run multiple strategies concurrently (e.g., Quality + Trend
Leaders), you'll get overlapping recommendations (HINDZINC might
appear in both). Today each strategy's `/rebalance` is independent.
A combined view that shows "consolidated buy list across selected
strategies, de-duplicated" would prevent over-allocating to a
single stock.

### R-12. Paper-trading mode

A toggle that lets the user "simulate execution" — mark the orders
as executed at OHLC/4 fill prices without actually sending to Kite.
Useful for confidence-building on new strategies before going live.

---

## Open questions / decisions needed

1. **Live vs backtest divergence** — the `/positions` page shows
   actual Zerodha holdings; `/rebalance` shows backtest-derived target
   holdings. If they diverge (which they will once you start trading
   live), which is the source of truth for "current holdings" when
   computing adds/drops? Likely live, but needs a decision.

2. **Multi-strategy capital allocation** — if you trade more than one
   strategy live, how is capital split? Equal? Risk-weighted? Manual?
   Drives R-3.

3. **Where do v3 strategies write changes/orders if we do R-1 Path A?**
   The legacy script writes them next to the timestamped portfolio
   dir. v3 should follow the same pattern: write
   `data/om25_v3_portfolios/om25_v3_portfolio_<ts>/changes_<date>.csv`.

4. **Should the `Rebalance` DB row get auto-populated from each
   portfolio runner?** Today it requires a manual write (visible
   from `kite-api/app/services/rebalance_service.py:212`). Could be
   added to each runner's cleanup step.

---

## Suggested execution order

If you tackle this end-to-end, this ordering minimizes rework:

1. R-1 (Path A) — unblocks every downstream rebalance UI feature
2. R-2 — once strategies write changes files, the cadence-aware status logic becomes meaningful
3. R-4 — message cleanup falls out of R-1
4. R-3 — order quantities (depends on R-1 being done first)
5. R-5 — regime surface (small, independent)
6. R-7 — execution feedback loop
7. R-6, R-8, R-9, R-10, R-11, R-12 — in any order, all independent

Estimated effort: R-1 through R-4 is ~half a week of focused work.
The full backlog is ~2 weeks.
