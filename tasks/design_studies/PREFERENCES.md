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
