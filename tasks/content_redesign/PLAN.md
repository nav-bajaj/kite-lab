# content_redesign — rebuild the editorial layer for first-time viewers

## Why this exists

The `content_bridge` initiative shipped the plumbing cleanly: kite-lab
publishes signal-shaped JSON, finance-content-os imports it, runs a
pipeline, and the kite-dashboard serves it at `/library`. End-to-end
proven on the `may27_drift_mode_note` pack.

The first piece through the loop revealed the real gap. The editorial
layer in finance-content-os was designed 6-8 weeks ago around an
existing-subscriber persona — calm, technical, framework-heavy. When
asked to render a piece for a first-time viewer, it produced
technically-correct output that no first-time viewer would finish
watching. **The plumbing works; the editorial layer needs a
first-principles rebuild.**

Three pieces of strategic clarity unlocked in conversation:

1. **Target viewer is Karan** (28, Chandigarh, self-picked portfolio,
   curious but no system). He needs frames, not data dumps. Every
   word in a piece is evaluated against "would Karan understand this
   without prior context?"
2. **Founder is the topic source.** Outside auto-sourced technical
   market reports from kite-lab, the pipeline does NOT brainstorm
   topics. It takes a one-line founder phrase and turns it into a
   polished piece. The v2 `generate-signals` skill is obsolete.
3. **CTAs reference real, existing MarketWorks offerings only.**
   Never invent a "weekly read" or "daily reads" stream that doesn't
   exist. Four CTAs locked (see `_meta.yml`).

## Outcome

A founder types a topic phrase into a Claude Code session in
finance-content-os. Within ~10 minutes, a ready-to-record script comes
out — calibrated to the validated voice, grounded in verified data
from the insight engine, with a CTA that points at one of the four
real MarketWorks offerings.

Three formats supported:

- **Snippet (25-30s)** — single term, tip, or current event
- **Daily take (45s)** — specific upmove from a kite-lab signal OR a
  sector / market observation
- **Weekly roundup (75s)** — synthesised view of the week with one
  big frame

Repeatable, reliable, format-aware. Done well, this is the engine
behind getting from zero to a published cadence on Instagram + the
dashboard library.

## Reference calibration — the bar

Three example scripts were drafted in conversation and validated by
the founder. They are the bar the rebuilt pipeline reproduces.

1. **Snippet** — *"Three stocks. The whole rally."* (index concentration)
2. **Daily take** — *"The trade most retail is 2 years late to."* (defence rally)
3. **Weekly roundup** — *"The week the dollar quietly broke things."* (rupee weakness)

Voice principles extracted from these three (locked):

1. **One frame, one feeling per piece.** Karan walks away with one
   idea, said well. Not five takeaways, not three sectors, not
   eleven numbers.
2. **Define on use, or don't use it.** Any term Karan wouldn't have
   a definition for gets defined in the same sentence.
3. **Hook = curiosity gap, not stats.** Open with an observation or
   contradiction Karan needs answered. Numbers go inside the piece.
4. **Names as illustration, never recommendation.** "Metals" or
   "JPPOWER broke out" make a frame tangible. Never a buy/sell call.
5. **CTA points at a real, existing offering.** One of the four in
   `_meta.yml`. The piece's subject picks which.

## Architecture

```
[founder topic phrase]
        │
        ▼
ANALYZE  ──  kite-lab/scripts/analyse_topic.py
        │   produces a topic dossier (claim verification + data points + chart options)
        ▼
FRAME    ──  finance-content-os/skills/frame-piece
        │   produces the single frame the piece will hang on
        ▼
WRITE    ──  finance-content-os/skills/write-{snippet,daily-take,weekly-roundup}
        │   produces a complete script (hook, body, takeaway, CTA, stage directions)
        ▼
GUARD    ──  finance-content-os/.claude/agents/voice-guard
        │   pass / fail (jargon, off-voice, fake CTA, unverified numbers)
        ▼
[ready-to-record script]
```

Four stages, format-specific writers, an independent voice check via
subagent so author-mode drift doesn't get rubber-stamped by the same
context that wrote the piece.

### What lives where

| Layer | Repo | Why there |
|---|---|---|
| Analyse-topic tool | `kite-lab` | Reads insight engine modules directly. CLI surface. |
| New skills (frame, write-*) | `finance-content-os` | Editorial — voice, format, calibration. |
| Voice guard subagent | `finance-content-os/.claude/agents/` | Independent context for sharper review. |
| SessionStart hook | `finance-content-os/.claude/settings.json` | Auto-loads brand voice + CTA inventory + calibration refs at session start, so author Claude has the bar in context from message 1. |
| Tracking | `kite-lab/tasks/content_redesign/` | Mirrors `content_bridge/` convention. |

## Interaction model

