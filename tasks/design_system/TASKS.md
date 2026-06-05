# design_system — phased build

Owner key: 🤖 Claude (unattended) · 👤 founder · 🤝 both.
Status key: ☐ todo · ◐ in-progress · ☑ done · ⊘ deferred

Most work lands in `~/marketworks-design/`. Consumer wiring lands
in `~/kite-lab/kite-dashboard/` and `~/finance-content-os/`. This
folder in kite-lab is the tracking + planning surface only.

---

## Phase 0 — Decisions (👤 locked)

| # | Item | Status |
|---|---|---|
| 0.1 | Serif headings: **Newsreader** | ☑ |
| 0.2 | Sans body/UI: **Outfit** | ☑ |
| 0.3 | "Your Green" naming: **Signal Green** (`#55C374`) | ☑ |
| 0.4 | Semantic palette separated from brand (web-standard greens/reds) | ☑ |
| 0.5 | Repo location: new private repo `~/marketworks-design/` published as `@marketworks/design` | ☑ |
| 0.6 | Tooling: Impeccable installed; Open Design declined | ☑ |
| 0.7 | Logo: wordmark "marketworks" in Outfit semibold until designer is hired | ☑ |

---

## Phase 1 — Foundations (🤖)

Brand contract, tokens, repo skeleton, hooks, skill install.

| # | Item | Status |
|---|---|---|
| 1.1 | Create `~/marketworks-design/` repo with directory structure | ☑ |
| 1.2 | Write `DESIGN.md` — identity, brand + semantic palettes, type system (Newsreader + Outfit), spacing, motion, anti-patterns, enforcement, changelog | ☑ |
| 1.3 | `tokens/colors.ts` — brand + semantic constants + `renderCssVariables()` | ☑ |
| 1.4 | `tokens/typography.ts` — families, scale, weights, OpenType features, Google Fonts link | ☑ |
| 1.5 | `tokens/spacing.ts` — 4px modular scale + containers + radii | ☑ |
| 1.6 | `tokens/motion.ts` — duration + easing + stagger | ☑ |
| 1.7 | `tokens/index.ts` + `src/index.ts` barrel exports | ☑ |
| 1.8 | `package.json` — `@marketworks/design@0.1.0`, peerDeps, devDeps, scripts | ☑ |
| 1.9 | `tsconfig.json` — strict + Bundler resolution + react-jsx | ☑ |
| 1.10 | `playwright.config.ts` — scaffold; fixtures land in Phase 2 | ☑ |
| 1.11 | `.claude/settings.json` + `.claude/hooks/load-design-context.sh` SessionStart hook — verified emits 366 lines of brand context | ☑ |
| 1.12 | Install Impeccable skill at `.claude/skills/impeccable/` (Apache-2.0 license carried) | ☑ |
| 1.13 | `README.md`, `.gitignore` | ☑ |
| 1.14 | Initial commit | ☑ |
| 1.15 | `npm install` to materialise `node_modules` + `package-lock.json` | 👤 ☐ |
| 1.16 | Run Impeccable's `init` flow once to align it with our DESIGN.md — **done 2026-06-04**: wrote `PRODUCT.md` (register: brand) from DESIGN.md + the Karan persona; `context.mjs` clean, so `/critique` `/audit` `/polish` work. mw `15b65f9`. | ☑ |

**Risk tag:** 🟢 low. Scaffolding, no runtime impact.

---

## Phase 2 — Primitives + reference site (🤖)

Foundational React components every other component is built on.

