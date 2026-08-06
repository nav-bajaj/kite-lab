# design_studies — plan

## Why

The beta shipped on the redesign branch's visual system (six palettes,
layered marketing surface), but the 2026-08-06 audit (AUDIT.md, 13/20)
found the marketing surfaces carry recognizable AI-generated section
grammar (eyebrow scaffold, numbered markers, three-card icon grid,
em-dash copy), the dashboard has drifted off the token system (dual P&L
colors, stale chart hexes, four card implementations), and the tested
primitives in `@marketworks/design` are not actually consumed by the
site. Founder wants: detect and eliminate AI-slop patterns, develop a
better UI (aesthetics + functionality), and build a modular primitive
kit that serves the website, social posts/videos, and research reports.

## Outcome

1. **GUIDE.md** — the anti-slop contract for all Marketworks surfaces
   (shipped with this plan; living doc).
2. **Preference-driven direction** — iterative study loops seeded with
   the founder's Mobbin screenshots; preferences codified in
   PREFERENCES.md; direction sign-off per surface before build.
3. **Primitive kit** — `@marketworks/design` consumed by the dashboard;
   extended with Surface/Card/ChartFrame/Overlay/Background/StatCallout/
   ReportPage primitives; one render pipeline for web, social, reports.
4. **Re-skinned surfaces** — homepage first, then portfolio cards,
   dashboard data views, report templates. Audit re-run ≥17/20.

## Scope boundary

- In: kite-dashboard UI, marketworks-design package, social/report
  render templates, marketing copy where it's a slop tell.
- Out: backend/API changes (except token plumbing), portfolio logic,
  auth flows. CSP fix (AUDIT P0) ships separately with a register row.

## Critical files

- `tasks/design_studies/AUDIT.md` + `evidence/` — findings + screenshots
- `tasks/design_studies/GUIDE.md` — the anti-slop contract
- `~/marketworks-design/DESIGN.md` — brand contract (upstream truth)
- `kite-dashboard/src/app/globals.css`, `src/styles/marketworks/*` —
  vendored token layer
- `~/marketworks-design/src/{primitives,charts,templates}/` — the kit

## Working agreement

Branch `design_studies` (off `beta_gtm_mvp`, worktree
`.worktrees/design_studies`). Visual-validate before building: no
component code before direction sign-off on rendered variants.
`beta_gtm_mvp_redesign` is retired (fully merged, kept for history).
