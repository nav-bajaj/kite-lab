# design_studies — tasks

## Phase 0 — audit + contract (done 2026-08-06)

- [x] 🤖 Branch audit: confirm redesign fully merged into beta_gtm_mvp
- [x] 🤖 Impeccable detector over beta_gtm_mvp dashboard source
- [x] 🤖 Live-site visual audit (desktop + mobile + /library)
- [x] 🤖 Component/token survey of kite-dashboard + marketworks-design
- [x] 🤖 AUDIT.md (13/20) + GUIDE.md shipped

## Phase 1 — quick fixes (independent of design direction) [low risk]

- [ ] 🤖 File risk-register row + add `accounts.marketworks.in` to
      connect-src (AUDIT P0)
- [ ] 🤖 Fix empty reveal panel on desktop homepage (AUDIT P0)
- [ ] 🤖 Kill `getPnLClass()` raw greens → semantic tokens (~35 sites)
- [ ] 🤖 `allocation-chart.tsx` → `--chart-series-*` tokens
- [ ] 🤖 `bg-amber-*` → `--warning`; Clerk appearance → tokens
- [ ] 🤖 Copy pass: em dashes + aphorism cadence on marketing/library

## Phase 2 — study loops (iterative, founder in the loop) [direction risk]

- [ ] 👤 Seed references: Mobbin screenshots / app names → `references/`
- [ ] 🤖 PREFERENCES.md from extracted principles
- [ ] 🤖 Study loop 1: homepage section grammar (2-3 rendered variants)
- [ ] 👤 Direction sign-off per surface
- [ ] 🤖 Settle study items: Fraunces/Outfit keep-or-evolve;
      illustration replacement; section cadence

## Phase 3 — primitive kit [integration risk]

- [ ] 🤖 Consume @marketworks/design in kite-dashboard (Phase A of
      GUIDE.md §6); collapse 4 card systems into 1
- [ ] 🤖 New primitives with stories + visual tests: Surface, Card,
      ChartFrame, Overlay, Background, StatCallout, ReportPage
- [ ] 🤖 Extend render-asset pipeline to report-page targets

## Phase 4 — re-skin + verify

- [ ] 🤖 Homepage → portfolio cards → dashboard data views → reports
- [ ] 🤖 Re-run audit; target ≥17/20; visual regression green
- [ ] 👤 Ship decision (merge design_studies → beta_gtm_mvp)
