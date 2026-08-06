# Founder preferences — extracted principles

Living doc. Each entry: the reference, what the founder singled out, and
the named principle we carry into studies. References land in
`references/`.

## R1 · cartesia.ai (2026-08-06) — REJECTED after render

Variant A (rails + textured rhythm strips on the homepage, commit
6874b24, reverted) was built and shown live; founder verdict: "I don't
think this is looking nice at all," direction dropped entirely.
Learning for future loops: the founder evaluates rendered results, not
concepts — and a structural/engineered grid layer does not fit the
brand's calm-editorial register on our surface even though it worked on
Cartesia's. The P2/P3/P4 principles (texture never behind content, one
token drives all lines, minimalism as density control) remain valid
independent of the rejected rail aesthetic. The decorative FlowGrid
background returned with the revert; its `codex-grid-background`
advisory stands open for whatever direction wins.

<details><summary>Original R1 study (kept for the record)</summary>

Screenshot: `references/cartesia_home.jpg`. Founder's focus: **the
background grid that doubles as a layout layer**, and the overall
minimalism. Explicitly NOT the colors or typography.

Decoded implementation (inspected live):

- One page-level CSS grid with named lines:
  `[full-start] 96px [content-start] 1248px [content-end] 96px
  [full-end]`. Every section is a grid child choosing `col-[content]`
  or `col-[full]`.
- **Vertical rails:** every content section carries `border-x` in a
  single shared `--border` token (`#E4E3DB`); stacked sections make the
  rails read as continuous full-height lines. Content aligns to the
  rails, so the grid IS the layout, not a backdrop.
- **Rhythm strips:** 40px full-bleed bands between sections textured
  with `repeating-linear-gradient` — three flavors: vertical ticks
  (1px line / 10px gap), 45° diagonal hatch, 20px crossed grid. Texture
  lives only in these gutter strips and page margins, never behind
  content.
- All lines derive from one border token; horizontal rules are plain
  `border-t/b` on the same token. Body ground is a warm near-white
  (`oklch(0.982 0.001 106)`), one brand accent, no shadows doing
  structural work.

### Named principles

- **P1 — Structural grid.** The page grid is visible architecture:
  rails + rules + textured gutters carry the section cadence. This is
  the candidate *replacement* for the banned eyebrow/numbered-marker
  scaffold: structure by architecture, not by labels.
- **P2 — Texture in gutters only.** Ornament is confined to the
  non-content bands; content zones stay clean. (Harmonizes with our
  existing rule: accent rotation encodes structure, data surfaces stay
  clean. The current `.mw-grid` quant texture sits *behind* content —
  the Cartesia move is more disciplined.)
- **P3 — One-token line system.** Every rule, rail, and texture derives
  from a single border token, so the whole layer re-themes with the
  palette system for free.
- **P4 — Minimalism as density control.** Sparse sections, hairline
  separation, generous margins; color reserved for meaning.

Study question for loop 1: how the structural grid coexists with our
layered inset-panel model (§2.5) — rails + floating panels, or rails
replacing panels on marketing surfaces.

Corroboration (2026-08-06): Impeccable v4's detector flags our current
`.mw-grid` background (two-axis hairline gradient field behind content,
`globals.css:252`) as `codex-grid-background`, a newly saturated
generated-UI signature. The founder's instinct and the detector agree:
retire the decorative background grid, replace it with the structural
grid (P1/P2). One move fixes the last remaining detector finding and
implements the reference.

</details>

## R2 · base.org (2026-08-06) — ACTIVE

Founder's focus: "incredibly minimal and modern, but also uses a lot
of motion in interesting ways." Screenshot:
`references/base_home.jpg`. Decoded live:

- **Surface:** pure white, black ink, exactly one saturated accent
  (display-p3 pure blue). No tinted panels, no shadows; 1px hairline
  borders carry all structure. Flat modules, not layered depth.
- **Type:** one custom grotesk (baseSans) at every size; huge
  tight-leading headline; a matching mono (baseSansMono) for stat
  labels and captions. No serif anywhere, no tracked-uppercase
  eyebrows; sections open with the headline itself.
- **Motion (the interesting part):** NO animation library — no GSAP,
  no framer-motion, no Lottie, no WebGL. Three bespoke 2D-canvas
  scenes carry the identity (hero pixel-dissolve field, dot-matrix
  stats band, CTA pixel waveform), plus one 55s CSS logo marquee and
  150ms micro-transitions (color/transform) on interactive elements.
  Motion IS the brand texture (pixels = onchain data), not
  choreography; zero scroll-reveal sequencing.
- **One drench moment:** a single full-bleed pure-blue CTA band with
  a live canvas waveform; everything else stays white.

### Named principles

- **P5 — Radical reduction.** White ground, ink, one accent. Hairlines
  instead of shadows/washes for structure.
- **P6 — Type talks, labels are mono.** Sans display at scale opens
  sections directly; small mono for metadata/stat labels replaces the
  tracked-eyebrow scaffold.
- **P7 — Motion as identity texture.** A small number of bespoke
  canvas scenes drawn from what the brand IS (for Marketworks: live
  market data — flow fields, tick waves, price particles), plus 150ms
  micro-transitions. No reveal choreography, no motion library.
