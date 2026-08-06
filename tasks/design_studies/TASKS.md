# design_studies — tasks

## Phase 0 — audit + contract (done 2026-08-06)

- [x] 🤖 Branch audit: confirm redesign fully merged into beta_gtm_mvp
- [x] 🤖 Impeccable detector over beta_gtm_mvp dashboard source
- [x] 🤖 Live-site visual audit (desktop + mobile + /library)
- [x] 🤖 Component/token survey of kite-dashboard + marketworks-design
- [x] 🤖 AUDIT.md (13/20) + GUIDE.md shipped

## Phase 1 — quick fixes (independent of design direction) [low risk]

- [x] 🤖 File risk-register row (R-023) + add `accounts.marketworks.in`
      to connect-src (close row after live verification)
- [x] 🤖 ~~Empty reveal panel~~ retracted: lazy-load screenshot artifact
- [x] 🤖 Kill `getPnLClass()` raw greens → semantic tokens (9 files)
- [x] 🤖 `allocation-chart.tsx` → accent-rotation tokens + color-mix tints
- [x] 🤖 `bg-amber-*` → `--warning` (Clerk appearance stays literal-hex by design)
- [x] 🤖 Copy pass: em dashes + aphorism cadence (marketing/library/legal/universes)

## Phase 2 — study loops (iterative, founder in the loop) [direction risk]

- [~] 👤 Seed references: R1 cartesia.ai captured; more screenshots incoming
- [x] 🤖 PREFERENCES.md opened (R1 structural grid + typography shortlist)
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
