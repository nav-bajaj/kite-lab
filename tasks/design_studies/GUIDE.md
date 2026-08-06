# The Marketworks anti-slop guide

How we detect AI-generated design patterns, eliminate them, and build a
better UI — aesthetically and functionally — across the website, social
assets, and research reports. Derived from the Impeccable skill's
references, DESIGN.md (the brand contract), and the 2026-08-06 audit of
the live site (AUDIT.md). This is a living doc for the `design_studies`
initiative.

---

## 1 · What "AI slop" actually is

Not any single element — it's **reflex**. A generated design converges
on the statistically average answer for its category. Two tiers:

- **First-order reflex:** the theme/palette is guessable from the
  category alone. "Fintech → navy, trust-blue, gradient CTA."
- **Second-order reflex:** the *escape* is guessable. "Fintech that's
  not navy → editorial serif + mono labels + monochrome restraint."
  This is where Marketworks lives: our cool-mist + Fraunces editorial
  lane was chosen to escape tier one, and parts of it have since become
  the saturated lane itself.

**The test we run on every surface:** could a fluent design reader say
"AI made that" without hesitation? For product surfaces (dashboard) the
bar is different: would a user fluent in Linear/Stripe/Zerodha *trust*
this screen, or pause at subtly-off components?

## 2 · The ban list (calibrated to Marketworks)

Hard bans — rewrite the element if you're about to produce one:

| Ban | Why | What to do instead |
|---|---|---|
| Tracked-uppercase eyebrow above **every** section | The single most saturated AI scaffold of 2023–26; we currently do this on every marketing/library section | One named kicker max per page as a deliberate system, or a different cadence entirely (see §5) |
| Numbered section markers (01/02/03) as default scaffolding | The eyebrow trope one tier deeper; our "How it works" uses it | Numbers only when the content IS a real sequence and order carries information |
| Identical card grids (icon + heading + 2 lines, ×3) | Canonical SaaS landing; DESIGN.md §9 bans it explicitly | Data-led sections: real charts, real portfolio rows, asymmetric composition |
| Side-stripe borders (`border-left` accent > 1px) | Never intentional | Full borders, background washes, leading numbers |
| Gradient text, purple-blue gradients, glassmorphism | Linear/SaaS tell; already banned in DESIGN.md | Solid brand color; emphasis via weight/size |
| Hero-metric template (big number, small label, stat row) | "Stat soup" — numbers without stories | Numbers embedded in a narrative frame |
| Bounce/spring easing, animated counters, auto-rotating heroes | Editorial reads still | ease-out expo, motion conveys state only |
| Reveal animations that gate content visibility | Ships blank sections in headless/slow contexts (we have one live, see AUDIT P0) | Default state visible; motion enhances |
| Pure `#FFFFFF` surfaces / warm-cream body bg | Cream is the saturated 2026 default; pure white is contract-banned | Mist-tinted near-whites per §2.5 of DESIGN.md |
| Raw green/red for P&L | Confuses brand identity with meaning; finfluencer-adjacent | `--positive` / `--negative` semantic tokens, always |

Copy bans (the writing tells are as loud as the visual ones):

- **Em dashes.** Zero in UI copy and marketing prose. We ship 20+ on the
  homepage today. Commas, colons, periods, parentheses.
- **Aphoristic rebuttal cadence.** "X isn't a hunch. It's a factor." Once
  per page is voice; three times is AI grammar. We're over the line.
- **Buzzword family:** streamline / empower / seamless / supercharge /
  world-class / cutting-edge. Specific nouns, literal verbs.
- **Button labels are verb + object.** "Get beta access" passes. "OK",
  "Learn more" fail.

## 3 · What already works (protect these)

The audit found genuine, distinctive systems. The redesign evolves them,
it does not restart:

1. **Layered marketing surface** — inset rounded panels floating on a
   continuous tinted base, ink-tinted shadows. Not a template look.
2. **Six-palette system** with CI-enforced contrast and accent rotation
   that encodes structure (sibling identity), never decoration.
3. **Midnight** — a designed dark theme, not an inversion.
4. **Identity vs meaning separation** — lichen/signal-green for brand,
   muted forest/clay for direction. (Enforce it where the code drifts.)
5. **The data-as-identity principle** — "show the work, not just type."
   This is our structural escape from the editorial-typographic slop
   lane: slop pages have no real data; we have live portfolios, real
   equity curves, real rebalance history. Every surface that replaces a
   decorative illustration with a real chart moves us further from the
   reflex band than any font choice can.

