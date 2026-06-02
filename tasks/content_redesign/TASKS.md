# content_redesign — phased build

Owner key: 🤖 Claude (unattended, modulo cross-repo permission prompts) ·
👤 founder · 🤝 both (Claude executes, founder reviews + gates).

Status key: ☐ todo · ◐ in-progress · ☑ done · ⊘ deferred

Phases run roughly sequentially. Phase 1 (kite-lab tool) and Phase 2
(content-repo foundations) can run in parallel if useful, but Phase 3
needs both.

---

## Phase 0 — Lock decisions (👤)

| # | Item | Status |
|---|---|---|
| 0.1 | CTA inventory (four real offerings) | ☑ |
| 0.2 | Instagram handle (`@marketworks.in`) | ☑ |
| 0.3 | Task folder location (`kite-lab/tasks/content_redesign/`) | ☑ |
| 0.4 | Branch naming on both repos (`content-redesign`) | ☑ — kite-lab branched; finance-content-os pending Phase 2 |
| 0.5 | Keep v1 skills alongside new ones as historical reference | ☑ |
| 0.6 | First end-to-end target: snippet writer | ☑ |
| 0.7 | Regression test: replay may27_drift_mode_note signal through new pipeline | ☑ |

---

## Phase 1 — Analyse-topic tool (🤖 · kite-lab)

Build the founder-facing CLI that turns a topic phrase into a
verified data dossier.

| # | Item | Status |
|---|---|---|
| 1.1 | `TopicDossier` shape defined in `data/topic_dossiers/SCHEMA.md` — claim, verified_facts, data_points, chart_suggestions, related_signals, confidence | ☑ |
| 1.2 | `scripts/analyse_topic.py` CLI: `--topic`, `--slug`, `--asof` | ☑ |
| 1.3 | Keyword-based routing with 5 categories (sector, currency, concentration, watchlist, regime), plus an `unrouted` fallback to regime + concentration | ☑ |
| 1.4 | Module wrappers — `analyse_sector` (sector_rs), `analyse_currency` (cross_asset), `analyse_concentration` (concentration), `analyse_watchlist` (watchlists), `analyse_regime` (regime + stress). Subgroups and calendar_content deferred to v2. | ☑ |
| 1.5 | Claim verification fires for sector-leadership and currency-weakness/rally phrases; sets `claim.verified` true/false with specific evidence. Other categories return `not_applicable`. | ☑ |
| 1.6 | Auto-slug from phrase; output to `data/topic_dossiers/<slug>.json` | ☑ |
| 1.7 | `.gitignore` updated — dossiers gitignored as regenerable, schema doc excepted | ☑ |
| 1.8 | Smoke-tested on three phrases (`defence sector momentum` · `rupee weakness this week` · `Reliance share of Nifty move`) — all return `confidence: high` with grounded data. Rupee weakness claim verified TRUE at the 96th percentile. | ☑ |
| 1.9 | Brief usage row in `scripts/README.md` | ☐ |

**Risk tag:** 🟡 medium. The routing logic is novel — phrase → module mapping has fuzzy edges. Start with explicit keyword routing, NLP refinement only if needed.

---

## Phase 2 — Content-repo foundations (🤖 · finance-content-os, cross-repo)

Brand voice, CTA inventory, calibration references, SessionStart hook.
These are the scaffolding the writers depend on.

| # | Item | Status |
|---|---|---|
| 2.1 | Branched `content-redesign` from `content-bridge` in finance-content-os | ☑ |
| 2.2 | `brand/voice_v2.md` written — locked stance, tone anchors (Sonia/Zerodha/Sharan-catchy/Ackman/Dalio/Chamath), the five voice principles, four V1 anti-patterns with concrete ✅/❌ examples from the may27 piece, voice-guard pass criteria | ☑ |
| 2.3 | `brand/cta_inventory.md` written — four locked CTAs with wording variants, when-to-use rules, real-today status, and an explicit "what is NOT in the inventory" anti-list | ☑ |
| 2.4 | `brand/calibration/` directory created with three validated reference scripts: snippet (index concentration), daily take (defence rally), weekly roundup (dollar strength). Each annotated with "why this works" and the writer's contract. | ☑ |
| 2.5 | `brand/personas/karan.md` written — full persona doc (demographics, portfolio reality, the actual pain, consumption habits, literacy floor, voice fit, success definition). Directory is plural-ready. | ☑ |
| 2.6 | `CLAUDE.md` updated with a top-level "V2 rebuild in progress" block pointing at the new structure and naming superseded files. V1 docs left in place for reference. | ☑ |
| 2.7 | `.claude/hooks/load-brand-context.sh` + `.claude/settings.json` configured. SessionStart hook globs `personas/*.md` and `calibration/*.md` so future additions are picked up automatically. | ☑ |
| 2.8 | Hook tested manually — produces 742 lines of brand context with all sections present and properly delimited | ☑ |

