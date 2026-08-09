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

## Loop 6 (2026-08-06) — iterative mode; hybrid composition

Founder reset of process AND structure: snap scrolling removed
(disliked); iterate in small scoped steps from here, no sweeping
rewrites. KEEP: gradient hero, drench CTA band, flat navy footer.
Middle sections RETURN to the production design system (SectionPanel
mist/deep, illustrated FeatureCards, MarketingCards with accent chips,
Reveal) — the founder finds the card system's hierarchy stronger than
the flat banded middle. Note: the production components bring the
Fraunces serif headings back to the middle sections; surfaced to the
founder rather than silently changed. Horizon palette carried the
page; mist/tint panel surfaces re-derived toward the Horizon hue so
the panels cohere (was green mist). Palette question (blue Horizon vs
re-vibranced brand Mint) put to the founder explicitly.

## Loop 7 (2026-08-06) — Mint v2 + two-sans typography

Founder picks: the page runs on re-vibranced brand GREENS (Mint v2),
not Horizon blue; headings go sans everywhere, with TWO sans faces —
Outfit for content plus a slightly stylized heading face.

Applied: `.mw-mint2` (primary #00875F — purer emerald at 4.53:1 with
WHITE foreground; the old lichen was already at the top of the WCAG
vibrance band, so chroma push is modest and brightness comes from the
green hero sky, #FAFDFB ground, white cards); `.mw-hero-sky-mint`
(deep forest -> emerald -> pale mint -> white); heading layer
`.mw-sans-headings` flips all h1-h4 (including inside shared
components) to Schibsted Grotesk (--font-schibsted via next/font) —
swap the face in layout.tsx to trial Cabinet Grotesk / General Sans
later. Fraunces is now fully off the homepage. Horizon light/dark
blocks remain in CSS as parked references.

## Loop 8 (2026-08-06) — Stack Sans Notch + grain hero

Founder supplied both: Stack Sans Notch (spotted on Google Fonts) as
the stylized heading sans, and the Google Fonts Noto banner as the
hero reference (grain + soft pastel gradient, dark text).

Applied: Stack Sans Notch heads the heading stack (too new for this
Next version's next/font data — loads via the Google Fonts stylesheet,
which our CSP already allows; self-host after the next Next upgrade;
Schibsted Grotesk remains the loaded fallback). Hero swapped to
`.mw-hero-grain`: layered pastel radials (brand mint + one cool-blue
corner echoing the reference) over near-white, with an SVG
fractal-noise grain overlay (data URI, soft-light blend — no image
assets, CSP-clean). Ink headline on light ground, primary back on the
word "calm", emerald CTA pill. The dark mint sky (.mw-hero-sky-mint)
and Horizon skies stay in CSS for instant revert.

Note for next loops: Stack Sans Notch is strongly characterful
(notched cuts) — currently headings-only, which is the right dosage;
resist letting it leak into body/UI sizes.

## Loop 9 (2026-08-06) — grain up, Stack Sans Text, palettes cycling

Founder: grain too subtle (0.16 -> 0.34); Stack Sans NOTCH too
characterful — swapped to its simpler cousin STACK SANS TEXT (verified
on Google Fonts, weights 500-700); and the palette SYSTEM is back —
picker restored to the marketing nav, and the new design re-themes:
the grain hero's blobs/base now derive from var(--primary)/
var(--secondary) via color-mix (each palette gets its own field; a
dark composition handles Midnight), and the Mint v2 vibrance override
is scoped to the mint palette only so Ocean/Amber/Coral/Charcoal/
Midnight render their own token sheets. Verified live: Mint (emerald
field), Ocean (blue field + sun blob), Midnight (dark field, signal
blue). Secondary hero pill made theme-aware (bg-background/60).

## Loop 10 (2026-08-06) — stronger grain; Horizon rides Ocean

Grain fixed for real: the problem was the blend mode, not opacity —
soft-light nearly vanishes on near-white grounds. Now normal blend at
0.18 (mid-grey speckle, visible on light AND dark fields). The
sui-vibrant Horizon system (#0A5CFF + sun + coral, incl. panel
surfaces and washes) now rides the OCEAN palette slot via
html[data-palette=ocean] .mw-brand — picking Ocean in the picker
shows the whole marketing surface in the vivid system. Verified:
hero field renders blue+sun-gold, cards wash blue/sun/coral, research
panel ink-navy. Pending founder verdict before extending the vibrance
treatment to the remaining palettes.

## Loop 11 (2026-08-06) — dramatic dark hero (Sui anatomy)

Light pastel hero judged too light; founder wants dark and dramatic
per sui.io. New `.mw-hero-drama`: token-derived vertical sky —
near-black-mixed primary at the crown, luminous primary mid, pale
exit into the ground — so Ocean(Horizon) reproduces the actual Sui
navy->vivid-blue->pale gradient and every palette gets its own dark
drama (Mint = deep forest). White headline/sub/CTAs return; grain
overlay rides the dark field (shared ::after). The light grain-pastel
hero (.mw-hero-grain) stays in CSS as the alternate.

## Loop 12 (2026-08-06) — stylistic riso grain (Noto reference, take 2)

The Noto card's grain is coarse and clumpy (riso/print), not uniform
film noise. Rebuilt: turbulence frequency 0.82 -> 0.34 with 3 octaves
and a steep contrast table (chunky speckle), blended OVERLAY at 0.5 so
grains dye in the field's own color — blue grain in blue zones like
the reference — plus a faint fine pass underneath for micro-texture.
Verified on the Ocean drama sky at device scale: clearly stylistic.
Knobs: coarseness = baseFrequency, punch = opacity/table.

## Loop 14 (2026-08-06) — grain settled (founder-tuned) + background-only

Founder tuned via the panel and locked: baseFrequency 0.80, contrast
table [0 0.45 0.55 1], opacity 0.45, blend soft-light, fine layer
0.10 — i.e. fine film grain at moderate strength, not the chunky riso.
Baked as the CSS defaults. Grain now paints on the BACKGROUND only:
hero sections isolate their stacking context and both grain
pseudo-layers sit at z-index -1, so text/buttons above are ungrained
(founder request). GrainTuner unmounted from the page; the component
stays in the repo for future texture-tuning sessions.

## Loop 15 (2026-08-06) — card primitives (side exercise)

References: Google Fonts Knowledge banner (grain + abstract glyph +
guide lines), clay.com (pastel stack cards; UI-collage media fields),
teak.io (grid background fading in/out with scroll — decoded as an
SVG pattern layer; reimplemented with CSS mask + scroll-driven
animation where supported).

Built in `components/marketing/study-cards.tsx`, showcased at
`/primitives` (public + noindex ON THIS BRANCH ONLY via a marked
middleware entry — REMOVE before any merge):
- **GrainCard** — corner wash (token-derived), the tuned grain via the
  generalized `.mw-grainy` class, oversized cropped glyph, dashed/solid
  typographic guide lines.
- **StackCard** — clay pastel stack: wash layers peeking behind, pill
  label, two-tone heading slot, actions, optional media panel.
- **CollageCard + FloatPanel + GhostRows** — blob field with
  overlapping floating panels; slots intended for REAL product UI
  screenshots later, placeholder rows are deliberately data-free.
- **GridFadeSection pattern** (`.mw-grid-fade`) — teak-style grid that
  breathes in/out with scroll (`animation-timeline: view()` +
  static mask fade fallback; disabled under reduced-motion).

All token-derived — the palette picker re-themes the whole gallery.

## Loop 16 (2026-08-06) — the gallery IS the direction; library batch 2

Founder on the /primitives page itself: "looks beautiful... the right
balance of everything... engaging" — and wants the HOMEPAGE after the
hero to feel like it: centered content in dynamic sections, different
card layouts, primitives chosen per the content's needs. That page's
recipe, named for reuse: one centered column, mono index captions,
varied card families in sequence, generous vertical air, everything
token-derived.

Batch 2 primitives (clay.com references):
- **SectionHeader** — centered heading/sub + one dark pill CTA.
- **FeatureTile** — soft neutral tile: icon, air, heading, body.
- **FrameCard / GuideCard** — colored frame wrapping cropped media +
  tag pill + title + footer meta; frames rotate accent colors. Media
  slots await REAL product screenshots; ghost rows until then.
- **SelectorPanel / FactTile** (client) — clay signal-picker: pill
  list left, detail surface right, footnote; gallery demo runs on real
  UNIVERSES data (no invented figures).

Next natural step (not yet done): compose the homepage mid-page from
these primitives, section by section, per the founder's direction.

## Loop 17 (2026-08-06) — homepage full pass from the primitive library

Founder go-ahead: compose the homepage with the primitives; OCEAN is
the study's base palette (providers defaultTheme "system" -> "ocean";
marked revisit-before-merge). Mid-page now follows the gallery recipe
verbatim — centered 1140px column, mono index captions (01-05, a
deliberate named system), one primitive family per section:

