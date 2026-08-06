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

- [x] 17 loops run 2026-08-06 (R1 cartesia REJECTED; R2 base.org; R3
      phantom; R4 sui.io; Noto grain; clay.com + teak.io primitives).
      Full narrative in PREFERENCES.md; current state in STATE.md.
- [x] 🤖 Homepage composed from the primitive library (loop 17);
      Ocean base; hero/CTA/footer keepers locked
- [x] 🤖 Typography: Stack Sans Text + Outfit (+ mono); Fraunces off
      the homepage
- [ ] 👤 Continue loops: media slots (real screenshots), remaining
      surfaces, palette + typography endgames

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