**Risk tag:** 🟢 low — text files and a settings.json change. The hook
is the only moving part; if it's a problem, fall back to manual `Read`
at session start.

---

## Phase 3 — Snippet writer end-to-end (🤖 · finance-content-os)

The first complete pipeline. Skills + agent + orchestration for the
snippet format only. This is the most important phase — if this
works at the bar, scaling to other formats is straightforward.

| # | Item | Status |
|---|---|---|
| 3.1 | `.claude/skills/frame-piece/SKILL.md` written — three candidate frames, picks the sharpest, output FrameStatement JSON. 3 worked examples drawn from the calibration scripts. Anti-patterns enumerated. | ☑ |
| 3.2 | `.claude/skills/write-snippet/SKILL.md` written — full snippet arc spec (hook / body / takeaway / CTA + stage directions). Output ScriptDraft JSON with `anchor_fact` and `cta_inventory_id` fields. Quality-bar self-check before invoking voice-guard. 5 anti-patterns from V1 enumerated. | ☑ |
| 3.3 | `.claude/agents/voice-guard.md` written — independent reviewer, 8 pass criteria each with specific failure rules. Output GuardVerdict JSON. Explicit "do not rewrite" / "do not soften" behavior contract. | ☑ |
| 3.4 | `docs/workflow_snippet.md` — end-to-end founder workflow doc (analyse → frame → write → guard → publish). Troubleshooting table included. | ☑ |
| 3.5 | 🤝 Smoke test (founder runs in finance-content-os session): pick one of the 3 dossiers in `~/kite-lab/data/topic_dossiers/`, run the workflow, evaluate against `brand/calibration/snippet_index_concentration.md` | ☐ |
| 3.6 | 🤝 Iterate the skills based on smoke-test feedback | ☐ |
| 3.7 | 🤝 Re-test on 2 more dossiers until the writer produces guard-passing output in one pass | ☐ |

**Risk tag:** 🟡 medium. The hardest part is calibrating the skill
prompts. Plan to iterate 5-10 times before locking.

**Gate:** 🤝 founder reviews the output of 3.5 / 3.7. If it doesn't
meet the bar, don't advance to Phase 4.

---

## Phase 4 — Voice guard hardening (🤖 · finance-content-os)

The guard is the structural defence against voice drift. Make it
fail loudly on real failure modes.

| # | Item | Status |
|---|---|---|
| 4.1 | Build a small corpus of deliberately broken scripts: undefined jargon, fake CTA, made-up numbers, off-voice clinical tone, off-voice finfluencer tone | ☐ |
| 4.2 | Run each through the voice guard, verify it fails with specific reasoning | ☐ |
| 4.3 | Run the 3 calibration reference scripts through, verify it passes | ☐ |
| 4.4 | Run the 3 Phase-3 produced scripts through, verify it passes | ☐ |
| 4.5 | Document failure-mode taxonomy in `brand/voice_guard_taxonomy.md` for repeatability | ☐ |

**Risk tag:** 🟢 low. This is a verification phase, not a build phase.

---

## Phase 5 — Replay drift-mode signal (🤝)

The structural regression test. Take the original v1 failure case
and run it through the new pipeline.

