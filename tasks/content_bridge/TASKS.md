# content_bridge — phased build

Owner key: 🤖 = Claude can do unattended (subject to cross-repo permission
prompts) · 👤 = needs founder · 🤝 = needs both (Claude executes, founder
reviews + gates).

Status key: ☐ todo · ◐ in-progress · ☑ done · ⊘ deferred to follow-up

---

## Phase 0 — Decisions (👤)

Lock the five Phase 0 decisions in `PLAN.md` before anything below starts.
The recommendations are pre-filled; founder confirms or redirects.

| # | Item | Status |
|---|------|--------|
| 0.1 | Marketing route name (`/library` recommended) | ☐ |
| 0.2 | Bridge-2 sync strategy (Option A recommended) | ☐ |
| 0.3 | First signal source (postclose daily quant note recommended) | ☐ |
| 0.4 | Schema source-of-truth + copy convention | ☐ |
| 0.5 | Branch naming in finance-content-os (`content-bridge` recommended) | ☐ |

---

## Phase 1 — Publisher in kite-lab (🤖)

Build the signal exporter. No changes to FastAPI or kite-dashboard yet.

| # | Item | Status |
|---|------|--------|
| 1.1 | Create `kite-lab/data/published/` directory + brief README | ☑ |
| 1.2 | Copy `signal.schema.json` from finance-content-os to `kite-lab/data/published/schema/`, hash-check at publisher startup | ☑ |
| 1.3 | ~~Add `jsonschema` to `kite-api/requirements.txt`~~ — went with inline validator instead (avoid Railway runtime dep for a local-dev tool) | ☑ |
| 1.4 | Write `scripts/publish_signal.py` with two subcommands: `from-daily-note --date YYYY-MM-DD --mode {premarket,postclose,weekly}` and `from-rebalance --portfolio <id> --changes-csv <path>` | ☑ |
| 1.5 | Daily-note mapping: title from headline, signal_type classified by regime + stress, why_interesting/why_now from `commentary.compose()`, data_points = stress + regime + sector RS top/bottom + watchlist names, source = explicit attribution. `learn_moment` carried through as a bonus field. | ☑ |
| 1.6 | Rebalance mapping: title = `{portfolio} rebalance — {date}`, signal_type=`portfolio`, ticker_or_theme = portfolio name, why_interesting = `{N adds, M removes, K rank changes}` + framework reminder, data_points = adds/removes/rank-changes (top 8 each), source = portfolio runner attribution. Date auto-inferred from filename if omitted. | ☑ |
| 1.7 | Writes Signal JSON to `data/published/signals/{date}_{source}.json`; pretty-print 2-space indent; UTC `published_at` timestamp included | ☑ |
| 1.8 | Append/update `data/published/signals/MANIFEST.json` — sorted desc by `published_at`, idempotent on re-publish | ☑ |
| 1.9 | Validates every emitted file before write (required fields, enum membership, types); fails loudly if invalid | ☑ |
| 1.10 | Smoke test: ran `python scripts/publish_signal.py from-daily-note --date 2026-05-27 --mode postclose` — published `2026-05-27_postclose_note.json` with 3 data points, regime=DRIFT, stress=62/100, signal_type=rotation, learn_moment carried through | ☑ |
| 1.11 | Brief usage section appended to `scripts/README.md` (new "Content bridge" row in the layout table) | ☑ |

**Risk tag:** 🟢 low. New script, new directory, no impact on existing
pipeline. The publisher is read-only against insight engine modules.

---

## Phase 2 — Importer in finance-content-os (🤖, cross-repo)

Build the receiving side. Requires permission to write into
`~/finance-content-os` — confirm on first write.

