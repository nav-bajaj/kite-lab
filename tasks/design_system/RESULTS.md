# design_system — RESULTS

Close-out record for the design-system initiative. Companion to
`PLAN.md` (intent), `TASKS.md` (phased checklist), `_meta.yml`
(metadata). Written 2026-06-05.

## One-line outcome

A canonical brand design system (`~/marketworks-design`, package
`@marketworks/design`) plus its application across every Marketworks
web surface — social asset templates, `/library`, `/insights`, the
public landing + auth, and the authenticated app — all on one token
contract, light + dark.

## What shipped vs planned

| Surface (planned in `_meta.surfaces`) | Status |
|---|---|
| Instagram assets (carousel/quote/chart/CTA templates + headless render CLI) | ✅ shipped (Phase 3 / 3.5) |
| Library reading page `/library`, `/library/[slug]` | ✅ shipped (Phase 4) |
| Insights dashboard `/insights` + sub-pages (sectors, watchlists, learn) | ✅ shipped (Phase 5 / 5.4) |
| Landing page `/` + signup/sign-in | ✅ shipped (Phase 6) |
| Main authenticated app (dashboard, positions, performance, …) | ✅ shipped (Phase 7) |
| Token/hex audit + migration cleanup | ✅ shipped (Phase 8.1, this session) |

**Mechanism that made it deployable:** the dashboard does **not** take a
`file:` or package dependency on `~/marketworks-design` (that wouldn't
resolve on Vercel). Instead the brand token *values* are mirrored into
three scopes in `kite-dashboard/src/app/globals.css`:

- `.mw-brand` — light-locked marketing/library surfaces
- `.mw-app` — light + dark authenticated app (with `.dark .mw-app` inversion)

The `@marketworks/design` repo stays the canonical source; the dashboard
is self-contained. `~/marketworks-design` is referenced only in code
*comments* for provenance — no imports. So `kite-dashboard` is
Vercel-ready as-is.

## Phase 8 — what was done this session

- **8.1 token audit** — swept `kite-dashboard/src/**` for hard-coded
  hex / `hsl(var())` / font-family.
  - Fixed: chart components used raw Tailwind hex and the now-broken
    `hsl(var(--background))` pattern (brand tokens are hex, not HSL
    triplets, so `hsl(#ECF3EF)` was invalid). Retokened
    `equity-curve` (→ `--chart-1`, `--muted-foreground`),
    `drawdown-chart` (→ `--negative`, `--border`), and tooltip
    `contentStyle` (→ `--popover`/`--border`). Verified `var()`
    resolves in SVG `fill`/`stroke` attributes (browser test) so the
    chart colors are theme-adaptive.
  - `allocation-chart` — replaced the 24-colour arbitrary Tailwind
    palette with a 12-colour brand-derived palette (lichen / signal /
    slate / violet / ochre + tints), static hex (a 25-slice categorical
    scale needs more steps than the five themeable `--chart-*` tokens).
  - **Accepted exceptions (not regressions):** `global-error.tsx`
    (inline hex required — it renders when React/CSS is unavailable);
    `clerk-appearance.ts` (Clerk's appearance API takes raw colour
    strings; values already match brand).
- **8.7 `file:` dep migration** — moot. `package.json` is already
  self-contained (verified: no `file:`/`@marketworks` deps, no imports).
- **8.3 / 8.4 / 8.5** — OVERVIEW.html, `_meta.yml → shipped`, this file.

## Deferred (logged, not done)

| Item | Why deferred |
|---|---|
| Visual-regression fixtures for `/library` + app surfaces (5.5 / 7.3) | Harness exists (Phase 2); populating fixtures for every page deferred to a follow-up. |
| Impeccable `/audit` passes on library/insights/landing (4.6 / 5.6 / 6.5) | Built surfaces validated visually + against the Pencil guide; formal Impeccable audit deferred. |
| npm registry decision (8.6) | **Non-blocking** — only needed if the dashboard ever *imports* `@marketworks/design` instead of mirroring values. Founder decision when/if that's wanted. |
| Allocation pie dark-mode adaptation | Static brand hex chosen for the 25-slice categorical scale; mid-tones picked to read on both card backgrounds. Themeable version deferred. |

## 🚩 Founder action items BEFORE beta viewers

These are outside the design system but gate "ready for viewers":

1. **`/privacy` legal copy** — page body is accurate, but `Last updated`,
   the contact email, and a visible "this page is a placeholder" line are
   stubs. Founder is writing the finalized legal text. (`/terms`,
   `/disclaimer` are real.)
2. **Copy review** — all landing / library / insights copy is real (no
   lorem, no fabricated stats) but is Claude's draft. Read + edit for
   voice/accuracy before viewers.
3. **Prod `/insights` returns 500** — the insight engine is file-based
   (reads local CSVs); those data files are **not** on Railway, so
   `GET /api/insights/reading` 500s in production ("No objects to
   concatenate"). Must be fixed before `/insights` is exposed to beta
   users — either upload the insights data to Railway or have the daily
   pipeline produce it there.
4. **Library has 1 piece, 0 social assets wired** — `rupee_weakness_roundup`
   is the only live piece and its `assets[]` is empty though 9 rendered
   PNGs exist. The CTA→library gate wants 3+ pieces before driving
   traffic. (Content track, chosen for after Phase 8 / shipping.)
5. **`trades-table.tsx`** hardcodes universe `nse500` (`// TODO: get from
   context`) — admin-only page, minor.

## Verification log

- `~/marketworks-design`: 121 component/token tests green; brand guide
  validated against the Pencil `.pen` (9 boards bound to real tokens).
- Serif rendering bug (stale Turbopack CSS from a disk-full `ENOSPC`
  event) diagnosed and fixed; confirmed in a headless browser that
  `font-serif` computes to Fraunces.
- Local end-to-end this session: frontend `:3100` + backend `:8000`,
  `/api/insights/reading` 200 with live data (regime DRIFT, stress
  62/89th pctile), portfolio holdings 200 (25 rows).
- kite-lab design_system commits: `d89c5eb` … `72e3aef` (17 commits)
  + the Phase 8 commit. Not yet merged to `main`.