| # | Item | Status |
|---|---|---|
| 2.1 | Styling layer chosen: **Tailwind utility classes emitted from primitives via `cn()`, role tokens shipped as CSS variables**. Aligns with the existing kite-dashboard stack (Next.js 16 + Tailwind v4 + shadcn/ui). One stylesheet ships :root (light) + .dark blocks; consumers `import "@marketworks/design/styles.css"` once and existing shadcn components inherit brand automatically. | ☑ |
| 2.2 | `src/primitives/Text.tsx` — size + color + tabular props; emits Tailwind utility classes | ☑ |
| 2.3 | `src/primitives/Heading.tsx` — serif h1-h6 with semantic level vs visual size independence | ☑ |
| 2.4 | `src/primitives/Box.tsx` · `src/primitives/Stack.tsx` — token-driven padding, container, gap, alignment via Tailwind utilities | ☑ |
| 2.5 | `src/primitives/Eyebrow.tsx` — uppercase label, 12px / 0.14em tracking / Outfit semibold | ☑ |
| 2.6 | `tokens/css.ts` programmatic generators + `tokens/tailwind.ts` Tailwind v4 `@theme inline` preset | ☑ |
| 2.7 | Ladle 5.1.1 reference site at `http://localhost:6006`. `.ladle/config.mjs` + `.ladle/components.tsx` + 30+ `*.stories.tsx` across the five primitives. Tailwind v4 via Play CDN dev-time only (consumers use proper compilation). Playwright `webServer` boots Ladle automatically. | ☑ |
| 2.8 | Visual regression — `tests/visual/primitives.spec.ts` · **7 screenshot fixtures** across composite stories. Baselines in `tests/visual/primitives.spec.ts-snapshots/`. `maxDiffPixelRatio` 0.02. | ☑ |
| 2.9 | Token contract suite — **18 tests passing**. Verifies brand identity (5 tokens), semantic palette, light + dark role tokens (incl. lichen↔signal-green inversion), typography, spacing, motion, styles.css↔tokens.ts sync. | ☑ |
| 2.10 | TDD behavior suite — `tests/behavior/{heading,text,eyebrow,box,stack}.spec.ts` · **30 behavior tests** asserting DOM tags, utility-class application, and computed-style resolution against role tokens. Each test written red-first, then story written to make it green. | ☑ |
| 2.11 | Impeccable installed properly via `npm install -D impeccable` + `npx impeccable skills install` (the earlier copy was the unbuilt source bundle; SKILL.src.md isn't Claude-Code-discoverable). Deterministic `impeccable detect` scan run across 7 composite stories — 6 pass clean, 1 finding (`flat-type-hierarchy` on `text--all-sizes`) documented as an intentional editorial exception in DESIGN.md §3. **LLM-driven `/impeccable audit` is founder-side** — open Claude in `~/marketworks-design/` (skill now discoverable), invoke `/impeccable audit`. | ☑ |
| 2.12 | **Architectural re-alignment after dashboard survey** — color system reframed into three layers (brand identity / role tokens / semantic). Role tokens use shadcn variable names so existing dashboard components inherit brand automatically. Dark mode added for dashboard surfaces only; /library + social + landing + signup are light-locked. Fonts moved off CDN @import (CSP-blocked); next/font is the documented consumer path. Primitives emit Tailwind utility classes via cn() — scoped `mw-*` class system dropped. | ☑ |

**Phase 2 totals:** 55 tests passing in ~8s (18 contract + 30 behavior + 7 visual).

**Risk tag:** 🟡 medium. Styling-layer choice is sticky; pick once.

---

## Phase 3 — V1 social asset templates (🤖)

CarouselSlide, Thumbnail, ReelOverlay + headless render CLI for
finance-content-os to call.

| # | Item | Status |
|---|---|---|
| 3.1 | `src/templates/CarouselSlide.tsx` — 1080×1080, three variants (cover · body · cta), data-template + data-variant + data-slot attributes for stable selection. 10 behavior tests + 3 visual baselines. | ☑ |
| 3.2 | `src/templates/Thumbnail.tsx` — square 1080×1080 and vertical 1080×1920, optional eyebrow + accent stat (80px serif primary). 7 behavior tests + 4 visual baselines. | ☑ |
| 3.3 | `src/templates/ReelOverlay.tsx` — 1080×1920, solid (cream) and transparent modes, hook + optional stat callout (160px serif primary), handle always at bottom. 6 behavior tests + 2 visual baselines. | ☑ |
| 3.4 | `scripts/render-asset.ts` — headless render CLI. Boots Ladle if not running, navigates to the parametric `render--asset` story with template + props url-encoded, screenshots `[data-template=…]` selector, writes PNG. Smoke-tested on all three templates at canonical sizes. | ☑ |
| 3.5 | Visual regression fixtures — `tests/visual/templates.spec.ts` ships 9 baselines (3 carousel × 4 thumbnail × 2 reel-overlay). | ☑ |
| 3.6 | `~/finance-content-os/scripts/render_social_assets.py` reads a `PublishedPiece` JSON and shells out to the design CLI to produce a thumbnail + reel + N carousel slides. Body→carousel split uses first-sentence headline + remainder body. Committed on finance-content-os `design_system` branch (ca24773). | ☑ |
| 3.7 | Smoke-tested on `published/pieces/rupee_weakness_roundup.json` — 10 PNGs rendered at canonical sizes (1 thumbnail + 1 reel @ 1080×1920 + 8 carousels @ 1080×1080). Visual review pending. Live `/library` piece's `"assets": []` not updated yet — that's the next step once founder reviews the rendered output. | ☑ |

**Risk tag:** 🟡 medium. CLI complexity for headless rendering.

---

## Phase 3.5 — Rich visual library (🤖)

After the v1 templates (3.1–3.7) shipped, the founder review surfaced
that text-only carousel slides aren't publication-ready — a finance
brand's identity is its data visualisation, not just typography. This
phase brings chart primitives, composite chart-driven slides, and a
deck-design skill that picks templates per slide instead of mechanically
mapping body paragraphs.

Decisions locked in conversation:
- Chart library: **Recharts** (already a kite-dashboard dep; React-first; built on D3 so we can drop down for custom-graph cases without abandoning the stack)
- Icons: **Lucide** (already in kite-dashboard); defer custom sector icons to a hired designer later
- AI image gen: **out** for v1 (defer — the editorial references we anchor on are 95% programmatic data viz + typography)

| # | Item | Status |
|---|---|---|
| 3.5.1 | Chart primitives — `LineChart`, `BarChart`, `Sparkline` (`src/charts/*.tsx`). Branded Recharts wrappers with Outfit ticks, no vertical grid, brand-primary stroke. `BarChart` `semantic` mode uses semantic.positive/negative for finance up/down (never the brand colors). 7 behavior tests + 4 visual baselines. | ☑ |
| 3.5.2 | `ChartSlide` composite template — 1080×1080. Chart top, headline + caption bottom. Takes a discriminated `chart: { kind: "line" \| "bar"; … }` prop. 2 behavior tests + 2 visual baselines. End-to-end smoke-tested through the CLI on a synthetic USDINR series with annotation → 1080×1080 PNG. | ☑ |
| 3.5.3 | `StatCalloutSlide` — giant figure (180px Fraunces, lichen) + label + context, on mist with the lichen footer band. Sparkline deferred. 3 behavior + 1 visual. mw `15b65f9`. | ☑ |
| 3.5.4 | `ComparisonSlide` — two-column "A vs B" (e.g. METAL +19.6% / BANK -4.2%); direction via muted semantic palette + `tone` prop, lichen footer band. 3 behavior + 1 visual. mw `11ae587`. | ☑ |
| 3.5.5 | `QuoteSlide` — large Fraunces italic pull quote on mist + signal-green rule + lichen footer band. 3 behavior + 1 visual. mw `15b65f9`. | ☑ |
| 3.5.6 | `MechanismSlide` — vertical cause→effect chain of step cards connected by lichen Lucide down-arrows (custom sector icons still deferred to a designer). 3 behavior + 1 visual. mw `11ae587`. | ☑ |
| 3.5.7 | `design-social-deck` skill in finance-content-os — picks per-slide template based on script + dossier, maps script body + dossier data into slide props. Replaces the mechanical body→carousel mapping in `render_social_assets.py`. **Done 2026-06-04**: skill at `.claude/skills/design-social-deck/SKILL.md` (TDD shape — output contract + decision policy + anti-fabrication rules + failure modes + self-check). New `deck.json` artifact (DeckPlan) sits between script and renderer; contract `schemas/deck.schema.json`. Deterministic gate `scripts/validate_deck.py` (3 layers: schema → per-template props mirroring the `.tsx` contracts → numeric traceability — every on-slide number must trace to script/dossier, ISO-timestamp-stripped corpus, one-way rounding match). Accepts ScriptDraft **or** PublishedPiece as input (no reconstruction needed for shipped pieces). `render_social_assets.py` refactored: `--deck` is the primary path (validates then renders), mechanical mapping demoted to `--piece` legacy fallback. `voice-guard.md` extended with a DeckPlan-review branch (6 checks on on-slide copy, writes `deck_guard_verdict.json`). | ☑ |
| 3.5.8 | Re-render `rupee_weakness_roundup` with the rich library — proof point. **Done 2026-06-04**: deck at `data/content_packs/rupee_weakness_roundup/deck.json` — 7 slides: cover-with-stat (~5%) · **MechanismSlide** (drift→tax cause-chain) · 3 body slides (oil/electronics/foreign capital) · **QuoteSlide** (synthesis pull-quote) · cta, plus thumbnail (accent ~5%) + reel (stat ~5%, which the old render left empty). Honest skips proving the policy: **no ChartSlide** (dossier has only scalars, no series — a synthesised USDINR line would be fabrication) and **no ComparisonSlide** (the three effects all point the same direction — no real winner/loser). Validator green (numeric traceability on); voice-guard **PASS** (0 blocking — notably the deliberately-omitted 96th-percentile never resurfaced). 9 PNGs rendered to `published/assets/rupee_weakness_roundup/` at canonical sizes; cover/mechanism/quote/reel visually reviewed. | ☑ |
| 3.5.9 | CLI-level smoke test (`tests/smoke/render-cli.spec.ts`, tag `@smoke`, `npm run test:smoke`) — shells out to `render-asset.ts` for carousel-slide + comparison-slide, asserting non-trivial PNG output. Closes the URL-decode double-bug gap. mw `c94bb80`. | ☑ |

**Risk tag:** 🟡 medium. The deck-design skill (3.5.7) is the largest piece and the hardest to validate — needs TDD shape similar to the V2 content_redesign work.

---

## Phase 3.6 — Brand-guide validation + refinements (🤝 2026-06-04)

The founder paused the code build to de-risk the *look* before going
further: "I want to visually see what we make before committing to
this process further." We built a Pencil brand guide, critiqued it
with Impeccable, and shipped three token-level refinements.

| # | Item | Status |
|---|---|---|
| 3.6.1 | Built a 9-board Pencil brand guide at `~/marketworks-design/reference/brand-guide.pen` — cover, color, typography, logo/space/motion + applied surfaces (social carousel, library reading page, dark insights dashboard), every value bound to the real tokens. | ☑ |
| 3.6.2 | Impeccable critique pass. Finding: the system sat in the saturated **"editorial-typographic" lane** (italic serif + mono labels + monochrome restraint + no imagery). The "visually lacking" feeling was composition, not execution — fix = richer composition + real data viz + the refinements below. Also surfaced that Impeccable's `init`/PRODUCT.md is still unrun (Task 1.16). | ☑ |
| 3.6.3 | **Surface migration** — warm cream `#FAF7F2` → cool **mist** `#ECF3EF` (tinted toward the lichen hue, off the AI warm-cream default). `--brand-cream` → `--brand-mist`. mw `6c6ffec`. | ☑ |
| 3.6.4 | **Muted semantic palette** — positive/negative/warning/info desaturated to sit with the low-saturation brand (`#3F8059` / `#A64C42` / `#9E6A35` / `#42608E`). mw `c7596ae`. | ☑ |
| 3.6.5 | **Serif swap** Newsreader → **Fraunces**, chosen from a three-way reading-page comparison mocked in the guide (Newsreader / Fraunces / Spectral). Outfit + IBM Plex Mono unchanged. mw `e245347`. | ☑ |
| 3.6.6 | All three refinements shipped through the token-contract + behavior + visual-regression suites (re-baselined, full suite green). DESIGN.md changelog `2026.06.04` / `.04b` / `.04c`. `_meta.yml` foundations updated to the revised locked values. | ☑ |
| 3.6.7 | **Phase 3.5 kickoff** — restructured the React `CarouselSlide` to match the guide (padded body + full-bleed lichen footer band + top row eyebrow/page-indicator + optional serif stat callout), fixing the "empty slide" at the source. +2 behavior tests; carousel baselines re-gen. mw `c2fc044`. | ☑ |
| 3.6.8 | **Template fidelity vs the Pencil guide (2026-06-04, founder-flagged after 3.5.8 renders).** Read the guide's Social boards (Cover/Data/Takeaway) node-by-node and reconciled the React templates. (a) **Bug:** on-lichen text (footer wordmarks, cta drench) used `text-[color:var(--color-primary-foreground)]`, but the theme is `@theme inline` so that var has no runtime value — text fell back to dark ink instead of mist; switched to `text-primary-foreground`. Baselines had frozen the bug. (b) Cover headline display-2 (48px) → display-1 (64px). (c) `Eyebrow` gains `size` prop; social slides use `lg` (18px). (d) Pull-quote: swashy Fraunces italic → roman (founder-flagged). (e) cta variant now matches the Takeaway board: signal-green eyebrow + big mist takeaway + mist `pill` button (CTA-inventory-compliant). (f) New `RankedBars` chart + `ChartSlide` `ranked-bars` kind; ChartSlide restructured to the Data board (footer band, headline-above). Full suite re-baselined — 121 green. mw `e4e1cdd`, fco `b70197a`. DESIGN.md `2026.06.04d`. | ☑ |

**Outcome:** founder green-lit continuing the build in this direction;
the 3.5.8 renders were then fidelity-checked against the guide (3.6.8).

**Risk tag:** 🟢 low. Visual validation + token-level refinement, fully tested.

---

## Phase 4 — V1 library reading pages (🤖)

`/library` + `/library/[slug]` in kite-dashboard, rebuilt using
design-system components.

**Consumption decision (2026-06-05):** a cross-repo `file:` dep on
`~/marketworks-design` can't resolve on Vercel (it builds kite-dashboard
from the *kite-lab* repo only). So Phase 4 is **self-contained in the
dashboard** — brand token *values* mirrored into `globals.css` under a
`.mw-brand` scope, reading components built in `kite-dashboard/src/components/library/`,
fonts via `next/font`. The design package stays the source of truth; the
formal package dependency (registry vs vendor) is deferred to Phase 8.6/8.7.
Net effect: `/library` **deploys to Vercel today** with no registry blocker.

