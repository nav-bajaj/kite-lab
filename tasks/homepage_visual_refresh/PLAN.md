# homepage_visual_refresh — PLAN

## Why

The public homepage (`kite-dashboard/src/app/page.tsx`) is editorially sound but
visually flat: one mist (`#ECF3EF`) plane top to bottom, hairline-bordered cards
with no elevation, no illustration, no motion beyond a hand-rolled ambient
background. Over a long scroll it reads dull. The founder wants visual richness —
layering, depth, contrast, tasteful graphics and motion — **without deviating
from the brand**.

Direction validated against three reference sites the founder selected
(spade.com, corgi.insure, acctual.com); full teardowns with verified CSS/token
values in `REFERENCES.md`.

## What the outcome looks like

A homepage that keeps the calm FT/New Yorker register but gains depth:

- **Layered surface**, not one flat plane: a brighter near-white base that runs
  **continuously**, with `mist` / `lichen` / deep sections as **inset, rounded,
  floating panels** (Acctual model) — never full-bleed edge-to-edge bands, so the
  white flows around the color (founder note 2026-07-19).
- **Cards with real elevation** — the Corgi soft ink-tinted ambient shadow
  recipe, replacing today's flat borders.
- **An editorial halftone treatment** on the hero graphic / illustrations
  (Corgi's "dots" = newspaper engraving screen; on-register for us).
- **Contrast from underused brand tokens** — `signal-green`, `purple` (sparing),
  and muted semantics as accent moments instead of an all-lichen wash.
- **A floating nav** (Acctual's pill, our tokens, lowercase `marketworks`).
- **Restrained motion** — the Spade "content resolves as you read" idea rebuilt
  in CSP-safe SVG + Motion, not Spade's Rive/WASM.
- **Production-grade illustrations** from Recraft (not hand-authored SVG),
  normalized and self-hosted.

## Brand contract — needs a decision (⚠️ founder sign-off)

The move to a whiter base collides with two explicit rules in
`~/marketworks-design/DESIGN.md`:
- §2.1: "`mist` is the **surface anchor**."
- §9 anti-pattern: "**Pure white surfaces — use mist.**"

Reconciliation proposed (not a drift — a documented evolution):
- Base is **near-white with a faint lichen tint** (e.g. `#FAFCFB`), **not** pure
  `#FFFFFF` — honors the "no pure white" spirit while brightening the page.
- **`mist` stays load-bearing** as the primary alternating band + card-tint
  color, so it remains the anchor hue, just no longer the entire canvas.
- Adds a **shadow scale**, a **mist→white tint ladder**, a **deep-lichen drench
  band**, and a **halftone** token to the system.

This is a `DESIGN.md` amendment (CalVer changelog bump) + token additions in
`@marketworks/design`, mirrored into `kite-dashboard/globals.css`. **Do not
implement tokens until the founder signs off on the surface-model change and on
a full-page visual mock** (per the visual-validation-first working rule).

## Scope boundary

- **In:** the public marketing homepage (`/`) and the shared marketing chrome it
  uses (`marketing-nav`, `marketing-footer`, `portfolio-card`), the design-token
  additions that serve it, and the illustration batch.
- **Out (this task):** `/portfolios`, `/library`, `/insights`, `/sign-up`, and
  the authenticated dashboard. They inherit token changes for free but are not
  re-laid-out here. No copy/positioning changes (verbatim current copy).
- **Invariant:** stays light-locked and **CSP-clean** — static SVG + CSS +
  self-hosted Motion only. No Rive/Lottie/WASM/CDN (would need a risk-register
  row first per CLAUDE.md; explicitly avoided).

## Critical files

| File | Role |
|---|---|
| `kite-dashboard/src/app/page.tsx` | The homepage being rebuilt |
| `kite-dashboard/src/app/globals.css` | `.mw-brand` token scope (mirrors design pkg) |
| `kite-dashboard/src/components/marketing/*` | nav / footer / portfolio-card |
| `~/marketworks-design/DESIGN.md` + `tokens/*` | brand contract + token source of truth (amendment lands here first) |
| `tasks/homepage_visual_refresh/REFERENCES.md` | distilled, tokenized recipes from the 3 teardowns |
| scratchpad `illustration_brief.md` | Recraft batch brief (6 editorial line illustrations) |

## Phases (detail lands in TASKS.md once scope is locked)

0. Design spec + brand-contract reconciliation (this PLAN + REFERENCES). 🤖
1. **Full-page HTML mock** in the new layered brand → **founder sign-off**. 🤖→👤
2. Illustration batch: Recraft generate → normalize → halftone → self-host. 🤖 (👤 Recraft acct/key: key present)
3. Token + `DESIGN.md` amendment in `@marketworks/design`, mirror to `globals.css`. 🤖→👤 sign-off
4. Implement homepage in Next.js: nav, layered sections, cards, motion (Motion lib), halftone, illustrations. 🤖
5. QA: Playwright (reduced-motion renders complete, light-lock, **zero CSP violations**), responsive 360/768/1080, Lighthouse ≥90 mobile. 🤖
6. Ship on a branch off `beta_gtm_mvp` → Vercel deploy → verify live URL. 🤖→👤

## Still needed from founder

- **Mobbin references** → become Recraft Style-Lock inputs + composition grounding.
- **Sign-off** on the surface-model brand amendment (§Brand contract) and the Phase-1 mock.
