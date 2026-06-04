# design_system — single design umbrella for everything Marketworks ships

## Why this exists

Marketworks now has three distinct surfaces — the website (kite-dashboard),
the content factory (finance-content-os), and the data engine
(kite-lab/insights) — and each has been styling itself ad-hoc. The
existing `finance-content-os/design-system/` was a V1 attempt that
collected references and a draft lichen palette but was never built
out as a working system.

The strategic ask: **a single design umbrella** that every Marketworks
surface inherits from. Whether the founder ships an Instagram
carousel, a library reading page, a portfolio rebalance card, or a
landing page hero, all of it reads as one brand because all of it
draws from one codified system.

Two new technical inputs make this the right moment:

- **Impeccable** — a Claude Code skill (`github.com/pbakaus/impeccable`)
  that ships 26 design reference docs + 23 commands + 27 anti-pattern
  rules. The agent-vocabulary problem the V2 content_redesign solved
  for editorial voice, Impeccable solves for visual design.
- **DESIGN.md convention** — both Impeccable and Open Design treat
  a single canonical `DESIGN.md` as the brand contract that any
  agent doing design work reads into context. Same pattern as our
  V2 `voice_v2.md`.

## Outcome

A new repo `~/marketworks-design/`, published as the private npm
package `@marketworks/design`, with:

1. **DESIGN.md** as the canonical brand contract, auto-loaded by a
   SessionStart hook in every Claude Code session in the repo.
2. **Tokens** (colors, typography, spacing, motion) as TypeScript
   constants — single source of truth importable by every consumer.
3. **React components** at three layers: primitives → branded
   components → render-target templates.
4. **Playwright** harness for visual regression and token contract
   tests — design changes ship through tests, not through "looks
   right to me."
5. **Three consumers wired** by V1 end:
   - `kite-dashboard` for /library + /insights surfaces
   - `finance-content-os` for Instagram-asset rendering
   - The reference site itself

## Strategic frame

| Decision | Locked value |
|---|---|
| Target viewer | Karan (see `~/finance-content-os/brand/personas/karan.md`) |
| References to emulate | FT · NYT · The New Yorker · The Morning Context · Capitalmind · Zerodha Varsity |
| References to avoid | Linear / SaaS purple-gradient cards · finfluencer thumbnails · lifestyle photography |
| Serif (headings) | **Newsreader** (Google Fonts) |
| Sans (body / UI) | **Outfit** (Google Fonts) |
| Brand palette | Lichen — cream `#FAF7F2`, foreground `#14715F`, signal-green `#55C374`, purple `#9750F8` (accent only), ink `#1A1A1A` |
| Semantic palette | Web-standard, **separated from brand** — positive `#0F8A3C`, negative `#B91C1C`, warning `#B45309`, info `#1D4ED8`, neutrals 100/300/500/700/900 |
| Spacing | 4px modular scale (`space-1` … `space-10`) |
| Tools adopted | Impeccable (skill), Playwright (TDD) |
| Tools declined | Open Design — Impeccable already covers our agentic-design needs |
| Repo location | New repo `~/marketworks-design/`, private, npm name `@marketworks/design` |
| Logo | Wordmark "marketworks" set in Outfit semibold for now; custom logo deferred to hired designer |

All other tokens live in `DESIGN.md` and `tokens/*.ts` in the design
repo.

## Architecture

```
~/marketworks-design/                ← canonical source of truth
├── DESIGN.md                        ← brand contract (auto-loaded in every session)
├── tokens/                          ← TypeScript single-source-of-truth
│   ├── colors.ts · typography.ts · spacing.ts · motion.ts · index.ts
├── src/
│   ├── primitives/                  ← Text, Box, Stack, Heading
│   ├── components/                  ← Card, Article, Hero, Chart
│   └── templates/                   ← CarouselSlide, Thumbnail, ReelOverlay
├── tests/
│   ├── visual/                      ← Playwright screenshot regression
│   └── contract/                    ← token contract
├── reference/                       ← visual reference site (Phase 2)
├── scripts/
│   └── render-asset.ts              ← CLI: pack JSON + template → PNG
├── .claude/
│   ├── settings.json                ← SessionStart hook
│   ├── hooks/load-design-context.sh
│   └── skills/impeccable/           ← installed Impeccable skill (Apache-2.0)
└── package.json                     ← @marketworks/design, file:-installable

~/kite-lab/kite-dashboard            ← consumer 1 (React imports)
~/finance-content-os                 ← consumer 2 (headless asset rendering)
```