| # | Item | Status |
|---|---|---|
| 4.1 | **Done 2026-06-05** (revised — see decision above). `next/font/google` wires **Fraunces** (display serif; not Newsreader — superseded by 3.6.5) + **Outfit** in `layout.tsx`. Brand role tokens mirrored into `globals.css` under `.mw-brand` (not a package import); `--font-serif`=Fraunces added to `@theme inline`. | ☑ |
| 4.2 | Verified shadcn/Tailwind utilities inherit the brand — `.mw-brand` overrides the runtime role vars (`--primary`, `--background`, …) that `@theme inline` resolves to, so cards/buttons/text re-skin automatically inside the scope. Confirmed on the rendered index + reading pages. | ☑ |
| 4.3 | Light-locked via the `.mw-brand` wrapper in `app/library/layout.tsx`: the brand's light token values resolve to the nearest ancestor, overriding any `.dark` on `<html>` for the subtree — no `forcedTheme` needed. | ☑ |
| 4.4 | Reading components at `src/components/library/article.tsx` (Article, PieceHeader, Eyebrow, Lead, BodyParagraph, PullQuote, Figure, TakeawayCard, CtaCard, SourceData) + `PieceCard.tsx` + `MarketingNav.tsx` + `lib/library-format.ts`. Matched to the guide's "Library / Reading Page" board (680px column, eyebrow→Fraunces 54px→byline, Outfit lead/body, signal-green pull-quote, white figure card, lichen-tint takeaway). | ☑ |
| 4.5 | `library/page.tsx` (index, grouped PieceCards) + `[slug]/page.tsx` (Article) refactored to the brand components. Full `next build` green — `/library` static, `/library/[slug]` SSG. | ☑ |
| 4.6 | Run Impeccable `/audit` against /library locally | 👤 ☐ |
| 4.7 | Playwright visual regression on /library pages (dashboard has no Playwright harness yet — optional) | ☐ |
| 4.8 | Re-deploy preview branch and visual-check `/library/rupee_weakness_roundup` — **unblocked** (self-contained, build green) | 👤 ☐ |