| # | Item | Status |
|---|------|--------|
| 2.1 | Create branch `content-bridge` in finance-content-os | 👤 ☐ — defer until founder is ready to commit |
| 2.2 | Add `bridge/` directory + `bridge/__init__.py` + README | ☑ |
| 2.3 | Write `bridge/import_from_marketworks.py`: `--list`, `--signal <filename>`, `--slug <pack-slug>`, `--force` | ☑ |
| 2.4 | Env var: `MARKETWORKS_DATA_PATH` defaults to `~/kite-lab/data/published/`. Documented in `bridge/README.md`. | ☑ |
| 2.5 | Validates signal against required-fields + signal_type enum + strength enum on read | ☑ |
| 2.6 | Replicated the `init` pack-creation logic inline (creates `data/content_packs/<slug>/` + `assets/` + `content_pack.json` with status=`imported` + `source_repo=kite-lab`) — cleaner than shelling out to `run_v2_pipeline.py` | ☑ |
| 2.7 | Writes `signal.json` verbatim into the pack; manifest references the signal at the canonical path | ☑ |
| 2.8 | Appends to `data/memory/topic_index.md`: row with slug, today's date, pillar (mapped from signal_type), thesis (first sentence of why_interesting), format=`reel`, status=`imported` | ☑ |
| 2.9 | Smoke test: ran `python bridge/import_from_marketworks.py --signal 2026-05-27_postclose_note.json --slug may27_drift_mode_note` — pack created cleanly, topic_index row appended (pillar=`active frameworks`) | ☑ |

**Risk tag:** 🟢 low. New module, no existing-skill changes.

---

## Phase 3 — Run the v2 pipeline end-to-end (🤝)

Use the imported signal to drive the existing finance-content-os
skills. No new code — this is the proof that the bridge feeds a real
piece.

| # | Item | Status |
|---|------|--------|
| 3.1 | Read the imported signal (`data/content_packs/<slug>/signal.json`) | ☐ |
| 3.2 | Run `generate-insight` skill (manual invocation in finance-content-os Claude Code session) → save `insight.json` | ☐ |
| 3.3 | ⏸ **Founder gate:** verify the insight reads as a real MarketWorks observation, not invented. All numbers traceable to kite-lab data. | ☐ |
| 3.4 | Run `generate-hooks` → save `hook_set.json` | ☐ |
| 3.5 | Run `write-short-video-script` → save `script.json` | ☐ |
| 3.6 | Run `repurpose-content` → update `content_pack.json` with carousel/thread/thumbnail variants | ☐ |
| 3.7 | Run `growth-review` → update with retention notes | ☐ |
| 3.8 | Run `review-finance-content` → save `compliance_report.json` | ☐ |
| 3.9 | `python scripts/run_v2_pipeline.py finalize --slug <slug>` — validates artifacts, exports `assets/script.md` + `assets/pack_summary.md`, logs run | ☐ |
| 3.10 | Render visual assets (Remotion: thumbnail PNG, carousel slides, optionally reel overlay) into `assets/` | ☐ |
| 3.11 | ⏸ **Founder gate:** approve the completed pack for publishing | ☐ |

**Risk tag:** 🟡 medium. The pipeline has been dormant ~6 weeks. Skills
+ schemas should still work but the first run may surface drift
(missing deps, schema mismatches, stale brand refs). Budget half a day
of buffer for fixing.

---

## Phase 4 — Publish step in finance-content-os (🤖, cross-repo)

Normalize a finished pack into web-ready form and sync to kite-dashboard.

| # | Item | Status |
|---|------|--------|
| 4.1 | `PublishedPiece` shape defined in `published/SCHEMA.md` — slug, title, pillar, format, duration, published_at, hook, alternate_hooks, body, key_takeaway, contrarian_angle, cta, assets[], meta{} | ☑ |
| 4.2 | Wrote `scripts/publish.py` with `--slug`, `--dest-dashboard`, `--dry-run` | ☑ |
| 4.3 | Refuses to publish unless `content_pack.json.status == 'reviewed'` AND `compliance_report.json` exists | ☑ |
| 4.4 | `published/pieces/<slug>.json` assembled from `signal.json` + `insight.json` + `hook_set.json` + `script.json` + `compliance_report.json` | ☑ |
| 4.5 | Copies assets (non-`.md`/`.txt`) from pack `assets/` to canonical + dashboard locations | ☑ |
| 4.6 | Updates `published/manifest.json` — entries sorted desc by `published_at`, idempotent on re-publish | ☑ |
| 4.7 | Dashboard sync writes pieces JSON to `kite-dashboard/src/marketing-content/pieces/`, assets to `kite-dashboard/public/marketing-content/assets/<slug>/`, and updates the dashboard's `manifest.json` | ☑ |
| 4.8 | End-of-run prints both canonical and dashboard write paths + the two `git add` / `git commit` commands needed | ☑ |
| 4.9 | Smoke test: deferred to Phase 3 (needs a finalised pack to publish) | ◐ |