- **P8 — Flat bordered modules.** Cards: 1px border, white bg, no
  shadow, modest radius; diagrams/visuals live inside bordered frames.
- **P9 — One drench.** A single saturated full-bleed band per page
  (deliberate exception to §2.5's inset-only rule; the drench carries
  a canvas texture, not flat color).

Marketworks translation notes: our bespoke canvas already exists
(HeroFlow); the palette system supplies the one accent per palette;
P6 aligns with the founder's all-sans openness and kills the eyebrow
scaffold at the same time.

### Loop-1 feedback on Variant B (2026-08-06) — LANE CONFIRMED

Founder: full-bleed drench CTA is a keeper; total grid removal made
the page "very plain" — the grid should return *creatively in certain
fields/sections*, not as page wallpaper; try an almost-white ground
("brighter and sharper"); stay in this lane and refine.

Variant B2 applied: `.mw-bright` ground (98% white + 2% palette
primary, Midnight untouched); grid back in exactly two contained
zones — chart-paper under the hero flow line (a real measurement
surface) and a foreground-tinted grid field emerging from the right
of the drench band, masked away from the copy. New principle:

- **P10 — Grid as field, not wallpaper.** The quant grid appears only
  inside bounded zones where it reads as instrument/chart texture
  (hero canvas band, drench field, future chart frames), always masked
  or contained, never behind body copy.

### R2 addendum — Base typography census (2026-08-06, live DOM)

Base is a single-family SYSTEM, not a single font file: `baseSans`
(display + UI, 72px→14px), `baseSansText` (body-optimized cut),
`baseSansMono` (stat labels, Geist Mono fallback), plus `doto` — an
actual dot-matrix font — for the pixel wordmark brand moment only.
(googleSansFlex/CoinbaseSans hits are third-party chrome.) Lesson for
Marketworks: one sans family in functional cuts + a true mono for
numbers covers everything; a single decorative accent font is
permitted if it IS the brand gesture, not garnish.

## Horizon study palette (2026-08-06) — loop 2

Founder brief: more saturation and brightness; root it in Ocean but
polychrome, pulling the liked colors from the existing six palettes;
endgame is likely a plain light+dark pair replacing the palette picker.
Shipped as `html:not(.dark) .mw-horizon` (homepage-scoped study,
Midnight untouched), all bars WCAG-verified by script:

| Token | Value | Note |
|---|---|---|
| primary | `#0A5CFF` | 5.3:1 on white — vibrance band |
| display-accent | `#E0604D` coral | large type only (3.5:1) |
| secondary | `#E8A33D` sun | warms the hero canvas; keyline only |
| acc rotation | blue/sun/green/coral/purple/teal | fg ≥4.5 on wash AND white |
| chart series | `#0A5CFF` / `#C77E14` / `#64748B` | marks ≥3; sun too light for marks |
| deep panel | `#0A2C66` ink-navy | footer coheres with the drench |

## Typography (2026-08-06, in chat)

- **Keep Outfit.** Non-negotiable baseline.
- **Fraunces is replaceable.** It's on Impeccable v4's reflex-reject
  list; founder is open to swapping the display face.
- **All-sans is on the table** — Outfit + a distinctive display sans,
  plus a mono for numbers/tickers (tabular figures mandatory).
- **Direction: "more modern" is acceptable if it's better**, i.e. the
  editorial register can shift toward a cleaner instrument-like look;
  decide via rendered comparisons, not in the abstract.

### Shortlist for study loop 1 (all clear of Impeccable v4's
### saturated-font list; all Google Fonts / next-font compatible)

Voice words: calm, sharp, editorial. Physical object: a well-set
research note / broadsheet data page, not a startup deck.

**Direction A — modern editorial serif display (evolution):**
- *Source Serif 4* — contemporary editorial workhorse, optical sizing,
  quiet authority. Safest modernization.
- *Besley* — Clarendon-blood British newsroom sharpness; more voice,
  still sober.
- *Spectral* — screen-first editorial serif, cool and precise.

**Direction B — all-sans modern (the "instrument" look):**
- *Schibsted Grotesk* — commissioned for a news group; sharp, modern,
  editorial-native sans. Strongest candidate for "modern but still a
  research house."
- *Hanken Grotesk* — calmer, rounder grotesk; low risk.
- *Bricolage Grotesque* — most character (display cuts get loud);
  bolder-brand option.
- Numbers mono (tickers, tables): *Spline Sans Mono* (quiet, pairs
  with grotesks) or *Martian Mono* (wide, instrument-panel voice).
  Avoid IBM Plex Mono / Space Mono (saturated list).

**Held for later (licensed, non-Google):** Tiempos Headline, Publico —
true FT-register faces if we outgrow Google Fonts.

Outfit stays as body/UI in both directions (identity-preservation; it
is on the saturated list, but it's the shipped brand and the display
face is where distinctiveness is won). Loop-1 study renders each
candidate on: homepage hero, a /library article page, and a dashboard
data table with tabular figures.

## Critique loop 1 outcomes (2026-08-06)