V1 (this initiative):

1. Founder runs `python scripts/analyse_topic.py "defence sector momentum"`
   in kite-lab. The tool writes a dossier JSON.
2. Founder opens a Claude Code session in finance-content-os.
   `SessionStart` hook loads brand voice + CTA inventory + the three
   calibration reference scripts into context.
3. Founder asks: *"Write a snippet from this dossier:
   `kite-lab/data/topic_dossiers/defence_sector_momentum.json`"*
4. Claude runs `frame-piece` → `write-snippet` → invokes the
   `voice-guard` subagent → returns the script.
5. Founder reads. If acceptable, publishes via the existing
   `content_bridge` Phase 4 flow (publish.py → /library).

V2 (later, not in scope): the analyse-topic tool becomes an MCP
server or skill that Claude invokes directly without the founder
having to run a CLI first. Possibly the whole thing gets packaged as
a `marketworks-content` plugin for portability. Defer until V1 ships.

## Scope boundary

**In scope:**

- The 4-stage pipeline end-to-end
- All three format writers (snippet, daily take, weekly roundup)
- The analyse-topic tool covering the high-leverage analyses: sector
  RS, concentration, regime, cross-asset, watchlists, anniversary
- Voice guard with explicit pass/fail criteria
- SessionStart hook for finance-content-os Claude sessions
- Documentation (PLAN, TASKS, OVERVIEW.html for repeatability)

**Out of scope (defer):**

- Re-doing the bridge plumbing (it works)
- Carousel / Remotion render changes (the visuals were fine; the
  problem was the words)
- Founder on-camera production guidance
- Performance feedback wiring (revisit once content is live)
- Plugin packaging (consider after V1 produces ~5 pieces reliably)
- Hindi / vernacular variants (English-first for v1)
- New `Course` / `Lesson` schemas — courses still deferred per the
  content_bridge PLAN

## Phase 0 — decisions to lock

| # | Item | Default | Status |
|---|---|---|---|
| 0.1 | CTA inventory | Four CTAs locked in `_meta.yml` | ✅ |
| 0.2 | Instagram handle | `@marketworks.in` | ✅ |
| 0.3 | Task folder location | `kite-lab/tasks/content_redesign/` (mirror of content_bridge) | ✅ |
| 0.4 | New branches | `content-redesign` on both repos | ☐ confirm |
| 0.5 | V1 skill fate | Keep `finance-content-os/skills/{generate-signals, generate-insight, ...}/` as historical reference; new skills sit alongside, named with new shapes | ☐ confirm |
| 0.6 | First end-to-end target | Snippet writer producing a script at the calibration bar from one founder topic phrase | ☐ confirm |
| 0.7 | Re-test target | Replay the `may27_drift_mode_note` signal through the new pipeline as a regression check — does the rebuild fix the issue we identified? | ☐ confirm |

## Critical files

### kite-lab
- `tasks/content_redesign/` — PLAN, TASKS, _meta, OVERVIEW.html
- `scripts/analyse_topic.py` (new) — CLI: takes topic phrase, outputs dossier JSON
- `data/topic_dossiers/` (new) — output directory; gitignored (regenerable)
- `data/topic_dossiers/SCHEMA.md` (new) — dossier shape documentation

### finance-content-os (`content-redesign` branch)
- `.claude/settings.json` — SessionStart hook
- `.claude/agents/voice-guard.md` (new) — independent voice/jargon/CTA review subagent
- `brand/voice_v2.md` (new) — calibrated voice doc (supersedes v1 voice files)
- `brand/cta_inventory.md` (new) — the four real CTAs
- `brand/personas/` (new) — one .md per target persona. Karan today; the directory anticipates adding Priya / Anjali / advanced-trader personas later without restructure. Plural-by-design.
- `brand/calibration/` (new) — the three reference scripts as the bar
- `skills/frame-piece/SKILL.md` (new)
- `skills/write-snippet/SKILL.md` (new) — first writer
- `skills/write-daily-take/SKILL.md` (new — Phase 6)
- `skills/write-weekly-roundup/SKILL.md` (new — Phase 7)

## Verification at close

- [ ] Founder runs `analyse_topic.py` with a real phrase, gets a
      verified dossier
- [ ] Snippet writer produces a script that meets the calibration
      bar without manual rework on at least 3 distinct topics
- [ ] Voice guard fails loudly on a deliberately broken script
      (undefined jargon, fake CTA, made-up numbers)
- [ ] Daily take + weekly roundup writers ship and meet the bar on a
      test topic each
- [ ] The `may27_drift_mode_note` signal, replayed through the new
      pipeline, produces a script Karan would actually watch
- [ ] OVERVIEW.html documents the rebuild + the founder's daily
      operating workflow

See `TASKS.md` for the phased build.
