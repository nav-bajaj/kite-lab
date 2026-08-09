# design_studies — state of the study (2026-08-09)

> Loop 19 lives on branch **design_studies_clay** (off design_studies):
> clay.com decoded (CLAY_STUDY.md) and the six-palette picker collapsed
> to a two-theme system on the marketing surfaces — Clay-formula light
> (warm paper ground, Ocean primary, six vivid accent triads) + ink-navy
> dark; sun/moon ThemeToggle replaces the picker in FloatingNav.
> Sections below describe the parent branch through loop 18.

The living summary of where the redesign stands. The loop-by-loop
narrative (every reference decoded, every founder reaction) lives in
PREFERENCES.md; the original audit in AUDIT.md; the anti-slop contract
in GUIDE.md. This file is the "if you read one thing, read this."

## Where things run

- Branch `design_studies`, checked out at
  `~/kite-lab/.worktrees/design_studies` (the main `~/kite-lab`
  checkout stays on `options_data_v1` — open the worktree folder in
  your editor to work here).
- Dev server: `cd .worktrees/design_studies/kite-dashboard && npm run
  dev -- -p 3000`. Homepage at `/`, primitive gallery at `/primitives`.
- 30+ commits, all prefixed `design_studies:`. Nothing pushed; nothing
  merged. Evidence screenshots in `tasks/design_studies/evidence/`.

## The homepage today (the composed result)

1. **Hero** — dramatic token-derived sky (`.mw-hero-drama`, sui.io
   anatomy: near-black crown, luminous primary mid, pale exit), the
   founder-tuned film grain on the background only, giant white
   Stack Sans Text headline, white CTA pill.
2. **Mid-page** — the "gallery recipe" the founder named as the
   target: centered 1140px column, mono index captions (01–05, a
   deliberate brand system), one primitive family per section:
   - 01 the idea → `StackCard` + HeroFlow canvas on the fading grid
   - 02 how it works → `SectionHeader` + `FeatureTile` ×3
   - 03 the research → `GrainCard` (oversized "m", guide lines)
   - 04 the portfolios → `SelectorPanel` on real UNIVERSES data
   - 05 from the library → `GuideCard` ×2 (accent frames)
3. **Drench CTA band** (full-bleed primary + grid texture) and the
   **flat ink-navy footer** — confirmed keepers throughout.

Palette: **Ocean is the study's base** (providers `defaultTheme`), and
the Ocean slot carries the sui-vibrant Horizon system (#0A5CFF + sun +
coral). Mint stays available in the picker with the scoped "Mint v2"
vibrance (`.mw-mint2`, primary #00875F).

## The primitive library

`components/marketing/study-cards.tsx`:
`GrainCard` · `StackCard` · `CollageCard` + `FloatPanel` + `GhostRows`
· `SectionHeader` · `FeatureTile` · `FrameCard` · `GuideCard`.
`components/marketing/selector-panel.tsx` (client):
`SelectorPanel` · `FactTile`.
Textures in `globals.css`: `.mw-grainy` (founder-tuned grain on any
container, background-only), `.mw-grid-fade` (teak.io grid breathing
with scroll), `.mw-grid` / `.mw-grid-inverse` (chart-paper + drench
texture), `.mw-hero-drama` (the hero sky).
Tooling: `grain-tuner.tsx` — live slider panel for texture variables;
unmounted, re-mountable for any future tuning session.
Everything is token-derived: all primitives re-theme across palettes.

## Decisions ledger

KEPT (and why):
- Banded/centered composition with varied card primitives — the
  /primitives gallery's balance, explicitly chosen by the founder.
- Dramatic dark gradient hero (sui.io) with stylistic grain (Noto),
  tuned by the founder via sliders; grain never touches text.
- Drench CTA + flat footer (loved since loop 4-6).
- Production card hierarchy over flat minimalism for content sections.
- Two-sans typography: Stack Sans Text (headings, via Google Fonts
  stylesheet) + Outfit (body/UI); mono for metadata labels.
- Ocean-slot Horizon palette as base; palette picker retained.
- Interactive SelectorPanel with real data only — no fabricated
  numbers anywhere in the study (hard rule).
- Lenis smooth scroll (loop 22), homepage-only via `SmoothScroll` in
  page.tsx — inertia easing on the real scroll position, not the
  rejected snap/takeover scroll-jacking; reduced-motion skips it.

REJECTED / let go (code removed; history has it all):
- Cartesia structural grid (rails + rhythm strips) — loop 4 revert.
- Full flat Base-style minimal middle — read too plain.
- Sticky takeover scroll AND snap-to-section scrolling.
- Light pastel grain hero (superseded by the dark drama sky).
- HeroQuant (dither + breathing candles canvas) — superseded by the
  original HeroFlow's return; component deleted.
- Two-theme light/dark exploration: ThemeToggle deleted, Horizon Dark
  CSS removed (values preserved in PREFERENCES loop 3 if ever needed).
- Stack Sans Notch (too characterful), Schibsted-as-display (fallback
  only now), Fraunces on the homepage (still used on other pages).
- `.mw-bright`, mint/blue hero skies, `.mw-dots-light` — dead CSS
  removed in the loop-18 cleanup.
- Instrument Serif + Inter pairing (loop 22) — rejected on sight; the
  400-only display face reads light at card-heading sizes. Fraunces +
  Outfit confirmed again.

## Open threads (the long way still to go)

- **Media slots**: GuideCard/StackCard/CollageCard want REAL product
  screenshots (dashboard captures, chart crops) instead of ghost rows —
  highest-impact single upgrade.
- **Other marketing surfaces** (`/portfolios`, `/library`, sign-in/up,
  legal) still run the OLD design language (mist panels, Fraunces,
  FlowGrid) — the new language stops at the homepage + gallery.
- **Palette endgame**: ANSWERED in loop 19 (design_studies_clay) —
  collapse to light + dark, Ocean-based, per the Clay study. Marketing
  nav done; dashboard navbar still has the six-swatch picker and the
  five non-Ocean palettes still exist (removal is a merge decision).
- **Typography endgame**: Stack Sans Text is CDN-loaded (self-host via
  next/font after a Next upgrade); Fraunces' site-wide fate undecided.
- **Critique re-run**: baseline is 24/32 (loop 1); re-score the new
  composition when it stabilizes.
- **Evidence artifact** for the research section (founder to choose a
  real rebalance-note excerpt or sample daily read).
- Mobile pass beyond overflow checks; real-device test.

## Revisit-before-merge checklist (do NOT merge without these)

1. Remove `/primitives` from `middleware.ts` isPublicRoute (marked).
2. Decide providers `defaultTheme` ("ocean" is study-only; was
   "system").
3. Move Stack Sans Text to next/font self-hosting (CSP + perf).
4. R-023 (CSP `accounts.marketworks.in`): close the register row after
   live verification post-deploy.
5. Reconcile the homepage's new language with the other marketing
   pages before shipping any of it.
6. Re-run `/impeccable critique` + the detector; update AUDIT.md.
7. Lenis is homepage-only ("keep for now", loop 22): decide site-wide
   vs homepage vs drop before merge; anchor links would need
   lenis.scrollTo if it spreads to pages that use them.