| # | Item | Status |
|---|---|---|
| 5.1 | Topic phrase: *"metals beat banks while the Nifty went nowhere"*, asof 2026-05-27 | ☑ |
| 5.2 | `analyse_topic.py` produced `data/topic_dossiers/may27_drift_replay.json` — category sector, high confidence, real NIFTY_METAL / NIFTY_BANK facts | ☑ |
| 5.3 | Snippet workflow produced `may27_drift_replay` pack, guard PASS in one pass, 3 non-blocking polish notes | ☑ |
| 5.4 | 👤 Founder + Claude comparison vs V1 `may27_drift_mode_note/script.json`: V1 used 11 numbers + 4-5 jargon terms + assumed-positions takeaway. V2 uses 2 numbers, zero jargon, position-agnostic takeaway. CTA correctly routed to #3 (momentum portfolios) for sector-leadership subject. Same dossier data, unrecognisable output. | ☑ |
| 5.5 | Rebuild hit its bar. Editorial layer is fixed. | ☑ |

**Gate:** This is the "did we actually fix the problem" check. Don't
move forward until this passes.

---

## Phase 6 — Daily take writer (🤖 · finance-content-os)

| # | Item | Status |
|---|---|---|
| 6.1 | `.claude/skills/write-daily-take/SKILL.md` written — 45s structure with explicit `causal_frame` + `cultural_anchor` required output fields. Format-specific failure modes (snippet-density body, weekly-roundup over-stuffing, missing cultural anchor) enumerated. | ☑ |
| 6.2 | Smoke test on `defence_sector_momentum` dossier — guard PASS 8/8. Skill correctly pivoted when defence data wasn't tracked (used the absence as the frame). Diwali-party cultural anchor matched the calibration shape. CTA #3 correctly routed. | ☑ |
| 6.3 | Format independence verified — piece is structurally distinct from the calibration daily-take (different frame, fresh cultural anchor) despite same category | ☑ |
| 6.4 | Bar met on first pass — no iteration needed | ☑ |

---

## Phase 7 — Weekly roundup writer (🤖 · finance-content-os)

| # | Item | Status |
|---|---|---|
| 7.1 | `.claude/skills/write-weekly-roundup/SKILL.md` written — 75s structure with explicit `load_bearing_variable` + exactly 3 `three_effects` required output fields. Each effect must have a one-sentence mechanism explanation. Format-specific failure modes enumerated. | ☑ |
| 7.2 | Smoke test on `rupee_weakness_this_week` dossier (slug `rupee_weakness_roundup`) — guard PASS 8/8. Sharper frame than calibration ("slow tax on everything India imports"). Three effects deliberately distinct from calibration's three (oil/electronics/foreign-capital vs calibration's IT/FIIs/importers). Structural integrity held (exactly 3 effects, mechanism per effect, parallel rhythm). | ☑ |
| 7.3 | Format independence verified — same dossier produced a structurally distinct piece from the snippet version (you-are-late framing) and from the calibration (rippled-through-3-parts framing) | ☑ |
| 7.4 | Bar met on first pass — no iteration needed | ☑ |

---

## Phase 8 — Documentation + handoff (🤖)

| # | Item | Status |
|---|---|---|
| 8.1 | Write `tasks/content_redesign/OVERVIEW.html` — visual map of the rebuilt pipeline, parallel to `tasks/content_bridge/OVERVIEW.html` | ☐ |
| 8.2 | Write `docs/founder_workflow.md` in finance-content-os — the daily / weekly operating model for the founder | ☐ |
| 8.3 | Update `tasks/content_bridge/OVERVIEW.html` with a callout pointing at the redesign | ☐ |
| 8.4 | `_meta.yml` → `status: shipped`, fill `related_commits`, fill `sibling_commits` | ☐ |
| 8.5 | RESULTS.md — what was actually shipped vs. planned, deferred items, verification log | ☐ |

---

## Cross-cutting notes

**Branch hygiene:** both repos use `content-redesign` branch. Merge
each with `--no-ff` so the merge commit summarises the initiative.
Don't push until Phase 5 passes — this whole rebuild is local until
it's proven.

**V1 skill fate:** the existing 10 skills in `finance-content-os/skills/`
stay where they are during the rebuild. New skills sit alongside.
After Phase 5 passes, archive the v1 ones (move to `skills/_archive_v1/`
or delete on the branch).

**Plugin packaging:** out of scope for v1, but every new skill +
agent + hook is structured to be packageable later. Keep contracts
clean.

**Cross-repo execution notes:** writing into finance-content-os from
this Claude session will trigger permission prompts. Approve each —
they're additive changes in a sibling repo.
