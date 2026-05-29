# TDD review — looking at the insight-engine branch with a test-first lens

> *Drafted 2026-05-28, pause for reflection between Phase 4.3 and Phase 4.4.*

This document does three things:

1. **Honest assessment** — how the work *actually* happened on this branch
   vs. how it would have happened under TDD discipline
2. **What TDD would have changed** — concrete examples, not generalities
3. **Pragmatic adoption** — how to introduce TDD from where we are now
   without rewriting six weeks of work into red-green-refactor theater

---

## 1. How the work actually happened

**Honest answer: code-first, with tests written immediately afterward as
characterization or sanity tests.** This is the dominant pattern across all
261 insights tests.

Concrete examples:

| Work | Test pattern |
|---|---|
| `breadth.py` | Code first → 13 tests verify schema, value ranges, cache mechanics |
| `regime.py` | Classifier built → 17 tests verify it returns STRESS for March 2020, TREND_BULL for Oct 2021 |
| `concentration.py` | Engine built → 14 tests verify weight loading, sort invariants, JSON shape, COVID-day shape |
| `subgroups.py` | Module built → 13 tests verify membership integrity, snapshot shape, 2018 NBFC episode |
| `commentary.py` | Phrase tables built → 33 tests check jargon-free output, headline shape, parametrised phrase mappings |
| `watchlists.py` patterns (5.A) | Detectors built → assertions check entries exist + have required fields |
| `learn/` explainers | TypeScript content authored → build verifies they prerender |

There were **two genuine exceptions** that came close to TDD discipline:

1. **Analog validity study** (`tasks/insight_engine/ANALOG_STUDY.md`) — the
   user pushed back on the analog forward-return content, asked for a side
   study, the study failed the spec ("does this beat baseline drift?"), and
   the feature was retired. The study *was* the spec; the spec was written
   independently of the feature. That's TDD-shaped.
2. **Phase 4.2 pattern validity studies** (`pattern_validity_study.py` +
   `PATTERN_VALIDITY/*.md`) — the same pattern, formalised. Detector built,
   then a separate validity harness with a clear promotion rule
   (excess ≥ 1.0pp AND direction lift > 0 at 20d) decides whether the
   feature is published with forward-return narrative, "names-only", or
   not at all. `pullback_to_50dma` failed the spec and was not shipped to
   the UI.

Both exceptions share one property: **they apply to claims about future
returns**, which is where being wrong has the worst cost. The discipline
self-selected to the highest-stakes part of the system.

---

## 2. What TDD would have changed

### Where it would have helped — with examples

#### A) Threshold tuning (commentary engine)

The phrase tables in `commentary.py` use thresholds that are partly arbitrary:

```python
def _stress_band(score: float) -> str:
    if score >= 80: return "panic / capitulation territory"
    if score >= 60: return "elevated stress"
    if score >= 40: return "moderately elevated"
    if score >= 20: return "calm"
    return "very calm"
```

These bands are checked by tests:
```python
@pytest.mark.parametrize("score,kw", [
    (95, "panic"), (70, "elevated"), (50, "moderately"),
    (30, "calm"), (10, "very calm"),
])
def test_stress_band(self, score, kw): ...
```

**The test confirms the implementation matches the implementation.** It doesn't
verify the thresholds are correctly placed for real readers. A TDD approach
would have started with: *"given these sample stress scores from canonical
historical days, which English phrase would a reader find most informative?"*
That conversation would have happened **before** writing the function, and
the test cases would have been the boundary days from history (Mar 2020
panic should map to "panic"; Oct 2017 calm should map to "very calm").

#### B) Edge cases in pattern detectors

`get_breakouts` returns stocks closing above their 20-day high AND above
their 50-DMA. The current test ("returns valid entries") doesn't pin:

- What happens if a stock has exactly 50 days of history (boundary)?
- What happens if today's close ties the 20-day high (tie-breaking)?
- What happens if 50-DMA equals today's close (boundary)?
- What if the stock has an NaN value in the lookback window (data hygiene)?

Under TDD, those edge cases would have been written as failing tests FIRST,
forcing a deliberate decision on each.

