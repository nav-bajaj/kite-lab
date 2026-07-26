# Illustration style & process (cool muted pastel grain)

The repeatable pipeline for Marketworks illustration assets. Reference: the NYT
illustrator **Matija Medved** (style borrowed — grain, mood, metaphor — never
his specific images).

## The style

Soft, **muted, hazy, pastel/crayon grain** — quiet editorial op-ed illustration.
The whole point: it must sit *behind* the design, not compete with it. (The first
attempt was too vivid/saturated and overpowered the page — that was the failure.)

- **Texture:** fine soft-crayon / colored-pencil grain on paper; hazy, washed-out,
  soft edges. Keep assets **raster** (grain must survive).
- **Tone:** very low saturation, faded, pale, low-contrast, dreamy, calm.
- **Content:** a clear **metaphor** for the section, not a literal chart. Vary the
  scenes (interiors, tabletops, single objects — NOT all landscapes).

## Locked palette — COOL, muted only

No warm at all (the model drifts to vivid yellow/orange; forbid it explicitly).

| Role | rgb | note |
|---|---|---|
| mist off-white | 236,243,239 | light / sky |
| soft faded sage | 160,186,170 | dominant green |
| faded teal | 88,132,118 | dusty lichen |
| soft dusty lavender | 178,164,198 | muted purple |
| soft cool charcoal | 90,90,96 | not pure ink |

Passed as `controls.colors` AND named in the prompt. Prompt must say: "NO warm, no
yellow/orange/gold/red/brown, nothing saturated." (Marigold — the brand's warm
accent — is deliberately NOT used here; illustrations are cool-only.)

## Prompt formula

`[verbose concrete metaphor] + [fixed STYLE string]`, total **≤ 1000 chars**
(Recraft's hard cap). Verbose subject descriptions help; keep the STYLE string
tight so both fit. Fixed STYLE + palette clause live in `generate-comps.mjs`.

## Pipeline (scripts in this dir)

1. **Generate** — `node generate-comps.mjs [name ...]` — Recraft `recraftv3`,
   `style: digital_illustration`, `substyle: grain`, `n: 2`, `controls.colors` =
   locked cool palette. Output → `finalset/` (gitignored). Vector model = wrong
   tool (can't grain); raster only.
2. **Curate** — contact-sheet (html grid + screenshot); pick one variant per slot.
3. **Optimize** — `node optimize.mjs` — sharp → 900px webp (~120–200KB) into
   `kite-dashboard/public/illustrations/`. Edit the PICKS map to change a choice.
   Bump filenames (or clear `.next/cache/images`) when re-optimizing — next/image
   caches by URL and won't pick up an overwritten file in a running dev server.
4. **Wire** — `next/image`. The **hero** floats with a soft radial edge-fade mask
   (`HERO_FADE` in page.tsx) so its grain melts into the base — no card frame.
   Card / research / portfolios images stay contained in rounded frames.
5. **Verify** — render live; check muted + reads at size + light-lock + perf.
   (Lazy images can look blank in a stitched full-page screenshot; confirm via
   `img.complete` or a scrolled viewport shot.)

## Iteration history (what dialled it in)
- Abstract-geometry prompts on the **vector** model → generic junk. Fixed by
  concrete metaphors + **raster grain**.
- First grain pass too **vivid/saturated** → overpowered the page. Fixed by the
  **cool muted pastel** palette + "very low saturation / no warm" + more haze.
- Compositions too samey (all hills) → **varied scenes** (window, sill, desk,
  path, tree-rings, plants) with verbose descriptions.

## Guardrails
- **Adapt the style, don't clone.** Never upload the illustrator's images to a
  Recraft custom style.
- Cost ~$0.08/image; generate n=2 for choice, don't blind-batch.
- Extends DESIGN.md §7 (line-art) to a second sanctioned register (grain pastel).
