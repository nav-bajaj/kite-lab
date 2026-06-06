# REPEATABILITY — designing against creative drift

## The problem we're solving

When Claude generates creative content across multiple sessions, **voice
drifts**. The same brand doc, the same prompts, the same input data —
yet pieces produced on Monday and pieces produced on Friday look like
they're from different writers. This is fatal for a brand whose moat is
*calm, distinctive, trustworthy voice*.

Drift has identifiable causes:

| Cause | What it looks like |
|---|---|
| Brand voice docs are interpretive | "Calm and clear" means different things in different sessions |
| Skill prompts give too much creative latitude | The writer has 100 ways to interpret "punchy hook" |
| Multi-stage pipelines compound variance | Each stage interprets the previous loosely; errors stack |
| No anchor examples | Claude pattern-matches against general training data, not against our bar |
| Author-mode bias | The Claude that wrote the piece won't catch its own voice drift |
| No structural enforcement | A polite warning in a SKILL.md is ignorable; a hook that blocks Write is not |

The rebuild explicitly designs *against* each of these. This doc is the
playbook. Every skill / agent / hook in this initiative serves at least
one of these defenses.

---

## The eight defenses

### 1. Anchor by example, not by principle

**Why:** Claude pattern-matches against examples in context far more
reliably than against rules in prose. *"Hook is a curiosity gap"* is a
rule. *"Three stocks. The whole rally."* is an example. The example
wins every time.

**How:** `brand/calibration/` contains the three validated reference
scripts as standalone Markdown files. The SessionStart hook loads them
into context at every session start. Every SKILL.md cites them as the
bar. Over time we expand the library — each accepted piece becomes a
future calibration reference.

**Anti-pattern this prevents:** writing skills that *describe* the
voice. Skills should *show* the voice with worked examples and let the
reader pattern-match.

### 2. Tight stage contracts (JSON, not prose)

**Why:** Each pipeline stage's output is the next stage's input. If
stage outputs are freeform prose, the next stage interprets them
loosely, compounding drift. Tight JSON schemas force precision.

**How:**

```
ANALYZE  → TopicDossier         { claim, verified_facts[], data_points[], chart_suggestions[], confidence }
FRAME    → FrameStatement       { frame, why_this_frame, anti_frames[] }
WRITE    → ScriptDraft          { hook, body[], takeaway, cta, stage_directions[] }
GUARD    → GuardVerdict         { pass: bool, issues[], severity, suggested_fixes[] }
```

Every skill declares its input/output shape at the top. Outputs are
JSON, validated. Prose only appears INSIDE these fields, not between
them.

**Anti-pattern this prevents:** skills that produce "a markdown draft"
and trust the next stage to extract structure from it.

### 3. Few-shot examples in every SKILL.md

**Why:** A skill that says *"write a hook that creates a curiosity
gap"* gives Claude too much latitude. A skill that ALSO shows three
worked examples (input dossier → output hook) gives Claude a pattern
to imitate.

**How:** Every `SKILL.md` contains 2-3 *Worked Examples* sections —
real input/output pairs from the calibration library. Updated as the
library grows. Bad examples included too — labeled clearly so Claude
learns to avoid them.

**Anti-pattern this prevents:** skill prompts that only describe
desired behavior. The drift-mode v1 piece happened in large part
because the skills described principles without showing what they
look like in practice.

### 4. Independent guard subagent

**Why:** The Claude session that authored the piece will defend its
work. The Claude that reviews the work needs to be a different
context window — no shared rationalization, no sunk-cost reasoning.

**How:** `.claude/agents/voice-guard.md` runs in an isolated subagent
context. Reads the script + `brand/voice_v2.md` +
`brand/personas/<active>.md` + `brand/cta_inventory.md` + the source
dossier. Returns a structured `GuardVerdict`. If `pass=false`, the
orchestrator does not advance.

The guard subagent has NO access to the author's reasoning. It sees
the script as a finished artifact. This is the model-as-judge pattern
done right.

**Anti-pattern this prevents:** review checks that run in the same
context as authoring. ("I just wrote this; obviously it's fine.")

### 5. SessionStart hook for invariants

**Why:** A founder opening Claude in finance-content-os shouldn't
have to remember to load brand docs. The first message of every
session should already have the voice, the persona, the CTAs, and the
calibration references in context.

**How:** `.claude/settings.json` configures a SessionStart hook that
reads:

- `brand/voice_v2.md`
- `brand/personas/*.md` (every persona file in the folder, so adding
  Priya / Anjali / etc. later is a drop-in — no hook reconfiguration)
- `brand/cta_inventory.md`
- `brand/calibration/*.md` (all three reference scripts)

and injects them as system context. Author Claude starts every
session with the bar already loaded — message 1 already knows what
the right answer looks like.

**Anti-pattern this prevents:** "Did you remember to read CLAUDE.md
first?" friction. Hooks remove human dependence on remembering.

### 6. PreToolUse hook on script writes (structural enforcement)

**Why:** A polite warning in a SKILL.md saying *"run the voice guard
before saving"* will be skipped eventually — by Claude, by the
founder, by both. The only reliable enforcement is structural: the
write *cannot happen* unless the guard passes.

**How:** A `PreToolUse` hook configured on the `Write` tool with a
matcher for paths like `data/content_packs/*/script.json` or
`published/pieces/*.json`. When the matcher fires, the hook invokes
the voice-guard subagent on the proposed content. If the verdict is
`pass: false`, the hook **blocks the write** with the guard's issues
attached.