#### C) Numeric attribution math (concentration)

`concentration.compute_concentration` has subtle math: `contribution_bps =
weight * return * 100`. Edge cases:

- What if `nifty_return_pct` is exactly 0 (division)? — Currently handled
  with a 1e-6 epsilon, but no test pins that specifically.
- What if a constituent's prev close is 0? — Currently skipped, no test.
- What if `share_of_move` exceeds 100% (one stock contributing more than the
  index move, offset by negative contributors)? — Common in flat-index days;
  no test pins the expected UI behaviour.

#### D) Regime transitions

The classifier has 3-day confirmation smoothing. Tests verify "COVID is
STRESS" but don't construct synthetic input panels to verify:

- A 1-day border crossing should NOT flip the regime
- A 3-day persistent crossing SHOULD flip the regime
- The transition-day classification should match `prev_regime` correctly

These would be straightforward TDD tests with hand-crafted input dataframes.

#### E) Subgroup spread direction conventions

`SubgroupSpread.spread_60d_pp` is defined as `group_a - group_b`. The
commentary engine reads this and decides leader/laggard. There's a
sign-convention assumption that's currently only enforced by reading the
code. TDD would have specified: "given pair `(private_banks, psu_banks)`
with `private_banks.rs_60d = +5%` and `psu_banks.rs_60d = -3%`, expect
`spread_60d_pp == +8.0` and the spotlight to say 'private banks have
outpaced PSU banks'".

### Where TDD would NOT have helped much

- **Content authoring** (12 inline learn explainers, 38-term glossary,
  pattern guides). The output IS the spec. A test for "does the explainer
  exist" is just a build check; a test for "is the prose good" needs a
  human.
- **UI structure pages** (Pulse, Sectors, Watchlists). The current pages are
  structure-only awaiting design integration. Visual layout work doesn't
  map cleanly to assertion-based tests.
- **The validity studies themselves**. The harness IS the test. You can't
  TDD a TDD harness recursively.
- **MarketReading orchestrator**. It composes — no logic of its own beyond
  field plumbing. The composition test ("all expected keys present") is the
  only meaningful test, and we have it.
- **Refactors** (e.g., moving fabricated weights → dated factsheet snapshots).
  The behavioral contract didn't change; tests caught the field-name change
  via existing assertions.

### What TDD would NOT have caught

- **The fabricated weights episode (L1 in RESULTS.md).** TDD ensures the code
  behaves as specified — it does not ensure the data inputs are real. A TDD
  test for `load_weights()` would have asserted "loads 50 rows summing to
  100", which the fabricated CSV passed. The discipline that catches that
  failure mode is provenance hygiene, not TDD.

---

## 3. Pragmatic adoption — TDD from here

**Three options on the table, in order of cost:**

### Option A — Retrofit nothing; apply TDD discipline to new work only
- **Cost:** zero retroactive; small adjustment to forward workflow
- **Coverage:** future detectors, future thresholds, future engines
- **Risk:** existing 261 tests stay characterization-shaped (encoding what's
  built, not what *should* be built)
- **Honest verdict:** what most teams actually do, and it's defensible

### Option B — Surgical retrofit on the highest-stakes paths (recommended)
- **Cost:** ~4-6 hours of focused work
- **Coverage:** A targeted audit upgrades the ~6 highest-stakes tests from
  characterization to specification, plus a written TDD policy for going
  forward
- **Risk:** discipline can decay if not periodically re-affirmed

### Option C — Full retrofit (not recommended)
- **Cost:** 1-2 weeks
- **Coverage:** every existing function gets a specification-first test
- **Risk:** most of the work would be theater; the genuine value is concentrated
  in maybe 10-20% of the surface area

**Recommendation: Option B.** Concrete implementation below.

---

## 4. Concrete implementation — Option B

### Step 1 — Write a TDD policy document (30 min)

`tasks/insight_engine/TDD_POLICY.md`. Single page, defining:

- **In-scope for TDD discipline:**
  - New computational engines in `kite-api/app/insights/` (e.g., upcoming
    `cross_asset.py`, `fii_dii.py`, `calendar_content.py`)
  - New pattern detectors in `watchlists.py`
  - New threshold / classifier functions in `commentary.py`
  - New forward-return claims of any kind (validity study IS the spec)
