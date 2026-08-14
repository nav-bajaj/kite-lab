# Tasks — insights_dashboard_v2

Restructured 2026-08-14 (founder direction): development proceeds
**indicator-set by indicator-set** — vertical slices, each shipping
backend + card + detail view together — not all-backend-then-all-UI.
Owners: 👤 founder · 🤖 agent. Tags: [compliance] [licensing] [perf]
[data] [design].

## Phase 0 — Decisions (status)

- [x] D1 👤 Intraday posture — DECIDED: live route, posture C
      (register row owed before public exposure). `DECISIONS.md`.
- [x] D2 👤 IA — DECIDED: sidebar + mission-control overview +
      expand-to-detail; mock approved 2026-08-14. Production design
      system is authoritative for visual execution; mock is
      authoritative for structure. `DASHBOARD_DESIGN.md` §1.
- [ ] D3 👤 RRG methodology sign-off (`RRG_SPEC.md` §1-2: recipe A
      defaults, universe composites, benchmark choices). Needed
      before Slice 3 engine work — not before Slices 1-2.
- [ ] D4 👤 [compliance] Launch plan + consultant pass before the
      public flip. Needed before Phase L — not before dev slices.

## Slice 1 — Shell + Market set v1 (NO new engine work)

Everything here runs on endpoints that already exist in production
(`/reading`, `/breadth/timeseries`, `/stress/timeseries`,
`/regime/history`). Goal: the real mission control in the browser.

- [x] 1.1 🤖 Route restructure: `/insights` becomes the sidebar shell
      (site navbar untouched); Overview page skeleton with section
      headers; old tab pages kept reachable until slices replace them.
- [x] 1.2 🤖 Component kit: IndicatorCard (label/value/sparkline/
      expand), SectionHeader, DetailShell (back button + sub-rail),
      ChartModule on lightweight-charts (range picker, reference
      bands) — all on existing role tokens, all six palettes.
- [x] 1.3 🤖 Market cards v1: Market State (regime), Market Stress,
      Breadth — wired to existing endpoints, snapshot `?date=`
      preserved.
- [x] 1.4 🤖 Detail views v1: Breadth detail (bands from breadth_atlas
      percentiles, stats strip, learn panel) + Stress detail +
      Regime ribbon detail (episodes over Nifty).
- [x] 1.5 🤖 [compliance] Lexicon tests extended to new card/detail
      strings; disclaimer footer in the new shell verified.
- [ ] 1.6 👤 Browser review on real data → adjust before Slice 2.

## Slice 2 — Market set v2 (small backend additions)

- [x] 2.1 🤖 [data] `GET /api/insights/macro/timeseries` (VIX +
      z-bands) from the existing macro panel (TDD: shape spec).
- [x] 2.2 🤖 Cards + details: India VIX, Net New Highs, McClellan
      (both already in the breadth panel/timeseries whitelist).
- [x] 2.3 🤖 Movers rail on Overview (existing `/movers`), each rail
      linking toward its future list (Slice 4).
- [x] 2.4 🤖 [data] Concentration timeseries endpoint + card + detail
      (panel exists; endpoint missing).

## Slice 2.5 — Atlas follow-ups (from PRIOR_RESEARCH.md) — DONE 2026-08-14

- [x] 2.5a 🤖 Engine: pct_above_21dma, avg_dist_from_200dma,
      mcclellan_sum added to breadth panel (TDD synthetic fixtures +
      real-data correlation anchor); stale-schema cache guard so a
      fresh-by-mtime pickle from older code rebuilds on deploy.
- [x] 2.5b 🤖 Breadth detail: metric explorer — DMA family + avg-dist
      with per-metric atlas bands (p5/median/p95 each).
- [x] 2.5c 🤖 Regime detail: "What followed days like these" base-rates
      table from conditional_dist (n, median, middle half, % positive
      per horizon) with history-not-forecast framing [compliance].
- [x] 2.5d 🤖 Navigation audit: all insights hrefs verified against the
      new IA; legacy pages (sectors/watchlists/screener/learn/stocks)
      render correctly inside the app shell; no old-layout links remain.

