# content_bridge — wire MarketWorks into the content + marketing surface

## Why this exists

Marketworks (kite-lab) has the substance: 4 live portfolios, a daily
pipeline, the insight engine with state-of-market / breadth / sector /
calendar / cross-asset modules, and the daily quant note. None of this
currently reaches a public audience.

`~/finance-content-os` is a separate repo with the editorial engine: a
7-stage content pipeline, 11 schemas, 10 skills, 2 subagents, Remotion
compositions, and an established brand voice — but it has been dormant
~6 weeks and has zero connection to the platform's actual data. Both
finished content packs in that repo use unverified numerical claims;
`data/memory/lessons.md` flags this as the standing risk.

The next 8–12 weeks of solo-founder time go into distribution + GTM,
not more product. The unlock for that is the same in either direction:
**ground the content engine in verified MarketWorks outputs, then
surface the result on marketworks.in.** This task builds the two thin
bridges that make that possible.

## Outcome

One real piece of content — sourced from an actual kite-lab artifact
(daily quant note or portfolio rebalance), run through the v2 pipeline
in finance-content-os, with verified numbers and a final founder gate —
live at `marketworks.in/library/<slug>` in a public, SEO-indexable
route. End-to-end provable: kite-lab publish → content-os import →
pipeline → content-os publish → kite-dashboard build → live URL.

Once this loop works once, every subsequent piece is a repeat of the
same flow with no new infrastructure.

## Strategic frame

| Repo | Role | Knows about |
|---|---|---|
| `kite-lab` (kite-api + scripts) | The proof — portfolios, data, insights | nothing about content |
| `finance-content-os` | The editorial engine — voice, schemas, design | kite-lab only as a configurable input path |
| `kite-lab/kite-dashboard` | The marketing surface — public routes for content | finance-content-os only as a build-time data source |

Three pieces, two thin file-based contracts, zero build-time code
dependencies between them. Each repo can be refactored independently
as long as its contract output stays stable.

## Architecture

### Bridge 1 — kite-lab → finance-content-os (signal export)

```
kite-lab/
  scripts/publish_signal.py            ← publisher (new)
  data/published/
    signals/
      2026-05-31_daily_note.json       ← Signal-shaped JSON
      2026-05-31_tl25_rebalance.json
    schema/
      signal.schema.json               ← copy of canonical schema
    MANIFEST.json                      ← index for importers

finance-content-os/
  bridge/import_from_marketworks.py    ← importer (new)
  schemas/signal.schema.json           ← canonical source of truth
  data/content_packs/{slug}/signal.json
```

**Contract:** any JSON file in `kite-lab/data/published/signals/` that
validates against `signal.schema.json` is fair game for the importer.
Filenames follow `{YYYY-MM-DD}_{source}.json`.

**Sources for v1:**
1. Daily quant note (postclose mode) → 1 signal/day
2. Portfolio rebalance event → 1 signal per rebalance per portfolio
3. (Deferred) Validity study result, anniversary content, named
   watchlist update

### Bridge 2 — finance-content-os → kite-dashboard (web publish)

```
finance-content-os/
  scripts/publish.py                   ← publisher (new)
  published/
    pieces/{slug}.json                 ← web-ready normalized data
    courses/{slug}.json                ← (Phase 2 — courses, later)
    assets/{slug}/*.png|mp4            ← rendered assets
    manifest.json                      ← website index

kite-lab/kite-dashboard/
  src/marketing-content/               ← synced copy (committed)
    pieces/...
    assets/...
    manifest.json
  src/app/library/
    page.tsx                           ← /library — index
    [slug]/page.tsx                    ← /library/<slug> — piece
```

**Contract:** finance-content-os/published/ is the canonical record.
The publish step ALSO writes a synced copy into
`kite-lab/kite-dashboard/src/marketing-content/` so the Next.js build
can read directly from the dashboard repo without git-submodules or
CI fetches. Synchronisation strategy is part of Phase 0 decisions
(see below).

## Scope boundary

**In scope this task:**

- Both publishers + the importer
- One real signal + one finished content pack + one live URL
- Public routes: `/library` and `/library/[slug]` only
- Light styling — must look brand-appropriate, not necessarily polished

**Out of scope this task (later, separate tasks):**

- Courses infrastructure (`Course` / `Lesson` schemas) — defer until ≥5
  individual pieces are in market
- Paid course gating, Clerk role extension for course access
- Automated deploys (Vercel hooks) on content repo push — manual
  redeploy is fine for v1
- Asset migration to Vercel Blob — committed PNGs are fine at this scale
- Multi-signal-source publisher (calendar, validity, anniversary,
  watchlist) — daily note + rebalance only for v1