## 4 · Open study items (to settle deliberately, not by reflex)

- **Fraunces + Outfit** are now on Impeccable's reflex-reject list.
  Identity-preservation is a valid answer; silent inheritance is not.
  Study: does the pairing still read distinctive against 2026's
  editorial-lane saturation, or do we evolve the display face? Decide
  with rendered comparisons, not in the abstract.
- **The pastel 3D illustration set** (homepage "How it works") reads
  AI-generated and was already flagged as dated. Candidate replacements:
  real charts, halftone/grain treatments from the existing system, or a
  commissioned line-illustration language per DESIGN.md §7.
- **Section cadence for marketing pages** once eyebrows are demoted:
  candidates include oversized serial headings, data-strip dividers,
  color-block panel alternation (the inset-panel system already supports
  this). To be explored in the studies phase with Mobbin references.

## 5 · The iterative study loop (how we work)

Confirmed practice from prior work: **visual-validate before building.**
No component code until direction sign-off.

```
1. REFERENCE   You drop Mobbin screenshots (or names of apps/screens you
               like) into tasks/design_studies/references/ or paste them
               in chat. Mobbin MCP search is also wired into this
               environment, so "find me screens like X" works too.
2. EXTRACT     For each reference I write down WHY it works (hierarchy,
               density, color strategy, cadence) — preferences become
               named principles in PREFERENCES.md, not vibes.
3. STUDY      I produce 2-3 rendered variants per surface (Pencil mock
               or Ladle story in marketworks-design), each tagged with
               which principles it commits to. Slop-check each against
               §2 before showing you.
4. PICK        You react ("A's hierarchy, B's density"). I fold the
               picks back into PREFERENCES.md. Repeat 3-4 until a
               surface locks.
5. BUILD       Only then: primitives + pages, TDD'd against the design
               contract (visual regression in marketworks-design CI).
```

Each loop is small: one surface (homepage hero, portfolio card, chart
frame) per iteration, not the whole site.

## 6 · Primitives roadmap (the modular kit)

Goal: one set of primitives serving **web pages, social assets, and
research reports**. The foundation already exists in
`@marketworks/design` — the problem is the dashboard ignores it
(vendors 2 CSS files, re-implements everything else). Plan:

**Phase A — consume what exists.** Wire `@marketworks/design` into
`kite-dashboard` as a real dependency (or a synced source tree if the
private-package plumbing fights Vercel). Replace the four parallel card
implementations and the duplicate Eyebrows with the package primitives.
Kill `getPnLClass()` raw greens; route through semantic tokens.

**Phase B — extend the kit** (new primitives, designed in the study
loop, built in marketworks-design with stories + visual tests):

| Primitive | Serves | Notes |
|---|---|---|
| `Surface` / `SectionPanel` | web + reports | The §2.5 inset-panel model, generalized: base / mist / tint / deep variants |
| `Card` (one system, variants) | all three | Replaces shadcn Card + MarketingCard + PieceCard + insights constructs; radius/shadow from tokens only |
| `ChartFrame` + chart set | all three | Recharts (web) and the package's SVG charts (social/report) share `--chart-series-*` + accent rotation; one visual language |
| `Overlay` system | web | Dialog / sheet / popover / tooltip on a semantic z-scale, one motion spec (200ms ease-out, reduced-motion honored) |
| `Background` textures | all three | Quant grid, halftone, grain — today they're one-off CSS in globals.css; tokenize as composable layers |
| `StatCallout`, `DataStrip` | all three | The anti-"stat soup" number-with-story unit; doubles as social StatCalloutSlide and report pull-stat |
| `ReportPage` templates | reports | A4/PDF-ratio render targets alongside the 1080×1080/1920 social ones, through the same render-asset pipeline |

**Phase C — re-skin surfaces** using the kit, one surface per study
loop: homepage section grammar first (biggest slop debt), then portfolio
cards, then dashboard data views, then report templates.

Render pipeline note: `scripts/render-asset.ts` (Playwright against
Ladle) already turns templates into PNGs for social; Phase B extends the
same pipeline to report pages, so "website component" and "report
figure" are the same code with different render targets.

## 7 · Enforcement

- Impeccable detector run over changed files before each merge into the
  design branch (`node .claude/skills/impeccable/scripts/detect.mjs`).
- DESIGN.md contract tests + visual regression in marketworks-design CI
  stay the source of truth; new primitives land with stories + tests.
- Copy passes through the em-dash/aphorism check (§2) before shipping.
- CSP or CORS changes require a risk-register row first (unchanged).
