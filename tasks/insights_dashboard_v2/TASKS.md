# Tasks — insights_dashboard_v2

Status: DRAFT — exploration phase. Locks after founder decisions D1-D4.
Owners: 👤 founder decision/review · 🤖 agent-executable.
Risk tags: [compliance] [licensing] [perf] [data] [design].

## Phase 0 — Decisions & direction (gate for everything)

- [x] D1 👤 [licensing] Intraday posture: DECIDED 2026-08-13 — live
      route approved (posture C: live derived indicators, no public
      per-stock live quotes). See `DECISIONS.md`. Still owed: risk-
      register row before public exposure.
- [x] D2 👤 [design] PARTIAL 2026-08-13: insights stays inside
      kite-dashboard and becomes the primary signed-in surface (no
      separate app — `DECISIONS.md`). Still open: 4-tab IA + screener
      demotion sign-off via Pencil mock (0.1).
- [ ] D3 👤 RRG methodology sign-off (`RRG_SPEC.md`): normalization
      choice, universe-scoped composites, daily vs weekly default.
- [ ] D4 👤 [compliance] Confirm launch plan: portfolios admin-only at
      launch; compliance-consultant pass on new copy before public flip.
- [ ] 0.1 🤖 [design] Pencil mock of Pulse + Sectors & Rotation + Stock
      Lists (per visual-validation-first rule); founder review loop.

## Phase 1 — Backend: history plumbing + engines (TDD throughout)

- [ ] 1.1 🤖 [data] `GET /api/insights/macro/timeseries` (VIX + z-bands)
      and `/concentration/timeseries` from existing panels; extend
      `/breadth/timeseries` metric whitelist if needed.
- [ ] 1.2 🤖 [data] Daily cross-section persistence: append per-day
      (symbol, rank, percentile, 4 scores, tags, list membership) slice
      from the 16:30 pipeline; backfill from panels where cheap.
      Un-blocks rank sparklines + list-membership history.
      security-reviewer pass on any sync/upload path change.
- [ ] 1.3 🤖 RRG engine `app/insights/rrg.py` per RRG_SPEC: RS-ratio /
      RS-momentum math (spec tests first: synthetic series with known
      quadrant/rotation), tail assembly, universe-scoped sector
      composites, benchmark matrix, `GET /api/insights/rrg`.
- [ ] 1.4 🤖 Curated-list detectors formalized in `watchlists.py` (or
      new `lists.py`): volume_surge, coiled_fresh_momentum,
      custom_rs_leaders, trend_consistency. Each: synthetic
      fires/doesn't-fire spec tests, published criteria strings,
      lexicon-test coverage. Validity study per
      `pattern_validity_study.py` for any list we want to badge.
- [ ] 1.5 🤖 [data] Add missing indices to `tracked_indices.csv`
      (NIFTY 200, MIDCAP 100/50, SMLCAP 100/50, TOTAL MKT + any RRG
      needs); verify sync into the long panel; freshness rows.
- [ ] 1.6 🤖 [perf] Payload/latency budget: RRG + timeseries endpoints
      under 150 KB / <100 ms warm; extend the 15-min cache headers.

## Phase 2 — Frontend: the dashboard rebuild

- [ ] 2.1 🤖 [design] Chart-module component kit on lightweight-charts
      (range picker, reference bands, regime ribbon, provisional-point
      style, theme-var probe reuse); palette tokens for quadrants/bands.
- [ ] 2.2 🤖 Pulse rebuild: headline strip + factor-curated chart
      modules + movers rail (`DASHBOARD_DESIGN.md` §2).
- [ ] 2.3 🤖 Sectors & Rotation tab: RRG component (trails, playback,
      universe/benchmark switchers, synced table) + sector strip +
      subgroup block; absorb orphaned `/sectors`.
- [ ] 2.4 🤖 Stock Lists tab: 4 list products with criteria cards,
      list-specific columns, membership-history mini-panels; absorb
      `/watchlists`; presets removed from screener.
- [ ] 2.5 🤖 Screener demotion: move under Explore entry points; ship
      the minimal filter-rail UI (logic already exists client-side).
- [ ] 2.6 🤖 Learn: explainers for RRG, each list, each charted
      indicator; glossary additions. [compliance] lexicon tests on all
      new strings.
- [ ] 2.7 🤖 Mobile pass: sparkline collapse, RRG small-screen behavior
      (likely table-first with mini-graph).

## Phase 3 — Intraday layer (per D1)

- [ ] 3.1 🤖 `app/insights/intraday.py` + scheduler job + day-file
      persistence + `GET /api/insights/intraday` (+ delay parameter for
      posture B). TDD: synthetic quote fixtures.
- [ ] 3.2 🤖 [data] Time-of-day volume curve calibration probe (uses
      `nse500_data_hourly/`); powers intraday volume-surge counts.
- [ ] 3.3 🤖 Frontend live layer: market-hours SWR hook, live pills,
      flash-on-change, provisional tail point on charts.
- [ ] 3.4 🤖 Freshness row for intraday job; graceful token-expiry
      degradation; mid-session restart recovery test.
- [ ] 3.5 👤 [licensing] Re-verify posture with labels/wording as built
      ("delayed", "provisional") before public exposure.

## Phase 4 — Launch repositioning

- [ ] 4.1 🤖 Nav/shell: insights becomes signed-in home; portfolio nav
      behind admin flag (`nav.ts`, `bottom-nav.tsx` SLOTS,
      `navbar.tsx`, middleware redirect targets, marketing CTAs).
      Reversible by flag when regulatory approval lands.
- [ ] 4.2 🤖 [compliance] Disclaimer coverage audit after shell swap
      (DisclaimerFooter vs FooterPanel); no portfolio data on public
      marketing/SEO surfaces.
- [ ] 4.3 👤 [compliance] Consultant pass on all public copy; then flip
      `NEXT_PUBLIC_INSIGHTS_ACCESS=all`.
- [ ] 4.4 🤖 Prod data provisioning check (Railway panels, upload
      whitelist unchanged?); run full verification checklist; register
      rows (intraday posture, public surface) filed.
- [ ] 4.5 👤 Announce/beta comms (content engine work, separate task).

## Standing constraints

- TDD per `tasks/insight_engine/TDD_POLICY.md` for all engine/detector
  work; validity protocol for any forward-return claim.
- No pushes 09:00-15:30 IST (live services restart on deploy).
- `pytest tests/` + `npm run build` clean before any push to main;
  merge `--no-ff`.
