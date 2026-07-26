# REFERENCES — spade / corgi / acctual teardowns, tokenized for Marketworks

Distilled from three verified teardowns (values read from the sites' shipped CSS,
not inferred unless noted). Everything below is already translated into our tokens
and is CSP-safe (CSS / static SVG / self-hosted). Source galleries: none of the
three had Awwwards/Godly/Land-book writeups except Spade; facts are from shipped code.

---

## 1. Section layering — the flat-page fix (from Corgi + Acctual)

**Corrected direction (founder note, 2026-07-19):** the near-white base runs
**continuously** down the whole page; colored sections are **inset, rounded,
centered panels floating on the white** (like Acctual's dark panels) — **NOT**
full-bleed edge-to-edge bands (Corgi's model). Edge-to-edge color interrupts the
"flow"; inset panels let the white flow around the color. This is a hard rule,
encoded in a `SectionPanel` primitive.

Surface roles:

| Surface | Fill | Role |
|---|---|---|
| White base (continuous canvas) | `#FAFCFB` (near-white, faint lichen tint — **not** pure white) | the page; flows behind/around everything |
| Mist panel | `#ECF3EF` (mist) | quiet inset panel + card tint |
| Pale-lichen panel | `#F3F8F5` | soft inset "rest-stop" panel behind cards |
| Lichen panel | `#14715F` (lichen), text in mist `#ECF3EF` | the CTA / emphasis inset panel |
| Deep panel | `#1A1A1A` or deep lichen `#0E3B32`, faint lichen/signal glow | footer + maybe one feature, inset |

Panel construction: `max-width` container with side margins (never touching the
viewport edge), `border-radius: 24–32px`, the card shadow (§2) so it reads as a
floating slab, generous internal padding. Rhythm down the page:
`white → [mist panel] → white → [pale-tint panel w/ cards] → [LICHEN panel] →
white → [DEEP panel]`. Depth is born where **shadowed white cards float inside a
mist/tint panel** (panel-on-canvas + card-on-panel = three layers). Discipline: a
loud (lichen/deep) panel every 3–4 sections; Fraunces + whitespace carry the rest.

## 2. Card depth — the single highest-leverage steal (from Corgi)

Not a hard drop-shadow: a large soft **ink-tinted** ambient shadow with negative
spread. Layer 1 constant (the soft body), layer 2 grows with elevation.

```css
:root{
  --mw-shadow-sm: 0px 6px 24px -3px rgba(26,26,26,.07);
  --mw-shadow:    0px 6px 24px -3px rgba(26,26,26,.13), 0px 1px 2px -4px rgba(26,26,26,.13);
  --mw-shadow-lg: 0px 6px 24px -3px rgba(26,26,26,.13), 0px 4px 6px -4px rgba(26,26,26,.13);
}
.mw-card{
  background:#fff;                 /* or a pale mist tint for "colored" cards */
  border-radius:24px;             /* 32px for hero cards; controls stay 8–12px */
  box-shadow:var(--mw-shadow);
  transition:box-shadow .2s cubic-bezier(.2,.8,.2,1);
}
.mw-card:hover{ box-shadow:var(--mw-shadow-lg); }
/* premium/most-elevated variant: hairline ring + big lift, ring tinted lichen */
.mw-card--float{ box-shadow:0 0 0 1px rgba(20,113,95,.12), 0 12px 40px rgba(26,26,26,.14); }
```

Shadow color is **ink `#1A1A1A`, never black** — that is what keeps it warm/soft.
Interior pattern: graphic on a *tinted inner panel* (two layers) → Outfit
uppercase/tracked eyebrow (our mono-label substitute) → Fraunces heading → body →
link with a `↗` glyph. Corgi radii are 24/32px; our brand base `--radius` is 8px
for controls — introduce a `--radius-card: 24px` rather than overriding the base.

## 3. Editorial halftone — the "dots filter" (from Corgi)

Verified: Corgi **bakes** a variable-size black-on-white halftone (dense dots in
shadow, sparse in light — newspaper engraving) into the raster asset; it is NOT a
live filter. This is the New Yorker/FT print register as texture — on-brand for us.

- **Primary route (matches Corgi, most controllable, lightest):** pre-bake a
  halftone version of each hero graphic / Recraft illustration and ship as a static
  self-hosted `webp/avif`. Run it monochrome in **ink `#1A1A1A` on mist** or
  **lichen `#14715F` dots on white** (never duotone — too loud for our register).
- **Secondary route (decorative accent panels only):** live CSS dot screen —
  ```css
  .mw-halftone{ background-image:radial-gradient(circle, currentColor 1px, transparent 1.6px);
                background-size:6px 6px; color:#14715F; }
  ```
  Even dot field, not tonal. Layer two pitches for moiré depth. Use behind a stat
  band, not as the illustration treatment.

Also cheap live textures Corgi uses: tick-rule `linear-gradient(90deg,#E1E1E1 4px,#0000 4px)`,
diagonal hatch `repeating-linear-gradient(45deg,#0000 0 10px,#F5F5F5 10px 20px)`.

## 4. Floating nav (from Acctual)

A fixed floating **pill**, ~24px below the top edge, opaque-white → we go glass so
it picks up the band scrolling under it.

```css
.mw-nav{ position:fixed; inset:0 0 auto 0; z-index:50; display:flex; justify-content:center; padding:20px 24px 0; }
.mw-nav__pill{
  max-width:1100px; width:100%;
  display:flex; align-items:center; justify-content:space-between;
  padding:8px 20px 8px 22px; border-radius:9999px;
  background:rgba(255,255,255,.80); backdrop-filter:blur(12px); -webkit-backdrop-filter:blur(12px);
  border:1px solid rgba(26,26,26,.06);
  box-shadow:0 0 .5px .5px rgba(26,26,26,.05), .5px .5px 1px 0 rgba(26,26,26,.10);  /* whisper, not lift */
}
```
- Wordmark: lowercase `marketworks`, monochrome ink `#1A1A1A`, logotype not icon-lockup.
- Links: Outfit 500, `letter-spacing:-0.01em`, ink → hover lichen. **No dropdowns.**
- CTA: lichen filled pill (`#14715F`/white) echoing the outer pill geometry;
  "Sign in" as a plain ink text link to its left (two-tier action).
- `backdrop-filter` is pure CSS → CSP-safe. Scroll-restyle (shrink on scroll) was
  **unverified** on Acctual; optional for us.

## 5. Motion (from Spade) — borrow the idea, not the tech

⚠️ Spade's headline motion is **Rive (WASM)** — forbidden by our CSP. Do NOT copy
the method. Borrow 2–3 ideas, rebuilt CSP-safe:

1. **"Content resolves as you read"** — Spade's best idea (raw strings → structured
   record). Our version: a raw ticker/price string settling into a clean momentum
   row, or a scatter resolving into a trendline. Build as inline **SVG**
   `stroke-dashoffset` draw-on + staggered opacity, triggered `whileInView`
   (Motion, self-hosted). One per page, not every section.
2. **Contour/streamline background as depth texture** — we already have the rAF
   engine. Sharpen: 1–2 full-bleed `inset-0` layers behind hero + one interior
   section only; add `content-visibility:auto` so offscreen instances stop
   painting (Spade does this); slow it down, lower contrast → ambient, never
   competing with type.
3. **One functional data "gauge"** that animates its value on scroll-in — doubles
   as real product signal (ties to the dashboard-metrics rule: real distribution,
   not decoration).

**House easings (from Spade's CSS):**
- `cubic-bezier(.22,1,.36,1)` — expo-out, the signature reveal (soft landing).
- `cubic-bezier(.2,.8,.2,1)` / `.4,0,.2,1` — UI transitions.
- Durations: 0.15s UI, 0.2s reveal, 0.25s default. Big motion (the SVG resolve) is
  slow (~0.5–0.7s) and rare.
- **Avoid** overshoot/back easings (`.34,1.56,.64,1`) except a tiny stat pop —
  bounce reads consumer, wrong for editorial. Motion used *rarely* is what reads
  premium.

## Stack decisions (carried from prior research)
- **Illustration:** Recraft V4.1 → deterministic normalize (snap to 4 hexes, force
  stroke, SVGO) → optional halftone bake → static self-hosted. No CSP change.
- **Motion:** `motion` (`motion/react`), `LazyMotion`+`m` (~4.6KB initial). Keep the
  rAF background. Lenis only if scroll feels janky. GSAP only for a scrubbed/pinned
  sequence we likely won't need.
- **Reject:** Rive, Lottie/dotLottie, Spline/WebGL 3D — WASM/CDN → CSP risk-register
  event + too loud for the register.

## Verification gates (Playwright MCP + deterministic diff)
- Reduced-motion: SVG art renders complete, ambient background static.
- Light-lock: page stays light under emulated system dark.
- **Zero CSP violations / zero blocked external requests** under production CSP.
- Responsive at 360 / 768 / 1080; grids collapse < 860px.
- Lighthouse mobile ≥ 90; background loop pauses on hidden tab.
