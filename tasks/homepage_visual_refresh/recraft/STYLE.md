# Illustration style & process (grain editorial)

The repeatable pipeline for Marketworks illustration assets. Reference:
NYT-illustrator grain work (style borrowed, never the artist's specific images).

## The style

Grainy, atmospheric, **metaphorical** editorial illustration — NYT/FT op-ed
register. NOT line-art, NOT flat clean vector, NOT literal charts.

- **Texture:** heavy risograph/stipple grain across the whole image (this is the
  signature; it must survive — keep assets **raster**, never vectorize).
- **Composition:** simple flat forms with grainy shading, generous negative
  space, a big quiet sky, calm.
- **Content:** a metaphor for the section, not a depiction of it (a figure
  watching distant peaks = patient market-watching; a magnifying glass over
  hills = studying history). One cohesive landscape world across the set.

## Locked palette

Cool base + two accents. Passed as `controls.colors` AND named in the prompt.

| Role | Hex | rgb |
|---|---|---|
| mist (light/ground/sky) | `#ECF3EF` | 236,243,239 |
| lichen (primary green) | `#14715F` | 20,113,95 |
| signal (bright green) | `#55C374` | 85,195,116 |
| ink (figures/dark) | `#1A1A1A` | 26,26,26 |
| **marigold (warm accent)** | `#E8A33D` | 232,163,61 |
| **purple (cool spot)** | `#9750F8` | 151,80,248 |

Marigold is a deliberate brand-palette addition (warmth/welcome against the
restraint). Exclude blue/cyan explicitly — the model drifts there.

## Prompt formula

`[concrete metaphor for the section] + [fixed STYLE descriptor] + [palette clause]`

The fixed STYLE + palette clause live verbatim in `generate-final.mjs`. Vary only
the metaphor. Keep "no text, no words, no charts, no numbers, no logos" and
"NO blue, NO cyan, no other colours".

## Pipeline (scripts in this dir)

1. **Generate** — `node generate-final.mjs [name ...]` — Recraft `recraftv3`,
   `style: digital_illustration`, `substyle: grain`, `n: 2` per subject,
   `controls.colors` = locked palette. Output PNGs → `final/` (gitignored).
   (Vector model = wrong tool; it can't grain. Raster only.)
2. **Curate** — contact-sheet them (an html grid + a screenshot) and pick one
   variant per slot.
3. **Optimize** — `node optimize.mjs` — sharp → 900px webp (~120–200KB) into
   `kite-dashboard/public/illustrations/`. Edit the PICKS map to change a choice.
4. **Wire** — image-led `FeatureCard` (banner mode) + `next/image` in the hero /
   research / portfolios slots. Hero image gets `priority`; the rest lazy-load.
5. **Verify** — render live, check on-palette + reads at card size + light-lock +
   perf. (next/image lazy images can look blank in a stitched full-page
   screenshot; confirm via `img.complete` or a scrolled viewport shot.)

## Guardrails

- **Adapt the style, don't clone.** We take grain + atmosphere + metaphor and
  render in our palette. Do not upload an illustrator's images to a Recraft
  custom style.
- **Cost:** ~$0.08/raster image. Generate n=2 for choice; don't blind-batch.
- **Brand:** this extends DESIGN.md §7 (which only sanctioned line-art) to a
  second sanctioned illustration register — document any further evolution there.
- **The key was the prompt + right model + locked palette.** Abstract-geometry
  prompts on the vector model produced generic junk; concrete metaphors on the
  grain raster model with a locked palette produce the real thing.