## Slice 3 — Sectors & Rotation (the RRG flagship) — needs D3

- [ ] 3.1 🤖 [data] Add missing indices to `tracked_indices.csv`
      (NIFTY 200, TOTAL MKT, midcap/smallcap variants as needed);
      verify long-panel sync + freshness rows.
- [ ] 3.2 🤖 RRG engine `app/insights/rrg.py` (TDD per RRG_SPEC §6:
      synthetic rotation fixtures, universe-independence, W-FRI
      completed-bar resample, warm-up policy) + composite builder in
      the daily pipeline + `GET /api/insights/rrg`.
- [ ] 3.3 🤖 RRG canvas component (SVG: quadrants, tails, isolate,
      zoom/fit, playback scrubber) + synced quadrant table + mini-RRG
      card on Overview.
- [ ] 3.4 🤖 Sector RS bars card (existing `sector_rs`) + sector
      detail (existing 252d history endpoint) + constituent
      drill-down (vs market / vs sector composite toggle).
- [ ] 3.5 🤖 Learn: RRG explainer with the Optuma-caution framing
      [compliance]; glossary: quadrant, heading, velocity, distance.
- [ ] 3.6 [perf] RRG payload <150 KB / <100 ms warm; 15-min cache.

## Slice 4 — Stock Lists

- [ ] 4.1 🤖 [data] Daily cross-section persistence (date, symbol,
      rank, scores, tags, list membership) appended by the 16:30
      pipeline; backfill where cheap. security-reviewer on any
      sync-path diff.
- [ ] 4.2 🤖 Detectors formalized (TDD synthetic fires/doesn't-fire):
      volume_surge, coiled_fresh_momentum, custom_rs_leaders,
      trend_consistency. Validity study for any badge claim
      [compliance].
- [ ] 4.3 🤖 List cards on Overview + list detail pages (criteria on
      card, list-specific columns, membership-history mini-panel).
- [ ] 4.4 🤖 Screener demotion: sidebar bottom slot, presets removed
      (now lists), minimal filter-rail UI (logic already client-side).

## Slice 5 — Intraday layer (posture C; independent of 3-4)

- [ ] 5.1 🤖 `app/insights/intraday.py` + scheduler job + day-file +
      `GET /api/insights/intraday` (delay param for delayed-first
      rollout). TDD synthetic quote fixtures.
- [ ] 5.2 🤖 [data] Time-of-day volume curve probe (nse500_data_hourly)
      → intraday volume-surge counts.
- [ ] 5.3 🤖 Live pills + market-hours SWR hook + provisional tail
      point on charts + freshness row + token-expiry degradation.
- [ ] 5.4 👤 [licensing] Register row + label review before public.

## Phase L — Launch repositioning (needs D4)

- [ ] L.1 🤖 Insights = signed-in home; portfolio nav behind admin
      flag (`nav.ts`, `bottom-nav.tsx` SLOTS, `navbar.tsx`,
      middleware redirects, marketing CTAs). Reversible by flag.
- [ ] L.2 🤖 [compliance] Disclaimer coverage audit; no portfolio
      data on public marketing/SEO surfaces.
- [ ] L.3 👤 [compliance] Consultant pass → flip
      `NEXT_PUBLIC_INSIGHTS_ACCESS=all`.
- [ ] L.4 🤖 Prod provisioning check + verification checklist +
      register rows (intraday posture, public surface).

## Post-launch (documented, not scheduled)

- Personalization phase 1: watchlists + "My Watchlist" module
  (`PERSONALIZATION.md`) — sidebar slot already reserved.
- Alerts + notification center; entitlements tie-in.

## Standing constraints

- TDD per `tasks/insight_engine/TDD_POLICY.md`; validity protocol for
  forward-return claims; closed lexicon on all copy.
- No pushes 09:00-15:30 IST. `pytest tests/` + `npm run build` clean
  before push; merge `--no-ff`.
