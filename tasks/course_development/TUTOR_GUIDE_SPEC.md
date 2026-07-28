# Tutor guide spec — the module completion deliverable

When a module passes review, it ships one additional file:
`modules/<nn>_<name>/TUTOR_GUIDE.html` — a single self-contained page that
tells the tutor everything there is to know about the module. Exemplar:
`modules/01_market_universe/TUTOR_GUIDE.html`.

The guide is a **compilation, not new authorship**: every sentence is
drawn from the module's reviewed pack files. It is therefore excluded from
the review ledger (the sources carry the review), but it must be
regenerated whenever any pack file changes — the footer carries the
compile date.

## Required sections, in order

1. **Header** — module number/title, one-line scope, badges: review
   status, total learner time, module artifact, mastery rule.
2. **At a glance** — module promise, the habit/operating rule it installs,
   learner-time table by layer, completion evidence, authoring boundary
   (the no-recommendation disclaimer, always present).
3. **Run of show** — the timed segment table (time, segment, learner
   action, evidence) plus the opening-script anchor and any timing
   flex rules.
4. **Concept arc** — the module's argument in numbered moves, each with
   its canonical analogy, so the tutor can teach from structure rather
   than reading pages aloud.
5. **Terms and analogies** — the module's glossary rows: term, approved
   spoken gloss, canonical analogy. Source of truth stays GLOSSARY.md.
6. **Dated facts** — every changing fact taught, with value, as-of date,
   and primary-source link; the pre-teaching refresh checklist; the
   never-invent-a-number rule. This section is mandatory whenever the
   module states any market statistic.
7. **Live walkthrough** — timed screen-by-screen sequence with the
   teaching move per screen, plus the red-flags list (things to stop and
   correct if the tutor hears themselves say them).
8. **Answer keys** — every worksheet part with answers (including worked
   math), the quiz key with mastery and remediation rules, the exit-ticket
   standard, and the model version of the module artifact.
9. **Misconception playbook** — the learner questions most likely to come
   up, each with the full spoken response.
10. **Guardrails** — the Always / Never lists.
11. **Review status** — the rubric scoreboard from REVIEW.md.
12. **Production status** — what is drafted/reviewed vs still to produce
    (diagrams, screenshots, recordings), from ASSETS.md.
13. **Pack files** — one-line map of every file in the module folder.

## Build rules

- Self-contained HTML: inline CSS, no external assets, no JavaScript
  needed (a sticky table-of-contents nav with anchor links suffices).
- Match the Marketworks-adjacent style of the exemplar (light ground,
  teal accent, readable at 14–15px, tables for enumerable facts).
- No emojis. No content that isn't in a reviewed pack file. Answer keys
  and fixture numbers must match the pack byte-for-byte where quoted.
- Every dated fact keeps its date and source link exactly as sourced.
- The compile date appears in the header line and footer.