- WhatsApp / email distribution — content goes to the web first
- Performance feedback loop wiring (the analyze-performance skill
  exists but won't fire until pieces have analytics attached)
- SEO polish, Open Graph cards, Lighthouse pass — separate cleanup task

## Critical files

### kite-lab
| Path | Role |
|---|---|
| `kite-api/app/insights/notes/note_assembler.py` | Source of daily quant notes (`NoteBundle`) |
| `kite-api/app/insights/reading.py` | `MarketReading` — input to note assembly + regime/stress numbers |
| `scripts/generate_quant_note.py` | Existing CLI; the publisher reuses its mode-handling pattern |
| `scripts/generate_rebalance_trade_report.py` | Source of rebalance changes — publisher emits Signal from these |
| `scripts/run_daily_pipeline.py` | The orchestrator; `publish_signal` may eventually slot in as the last step |
| `data/published/signals/` | New directory — bridge contract |
| `kite-dashboard/src/app/library/` | New public routes — bridge consumer |
| `kite-dashboard/src/marketing-content/` | New directory — synced content from finance-content-os |
| `kite-dashboard/next.config.ts` | May need image domain config if assets reference URLs |

### finance-content-os
| Path | Role |
|---|---|
| `schemas/signal.schema.json` | Canonical schema; copy to kite-lab |
| `bridge/import_from_marketworks.py` | New — reads kite-lab published signals, lifts into a content pack |
| `scripts/publish.py` | New — normalises a finished pack for the web, syncs to kite-dashboard |
| `data/content_packs/{slug}/` | Standard pipeline output |
| `published/` | New — canonical record of what went out |
| `data/memory/topic_index.md` | Append-only log; importer appends an entry per signal |

## Phase 0 — decisions to lock before any code

These are surfaced first because they shape every file path below.
Each has a recommendation but is open for the founder to redirect.

| # | Decision | Recommendation | Rationale |
|---|---|---|---|
| 0.1 | Top-level marketing route name | `/library` | "Learn" already taken by insight engine's `/insights/learn/<topic>` explainers; "library" reads premium + educational; cleanly accommodates future courses at `/library/courses` |
| 0.2 | Bridge-2 sync strategy | **Option A: Sync at publish.** `scripts/publish.py` writes BOTH `finance-content-os/published/` (canonical) AND `kite-lab/kite-dashboard/src/marketing-content/` (renderable). One push per repo per content release. | Zero new infra. Vercel deploys when kite-lab pushes. Migrate to Option B (content repo deployed separately, dashboard fetches over HTTP) only when publish cadence exceeds ~daily. |
| 0.3 | First signal to test the loop | Most recent **postclose daily quant note** | Highest information density per artifact. Already has chart + commentary + regime/stress numbers. Rebalance bridge is simpler structurally but we currently aren't in a rebalance week. |
| 0.4 | Schema source of truth | `finance-content-os/schemas/signal.schema.json`; kite-lab keeps a copy at `data/published/schema/signal.schema.json`. Hash-checked on publisher startup. | Minor duplication, but eliminates cross-repo dependency. Update flow: edit in content repo, copy over, both repos validate independently. |
| 0.5 | Branch strategy | Already on `bridge` branch in kite-lab. Use a matching `content-bridge` branch in finance-content-os. Merge each with `--no-ff`. | Mirrors the kite-lab convention of `git merge --no-ff` so the merge commit summarises the initiative. |

If any of these change, the PLAN gets updated before TASKS execution
continues.

## Risk register additions (none required for v1)

None of this introduces new auth, network, or storage surface area.
`/library` and `/library/[slug]` are public Next.js routes serving
build-time-rendered content; no new API endpoints, no new external
calls at request time. No risk register row needed unless we add
runtime fetching (Phase 7).

## Verification at close

- [ ] One signal file exists at `kite-lab/data/published/signals/<date>_<source>.json` and validates
- [ ] That signal is imported into `finance-content-os/data/content_packs/<slug>/`
- [ ] The pack runs through `generate-insight` → `generate-hooks` →
      `write-short-video-script` → `repurpose-content` → `growth-review` →
      `review-finance-content`
- [ ] A finalised piece exists at `finance-content-os/published/pieces/<slug>.json` with assets
- [ ] The same piece is synced into `kite-dashboard/src/marketing-content/`
- [ ] `kite-lab/kite-dashboard` builds locally; `/library` and
      `/library/<slug>` render the piece without errors
- [ ] After commit + Vercel deploy, the live URL renders the piece
- [ ] `data/memory/topic_index.md` and `lessons.md` updated to reflect
      what was learned from the first run

See `TASKS.md` for the step-by-step build.
