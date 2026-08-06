# Design audit — marketworks.in (beta_gtm_mvp), 2026-08-06

Method: Impeccable v3.5 audit flow. Deterministic detector over the
`beta_gtm_mvp` dashboard source (`evidence/detect_beta.json`), live-site
screenshots at 1440px and 390px (`evidence/*.png`), full component survey
of `kite-dashboard` + `marketworks-design`, checked against DESIGN.md
(the brand contract) and the Impeccable register references.

## Audit health score

| # | Dimension | Score | Key finding |
|---|-----------|-------|-------------|
| 1 | Accessibility | 3 | Palette WCAG bars are CI-enforced; ad-hoc `text-[10px]`–`text-[13px]` sizes and raw Tailwind colors bypass the audited system |
| 2 | Performance | 3 | Desktop homepage ships an empty panel (scroll-gated reveal that never fires headless; needs on-device verification); CSP violation on every homepage load |
| 3 | Responsive | 3 | 390px holds together; hero flourish degrades gracefully; minor density issues in tables |
| 4 | Theming | 2 | Strong token system, weak adoption: dual P&L color systems, stale hexes, radius/shadow/type sprawl, design package not consumed |
| 5 | Anti-patterns | 2 | Eyebrow scaffold on every section, numbered markers, 3-card icon grid, pastel AI illustrations, em-dash copy cadence |
| **Total** | | **13/20** | **Acceptable — significant work needed** |

## Anti-patterns verdict

**Fail (marketing surfaces), pass-with-notes (dashboard).** A fluent
reader would clock the homepage as AI-assisted: tracked uppercase
eyebrows above *every* section (`PRIVATE BETA`, `WELCOME TO THE BETA`,
`THE RESEARCH BEHIND IT`, `THE PORTFOLIOS`), 01/02/03 numbered markers,
the canonical three-card illustration grid, and em-dash-saturated copy
with aphoristic cadence ("Process over prediction. Momentum isn't a
hunch. It's a factor."). The layered inset-panel system, the designed
Midnight dark mode, and the absence of gradients/glassmorphism are
genuine escapes — the bones are good, the section grammar is the tell.

## Findings

### P0 — fix immediately

- **CSP violation on every homepage load.** `connect-src` is missing
  `https://accounts.marketworks.in`; Clerk's connection to
  `accounts.marketworks.in/sign-in` is blocked (see console log,
  captured 2026-08-06). Functional risk for the sign-in flow.
  *Constraint: widening CSP requires a risk-register row first
  (R-006/R-007 closure). File the row, then add the origin.*
- **Empty white panel on desktop homepage** beside "Three ways to
  follow momentum." Likely a scroll-gated reveal whose default state is
  invisible — the exact anti-pattern Impeccable bans (content visibility
  gated on a class-triggered transition). Verify on a real device; make
  the default state visible, let motion enhance it.

### P1 — fix before the redesign ships

- **Dual P&L color systems.** `getPnLClass()` (`src/lib/utils.ts:85`)
  returns raw `text-green-600`/`text-red-600`; ~35 usages across trades,
  positions, rebalance. `insights/ui.tsx` correctly uses
  `--positive`/`--negative`. DESIGN.md §2.3 forbids raw green/red for
  financial direction. Route everything through the semantic tokens.
- **`allocation-chart.tsx:12-23`** hardcodes 12 hexes including stale
  lichen `#14715F` (pre-vibrance). Won't re-theme across the six
  palettes. Use `--chart-series-*` / accent-rotation tokens.
- **Eyebrow scaffold + numbered markers** as universal section grammar
  on marketing + library (absolute ban: one deliberate kicker is voice,
  an eyebrow on every section is AI grammar). Redesign section cadence.
- **Three-card icon grid** ("How it works") with pastel 3D illustrations
  — the canonical SaaS grid DESIGN.md §9 explicitly bans, and the
  illustrations read as generic AI-generated 3D (already flagged as
  "dated" in prior feedback). Replace with real data-driven imagery —
  the brand's stated identity is its data visualisation.
- **Marketing copy cadence.** 20 em dashes in `hero-flow.tsx` alone;
  visible on-page ("— without watching it all day", "— a 'rebalance' —").
  Aphoristic rebuttal-shaped sentences recur. Rewrite per the copy rules
  in GUIDE.md.

### P2 — next pass

- **Component sprawl:** four parallel card implementations (shadcn
  `Card`, `MarketingCard`, `insights/ui.tsx` constructs, `PieceCard`);
  Eyebrow re-implemented twice; radius spread across `md/lg/xl/2xl/3xl/
  card/panel`; token shadows (~16 usages) losing to default Tailwind
  shadows (~25); ad-hoc `text-[10px]`–`text-[15px]` sizes in tables/nav.
- **`@marketworks/design` not consumed.** The dashboard vendors only two
  CSS sheets; the tested primitives (Text/Heading/Eyebrow/Box/Stack),
  charts, and templates are ignored. This is the root cause of the
  drift above — see GUIDE.md §6 for the consumption plan.
- **Raw `bg-amber-*` warning colors** in `actionable-trades.tsx:251`
  instead of `--warning`.
- **Clerk appearance** (`clerk-appearance.ts`) styled with literal hexes
  — re-derive from tokens so auth screens follow the palette system.

### Noted, not defects

- **Single font family (Outfit) on dashboard surfaces** — the detector
  flags it, but the product register explicitly permits one well-tuned
  sans for app UI. Marketing/library correctly carry Fraunces. No action.
- **Fraunces + Outfit are on Impeccable v3.5's reflex-reject list.**
  Identity-preservation wins for existing surfaces (the skill's own
  rule), but this initiative should *deliberately* re-confirm or evolve
  the pairing rather than inherit it silently. Study item, not a bug.

## Positive findings

- The layered marketing model (§2.5): inset rounded panels on a
  continuous tinted base, ink-tinted elevation — genuinely distinctive.
- Six-palette system with CI-enforced WCAG bars; Midnight is designed,
  not inverted.
- Semantic/identity color separation (muted forest/clay for P&L, never
  brand green) — where it's actually used.
- No gradients, no glassmorphism, no hero-metric template, no bounce.
- Mobile layout survives 390px without horizontal scroll.

## Recommended next commands

1. **[P1] `/impeccable shape`** — the homepage section-grammar redesign
   (replace eyebrow scaffold + card grid with data-led sections).
2. **[P1] `/impeccable extract`** — consolidate the four card systems +
   P&L colors into consumed primitives (GUIDE.md §6 roadmap).
3. **[P2] `/impeccable clarify`** — copy pass: em dashes, aphorisms.
4. **[P2] `/impeccable polish`** — final pass after the above.