Dual-agent Impeccable critique: 24/32 (Good). Snapshot at
`.impeccable/critique/2026-08-06T09-51-33Z__kite-dashboard-src-app-page-tsx.md`.
Found + fixed same session: the mist-ground bug (unlayered .mw-brand
background beat the utility layer — the layered near-white base had
never actually rendered; also cleared 7 contrast near-misses).

Founder decisions on the critique's questions:
- **Frame:** keep the pill nav (distinctive), flatten the footer —
  done (`FooterPanel flat`, full-bleed ink-navy).
- **Polychrome:** semantic mapping, not sibling order — defensive
  wears teal, growth sun, quality blue (`riskAccent()`); step numbers
  went single-color primary. Defensive never wears the loss color.
- **P11 — Hero motion v2 brief (IMPORTANT, next build):** founder
  wants the flow-field replaced with a Base-adjacent quant texture:
  dither / data-point fields, breathing candlesticks or charts that
  come and go — something abstractly representing data and
  quantitative analysis. Simpler variant must run on mobile (mobile
  currently gets no identity element at all).

Open from critique, not yet done: evidence artifact in "Process over
prediction" (founder to pick the artifact); allowlist expectation-
setting near the CTA; mid-page mobile CTA (folds into hero-motion-v2
round); PalettePicker on public nav (endgame is light/dark anyway);
transform-based nav transitions; "Three ways" hardcoded numeral.

## Loop 3 shipped (2026-08-06)

- **P11 hero motion v2 LIVE** (`hero-quant.tsx`): dither field (value
  noise, breathing alpha, sun sparks) + candlestick clusters that fade
  in / breathe / dissolve. Up = filled primary, down = outlined — no
  red/green on marketing (identity vs meaning). Runtime token
  resolution + MutationObserver re-theme; reduced-motion static frame;
  mobile renders a 200px light-density band (identity element finally
  on mobile). HeroFlow retired from the homepage only.
- **Horizon Dark**: navy-black #0B1120 ground, luminous #4D8DFF primary
  with INK button text (white fails the bar on bright primary), coral
  #F27E6C display, solid dark washes; 27 bars script-verified.
- **ThemeToggle** (sun/moon) replaces PalettePicker on marketing nav;
  light=mint / dark=midnight so Clerk roaming + PaletteSync unchanged.
  Dashboard navbar still carries the picker until formal retirement.
- **Middle-section lift**: welcome = rank-strip frame on chart paper
  (true claims only in captions); research = abstract validation curve
  with shaded unseen-period region (no fabricated numbers); step cards
  = stroked icon tiles + mono numbers; portfolio cards = semantic
  icons (sparkles/trend/shield) in mapped accents.

Open: evidence artifact (founder to choose), allowlist copy near CTA,
mid-page mobile CTA, transform-based nav transitions, "Three ways"
numeral, dashboard picker retirement + palette-system teardown once
the two-theme direction is confirmed on real devices.

## Loop 4 pivot (2026-08-06) — B5 rejected, fresh composition

Founder verdict on the B-series result: wrong direction overall; keep
architectural plans, restart the design. Explicit keeps and rejects:

- KEEP: full-bleed **banded sections** (the drench CTA "looks
  fantastic" and is the model); the **grid texture** (serious,
  editorial) returns at section scale; the **dot pattern** from the
  prod footer panel; the **Horizon palette** (light); textures in play.
- REJECT: carded overlays as section grammar; the light/dark two-theme
  exploration (ThemeToggle removed from nav; Horizon Dark parked in
  CSS); B5's overall look.
- NEW: **white ground** experiment (founder explicitly ready to try
  pure white — recorded exception to the DESIGN.md near-white rule for
  this study); experiment-first mode, no commitment yet.

## R3 · phantom.com (2026-08-06)

Focus: how it scrolls section-to-section ("rational flow"). Decoded
live: NO animation library, no scroll-snap — tall (~1670px) sections
with inner content pinned via position: sticky (top ~450px), so each
band holds while the next slides over it: the sticky-stacking pattern.
- **P12 — Banded takeover scroll.** Full-bleed bands, each sticky at
  top on desktop, later bands slide over held earlier ones. CSS-only;
  mobile keeps normal flow (content must fit a viewport per band on
  desktop).

## R4 · sui.io (2026-08-06)

Focus: dramatic hero — "the text and the gradient, artistic not
sloppy"; blur explicitly NOT wanted. Decoded live:
- Typeface: **TWK Everett** + TWK Everett Mono (Weltkern, licensed).
  H1 at 176px weight 400, tracking -0.033em, white on gradient. The
  techy look = modest weight at huge size, tight tracking, mono
  companions. Free near-matches: General Sans / Cabinet Grotesk
  (Fontshare), Schibsted Grotesk (Google).
- Hero: atmospheric vertical gradient (near-black navy top → vivid
  blue → pale bottom), giant white text, white CTA pair. Flanking-word
  blur/glow = rejected part.
- **P13 — Atmospheric gradient hero.** One vertical multi-stop
  gradient from the palette's own family as the hero sky; giant
  tight-tracked sans in white; no gradient text, no blur.