01 the idea = StackCard + HeroFlow media on grid-fade ·
02 how it works = SectionHeader + FeatureTile x3 ·
03 the research = GrainCard ("m" glyph) ·
04 the portfolios = SectionHeader + SelectorPanel on real UNIVERSES
data with View-portfolio links ·
05 from the library = GuideCard x2 (accent frames).

Hero (drama sky + tuned grain), drench CTA, and flat footer unchanged.
Verified desktop full-page and mobile (no horizontal overflow; panels
stack). Open: GuideCard/StackCard media slots await real product
screenshots; palette endgame + light/dark question still parked.

## Loop 19 (2026-08-06) — clay.com decoded; the two-theme system (branch design_studies_clay)

Founder direction: study clay.com's TYPOGRAPHY and build a COLOR
PALETTE from it for our site; collapse the six-palette picker to just
light + dark; Ocean stays the base; below the hero the ground goes
almost white with the color carried by elements on top.

Study ran on the live site (Playwright) — full findings in
CLAY_STUDY.md; references saved (clay_home_hero / _yellow_card /
_stacked_cards.jpg). Headlines: ONE variable sans (Roobert VF) does
everything — hierarchy is size/weight/tracking, lh 1.0 + tracking to
-4% at display sizes, eyebrows the inverse (12px semibold uppercase
+9%); warm-paper near-whites (their "oat" ramp) make the cool vivids
pop; and the signature per-section monochrome TRIAD — pastel surface ·
vivid pill/action · deep same-hue text — which maps 1:1 onto our
accN-bg/-line/-fg sockets.