### How consumers wire in

For now (Phase 1-3), consumers reference the design repo by file path
in their `package.json`:

```json
"@marketworks/design": "file:../marketworks-design"
```

This works locally without a registry. Phase 7 or later migrates to
a private npm registry (GitHub Packages, Verdaccio, or similar) when
the cross-machine portability matters.

## Phase 0 decisions (locked)

Confirmed in conversation 2026-06-03. The locked values are in
`_meta.yml` and have already been encoded into `DESIGN.md` and the
token files.

**Revised 2026-06-04** after the Pencil brand-guide validation (see
`TASKS.md` Phase 3.6): base surface warm cream `#FAF7F2` → cool mist
`#ECF3EF`; semantic palette muted; headline serif Newsreader →
Fraunces. The strategic-frame table above and other Newsreader/cream
references in this file predate that revision — `_meta.yml`
foundations and `DESIGN.md` are the current source of truth.

## Scope boundary

**In scope (V1 — Phases 1-5):**
- Foundation files: DESIGN.md, tokens, repo skeleton, Impeccable, Playwright
- Primitives layer: Text, Box, Stack, Heading
- Three V1 surfaces:
  - **Instagram assets** — CarouselSlide, Thumbnail, ReelOverlay templates +
    headless render CLI
  - **Library reading pages** — Article, PieceHeader, Hook, BodyParagraph,
    Takeaway, CTA. Wired into kite-dashboard `/library/[slug]`.
  - **Insights dashboard** — Chart primitives (Line, Bar, Sparkline) +
    dashboard cards (RegimeCard, SectorCard, StressGauge). Wired into
    kite-dashboard `/insights`.

**In scope (V2 — Phases 6):**
- Landing page (`/`) + signup page

**In scope (V3 — Phases 7-8):**
- Main authenticated dashboard
- Migration of existing kite-dashboard ad-hoc styles to design-system
  components

**Out of scope:**
- Custom logo design — deferred to hired designer
- Custom serif typeface (e.g., commissioned FT-Display equivalent) —
  Newsreader is the V1 answer
- Multi-language type support (Hindi / Devanagari) — Latin-only V1
- Animation library beyond motion tokens — `framer-motion` integration
  considered if needed in a specific template
- Email template system — separate initiative
- Decks / pitch surface — separate initiative
- Open Design adoption — Impeccable covers the agent surface

## Critical files

### marketworks-design (the new repo)
| Path | Role |
|---|---|
| `DESIGN.md` | Canonical brand contract |
| `tokens/colors.ts` | Brand + semantic palettes as TS constants |
| `tokens/typography.ts` | Newsreader / Outfit, scale, OpenType features |
| `tokens/spacing.ts` | 4px modular scale + containers + radii |
| `tokens/motion.ts` | Duration + easing + stagger |
| `.claude/hooks/load-design-context.sh` | SessionStart hook |
| `.claude/skills/impeccable/SKILL.src.md` | Impeccable entry point |
| `package.json` | `@marketworks/design`, file:-installable |

### kite-lab
| Path | Role |
|---|---|
| `tasks/design_system/` | Strategic plan + task tracking (this folder) |
| `kite-dashboard/package.json` | Adds `@marketworks/design` as `file:` dep (Phase 4-5) |
| `kite-dashboard/src/app/library/[slug]/page.tsx` | Refactored to use design-system components (Phase 4) |

### finance-content-os
| Path | Role |
|---|---|
| `package.json` | Adds `@marketworks/design` as `file:` dep (Phase 3) |
| `scripts/render-social-asset.py` (new) | Calls into the design repo's `render-asset.ts` CLI to produce PNGs from content packs |

## Verification at close

- [ ] All three V1 surfaces draw exclusively from `@marketworks/design`
      tokens and components (no hard-coded hex, no raw `px` outside
      tokens)
- [ ] Playwright visual regression suite passes on every component
- [ ] Playwright token contract test passes: every brand and semantic
      token's value matches `DESIGN.md`
- [ ] A real Instagram carousel slide for a real content pack renders
      via the design repo's `render-asset.ts` and matches a reference
      screenshot
- [ ] `/library/<slug>` renders at the bar with design-system components
- [ ] `/insights` renders at least one chart card using design-system
      primitives
- [ ] Impeccable's `/audit` command run against any consumer surface
      reports no anti-pattern violations from the brand-relevant set
- [ ] `OVERVIEW.html` (Phase 8) is the visual map for future-you

See `TASKS.md` for the phased build.
