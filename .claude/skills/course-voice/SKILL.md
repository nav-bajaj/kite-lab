---
name: course-voice
description: Writing voice for all Marketworks course material (tasks/course_development/). Load before authoring or editing any learner-facing lesson, quiz, worksheet, video script, walkthrough, or module page. Defines the plain-language register, the jargon rule, analogy style, and the guardrails that simplification must never delete.
---

# Marketworks course voice

Every learner-facing sentence in this course is read by someone meeting the
Indian stock market for the first time. They are intelligent adults — often
professionals in other fields — but they do not yet know what an index is,
and English may be their second language. Write for them.

## Who is speaking

A patient friend who has traded for years and remembers not knowing anything.
Not a professor, not a compliance officer, not an index methodology document.

- Speak to "you". Use "we" when learner and teacher do something together.
- Contractions are fine ("you'll", "it's", "doesn't").
- It is always okay to say "this part trips people up" or "this sounds more
  complicated than it is."
- Let wrong answers be respectable: "You might guess 50 — that's a
  reasonable guess, and here's what it's actually counting."

## The jargon rule (the core of this skill)

**Plain idea first, term second.** Introduce the concept in everyday words,
then hand the learner the market term as a *name* for the idea they already
understand — never the reverse.

Wrong (term first): "A security is a financial claim."
Right (idea first): "When you buy a share, what you actually own is a claim —
a slice of the company that entitles you to a slice of what it earns. The
market's word for any tradable claim like this is a *security*."

- Every market term gets this treatment on first use in every document.
  A term explained in the lesson is still explained (in one short clause)
  in the quiz, worksheet, and video — learners open files out of order.
- After first use, the term may be used freely.
- Never define a term using another undefined term.

### Translation table — prefer the left, earn the right

| Say this first | Before using this term |
|---|---|
| the stocks actually available for the public to buy and sell | free float |
| how much the price moves against you just because you traded | impact cost |
| the member stocks of the index | constituents |
| the list gets refreshed twice a year | reconstitution / semi-annual review |
| how many stocks were actually counted | denominator |
| how many stocks joined the move | breadth / participation |
| comparing many stocks side by side on the same day | cross-sectional |
| the list as it stood on a specific date | snapshot / point-in-time |
| stocks that vanished from the record because they failed or left | survivorship bias |
| price × number of shares — what it costs to buy the whole company | market capitalization |

## Sentence and paragraph craft

- One idea per paragraph. Two to four sentences each.
- Average well under 20 words per sentence. If a sentence needs a semicolon
  chain to survive, it is three sentences.
- Prose over bullets. Use a bullet list only when the content is genuinely a
  list (max ~5 items), never to compress an argument.
- No lettered/semicolon enumerations ("(a) ...; (b) ...;").
- Headings are questions or plain claims a beginner can parse before reading
  the section ("The index went up. Did most stocks?" — not "Index return and
  breadth are different views").
- Read it aloud test: if you would not say the sentence to a friend across a
  table, rewrite it.

## Analogies

Anchor every abstraction in something from everyday Indian life the first
time it appears. Good, tested ones:

- Universe → the voter list: an election result means nothing until you know
  who was allowed to vote.
- Index selection → a cricket team: picked by written rules, refreshed on a
  schedule; selection is not a lifetime guarantee, and being picked doesn't
  make a player the best at everything.
- Weighted index vs breadth → class average vs how many students passed: the
  average can rise because two toppers scored high while most of the class
  slipped.
- Broker-search "everything" → a wedding guest list scraped from your entire
  contacts app: technically complete, useless for planning.

One analogy per concept. Retire an analogy rather than stretch it.

## What simplification must NEVER delete

These survive every rewrite, restated simply — not removed:

1. **Dates on facts.** Every changing number (counts, coverage %, membership)
   keeps its as-of date. Say it humanly: "as of December 2025."
2. **The denominator habit.** Any statistic keeps "counted out of how many,
   as of when."
3. **No recommendations.** Never "safe", "best", "quality stocks", "buy".
   Index membership is not advice; the Nifty 500 is a learning universe, not
   a starter portfolio.
4. **Official names and sources.** "Nifty 500" for the index, "Marketworks
   Nifty 500-derived universe" for the dated product dataset. Source links
   stay intact and attributed.
5. **Honest limits.** Every "what this can't tell you" caveat survives in
   plain words.

Simplicity is achieved by better explanation, not by omission.

## Calibration verdict (28 July 2026)

Three registers were tested side by side on the Module 1 lesson
(`tasks/course_development/voice_compare/`): the original
methodology-document draft, this course voice, and a deslop pass
(stephenturner/skill-deslop, an AI-pattern-removal ruleset, since
uninstalled) layered on top. The founder chose **this course
voice** as the standard. The deslop version was judged good but too casual
in places and sometimes too succinct to land the point.

Practical reading of that verdict:

- Full explanations beat brevity. When cutting a sentence would make the
  learner work harder, keep the sentence.
- The warm devices (direct address, "that's a reasonable guess", analogies,
  a guiding question before a concept) are features, not slop. Keep them.
- Still borrow deslop's restraint on tics: don't lean on the same opener
  ("Here's the...") or em-dash construction many times per page, and don't
  stack punchy one-line paragraph endings. Variety, not austerity.

## The authoring loop (how modules get made)

Voice rules alone don't guarantee quality; the loop does. For every
learner-facing document:

1. **Author** under this skill, pulling first-use term explanations from
   `tasks/course_development/GLOSSARY.md` (the canonical term bank). A term
   the glossary doesn't have yet gets a proposed entry in the same change.
2. **Review** — run the `course-reviewer` subagent on the document. It
   scores the eight dimensions in `RUBRIC.md` (same folder as this file)
   and runs the mechanical term audit: every market term classified
   A/B/C/D at first use, with a written fix for anything below A.
3. **Revise** until the verdict is pass (rigor gate at 5/5, total ≥ 32/40).
   After two failed cycles, take the sticking points to the founder instead
   of looping.
4. **Close the loop** — when the module passes: merge NEW glossary entries,
   and append any `PITFALL:` line from the review to RUBRIC.md's
   "Recurring pitfalls" so the next module starts smarter.
5. **Ship the tutor guide** — compile `TUTOR_GUIDE.html` in the module
   folder per `tasks/course_development/TUTOR_GUIDE_SPEC.md`: the
   single page that tells the tutor everything about the module (run of
   show, concept arc, glosses, dated facts, answer keys, misconceptions,
   guardrails, review scoreboard). It is compiled from reviewed sources —
   excluded from the review ledger, but regenerated whenever any pack
   file changes.

A module is not done while any of its documents holds a "revise" verdict.

The loop is enforced by the harness, not by memory: a PostToolUse hook
(`tools/course/review_ledger_add.sh`, wired in `.claude/settings.json`)
adds every edited learner-facing course file to
`tasks/course_development/.review_ledger` and reminds the session once per
file per cycle; a SessionStart hook surfaces anything still pending from
earlier sessions. When a file passes review, clear it with
`tools/course/review_ledger_clear.sh <repo-relative-path>`.

## Repo rules that apply here

- No emojis in files.
- Facilitator/instructor documents may be more compact, but any words meant
  to be spoken to learners (scripts, prompts, responses) follow this voice
  in full.
- The exemplar for this voice is
  `tasks/course_development/modules/01_market_universe/LESSON.md`. When in
  doubt, match it.