This is what state-of-the-art Claude Code looks like in 2026 — invariants
move from prompts (suggestion) to hooks (enforcement).

**Anti-pattern this prevents:** human review being the only gate. The
founder gets to focus on whether the piece is *interesting*, not
whether it has undefined jargon — the hook handles the latter.

### 7. Anti-pattern lists in every prompt

**Why:** Telling Claude *what to do* leaves a vast space of "almost
right" answers. Telling Claude *what NOT to do* sharpens the target.

**How:** Every SKILL.md includes a *"Failure modes"* section with
concrete examples drawn from the v1 may27_drift_mode_note piece:

- ❌ Hook: *"The Nifty is in drift mode — and history says guessing the next move is a coin flip."* (uses jargon "drift mode" before defining it)
- ✅ Hook: *"There are 50 stocks in the Nifty. Six sectors. And right now, two of them are telling completely different stories."*

The negative examples are pulled from real failure modes, not
hypothetical ones.

**Anti-pattern this prevents:** skills that only describe success
states. Failure-mode examples sharpen the contrast.

### 8. Plugin packaging (designed-for, deferred build)

**Why:** The founder will eventually use this from multiple machines,
maybe collaborate with another author. The whole setup needs to be
portable — same skills, same hooks, same brand context, same guard —
not "works on my machine."

**How (v2):** Once V1 ships 5+ pieces reliably, package the whole
content layer as a `marketworks-content` Claude Code plugin. Bundles
skills, agents, settings, brand docs. Installable via plugin manifest.
Same behaviour everywhere.

**Anti-pattern this prevents:** the system being tied to one
machine's filesystem layout. Plugin packaging is how we get
production-grade portability.

---

## How the eight compose

```
[founder topic phrase]
        │
        │      ┌─────────────────────────────────────────┐
        │      │  SessionStart hook (defense 5)          │
        │      │    loads voice + personas/*.md + ctas + │
        │      │    calibration/*.md into every session  │
        │      └─────────────────────────────────────────┘
        ▼
ANALYZE  ── analyse_topic.py (kite-lab) → TopicDossier (defense 2)
        ▼
FRAME    ── skill (defense 3 — few-shot + defense 7 — anti-patterns)
        ▼  → FrameStatement (defense 2)
WRITE    ── skill per format (defenses 1, 3, 7)
        ▼  → ScriptDraft (defense 2)
GUARD    ── voice-guard subagent (defense 4)
        ▼  → GuardVerdict (defense 2)
        │
        │      ┌─────────────────────────────────────────┐
        │      │  PreToolUse hook (defense 6)            │
        │      │    on Write to script.json paths:       │
        │      │    invokes voice-guard, blocks if fail  │
        │      └─────────────────────────────────────────┘
        ▼
[ready-to-record script]
```

Defenses 1-4 live in skills + agents. Defenses 5-6 live in hooks
(`settings.json`). Defense 7 is a prompt convention applied across
all skills. Defense 8 is the eventual packaging.

Each defense is *necessary but not sufficient*. Skills alone drift.
Hooks alone are too rigid. Together they create a system where
voice consistency is structural, not aspirational.

---

## Calibration regression as the heartbeat

Once a quarter (or after any skill / hook / brand-doc change), run
the three calibration topics through the pipeline and diff the output
against the reference scripts. If the output has drifted, the
pipeline has drifted. Fix it before any new piece ships.

This is the loop that makes the system actually repeatable over
months and years — not just within one session.

`tasks/content_redesign/calibration_runs/` will hold the regression
log: each row is `{timestamp, calibration_topic, output, diff_summary,
pass}`. Failing runs trigger a rebuild conversation.

---

## What we explicitly do NOT do

- **No "creative" generation with no guardrails.** Every output goes
  through the guard. No exceptions for "I just want a quick draft."
- **No skills that combine stages.** No `write-and-review` mega-skill.
  Separation of concerns keeps each stage testable.
- **No author-mode self-review.** The guard runs in a different
  subagent every time. No shortcuts.
- **No prompt-only voice enforcement.** If a check is critical, it
  goes in a hook, not a polite reminder.
- **No drift from the four CTAs.** A skill that wants to invent a new
  CTA is a bug, not a feature.

---

## How this maps to TASKS.md

| Defense | Phase | Concrete deliverable |
|---|---|---|
| 1 — Anchor by example | 2 | `brand/calibration/` directory with three reference scripts |
| 2 — Tight stage contracts | 1, 3, 6, 7 | TopicDossier (Phase 1), FrameStatement / ScriptDraft (Phase 3, 6, 7) |
| 3 — Few-shot in skills | 3, 6, 7 | Every SKILL.md has Worked Examples section |
| 4 — Independent guard subagent | 3 | `.claude/agents/voice-guard.md` |
| 5 — SessionStart hook | 2 | `.claude/settings.json` SessionStart config |
| 6 — PreToolUse hook | 3, 4 | `.claude/settings.json` PreToolUse on Write |
| 7 — Anti-pattern lists | 3, 6, 7 | Every SKILL.md has Failure Modes section |
| 8 — Plugin packaging | post-V1 | Deferred — design for it but don't ship |

The phases in TASKS.md remain unchanged; this doc clarifies the *why*
behind specific choices in each.
