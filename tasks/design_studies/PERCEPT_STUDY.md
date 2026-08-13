# demo.7iquid.com/percept decoded — bands, cards, textures (2026-08-13)

Live exploration (Playwright, 1440px): homepage full-scroll + link
map; DOM dig for implementation. Founder brief: banded sections,
multi-card layouts, card backgrounds, hero and footer. Colour and
type stay locked; Percept's serif-editorial register incidentally
validates our LB direction.

## 1. How it works (mechanics)

WordPress + Swiper + Waypoints — no motion engine. The entire
richness is **authored raster textures** (painterly brushed/woven
JPGs: `feature-item-bg-1..3.jpg`, `home-1-bg-*.jpg`,
`footer-bgr.png`) sitting under floating product-UI screenshots and
white serif type. Structure is a disciplined SaaS skeleton; the
paintings carry the premium feel.

## 2. Device catalogue

| # | Device | What it is |
|---|---|---|
| P1 | Dotted-paper hero band | Subtle dot-grid ground behind the whole hero region; split header (serif headline left, lede + CTA pair right); below, an asymmetric media collage row: B/W portrait card + product UI floating on a rich texture (≈40/60) |
| P2 | Texture-backed product cards | UI screenshots floating on painterly texture panels; each feature row gets its OWN texture family (brushed blue, woven teal, golden botanical) |
| P3 | The long ink band | A multi-screen dark movement mid-page ("why us"): chip marquee + white serif display + three dark hairline cards. Sustained, not a thin drench |
| P4 | Activity-chip rows | Pill chips with status dots drifting in faded rows; one chip highlighted white with an avatar — live product events as ambient texture |
| P5 | Accordion-synced feature rows | Text side is an accordion (one item open, +/− toggles); the visual panel swaps per open item |
| P6 | Case-study band cards | Full-width dark card with a solid accent top-strip, texture+logo panel left, before/after stat headline, person photo right |
| P7 | Full-bleed texture quote band | Giant painterly surface, white serif quote, attribution, prev/next |
| P8 | The textured mega-footer | CTA headline + hairline + 5-column sitemap + HUGE wordmark + newsletter + back-to-top, all on ONE continuous textured dark ground |
| P9 | Square-bullet chip eyebrows | Small pill eyebrows with a square bullet (their kicker device) |

## 3. What to TAKE (mapped)

1. **P2 card textures → the media-slot upgrade, our way.** This is
   where the parked asset-study work finds its real use: our
   generative fields (dither, drift lines, contour, chalk
   turbulence) were rejected as HERO backgrounds but are exactly
   right as CARD backdrops under floating product UI. Green-family
   texture panels behind FloatPanels upgrades StackCard/CollageCard
   media slots immediately — procedural SVG (token-derived) now,
   art-directed renders later if wanted.
2. **P8 the textured mega-footer → merge our CTA drench + footer.**
   One continuous green-deep textured surface: CTA headline, rule,
   sitemap columns, the giant lowercase wordmark, back-to-top.
   Their footer ground is practically our green-black already.
   Strongest single section take.
3. **P3 the long ink band → a sustained dark movement.** Our drench
   is a thin moment; Percept shows a multi-screen dark band carrying
   a whole argument ("what makes us different") with hairline cards.
   Gives the homepage a second act. Theme-lock note: one deliberate
   dark movement per page, entered and exited cleanly.
4. **P4 activity chips → the real signal feed.** Their fake events
   become our REAL ones: "HFCL entered Core Momentum · rank 1",
   "Weekly rebalance published · 16:30 IST", "OM25 regime: bull".
   Drifting chip rows (or static faded rows — marquee budget) with
   one highlighted chip. Product truth as ambient texture.
5. **P5 accordion-synced rows → "how it works", interactive.** Text
   accordion left, product visual swaps right. A natural upgrade for
   section 02 and later /docs.
6. **P6 case-band cards → portfolio story cards.** Accent top-strip
   + texture panel + a real stat headline per portfolio ("OOS
   2017–26 · 44.78% CAGR, drawdowns included"). Real figures only.
7. **P1 hero collage row** — the below-headline asymmetric media row
   (product UI on texture + one human/context card) is a hero-media
   pattern that needs no gradient sky at all. Feeds the founder's
   hero rethink.

## 4. What to SKIP

- **P7 quote band** — no real testimonials (no-fabrication rule);
  the device could carry a principle line instead, but that flirts
  with performative-poster territory; park.
- **P9 square-bullet eyebrows** — eyebrow budget stays spent; our
  SectionMeter already owns the kicker slot.
- **Their raster-painting sourcing** — we generate in the green
  family instead (or art-direct our own renders later); random
  stock paintings would break token-derivation and brand.
- Swiper carousels — nothing here needs a carousel yet.

## 5. Build shortlist (pending founder read; third reference site
still to come — builds can batch after it)

- C1 `TexturePanel` — generative green-family texture backdrops
  (dither / drift / turbulence variants) sized for card media slots;
  StackCard/CollageCard accept it today.
- C2 `TexturedFooter` — the merged CTA + footer mega-section on
  green-deep with the giant lowercase wordmark.
- C3 `InkBand` — the sustained dark movement wrapper (enter/exit
  rules + dark-card row).
- C4 `SignalChips` — real-event chip rows with one highlighted chip.
- C5 `AccordionShowcase` — synced accordion + visual swap.