**Risk tag:** 🟢 low. Component swap, dashboard already builds.

---

## Phase 5 — V1 insights dashboard (🤖)

`/insights` and its sub-pages, redrawn against design-system primitives.

| # | Item | Status |
|---|---|---|
| 5.1 | `src/components/charts/Line.tsx` · `Bar.tsx` · `Sparkline.tsx` — chart primitives using semantic positive/negative for direction | ☐ |
| 5.2 | `src/components/cards/RegimeCard.tsx` · `SectorCard.tsx` · `StressGauge.tsx` — dashboard cards consuming insight-engine data shapes | ☐ |
| 5.3 | Refactor `kite-dashboard/src/app/insights/page.tsx` to use design-system components | ☐ |
| 5.4 | Refactor `/insights/sectors`, `/insights/watchlists` to match | ☐ |
| 5.5 | Visual regression fixtures for each card + chart variant | ☐ |
| 5.6 | Impeccable `/audit` against /insights | ☐ |

**Risk tag:** 🟡 medium. Charts have real data dependencies; coordinate
with insight-engine response shapes.

---

## Phase 6 — Landing + signup (🤖)

| # | Item | Status |
|---|---|---|
| 6.1 | **Done 2026-06-05.** `src/components/marketing/`: `marketing-nav.tsx` (auth-aware — `useAuth()` swaps Sign in/Get-beta CTAs for Dashboard+`UserButton`; client comp since this Clerk build doesn't export `SignedIn`/`SignedOut`), `marketing-footer.tsx` (shared with /library), `portfolio-card.tsx` (fed by `lib/universes.ts` — never hand-typed). Hero + feature/portfolio/CTA sections inline in the landing page. **`TestimonialBlock` deliberately skipped** — no real testimonials, and fabricating social proof violates the no-made-up-data rule. | ☑ |
| 6.2 | **Done.** Public landing at `src/app/page.tsx` (mw-brand scope): hero ("Indian markets, the calm way."), three value features, the 4 client portfolios from `UNIVERSES`, lichen CTA band. Compliance-safe copy — "model portfolios", "private beta", "not personalised advice", no performance claims, disclaimer in footer. Static-prerendered (`○ /`). | ☑ |
| 6.3 | **Done.** `sign-up` + `sign-in` wrapped in the brand shell (wordmark + Fraunces heading + mist surface) with `lib/clerk-appearance.ts` theming the Clerk widget (lichen primary, Outfit, 8px radius). The widget correctly shows the real beta **allowlist gate** ("Access restricted"). | ☑ |
| 6.4 | **Done.** `/` added to `isPublicRoute`; the authenticated dashboard home moved `/` → `/dashboard` (`(dashboard)/dashboard/page.tsx`); sidebar + mobile-sidebar + error "home" links repointed to `/dashboard`; `ClerkProvider` `signIn/signUpFallbackRedirectUrl="/dashboard"` so post-auth lands on the dashboard, not the marketing page. Full `next build` green (32 routes). | ☑ |
| 6.5 | Impeccable `/polish landing` | 👤 ☐ |
| 6.6 | Visual regression + Lighthouse score check | 👤 ☐ |

**Risk tag:** 🟡 medium. Changed the auth-redirect behaviour: `/` is now the public landing; the dashboard home is `/dashboard`; post-auth redirect points there. Build green; founder to smoke-test the signed-in flow.

---

## Phase 7 — Main dashboard (🤖)

The authenticated app — portfolios, rebalances, account.

| # | Item | Status |
|---|---|---|
| 7.1 | `src/components/dashboard/` — TopNav, SidebarNav, PortfolioRow, RebalanceTable, AccountPanel | ☐ |
| 7.2 | Refactor `/account`, `/positions`, `/rebalance`, `/trades`, `/performance` | ☐ |
| 7.3 | Visual regression on each route | ☐ |

**Risk tag:** 🟡 medium. Largest surface; do last.

---

## Phase 8 — Migration cleanup + OVERVIEW.html (🤖)

| # | Item | Status |
|---|---|---|
| 8.1 | Audit `kite-dashboard/src/**` for hard-coded hex / px / font-family — replace with design-system tokens | ☐ |
| 8.2 | Audit `finance-content-os/scripts/` for any remaining V1 Remotion asset paths — switch to design-system render CLI | ☐ |
| 8.3 | Write `tasks/design_system/OVERVIEW.html` — visual map parallel to the existing OVERVIEWs for content_bridge and content_redesign | ☐ |
| 8.4 | `_meta.yml` → `status: shipped`, fill `related_commits`, fill `sibling_commits` | ☐ |
| 8.5 | `RESULTS.md` — what was shipped vs planned, deferred items, verification log | ☐ |
| 8.6 | Decide on private npm registry — GitHub Packages vs self-hosted Verdaccio | 👤 ☐ |
| 8.7 | Migrate consumers from `file:` deps to registry version | ☐ |

**Risk tag:** 🟢 low. Mostly bookkeeping.

---

## Cross-cutting notes

- **Impeccable usage:** invoke `/impeccable shape` before designing a
  new surface, `/audit` after building it, `/polish` before merging.
  The Impeccable commands embed our DESIGN.md as their reference.
- **TDD discipline:** every primitive lands with a visual regression
  fixture and a token contract test before merging. No exceptions.
  Phase 2 establishes the harness; Phases 3-7 must populate it.
- **Consumer wiring is `file:` first.** Don't bother with private npm
  registry until Phase 8.6.
- **Commit prefix:** `design_system: <phase> — <summary>` in the
  marketworks-design repo; `design_system: <phase> — <summary>` in
  consumer repos.
- **One pixel of un-tokenised hex in production code is a regression.**
  Phase 8.1 audits this; subsequent contributions are expected to
  honour it without re-audit.
