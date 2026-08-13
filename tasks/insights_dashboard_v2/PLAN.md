# Insights Dashboard v2 — insight_engine as the launch product

Branch: `insights_dashboard_v2` (off `auth_stack_v2`, 2026-08-13).
Status: exploration/planning. Nothing here is implementation yet.

Companion docs in this folder:

| Doc | Contents |
|---|---|
| `DATA_INVENTORY.md` | What data assets exist today (indices, sectors, stock panels, breadth history) |
| `DASHBOARD_DESIGN.md` | Information architecture + module-by-module design of the new dashboard |
| `RRG_SPEC.md` | Relative Rotation Graph: methodology, math, UX, universe scoping |
| `REALTIME_SPEC.md` | Intraday refresh layer: options, licensing posture, technical design |
| `TASKS.md` | Phased breakdown (written once scope is locked with the founder) |
| `DECISIONS.md` | Founder decisions log + canonical list locations (start here for "what did we decide") |

## Why this work

Strategic repositioning: **we launch publicly with the insight_engine,
not the portfolios dashboard.** We do not have regulatory approval to
show the portfolios to the public; stock-based analytical tools are
fine. The insight engine therefore stops being a side surface and
becomes the product. That demands three upgrades:

1. **From lists-and-links to a dashboard.** Today `/insights` is a set
   of pages with cards, tables, and links to more tables. The new
   surface is *data + charting augmented*: every headline indicator
   shows its value today **and** its historical context as an
   interactive chart. Example: Daily Pulse breadth shows today's
   % above 200-DMA and a multi-year chart of that series with regime
   shading.
2. **Live during market hours.** The engine is strictly EOD today
   (16:30 IST pipeline). The dashboard should update intraday —
   subject to the data-licensing posture in `REALTIME_SPEC.md`, which
   is a genuine gate, not a formality.
3. **New flagship analytics.** Headline addition: a state-of-the-art
   **Relative Rotation Graph** for sector rotation, scoped to
   Nifty 50 / 100 / 250 / 500, with historical scrubbing
   (`RRG_SPEC.md`).

## Product philosophy (binding on design decisions)

Marketworks is **not** an empty screener playground — plenty of
platforms do that. It is a *guided* analytical surface: we hold a
market philosophy (momentum, trend, participation) and the dashboard
walks users toward it through pre-made lists and proprietary
indicators backed by our own research. We never tell users to do
anything; every module should let a user reach a logical, rational
conclusion on their own. Concretely:

- Curated, named lists over free-form filters. The general screener is
  demoted to a secondary "explore" affordance, not a tab-level peer.
- Every proprietary indicator ships with (a) today's value, (b) its
  history, (c) a plain-language "how to read this" (the Learn hub
  already does this well — keep and deepen it).
- Compliance frame is unchanged and binding: conditions, not
  instructions. No buy/sell/target/stop-loss language. Forward-return
  claims only after `VALIDITY_PROTOCOL.md`. The existing lexicon tests
  extend to all new copy.

## What already exists (the short version — details in DATA_INVENTORY.md)

The exploration found the codebase is much closer to this vision than
expected:

- **Engines**: breadth, VIX/macro, stress composite, 4-state regime,
  concentration, per-stock metrics (~25), RS ranks, 4 transparent
  scores + 8 tags, 5 watchlist detectors, sector RS + sector breadth +
  subgroups, analogs, conditional distributions, seasonality/calendar.
  All full-history panel builders with mtime-invalidated caches.
- **History exposure is asymmetric**: `/breadth/timeseries`,
  `/stress/timeseries`, `/sectors/{name}` (252d) and `/regime/history`
  already return true time series; everything else is point-in-time.
  The dashboard mostly needs *plumbing to expose existing panels*, not
  new math.
- **Charting**: `lightweight-charts` 5.2 (one price chart) and
  `recharts` 3.7 (portfolio side) already ship. The insights surface
  itself is nearly chart-free today — cards, hand-rolled bars, tables.
- **Sector data**: 23 sectoral indices fetched daily; three sector
  taxonomies committed (NSE 20-industry, Zerodha 30-sector,
  15 super-sectors); 12 sector-index constituent snapshots; index
  weights for 6 indices.
- **Two fully built pages are currently unlinked** (`/insights/sectors`,
  `/insights/watchlists`) — the "reduce tabs, guide users" instinct
  already started; this initiative completes it with a coherent IA.
- **Prior research**: `tasks/breadth_atlas/REPORT.md` profiles all 14
  breadth metrics (distributions, dwell times, extremes, half-lives,
  PCA). This directly informs which series deserve headline charts and
  what reference bands to draw on them (e.g. p5/p95 panic thresholds).

## Scope boundary

**In scope**
- IA + visual redesign of `/insights` into a dashboard (see
  `DASHBOARD_DESIGN.md`): Pulse-as-dashboard, indicator time-series
  everywhere, curated list rails, RRG section, demoted screener.
- Backend: time-series endpoints for indicators that lack them; RRG
  engine (TDD); curated-list detectors formalized (volume surge,
  coiled fresh momentum, custom RS, trend & consistency).
- Intraday layer design + licensing decision; implementation gated on
  that decision.
- Launch repositioning: nav/landing changes to make Insights the
  primary client surface; portfolios remain admin-only
  (flag-controlled, reversible when regulatory approval lands).

**Out of scope**
- Portfolio product changes (stays as-is behind admin).
- Cross-asset module (dropped 2026-08-13 — see `DECISIONS.md`; VIX
  stays, it is part of the macro/stress stack).
- Fundamental data, delivery volumes, options analytics.
- Alerts, saved watchlists, notes archive (post-launch).
- WhatsApp/email broadcast automation.
- Any forward-return claim that has not passed the validity protocol.

## Regulatory / compliance considerations (flag early, decide with founder)

1. **Portfolios gating**: "admin-only" is currently a *frontend* flag —
   the FastAPI insights routes are public by design (R-023), but the
   portfolio API routes are Supabase-auth'd, so the backend side is
   fine. The launch checklist must verify no portfolio data leaks
   through public marketing pages/SEO.
2. **Guided lists vs advice**: named lists ("Volume surges", "Coiled
   fresh momentum") built from transparent, published criteria are
   condition-labels, consistent with the existing pre-RA posture. Keep
   criteria on the card, keep the closed lexicon, keep disclaimers.
   Worth one pass with the compliance consultant before the public
   flip (this was already a Phase D item in insights_v2).
3. **Market data licensing for intraday display**: the serious one —
   see `REALTIME_SPEC.md`. EOD display of derived analytics is the
   current (reviewed) posture; publicly displaying intraday values
   sourced from a personal Kite Connect subscription needs an explicit
   decision, possibly an NSE delayed/real-time data agreement.

## Execution shape (proposed)

Phase 0 — decisions (founder): licensing posture, RRG methodology
sign-off, IA sign-off (mock first, per the visual-validation rule).
Phase 1 — backend history plumbing + RRG engine (TDD).
Phase 2 — dashboard UI rebuild (Pulse, RRG section, list rails,
screener demotion).
Phase 3 — intraday layer per chosen posture.
Phase 4 — launch repositioning (nav, landing, marketing, compliance
review, public flip).

Details per phase in `TASKS.md`.
