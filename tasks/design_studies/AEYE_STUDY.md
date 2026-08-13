# aeye-saas.webflow.io decoded — layout, sections, motion (2026-08-13)

Live exploration (Playwright, 1440px): homepage full-scroll + about,
pricing, docs, changelog. Founder brief: mine LAYOUT / SECTIONS /
CARDS / ANIMATIONS only — colour and type are set (loop 23/25) and
none of this study touches them. Screenshots in the session scratch;
mechanics verified in the DOM.

## 1. How the site works (mechanics)

- **GSAP + ScrollTrigger + ScrambleTextPlugin.** Every section
  headline carries a scramble-decode moment (mid-scramble frames
  read "workfl}—", "produ+&", "the]_"); the hero keyword
  "[ AI Product█ ]" types in a pixel face with a block cursor.
- **Sticky sheets.** Three sticky layouts: `hero-header` (a dark
  grid plate stays fixed while the white page slides up OVER it),
  `hiw-layout` (sticky numbered list + diagram), `install-layout`
  (sticky terminal panel + scrolling keyline list).
- **A pixel display font (Geist Pixel Square) for decoration only**
  — slashes flanking headlines, block cursors, tiny icons. 40
  elements. Their "data-as-pixels" note, same family as our dither.
- **Marquees** for logo chips and a with/without bar-chart strip.
- Everything else is hairline tables and borders — almost no radius,
  no shadows, table-as-layout.

## 2. The device catalogue

| # | Device | What it is |
|---|---|---|
| D1 | Tab-strip nav | Boxy terminal tabs; active tab accent-filled with `<ANGLE>` brackets; count badge on one tab; CTA boxed separately |
| D2 | Sticky plate opening | Dark grid-plate header (wordmark, version chip, scroll cue) fixed; the white content sheet scrolls over it |
| D3 | Scramble headlines | GSAP ScrambleText on section H2s; decode-in on scroll |
| D4 | Section meter | `[N.02/11] > PERFORMANCE` mono meta + full-width hairline; numbered like an instrument readout |
| D5 | Hairline-table stat block | 2×2 stats in bordered cells (`< 1.8s / Generated Time`), no cards, just rules |
| D6 | Bordered-cell logo wall | Logos in table cells with hairlines, not floating rows |
| D7 | Index-card grid | Cards in a hairline table: `// 001` header row, content, `↗ VIEW` footer row |
| D8 | Corner tick marks | Four small corner brackets (camera focus marks) framing media panels |
| D9 | Sticky scrub list | Sticky panel one side; other side scrolls a numbered list with a progress keyline; active row dark, inactive grey |
| D10 | Node-diagram panel | Workflow nodes + connecting lines on a dotted canvas; labelled boxes ("SIGNALS") |
| D11 | Selection-highlight labels | Mono uppercase captions with a text-selection-style background highlight |
| D12 | Numbered accordion | `//001 ···· question ···· [+]` FAQ rows, dotted leaders, square plus |
| D13 | With/without bar marquee | Comparison strip: filled bars vs empty bars scrolling |
| D14 | Handle-tag photos | B/W photos with `@HANDLE` mono tag overlaid; dark testimonial band |
| D15 | Selection-handle featured card | Pricing "Pro" card: accent border with tiny corner squares like a design-tool selection |
| D16 | Segmented toggle + save chip | Monthly/Annually boxed toggle, `SAVE 20%` highlight chip |
| D17 | Pixel slash flourishes | `/` glyphs in the pixel face flanking every display headline |

## 3. What to TAKE (mapped to Marketworks)

Ordered by fit with Finance × Technology × Editorial Research and
with what the branch already has:

1. **D4 section meter → upgrade our indexed sections.** The homepage
   already runs mono captions (`01 · the idea`) as a chosen brand
   system. Evolve them to the metered form: `[02/05] > HOW IT WORKS`
   + full-width hairline. Reads as instrument telemetry — the
   Technology corner. (Tension noted: the design-taste skill bans
   section-number eyebrows as decoration; ours pre-date this study
   as a founder-chosen system, and the meter makes them functional
   wayfinding. Founder's call stands.)
2. **D5 hairline stat tables → the portfolio figures.** Our real
   CAGR/Sharpe/MaxDD belong in bordered cells, not floating stat
   chips. Also echoes the ledger/contract-note heritage from the
   design_reset detour. Direct FactTile/SelectorPanel upgrade.
3. **D10 node diagram → the daily pipeline, drawn.** We own a real
   pipeline (16:30 IST: fetch → adjust → score → rank → publish).
   Drawing it as labelled nodes on a dotted canvas is product truth
   as image — the strongest single section idea in the template.
4. **D9 sticky scrub list → "the weekly ritual" section.** Sticky
   rebalance-note/product panel on one side; the subscriber's weekly
   steps scroll past with a green progress keyline. Also a natural
   /docs pattern later.
5. **D8 corner ticks → exhibit framing.** Four corner marks around
   chart panels ("Exhibit A" framing without the full certificate
   frame). Cheap, distinctive, pairs with annotated-exhibit work.
6. **D3 scramble, RATIONED → one authored decode.** One ScrambleText
   moment (hero keyword or the drench headline), scroll-triggered
   once, reduced-motion static. Not on every H2 — that is the
   template's tell. Emil gate: marketing/explanatory tier, fine.
7. **D2 sticky plate opening → hero-gradient replacement CANDIDATE.**
   A green-deep plate (wordmark + real tape line) that the white
   sheet slides over would retire the dated gradient entirely.
   Belongs to the founder's hero exploration — flagged, not built.
8. **D15 selection handles → SelectorPanel active state.** The tiny
   corner squares on the active portfolio pill/card — a design-tool
   "selected" metaphor for a selector that literally selects.
9. **D12 numbered accordion + dotted leaders** — future FAQ + any
   holdings/spec list; the dotted-leader row is a good table device.
10. **D11 selection-highlight labels** — as an occasional emphasis
    treatment on our existing mono captions.
11. **D17 pixel flourishes, sparingly** — block-cursor / slash
    accents join the dither family (data-as-pixels). Decorative
    budget: one or two per page, not seventeen.

## 4. What to SKIP (and why)

- **D1 tab-strip nav** — charming but it rebrands the global nav
  around a terminal metaphor; our audience includes non-devs and the
  FloatingNav identity is settled. Revisit only if the founder wants
  a nav round.
- **D3 scramble-everywhere** — on every headline it becomes the
  site's personality; ours is calm. One moment only.
- **D13 bar marquee** — marquee budget (max one/page per the taste
  skill) is better spent elsewhere; a with/without comparison for us
  is better served by the real chart.
- **D14 handle-tag testimonials** — no testimonials exist
  (no-fabrication rule); shelve until real ones do.
- **D16 save-chip toggle** — pricing surface doesn't exist yet.
- The template's overall **grey-on-grey chill** — our white ground +
  green warmth stays; we take structure, not temperature.

## 5. Proposed build shortlist (next loop)

Four primitives/sections onto /primitives, all on the set system:

- B1 `SectionMeter` — the metered index header (evolves the existing
  mono captions in place on the homepage).
- B2 `StatTable` — hairline-cell figures block wired to real
  portfolio data (upgrades FactTile).
- B3 `PipelineDiagram` — the daily pipeline as nodes on a dotted
  canvas, one slow light tracing the path (CSS, reduced-motion
  static).
- B4 `ExhibitFrame` — corner-tick media/chart frame (+ optional
  scrub-keyline list variant later).
Plus one motion spike: a single ScrambleText-style decode (no GSAP
dependency — small hand-rolled, ~30 lines, transform/opacity-free
text swap, reduced-motion instant) on the drench headline.

Founder picks from here; nothing built without his read.
