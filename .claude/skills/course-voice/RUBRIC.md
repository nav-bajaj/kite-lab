# Course content review rubric

Scoring instrument for any learner-facing course document (lesson, quiz,
worksheet, video script presenter lines, walkthrough spoken blocks, module
page copy). Used by the `course-reviewer` subagent and by any human doing a
manual pass. Companion to `SKILL.md` (the voice rules) and
`tasks/course_development/GLOSSARY.md` (the term bank).

## How to score

Rate each dimension 1-5 using the anchors below. Report every score with
one quoted example from the text that justifies it. No dimension may be
scored without evidence.

### 1. Term clarity (the jargon rule)

Derived from the term audit (below), not from impression.

- 5 — every term rated A (idea-first at first use, matches glossary).
- 4 — no C or D terms; at most two B terms.
- 3 — one or two C/D terms, rest explained.
- 2 — several C/D terms; a beginner would stall.
- 1 — reads like a methodology document.

### 2. Motivation before mechanism

Does each concept arrive because a question or problem made it necessary,
or is it defined cold?

- 5 — every major concept is preceded by the question it answers.
- 3 — concepts mostly motivated but at least one lands as a bare definition.
- 1 — definitions first, purpose later or never.

### 3. Plain-language craft

- 5 — short sentences, one idea per paragraph, passes the read-aloud test
  throughout; no semicolon-chain enumerations.
- 3 — mostly plain but with dense patches a beginner rereads.
- 1 — academic register, long compound sentences, list-stacking.

### 4. Warmth and directness

- 5 — speaks to "you"; wrong answers treated as respectable; no
  condescension and no false cheer; sounds like the exemplar lesson.
- 3 — correct but impersonal in stretches.
- 1 — lecture voice, or warmth that tips into patronizing.

### 5. Analogy quality

- 5 — each hard abstraction anchored in one everyday-life analogy; none
  stretched past its limit; consistent with the glossary's canon.
- 3 — analogies present but missing at a hard concept, or one is strained.
- 1 — no analogies where needed, or a metaphor beaten to death.

### 6. Learner activation

- 5 — the learner predicts, calculates, sorts, or writes something at every
  major beat; the document hands off to an exercise where ideas peak.
- 3 — some activity, but long passive stretches.
- 1 — pure reading/listening.

### 7. Rigor and guardrails — HARD GATE

- 5 — every changing fact carries its as-of date; every statistic carries
  its denominator or coverage note; official names used correctly
  (Nifty 500 vs Marketworks Nifty 500-derived universe); source links
  intact; zero recommendation language ("safe", "best", "quality", "buy");
  every "what this can't tell you" caveat present.
- Anything less than 5 on this dimension fails the whole review regardless
  of total score. List each violation precisely.

### 8. Pack consistency

- 5 — terminology, analogies, numbers, and answer keys agree with the
  module's sibling files and the glossary; facts identical across files.
- 3 — minor drift (wording of an explanation differs enough to confuse).
- 1 — contradicts a sibling file or the glossary.

## The term audit (feeds dimension 1)

Mechanical procedure — run it before scoring:

1. Extract every market/finance term in the document. Candidates: anything
   in the glossary, plus any word or phrase a smart adult outside finance
   would not already know (including abbreviations like DMA, ETF, SME).
2. For each term, find its **first use** and classify:
   - **A** — explained idea-first at first use, consistent with the
     glossary's approved explanation.
   - **B** — explained, but term-first, partial, or only by reference to
     another section ("see Part 3").
   - **C** — used with no explanation in this document. (Every document is
     scored standalone: learners open files out of order.)
   - **D** — explained, but the explanation conflicts with the glossary.
3. Report as a table: term | first-use location | class | quote | suggested
   fix (for B/C/D, write the actual replacement sentence, don't just name
   the problem).
4. Any term not yet in the glossary gets flagged `NEW` with a proposed
   glossary entry.

## Verdict

- **Pass** — dimension 7 = 5, no dimension below 3, total ≥ 32/40.
- **Revise** — anything else. The review must list fixes in priority
  order; the author revises and re-submits. After two failed cycles,
  escalate to the founder with the sticking points instead of looping.

Report format (always):

```text
VERDICT: pass | revise
TOTAL: n/40  (gate: dim 7 = n/5)
SCORES: 1:n 2:n 3:n 4:n 5:n 6:n 7:n 8:n   (each with quoted evidence)
TERM AUDIT: n terms — A:n B:n C:n D:n NEW:n  (+ table)
TOP FIXES: ordered list, concrete rewrites
GLOSSARY PROPOSALS: entries for NEW terms
```

## Recurring pitfalls (grows over time)

Append one line per lesson learned from each module's review cycles, so the
next module doesn't repeat it. Seeded from the Module 1 second pass:

- First drafts default to methodology register: definitions before
  motivation, semicolon enumerations. Motivate first.
- Coverage numbers (92.04%/84.07%-style) tend to get spoken without their
  as-of date in scripts. The date is part of the number.
- Deslop-style compression was tested and rejected (28 July 2026): don't
  trade explanation for brevity, but do vary openers and avoid em-dash and
  punchy-fragment tics.
- Bare finance terms slip into quiz distractor options (e.g. "demat
  account") because authors gloss concepts only in answer feedback — audit
  distractor options as first-use sites, not just stems and correct
  answers. (Module 1 review, 28 July 2026)
- The bare-distractor failure hits the marquee conceptual terms hardest
  (e.g. "survivorship bias"): authors gloss friendly concrete terms inline
  but leave the scary abstraction bare because "the lesson taught it".
  Audit the module's flagship concepts in distractors first. (Module 1
  full-pack review, 28 July 2026)
- Adaptations that compress the lesson (HTML page, video script,
  walkthrough) drop per-item idea-first glosses first — acronyms listed as
  "other kinds" (ETF/REIT/InvIT) inside diagrams, lists, or one-breath
  spoken lines, and foundational terms assumed known from earlier files.
  Audit every acronym-in-a-list and assumed-known term as a standalone
  first-use site. (Module 1 full-pack review, 28 July 2026)
- When a worksheet's fill-in design changes (blank style, card fields), the
  facilitator answer guide silently goes stale — mechanically re-key every
  answer-bearing section against the current worksheet before scoring
  dimension 8. (Module 1 full-pack review, 28 July 2026)
- Rhetorical hooks reuse market terms (exchange, index) before the lesson
  formally glosses them — treat the first spoken sentence of an opening
  script as a first-use site and gloss every term in it, even the
  "obvious" ones. (Module 1 cycle-2 review, 28 July 2026)
- Build-finalization passes (favicons, noscript, ARIA/marker text,
  denominator fixes) can silently alter learner-visible copy — treat any
  added user-facing string (fallback banners, state labels, grading
  markers) as a first-use site and voice-check it, and re-key any changed
  answer/verdict logic against its source-of-truth sequence. (Module 1
  build-finalization review, 28 July 2026)
