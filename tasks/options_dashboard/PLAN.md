# Options Analytics Dashboard — real-time, interactive, subscriber-grade

## Why

The options program now computes things nobody's broker terminal shows:
a measured gamma profile with a regime read, parity-forward vs spot
divergence, IV percentile against our own day-type library, OI-migration
signatures (pin-build / call-covering / PE de-grossing), a paper-straddle
risk ledger (MAE + underwater-minutes), and a morning structure advisory.
Today all of that surfaces as an EOD markdown report and two /admin
cards. The data refreshes every 10 seconds in Postgres; the presentation
is the bottleneck, not the pipeline.

The outcome: a real-time interactive analytics page — first for us
(admin), then as the flagship surface for subscribers who want live
options insights that are not accessible anywhere else. Explicitly NOT
simple option/futures price charts (broker platforms own those); every
chart on this page is a computation only our dataset can draw.

## What it shows (chart inventory, each mapped to an existing computation)

| # | Chart | Source computation | Why a broker can't show it |
|---|---|---|---|
| 1 | Gamma profile by strike (bar, live) with max-gamma strike, concentration %, regime badge (PIN-GRAVITY / MIXED / DIFFUSE) | `gamma_profile.compute_from_snapshot` on the 10s chain snapshot | Measured GEX, no dealer assumptions; regime label with sample-size honesty |
| 2 | Intraday max-gamma migration map (strike vs time, today over prior sessions) | `gamma_profile_daily` + snapshot history | The pin-vs-chase signature (magnet static vs migrating) is our regime tell |
| 3 | Spot vs parity-forward + divergence band (line pair + deviation area, 40-pt flag) | `_divergence_section` / `divergence` field | Parity forward from the chain is computed, not quoted; close-print dislocation is invisible on price charts |
| 4 | ATM IV intraday path + IV percentile gauge vs our day-type library | greeks materialization + day-plan percentile | Percentile is against OUR recorded history, not a generic VIX |
| 5 | OI migration heatmap (strike x time, CE/PE build/drain vs 09:45 base) | `option_minute_bars` OI columns | The de-grossing / covering-fuel / pin-build signatures we journal |
| 6 | Straddle economics strip: ATM straddle price, implied-to-expiry %, live paper-straddle P&L, MAE, underwater-minutes | `paper_straddle` ledger + live marks | A risk LEDGER (what the position felt like), not a payoff diagram |
| 7 | Depth & friction: ATM±100 spread % of premium + book-imbalance vs baseline | minute-bar spread/imbalance columns | Whole-book friction time series exists only in our capture |
| 8 | Morning day-plan card: structure advisory + constraints + track record (advisory verdict history) | `day_plan.recommend_structure` | The advisory framing (probabilistic, never a trigger) IS the product |
| 9 | (Stage 3, gated on the sign test passing) Signed dealer-gamma flow gauge, labeled ESTIMATED | `signed_gex_probe` promotion | Nobody has the tick-attribution dataset |

Framing rule inherited from the program: every label is probabilistic and
diagnostic, thresholds carry their sample size, nothing is a trade
signal. ESTIMATED things say ESTIMATED on the chart.

## Architecture (all pieces exist; this initiative adds read paths + UI)

```
options worker (Railway, options_data_v1)
  └─ Postgres: option_chain_snapshots (10s), option_minute_bars,
     gamma_profile_daily, paper_straddle_ledger, option_greeks_minute
       └─ kite-api (Railway web, beta_gtm_mvp): existing
          /api/options/live-analytics (admin) + NEW read endpoints:
            /api/options/intraday-series   (gamma/IV/divergence paths, 1-min)
            /api/options/oi-heatmap        (strike x time OI deltas)
            /api/options/straddle-ledger   (ledger rows + live marks)
            /api/options/day-plan          (advisory + history)
              └─ kite-dashboard (Vercel): /options page, 10s polling
                 (matches snapshot cadence; SSE only if polling hurts)
```

- Charting: recharts (already in the dashboard) for bars/heatmap/gauges;
  lightweight-charts (already present) for the time-series panes.
- Refresh: poll 10s during market phase, idle outside market hours
  (market-clock endpoint already exposes phase). No websockets in v1.
- History depth: intraday series computed from minute bars on request,
  cached server-side per minute — no new worker responsibilities;
  ingestion stays untouched (V1 invariant).

## Access model (mirrors the platform's existing tiers)

- Phase A: `require_admin` — our own instrument panel, iterate freely.
- Phase B: subscriber tier behind a NEW entitlement (options-insights
  role/flag in Clerk publicMetadata, analog of `check_universe_access`).
  Every new endpoint goes through the security-reviewer subagent before
  merge (R-026 pattern); no widening of the /api/system surface.

## Phases

0. **Design mock first** (feedback memory: visual-validate before
   building). Mock the page in Pencil — layout, chart hierarchy, light +
   dark, the regime/advisory cards — get founder sign-off on direction
   BEFORE component code. Deliverable: .pen screens + exported stills.
1. **Read API**: the four endpoints above on beta_gtm_mvp, admin-gated,
   unit-tested against fixture DB rows; security-reviewer pass.
   (Absorbs the pending cross-branch follow-up: divergence field +
   day-plan on the /admin card — the card becomes a link into /options.)
2. **/options page v1 (admin)**: charts 1, 3, 4, 6, 8 live; 10s poll;
   deploy off-market-hours; a week of daily use during live sessions to
   shake out what a real user needs.
3. **History + heatmap**: charts 2, 5, 7; day selector for past
   sessions (the replay/教material value — any journaled day is
   reviewable visually).
4. **Subscriber productization**: entitlement, marketing surface,
   pricing input to the founder; only after Phase 2 has proven daily
   value to us.
5. **Stage-3 gauge**: only if/when the sign test passes (see
   tasks/options_data NOTE_stage3_signed_gex.md).

## Scope boundary

- No order placement, no alerts-as-signals, no per-user customization
  in v1. No new worker responsibilities. No public (unauthenticated)
  data exposure. Universe/equity insights pages are untouched.

## Critical files

- `kite-api/app/microstructure/*` — computations to expose (read-only).
- `.worktrees/beta_gtm/kite-api/app/api/options_worker.py` — endpoint
  home on the live branch.
- `.worktrees/beta_gtm/kite-dashboard/src/app/(dashboard)/` — page home.
- `kite-dashboard/src/lib/universes.ts` analog for the entitlement label.

## Open questions for the founder

1. Page name/route: `/options`? "Options Lab"? (marketing name can wait
   for Phase 4, route cannot.)
2. Does the subscriber tier reuse the beta allowlist or a new paid flag?
3. Which two charts are the "wow" opener for Phase 0's mock — proposal:
   gamma profile + divergence band, they're the most unique.
