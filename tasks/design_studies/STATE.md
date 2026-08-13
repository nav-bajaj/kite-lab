# design_studies — state of the study (2026-08-13)

> **PRIMITIVES PHASE CLOSED (2026-08-13, founder call).** Loops 23-31
> delivered: the SET colour system (single green, five triads,
> light + green-black dark) and type system (Libre Baskerville 500 ·
> Outfit · IBM Plex Mono) — contract at brand/palette.html; both
> ported into the app; and a 20-entry primitive library at
> /primitives spanning the clay-era cards (01-07), the instrument set
> (08-12), and the composition set (13-20, incl. the clay-committed
> portfolio stack in identity hues and the textured mega-footer).
> Reference decodes: CLAY_STUDY (+part 2), AEYE_STUDY, PERCEPT_STUDY.
> Refinement continues as-needed against real page builds. NEXT WHEN
> RESUMED: (1) homepage recomposition from the library — hero rework
> first (the gradient dies; candidates: sticky dark plate, table-as-
> hero, daylight collage row), then banded/carded body, ink band,
> committed stack, textured footer; (2) real product screenshots into
> the media slots (still the highest-impact open item); (3) other
> marketing surfaces (/portfolios, /library, sign-in) onto the
> system; (4) the merge checklist below (middleware /primitives,
> providers defaultTheme + dashboard picker retirement, Lenis scope,
> critique re-run, R-023); (5) port the final contract back to
> ~/marketworks-design as a new DESIGN.md major version. Branch has
> never been pushed — consider pushing design_studies_clay to origin
> as backup before a long pause.

> **Loop 31 — colour commitment, clay's way (founder amendment).**
> "We use the sets too sparingly - they are barely known." The
> elements-only rule is AMENDED: sibling section cards now take the
> FULL triad as their world (tint ground · deep ink · vivid marks —
> the CLAY_STUDY part-1 formula), with white page between cards and
> full-bleed bands still banned. Built: StackSection `accent` mode +
> `GhostPill` (clay's pill-with-ghost-pills, deep-on-tint so contrast
> is validated by construction) + TexturePanel `toneClassName`; the
> stack demo is now four portfolio cards in their identity hues
> (Core green · Quality sun · Trend sky · Defensive purple) with real
> figures and per-card toned textures. BUG found while building: the
> tint utilities are `bg-accN` (NOT `bg-accN-bg`) — loop-28/30 uses
> of `bg-accN-bg` (mosaic method cells, board pills/hot-row) were
> silently transparent; all fixed. Contract amended in
> palette.html. Evidence: `evidence/loop31_committed-stack.jpg`.

> **Loop 30 — founder curation + the accent/gradient rethink.**
> Cuts: TexturePanel drift + contour variants (founder), and
> `MethodMark` entirely — it resurrected the REJECTED design_reset
> certificate seal without approval; provenance lesson recorded.
> Adds: `grid` (chart paper) and `dots` (pipeline lattice) texture
> variants. Accents now do STRUCTURAL work per the loop-23 rule:
> ProofMosaic cell kinds carry triads (method = sun wash, rejected =
> coral, library = purple), SignalChips dot colour encodes event kind
> (green portfolio / sky system), SectionMeter takes a rotating
> accent for sibling section sets, and SignalBoard pills carry the
> PROPOSED portfolio identity hues (Core = green · Quality = sun ·
> Trend = sky · Defensive = purple — one hue per portfolio
> site-wide; founder to ratify). Gradient position: no decorative
> colour gradients on light surfaces — textures + masked fades do
> that work; luminous radials remain a dark-surface device; the
> legacy hero gradient dies in the hero rework. Gallery renumbered
> 13-20. Evidence: `evidence/loop30_accent-pass.jpg`.

