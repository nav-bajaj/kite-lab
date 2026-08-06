---
target: homepage (Variant B3, design_studies)
total_score: 24
max_score: 32
na_heuristics: 7,9
p0_count: 0
p1_count: 2
timestamp: 2026-08-06T09-51-33Z
slug: kite-dashboard-src-app-page-tsx
---
Method: dual-agent (A: design-review sub-agent · B: detector-evidence sub-agent)

Target: Marketworks homepage, Variant B3 (Base-lane flat + Horizon palette), kite-dashboard/src/app/page.tsx @ design_studies branch.

## Design Health Score

| # | Heuristic | Score | Key Issue |
|---|-----------|-------|-----------|
| 1 | Visibility of System Status | 3 | Hover feedback is a bare 1px border shift; nav lacks current-page state |
| 2 | Match System / Real World | 4 | Best-in-class plain language; jargon defined inline at first use |
| 3 | User Control and Freedom | 3 | Clean funnel, no traps; signed-in users routed to dashboard |
| 4 | Consistency and Standards | 2 | Three visual languages: glass-pill nav + flat B3 body + rounded inset footer |
| 5 | Error Prevention | 3 | Auth-aware CTA prevents redundant sign-up |
| 6 | Recognition Rather Than Recall | 3 | Card metadata reintroduces undefined jargon at the decision point |
| 7 | Flexibility and Efficiency | n/a | Single-path persuade surface |
| 8 | Aesthetic and Minimalist Design | 3 | Strong reduction; undermined by wrong ground (mist bug, now fixed), below-fold canvas |
| 9 | Error Recovery | n/a | No error-producing surfaces |
| 10 | Help and Documentation | 3 | Library serves as docs; post-signup expectations unset (allowlist unstated) |
| **Total** | | **24/32 (75%)** | **Good** |

## Design Specificity Verdict

LLM assessment: the words and the hero canvas are authored for this product (HeroFlow narrates signals-converge-to-portfolio; mono metadata is real product data; copy register is genuinely anti-finfluencer). But on mobile the canvas is hidden, and the remaining skeleton (hero → explainer → 3 steps → 3 cards → drench) could ship for any fintech with a copy swap. Specificity lives in writing + one desktop-only element.

Deterministic scan: 1 CLI finding — codex-grid-background advisory on the .mw-grid definition (globals.css:252), now used only in contained fields (hero chart-band, drench), which is the P10 exemption. In-page detector: low-contrast x7 (#737373 on #F0F7F3 at 4.4:1 — root-caused during critique to the mist-ground bug, fixed same session), layout-transition x2 (padding/height transitions), overused-font (Geist Mono at 16% — the mono is a Next.js default, not a chosen brand mono).

Convergence note: both assessments independently surfaced the wrong ground; A read it as a design flaw, B measured it as contrast near-misses; root cause was one unlayered CSS rule beating the utility layer.

## Priority Issues

- [P1] The frame contradicts the lane: glass-pill blurred nav + rounded deep-inset footer sandwich the flat hairline body — reads mid-migration, not conviction. Fix: flat B3 nav (hairline bottom rule) + flat full-bleed footer, or consciously keep the pill language and echo it in the body.
- [P1] Ground was the wrong white (mist #F0F7F3, not the almost-white) — FIXED during critique (unlayered .mw-brand rule beat bg-surface-base; .mw-bright now sets background-color directly).
- [P2] Red-coded mono label on the defensive product: accent rotation puts coral on "drawdown-reduced" — reads as loss-semantics in finance, on the most conservative offering. Fix: neutral mono for risk labels or deliberate mapping (defensive → teal/green).
- [P2] Zero evidence at the trust moment: "years of research" asserted three times, shown zero times. Host one honest process artifact (rebalance-note excerpt, sample daily read) in "Process over prediction".
- [P2] Portfolio card label wrap ("quality-tilt, regime-adaptive") breaks the three-card baseline. Fix: one-line label or fixed-height label row.
- [P3] Hardcoded "Three ways" copy vs data-driven clientVisible cards (prod shows 4 to clients); numeral goes stale when the flag flips.

## Persona Red Flags

Jordan (first-timer): card metadata drops the hand-holding exactly at the decision point; allowlist gating never stated — signs up, may hit a wall; two near-equal hero pills compete.
Riley (stress tester): "How it works" cards hover blue but aren't clickable (false affordance); PalettePicker (theme-lab control) ships on public marketing nav; all three "View portfolio" links go to the same URL; nav pill goes pale-blue-on-blue over the drench.
Casey (mobile): loses HeroFlow entirely — first screen is generic text; ~7 screen-heights with no CTA between hero and final drench; two stacked same-size pills invite mistap.

## Minor Observations

- Drench headline is a status line, not a benefit.
- Step numbers 01/02/03 in three colors: sequence already encodes order; rotation adds color without meaning there.
- Hero canvas sits almost entirely below the fold at 1440x900.
- Footer mixes product and legal links in one flat row.
- Layout-transition x2 (padding/height) — likely the floating nav; move to transform-based motion.

## Questions to Consider

1. If the flow-field canvas is THE identity element, why does the mobile-first Indian audience never see any version of it?
2. Can a research brand keep saying "years of research" while showing zero research artifacts within compliance?
3. Is this a two-color page (blue + coral) wearing a five-color system — would B3 be stronger with rotation cut on marketing and polychrome saved for product UI?

## What's Working

- HeroFlow: motion-as-identity done right (encodes the product story, token-driven colors, reduced-motion safe).
- Copy register IS the brand: inline definitions, honest hedges, unhidden disclaimers.
- State-aware CTA plumbing (signed-in → View dashboard).
- Cognitive load: 0 hard failures on the 8-item checklist — the reduction is working.