**Risk tag:** 🟢 low. New code; no changes to existing pipeline.

---

## Phase 5 — Public routes in kite-dashboard (🤖)

Add `/library` and `/library/[slug]` as public Next.js routes. Light
styling, brand-appropriate but not polished.

| # | Item | Status |
|---|------|--------|
| 5.1 | Created `src/marketing-content/{pieces/,manifest.json,README.md}` and `public/marketing-content/assets/` with empty starter manifest | ☑ |
| 5.2 | `src/lib/library.ts` — typed data loader with `getManifest`, `getAllSlugs`, `getPiece`, `groupByPillar` using `fs.readFileSync` at build (Server Component only) | ☑ |
| 5.3 | `src/app/library/page.tsx` — index grouped by pillar with the brand's plain-English headers, dark mode, handles empty state | ☑ |
| 5.4 | `src/app/library/[slug]/page.tsx` — piece page renders thumbnail → hook → body → takeaway → carousel → CTA → source-data details + disclaimer footer | ☑ |
| 5.5 | Added `/library(.*)` to `isPublicRoute` in `middleware.ts`; routes confirmed public | ☑ |
| 5.6 | `generateStaticParams` returns all slugs from the manifest — SSG at build | ☑ |
| 5.7 | `generateMetadata` per piece — title, description from hook/takeaway, OG image from thumbnail asset | ☑ |
| 5.8 | Styling reuses existing Tailwind tokens (`prose`, neutral palette, emerald accent for takeaway, dark-mode-aware) — no new components | ☑ |
| 5.9 | `npx tsc --noEmit` clean. Local `npm run build` deferred to founder before push. | ◐ |
| 5.10 | Assets are local (`/marketing-content/assets/*`), no CSP change needed | ☑ |

**Risk tag:** 🟡 medium. Touching Clerk middleware to allow public
access has a footgun (R-006 territory). The default middleware matcher
in kite-dashboard already excludes static assets; verify it excludes
`/library/*` or add an explicit `publicRoutes` rule.

---

## Phase 6 — One piece live on marketworks.in (🤝)

Ship the loop.

| # | Item | Status |
|---|------|--------|
| 6.1 | Commit kite-lab branch (publisher + dashboard routes + synced content) | ☐ |
| 6.2 | Commit finance-content-os branch (importer + publish step + content pack + canonical published/) | ☐ |
| 6.3 | Push finance-content-os branch + open PR to its main | 👤 ☐ |
| 6.4 | Push kite-lab branch + open PR to main (or merge directly per repo convention) | 👤 ☐ |
| 6.5 | After merge: Vercel auto-deploys kite-dashboard | 🤖 (auto) ☐ |
| 6.6 | Visit `https://marketworks.in/library/<slug>` — verify piece renders, OG card present | 👤 ☐ |
| 6.7 | Verify `https://marketworks.in/library` index lists the piece | 👤 ☐ |
| 6.8 | ⏸ **Final founder gate:** public-ready or pull-down + iterate | 👤 ☐ |

**Risk tag:** 🟢 low for the deploy itself; 🟡 for first-real-publish
brand-voice check. The piece is reviewed at Phase 3.11; this is the
"see it live" gate.

---

## Phase 7 — Deploy automation (⊘ deferred)

Out of scope for v1. Tracked here for visibility.

| # | Item | Status |
|---|------|--------|
| 7.1 | Vercel deploy hook triggered by push to finance-content-os main | ⊘ |
| 7.2 | GitHub Action in finance-content-os: on push, POST to deploy hook | ⊘ |
| 7.3 | Migrate Bridge-2 to Option B (content-repo separately hosted, dashboard fetches at build time) | ⊘ |

Revisit Phase 7 when publish cadence exceeds ~2/week and the manual
two-commit flow becomes friction.

---

## Cross-repo execution notes

When Claude needs to write into `~/finance-content-os` (Phases 2, 4),
permission prompts will appear. Approve each — they're additive
changes in a separate repo, none of them touch kite-lab.

If at any point a phase fails or surfaces a design issue, update
`PLAN.md` Phase 0 decisions before continuing. The plan is the source
of truth; tasks bend to it, not the other way around.