- **Out-of-scope:**
  - Content authoring (learn explainers, glossary)
  - UI structure / layout
  - Pure refactors
  - Orchestrator field-plumbing
- **The default new-work loop:** write a spec test that imports something
  that doesn't exist yet → see the import error → write the minimum to make
  it import → see the assertion fail → write the minimum to make it pass →
  refactor with tests green.

### Step 2 — Identify the 6 highest-stakes existing functions and harden them (3-4 hours)

These are the ones where being wrong has the highest cost or the contract is
subtlest:

1. **`commentary._stress_band` + `_vix_z_descriptor`** — directly drives
   reader-facing language. Replace the current "implementation echo" tests
   with tests that pin a small canonical table of (historical date, expected
   phrase) tuples that we'd actually defend in code review.
2. **`concentration.compute_concentration`** — edge cases when index move is
   near zero, when a constituent has stale data, when weights don't sum
   exactly to 100 pre-normalisation. Write 3-4 hand-crafted test fixtures.
3. **`watchlists.get_breakouts`** + new detectors — synthetic price panels
   that should and shouldn't fire each detector. Forces tie-breaking
   decisions into the test.
4. **`regime`** transition smoothing — synthetic input panels covering 1-day
   border crossings, 3-day persistent crossings, 2-day transitions that
   shouldn't flip.
5. **`subgroups.get_sibling_spreads`** — sign-convention test with a
   constructed snapshot fixture.
6. **`stress.compute_stress_panel`** — boundary cases when one of the four
   components is missing (e.g., dispersion can't be computed early in the
   series). Currently behaviour is implicit; pin it.

For each, the playbook is identical:

```python
# 1. Write the spec test first, deleting or commenting out the existing
#    characterization test.
# 2. Run it — it should pass (the code already works for this case).
# 3. If it FAILS, that's the genuine surprise — investigate before fixing.
# 4. Add 2-3 edge cases the spec doesn't yet pin.
# 5. Run again. Anything that fails is a real bug; anything that passes
#    is now genuinely specified.
```

The retrofit is **a deliberate re-think of what each function should do**,
expressed as tests. The existing implementation is the prior art; the new
tests are the spec. **If the test and the implementation disagree, the test
wins** — that's how you turn characterization into specification.

### Step 3 — Apply TDD to Phase 4.4 in real time (next session)

The unblocked next phase is 4.4 (anniversary / calendar). Drive that one
fully TDD: write the spec test for `calendar_content.get_on_this_day(date)`
before the function exists. Use the practice to validate the policy.

### Step 4 — Capture the discipline in CI (10 min)

Add a brief note to `CLAUDE.md` and the workflow playbook in
`.claude/workflows/` so future sessions default to the new policy on
in-scope work.

---

## 5. What this branch should NOT do

- **Don't try to be 100% TDD-after-the-fact.** Most of the high-value retrofit
  is on six functions. The other 250+ tests are fine where they are.
- **Don't gate the design integration on this work.** TDD discipline applies
  to backend / data / engine code. The dashboard's structure-only state is
  waiting for content/design work that doesn't benefit from the discipline.
- **Don't conflate TDD with validity studies.** The validity protocol
  (`PATTERN_VALIDITY/`) is its own thing — empirical evidence on
  forward-return claims. TDD is structural specification on code behaviour.
  Both are good; neither replaces the other.

---

## TL;DR

- The branch was 95% code-first, with characterization tests written after.
- The 5% that wasn't (validity studies) was where it mattered most — claims
  about future returns.
- Full retrofit isn't worth it. Surgical retrofit of 6 high-stakes functions
  + a written TDD policy for new work is the right answer.
- Cost: ~4-6 hours total. Value: the next computational engine ships with
  intent-shaped tests, not behavior-shaped tests.

The deeper observation: **TDD-after-the-fact is a different (and usually
lesser) thing than TDD-first.** Pretending otherwise is theater. The honest
move is to apply the discipline going forward where it actually adds value,
and to harden the few existing paths where being wrong would hurt the most.
