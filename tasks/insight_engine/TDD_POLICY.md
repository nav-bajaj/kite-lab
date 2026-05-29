# TDD policy — insight-engine (and onward)

Adopted 2026-05-28 following the review in `TDD_REVIEW.md`. Scope is the
quant-analytics surface of the codebase (`kite-api/app/insights/`,
`scripts/insights_*`, and any related research probes). Other parts of the
repo continue to follow CLAUDE.md general practice.

---

## In-scope — TDD discipline is the default

For any of the below, write a **failing spec test first**, then the minimum
code to make it pass, then refactor with tests green:

1. **New computational engines** in `kite-api/app/insights/` — e.g.
   `cross_asset.py`, `fii_dii.py`, `calendar_content.py`. The spec test
   says what the engine returns for a small, hand-crafted input, *before*
   the engine is implemented.

2. **New pattern detectors** in `watchlists.py` (or anywhere else). The
   spec test constructs a synthetic price panel that should fire the
   pattern and one that should not. Tie-breaking and boundary behavior are
   pinned in the test, not discovered in code.

3. **New threshold / classifier / phrase-table functions** in
   `commentary.py` and similar. The spec test enumerates canonical
   `(input, expected_output_phrase)` pairs derived from external
   requirements (user-facing wording, historical examples), not from
   reading the function.

4. **New forward-return claims** of any kind — anything the UI presents
   as "X has historically returned Y%". The validity study at
   `tasks/insight_engine/pattern_validity_study.py` IS the spec.
   Promotion rule: excess ≥ 1.0pp AND direction lift > 0 at 20d → live
   with forward-return narrative; excess ≥ 0.3pp + positive direction
   lift → names-only; otherwise → not surfaced.

5. **New numeric invariants** — e.g. "subgroup spread sign convention is
   group_a - group_b", "weights normalize to exactly 100 on load",
   "concentration table sorted by absolute contribution descending". Each
   invariant gets a dedicated assertion before any consumer relies on it.

## Out-of-scope — TDD is not the right tool

For these, write what tests make sense after the work, but don't pre-write
spec tests:

- **Content authoring** — Learn explainers under
  `kite-dashboard/src/content/insights/learn/`, glossary entries, pattern
  guides. The prose IS the spec; review by reading.
- **UI structure / layout pages** under `kite-dashboard/src/app/insights/`.
  Visual layout doesn't map to assertions; verify by running `next build`
  and looking at the result.
- **Orchestrator field-plumbing** — `MarketReading.to_dict()`, API route
  shaping. One "all expected keys present" test is the spec; no need to
  TDD the wiring.
- **Pure refactors** — moving files, renaming, restructuring. Existing
  tests are the safety net; if they pass, the refactor is correct.
- **One-off research probes** in `tasks/<name>/` that won't ship to
  production.

## The default new-work loop

When working on an in-scope item:

1. Write the failing spec test. It should fail because of an import error
   (the thing you're testing doesn't exist yet) or because the assertion
   is making a claim the code hasn't been written to satisfy.
2. Run it. **See the failure with your own eyes.** This is not optional —
   if you skip seeing red, you can't tell whether your test was vacuously
   passing.
3. Write the minimum implementation that makes the test green.
4. Run again. Confirm green.
5. Add 2-3 edge cases the spec doesn't yet pin (boundary, tie, missing
   data). Each one fails first, then passes.
6. Refactor with all tests green if the implementation has gotten ugly.

## Existing characterization tests

The 261 insights tests on this branch as of 2026-05-28 are mostly
characterization tests — they pin what the code *does*, not what it
*should* do. That's defensible; redoing them is not worth the cost. **Six
high-stakes paths** have been promoted from characterization to
specification on this same date — see the retrofit log in `RESULTS.md`
once it ships. Everything else is left as-is until something forces a
re-think.

## Validity studies vs TDD

These are different disciplines. Don't conflate.

- **TDD** specifies *code behavior* — given input X, the function returns
  output Y. Catches structural bugs.
- **Validity study** verifies *empirical claims* — given pattern detector
  X, do its firings historically beat the unconditional baseline? Catches
  feature-publication bugs.

Both are needed; neither replaces the other. The pattern validity harness
at `tasks/insight_engine/pattern_validity_study.py` is the canonical
example of the empirical side. The retrofit work in TDD_REVIEW.md Step 2
is the canonical example of the structural side.

## When to ignore this policy

Three legitimate cases:

1. **The user explicitly says "just ship it"** in a session — discipline
   yields to direction.
2. **A failing test would block a critical hotfix** — ship the fix, write
   the regression test in the next commit, log the gap.
3. **The behavior is genuinely emergent / hard to specify in advance** —
   e.g. tuning a classifier threshold to match human aesthetic judgment.
   In that case, ship code-first and then ask: "what is the smallest set
   of historical examples I would defend in code review?" That set is the
   specification.

Any other deviation should be flagged in chat with the rationale.