> **Loop 29 — system-incorporation pass (founder flagged it).** Two
> real defects found and fixed: (1) the green light theme was still
> GATED to `data-palette="ocean"` — any visitor with a stale stored
> palette from the retired picker rendered old tokens; the light
> block is now `html:not(.dark) .mw-brand` (palette attribute is
> irrelevant on brand surfaces, per the loop-23 no-picker decision).
> (2) both marketing pages still carried the loop-7 `.mw-mint2`
> override (old lichen #00875F) — class and CSS retired. Verified by
> simulating stale `mint` and `midnight` visitors: both now render
> the set systems (#0B7E52/white · #3FCE95/#0D1412), LB 500
> headings, Plex Mono. Reminder that masked the fix during
> verification: the Turbopack stale-CSS gotcha (`rm -rf .next`).

> **Loop 28 — the full composition batch (founder: "make the whole
> batch, we can always delete later").** All nine menu items from the
> three reference studies, gallery entries 13-21:
> `TexturePanel` (4 generative card-backdrop variants — the parked
> asset fields re-homed at card scale), `SignalChips` (real 12-May
> events, light + dark), `ProofMosaic` (stats/method/rejected/library
> tiles, one cell language), `MethodMark` (rose-curve fact roundels),
> `InkBand`+`InkCard` (the sustained dark movement), 
> `AccordionShowcase` (synced accordion + swapping visual, client),
> `SignalBoard` (the real table as hero media), `StackSection`
> (clay stacking, colour-rule-resolved: white/soft/wash panels only),
> `TexturedFooter` (merged CTA+footer on textured green-deep, giant
> wordmark). Components: `composition-primitives.tsx` +
> `accordion-showcase.tsx`; CSS: `.mw-chip-row`, `.mw-fade-in`. All
> deterministic (RSC-safe), all real data, reduced-motion static.
> Evidence: `evidence/loop28_composition-batch.jpg`. Founder curates:
> keep / tune / delete per entry.

> **Loop 27 — instrument primitives shipped to /primitives (founder
> to judge).** From AEYE_STUDY.md, five devices built on the set
> system, gallery entries 08-12: `SectionMeter` (metered index
> header), `StatTable` (hairline-cell figures, real Quality Momentum
> record), `PipelineDiagram` (the real daily pipeline as nodes on a
> dotted canvas, travelling light on the rail, static under
> reduced-motion), `ExhibitFrame` (corner-tick media framing), and
> `ScrambleIn` (the single rationed decode moment, hand-rolled, no
> GSAP). Components:
> `components/marketing/instrument-primitives.tsx` + `scramble-in.tsx`;
> CSS: `.mw-dot-canvas`, `.mw-pipe-light` in globals. Evidence:
> `evidence/loop27_instrument-primitives.jpg`.

> **Loop 26 — the SET systems are IN THE APP.** kite-dashboard now
> renders the loop-23/25 decisions: the ocean slot carries the
> single-green light theme, `.dark .mw-brand` is the green-black
> companion, and fonts are Libre Baskerville (next/font variable
> 400-700 + italic; `.mw-serif-headings` pins 500) + Outfit + IBM
> Plex Mono (the data voice — `.mw-brand` re-points the mono var, so
> the dashboard keeps Geist Mono untouched). Stack Sans CDN link and
> Schibsted removed; /primitives moved to serif headings; hero-drama
> gradient anchors re-cast green (still the old gradient device — the
> founder's asset work replaces it). Evidence:
> `evidence/loop26_home-{light,dark}.jpg`, `loop26_primitives.jpg`.
> tsc clean; both themes verified. **Next: founder-led primitives /
> sections / assets exploration on this canvas** (exploration ideas
> to come from the founder).

> **Loop 25 — COLOUR + TYPE ARE SET. Serif revised to Libre
> Baskerville; asset studies parked.** The type system is now
> **Libre Baskerville** (display — Google Fonts serves
> 400/500/600/700 + italic; 500 is the working display weight; LB
> runs wide so display sizes step down vs Fraunces) + **Outfit**
> (body/UI) + **IBM Plex Mono** (data voice per loop 24). Decided
> after seeing LB in full composition (assets3.html serif toggle).
> The asset-study rounds are PARKED as founder-judged
> not-working-yet: `brand/assets.html` (v1 flat fields),
> `brand/assets2.html` (v2 luminous dark — "too crypto"),
> `brand/assets3.html` (v3 daylight convergence + agency-review
> fixes: asymmetric drench with one CTA, no hero eyebrows, gridded
> ASCII icons). Keep all brand HTML files — palette.html and
> fonts.html are the visual contract; the assets pages are the
> exploration record and contain reusable pieces (annotated-exhibit
> hero, daylight dot-map, drench band, dither edges). **Assets and
> primitives restart founder-led in the main study from here.**
> Useful context for that restart: the design-taste-frontend skill
> at `.agents/skills/design-taste-frontend/SKILL.md` (agency-grade
> review bar), and the open agency-review items: real product
> screenshots into media slots (highest-impact), accurate India
> geometry if the dot-map survives.

> **Loop 24 — type decided (superseded by loop 25 on the serif).**
> Nine wardrobes at `tasks/design_studies/brand/fonts.html` (6
> founder-named references harvested live: public.com, hebbia,
> tars.pro, zerohash, aeye webflow, clay.com; + 2 hybrids). Verdict:
> keep Fraunces + Outfit, adopt **IBM Plex Mono** as the third
> voice, used generously — figures, labels, captions, metadata,
> tickers, chart axes; never body text. Evidence:
> `evidence/loop24_fonts-{decided,study}.jpg`.

> **Loop 23 — direction reset (founder-approved): single-green colour
> system.** The six-palette system AND the loop-19 two-theme Clay
> mapping are superseded by one green-anchored light + dark system:
> white ground, ink `#141A17` + one grey `#5C6663`, brand green
> `#0B7E52` (4-step family), five leashed accent triads (sun / sky /
> coral / purple / lime), validated data inks, green-black dark
> companion. Live guide: `tasks/design_studies/brand/palette.html`
> (serve the folder; light/dark toggle; contrast badges computed
> live). Evidence: `evidence/loop23_palette-{light,dark}.jpg`.
> Positioning line (founder, binding): Marketworks lives in the
> overlap of **Finance × Technology × Editorial Research** — every
> element is judged against that. Roadmap: font pairings → asset
> study (hero replacement for the heavy gradient, textures, dither,
> light motion) → homepage re-composition (banded + carded rhythm).
> The guide page grows into the full visual contract; the /primitives
> page will be folded into it. Sections below describe loops ≤22.

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