Built: Ocean slot rewritten as the Clay-formula LIGHT theme (warm
paper ground #FBFAF7, ink #1B1A17, primary #0A5CFF, six vivid triads —
blue/sun/matcha/coral/ube/magenta, washes now true pastels) and a new
`.dark .mw-brand` DARK companion (ink-navy #0A111F ground, primary
#4D8DFF, triads inverted deep-wash/bright-line/pale-fg, hero sky
variant exiting into the dark ground). Marketing nav: PalettePicker →
sun/moon ThemeToggle (light = ocean slot, dark = .dark; device-local,
no Clerk roam). Homepage: hero type tightened per the study
(lh 1.0, tracking -0.035em), section eyebrows now Clay-style colored
uppercase, the 02 feature tiles take one triad hue each
(blue/sun/matcha tints + vivid icons). GrainCard/CollageCard
hardcoded whites replaced with var(--card) so they survive dark.

Verified both themes desktop full-page (evidence/loop19_*). tsc
clean. Open: dashboard picker still six-swatch (merge-checklist);
remaining palettes (mint2 etc.) untouched pending founder verdict on
this pair.

## Loop 20 (2026-08-06) — founder critique round 1 on the two-theme build

Five founder calls, all applied for the next critique pass:
1. Hero fades seamlessly into the page ground — longer exit ramp in
   both hero-sky gradients (ground reached before the section edge and
   held) + the grain now dissolves via mask before the boundary.
2. `.mw-dots-edge`: faint dot field over the whole mid-page, visible
   at the left/right page edges, masked away across the center where
   the content column sits (successor to the grid lines).
3. Fraunces + Outfit back for another look: `.mw-serif-headings`
   replaces `.mw-sans-headings` on the homepage (Stack Sans class kept
   in CSS); serif-friendly tracking -0.012em, hero leading 1.04.
4. Section 02 re-follows the primitives-gallery 04 recipe verbatim:
   soft card container, centered opener WITH the dark pill CTA,
   NEUTRAL tiles — the loop-19 triad tiles are out.
5. Ground is pure white (#FFFFFF, was warm paper #FBFAF7) — founder
   expects white to make the colors pop hardest.

Verified both themes (evidence/loop20_*). tsc clean. Phased format
agreed: founder critiques each round, then we move ahead.

## Loop 21 (2026-08-06) — founder round 2: later fade + the research lens

Two founder calls on the loop-20 build:
1. Hero CTAs were sitting on the pale zone. Chose "fade later" over
   smaller text: the luminous crest now holds through ~75% of the
   section (crest stop 62% -> 72%, ground ramp compressed into the
   last quarter; grain mask follows, 68% -> 78%). Both CTA pills sit
   on saturated blue; the exit into white stays seamless.
2. Section 03 gets a motion graphic: `ResearchLens`
   (components/marketing/research-lens.tsx) replaces the "m" glyph in
   the GrainCard right zone (new `visual` prop; glyph+guides remain
   the default). A magnifying glass drifts (lissajous) over a
   Bayer-dithered field of small cubes; inside the glass the field is
   magnified 1.75x and grid cells light up as data points (primary
   blue / sun gold, ease in-hold-out) — research as looking closely.
   HeroFlow idiom: token-exact colors re-resolved on theme change,
   DPR-aware, static frame under reduced-motion, pauses on hidden tab.

Verified both themes (evidence/loop21_*). tsc clean.

## Loop 22 (2026-08-09) — font trial rejected; Lenis scroll kept

1. Instrument Serif + Inter trial — REJECTED on sight ("this isn't
   looking good"). Wired via a `.mw-instrument` layer (Inter body,
   Instrument Serif 400-pinned headings — the face ships no bolder
   weight, so smaller headings read light and unstructured); founder
   reverted same session. Fraunces + Outfit stays. Code removed.
2. Lenis smooth scroll (lenis.dev, v1.3.26) — KEPT ("I like the
   smoothness"). `SmoothScroll` client component
   (components/marketing/smooth-scroll.tsx), homepage mount only,
   default settings (lerp 0.1, autoRaf). Skips init under
   prefers-reduced-motion; touch stays native (Lenis default). Drives
   the real scroll position, so grid fade / ResearchLens / FloatingNav
   needed no changes. Distinct from the rejected snap/takeover
   patterns: inertia easing only, user keeps control.

Toolchain note: Turbopack's persistent cache served stale compiled
globals.css across a dev-server restart — `rm -rf .next` is the fix
when style edits refuse to land.
