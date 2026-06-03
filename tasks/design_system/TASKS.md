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
| 1.16 | Run Impeccable's `init` flow once to align it with our DESIGN.md | 👤 ☐ |

**Risk tag:** 🟢 low. Scaffolding, no runtime impact.

---

## Phase 2 — Primitives + reference site (🤖)

Foundational React components every other component is built on.

| # | Item | Status |
|---|---|---|
| 2.1 | Styling layer chosen: **vanilla CSS variables + scoped `mw-*` class names**. One stylesheet (`src/styles.css`) ships Google Fonts import + :root variables + class definitions; consumers `import "@marketworks/design/styles.css"` once. No build step. | ☑ |
| 2.2 | `src/primitives/Text.tsx` — size + color + tabular props; refuses heading sizes (that's Heading's job) | ☑ |
| 2.3 | `src/primitives/Heading.tsx` — serif h1-h6 with semantic level vs visual size independence | ☑ |
| 2.4 | `src/primitives/Box.tsx` · `src/primitives/Stack.tsx` — token-driven padding, container, gap, alignment | ☑ |
| 2.5 | `src/primitives/Eyebrow.tsx` — uppercase label, 12px / 0.14em tracking / Outfit semibold | ☑ |
| 2.6 | `tokens/css.ts` shipped — `buildRootVariables()` + `buildTypeClasses()` programmatic generators. `src/styles.css` is the rendered output committed to git. | ☑ |
| 2.7 | Visual reference site scaffold — **needs founder call on tooling**: Ladle (lightweight, designed for this), custom Vite, or minimal Next.js. Recommendation: Ladle. | ☐ |
| 2.8 | First Playwright visual fixture — depends on 2.7 (needs a rendered surface to screenshot) | ☐ |
| 2.9 | Token contract test suite — `tests/contract/tokens.spec.ts`, 12 tests passing in 476ms. Verifies brand + semantic palette values, type scale has the 11 locked tokens, weight count rule (max 3), spacing scale, styles.css :root block matches token source. **Token drift now fails the build.** | ☑ |
| 2.10 | Impeccable `/audit` — pending 2.7 (nothing to audit without a rendered surface) | ☐ |

**Risk tag:** 🟡 medium. Styling-layer choice is sticky; pick once.

---

## Phase 3 — V1 social asset templates (🤖)

CarouselSlide, Thumbnail, ReelOverlay + headless render CLI for
finance-content-os to call.

| # | Item | Status |
|---|---|---|
| 3.1 | `src/templates/CarouselSlide.tsx` — 1080×1080 IG carousel slide. Props: headline, body, slide number, accent slot. Multiple variants (cover, body, CTA). | ☐ |
| 3.2 | `src/templates/Thumbnail.tsx` — 1080×1080 / 1080×1920 thumbnail. Props: headline, eyebrow, accent number. | ☐ |
| 3.3 | `src/templates/ReelOverlay.tsx` — 1080×1920 reel lower-third + stat callout overlays | ☐ |
| 3.4 | `scripts/render-asset.ts` — CLI: takes a template name + JSON props → headless Playwright renders → PNG. Used by finance-content-os. | ☐ |
| 3.5 | Visual regression fixtures for each template in `tests/visual/` | ☐ |
| 3.6 | Wire into finance-content-os: `scripts/render-social-asset.py` that reads a content pack and calls `render-asset.ts` for each template | ☐ |
| 3.7 | Render the live `rupee_weakness_roundup` pack through the new template pipeline; replace the placeholder/missing assets in `published/assets/` | ☐ |

**Risk tag:** 🟡 medium. CLI complexity for headless rendering.

---

## Phase 4 — V1 library reading pages (🤖)

`/library` + `/library/[slug]` in kite-dashboard, rebuilt using
design-system components.

| # | Item | Status |
|---|---|---|
| 4.1 | `src/components/Article.tsx` · `PieceHeader.tsx` · `Hook.tsx` · `BodyParagraph.tsx` · `Takeaway.tsx` · `CTA.tsx` — content-pack-shaped reading components | ☐ |
| 4.2 | Add `@marketworks/design` as a `file:` dep in `kite-dashboard/package.json` | ☐ |
| 4.3 | Refactor `kite-dashboard/src/app/library/page.tsx` to use design-system components | ☐ |
| 4.4 | Refactor `kite-dashboard/src/app/library/[slug]/page.tsx` to use design-system components | ☐ |
| 4.5 | Run Impeccable `/audit` against /library locally | ☐ |
| 4.6 | Playwright visual regression on /library pages | ☐ |
| 4.7 | Re-deploy preview branch and visual-check `/library/rupee_weakness_roundup` | 👤 ☐ |

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
| 6.1 | `src/components/Hero.tsx` · `FeatureRow.tsx` · `PortfolioCard.tsx` · `TestimonialBlock.tsx` · `Footer.tsx` | ☐ |
| 6.2 | New `kite-dashboard/src/app/(landing)/page.tsx` — public landing page replacing the current Clerk-redirect behaviour | ☐ |
| 6.3 | `kite-dashboard/src/app/sign-up/page.tsx` refactor to design-system look | ☐ |
| 6.4 | Update `middleware.ts` to make `/` public (replacing the current "/" → /sign-in redirect) | ☐ |
| 6.5 | Impeccable `/polish landing` | ☐ |
| 6.6 | Visual regression + Lighthouse score check | ☐ |

**Risk tag:** 🟡 medium. Changes the auth-redirect behaviour for unauthenticated visitors.

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
