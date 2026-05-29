# Validity protocol for forward-return claims

> *Authored 2026-05-29 as Phase 5.D of the insight-engine roadmap.
> Formalises the discipline that emerged from the analog-feature
> retirement (`ANALOG_STUDY.md`) and the Phase 4.2 pattern validity
> studies (`PATTERN_VALIDITY/`).*

## Why this exists

In an Indian-equity panel that averages ~+10%/yr drift, any randomly
chosen historical bucket of dates will show a positive forward-return
distribution. **"Stocks in setup X gained Y% over the next N days
historically" is almost meaningless without comparing to the
unconditional baseline.**

We learned this the hard way: the analog forward-return content (10
historical KNN neighbors, median forward return as a "prediction")
shipped to the dashboard in May 2026. It read as a forecast. A
validity study showed IC near zero at 20d and direction lift actually
*negative* at 60-120d. We retired the feature.

This document codifies the rule so it doesn't happen again.

---

## Scope — what triggers the protocol

The protocol applies to **any feature that publishes a forward-return
claim** — anything where a subscriber reads a number or phrase that
could be interpreted as "X has historically returned Y% over the next
N days." Examples:

- Pattern watchlists' fwd-return narrative (e.g., "multi-year breakouts
  have outpaced the baseline by +1.4pp at 20d")
- Conditional-distribution content in the Daily Quant Note's
  "Historical base-rate" paragraph
- Analog-style "similar historical days saw X" content
- Validity-tested sector / subgroup / cross-asset claims
- Anything new that says "historically, when X, then Y"

The protocol does NOT apply to:

- Plain **observations** ("Stock X just broke out of a 5-year base")
- **Regime / stress / breadth state** statements without forward
  inference ("Stress is at 87/100 — panic territory")
- **Educational content** that teaches an indicator's construction
  without predicting outcomes
- **Sentiment / commentary** about the present rather than the future

---

## The checklist

A forward-return claim ships ONLY when all of the following hold:

| # | Check | Threshold |
|---|---|---|
| 1 | Sample size | n ≥ 100 historical observations in the bucket (200+ preferred) |
| 2 | Baseline excess at the headline horizon | mean(fwd_returns) − mean(unconditional_fwd_returns) ≥ +1.0pp |
| 3 | Direction lift at the headline horizon | P(fwd > 0 \| condition) − P(fwd > 0 \| unconditional) > 0 |
| 4 | Sign consistency | The excess has the same sign at 5d / 20d / 60d — no flipping |
| 5 | Survivorship hygiene | Bucket built from data available AT THE TIME, not in hindsight |
| 6 | Persistence | Excess persists when sample is split into rolling halves of the panel (no single regime drives it) |

**If only some pass:** publishing falls back to one of two weaker
tiers, each with its own framing rules.

### Promotion tiers

| Tier | Conditions | What gets published | UI badge |
|---|---|---|---|
| **Validated** | All 6 checks pass | Names list + forward-return narrative + excess-pp + direction-lift figures | `validity-tested ✓` (green) |
| **Names-only** | Direction lift > 0 AND \|excess\| < 1.0pp BUT > 0.3pp, OR n in [100, 200) | Names list, NO forward-return claims in copy. Footer: "Validity-tested but baseline excess is modest" | `names-only · no fwd-return claims` (amber) |
| **Not surfaced** | Excess ≤ 0 OR direction lift < 0 OR n < 100 | Feature does not appear in production UI | — |

---

## The harness

The reference implementation is at
`tasks/insight_engine/pattern_validity_study.py`. It accepts any
detector function with signature `f(asof) -> list[WatchlistEntry]` and:

1. Samples ~165 historical dates (every 21 trading days, 2012-2025)
2. For each date, captures the top-25 fires
3. Records forward 5/20/60/120-day returns per (date, symbol)
4. Compares against the NSE 500 unconditional baseline on the SAME
   dates (so survivorship + drift are matched)
5. Writes a Markdown report at `PATTERN_VALIDITY/<pattern>.md`

To run for a new pattern:

```python
# in pattern_validity_study.py:
PATTERNS = {
    ...,
    "my_new_pattern": my_module.get_my_new_pattern,
}
```

```
$ python tasks/insight_engine/pattern_validity_study.py my_new_pattern
```

The report at `PATTERN_VALIDITY/my_new_pattern.md` will auto-classify
the result against the tiers above.

For conditional-distribution claims (which use a different shape — one
fixed bucket rather than a daily detector), the relevant module is
`kite-api/app/insights/conditional_dist.py`. See the audit log below.

---

## Audit — existing live forward-return content

### Daily Quant Note · "Historical base-rate" paragraph

**Source:** `conditional_dist.by_regime()` and
`conditional_dist.get_today_conditional()`.

**What's published:** the Daily Quant Note's `_conditional_paragraph`
function says things like *"Across 1293 similar past days in DRIFT
mode, Nifty's median forward 20-day return has been +0.37%, with 54%
of historical observations finishing in positive territory."*

**Audit ran:** 2026-05-29 against the live engine + 16-year joint
panel. Numbers below are real, not synthetic.

| Bucket | n | 20d median | 20d mean | 20d % positive | Tier |
|---|---|---|---|---|---|
| **STRESS regime** | 778 | **+3.00%** | +2.73% | **72%** | ✅ Validated |
| **STRETCHED regime** | 177 | +1.69% | +1.92% | 72% | 🟡 Marginal (n borderline) |
| **TREND_BULL regime** | 1795 | +0.88% | +0.67% | 60% | ✅ Validated |
| **DRIFT regime** | 1293 | +0.37% | −0.10% | 54% | ⚠ Surfaced descriptively |

**Audit findings:**

- The **STRESS regime forward-return claim is the strongest piece of
  conditional content** in the platform. Sample is 778 observations
  over 16 years; 20d median is +3.00% vs an unconditional median
  closer to +0.6%; direction lift +13pp vs unconditional ~59%. This
  IS the "buy panic" thesis and the data backs it.
- **TREND_BULL is mildly validated** — modestly positive across all
  horizons, 60% positive at 20d. Reasonable to surface descriptively.
- **DRIFT is the weakest** — 20d median +0.37% is basically Nifty's
  natural drift. We should NOT claim "DRIFT mode predicts positive
  returns" because it doesn't predict anything beyond baseline. Today's
  copy reads "Nifty's median forward 20-day return has been +0.37%"
  — descriptive, not predictive. ACCEPTABLE under the protocol because
  the copy is not making a directional case; it's reporting historical
  central tendency. Borderline though — worth tightening the
  commentary to make the no-edge nature explicit.
- **STRETCHED** has n=177, below our preferred 200 threshold. The
  forward returns ARE strikingly positive at 60d/120d (median +7.34%
  / +10.65%) but should carry a "small-sample" caveat in copy.

**Action items from audit:**

- [x] Tighten `_conditional_paragraph` copy for DRIFT regime to
      explicitly say "no clear edge vs typical drift" rather than
      leading with the median. *Done 2026-05-29 — see
      `_conditional_paragraph` in `kite-api/app/insights/notes/commentary.py`.
      Spec test at `TestConditionalParagraphSpec` pins the requirement.*
- [x] Add small-sample disclaimer to STRETCHED-regime (or any n<200)
      copy. *Done 2026-05-29 — "limited history, treat this stat as
      directional only" suffix appears when n<200. Spec test pins
      the requirement.*

### Watchlists · validity-tested patterns

| Pattern | n fires (top-25 per date, 2012-2025) | 20d excess | 20d direction lift | Tier |
|---|---|---|---|---|
| multi_year_breakouts | 1783 | +1.41pp | +3.5pp | ✅ Validated |
| sustained_uptrend | 2979 | +0.75pp | +4.9pp | 🟡 Names-only |
| pullback_to_50dma | 3747 | −0.28pp | −0.6pp | ❌ Not surfaced |
| (Original 5 patterns) | — | — | — | Pre-protocol; descriptive only |

Original 5 watchlists (breakouts, rs_leaders, coiled_springs,
stretched, recent_breakdowns) were authored before the protocol was
codified. They publish names without forward-return narrative; their
copy carries the validity-aware framing inherited from the broader
voice rules. **No retroactive validity study has been run on them.**
This is acceptable under the protocol because they don't make
forward-return claims — they describe present-day setups only.

### Concentration · `_macro_spotlight` cross-asset claims

The Phase 4.5 macro spotlight says things like *"the rupee is near
its weakest level of the trailing year (96th percentile within its
trailing year)"*. This is **observation, not prediction** — it
describes the present state, makes no forward-return claim. The
protocol does not apply.

---

## Governance — when to run the harness

| Trigger | Required action |
|---|---|
| Adding a new pattern detector to `watchlists.py` | Run harness BEFORE adding to `get_all_watchlists()`. Add finding to `PATTERN_VALIDITY/`. |
| Adding a new conditional-distribution slice (e.g., `by_sector_breadth_decile`) | Audit-style run on the new slice; document in this file. |
| Changing the unconditional baseline definition (e.g., switching from NSE 500 to Nifty 100) | Re-run all existing studies. Stale baselines compromise excess-pp comparisons. |
| Modifying a detector's filter logic | Re-run that detector's study. Even small filter changes can shift the n and excess materially. |
| Quarterly | Spot-audit one live forward-return claim against the latest data. |

---

## Anti-patterns to avoid

1. **"Just publish the names without numbers" when the names list IS
   itself the implicit claim.** A "RS Leaders" list IS a statement
   that these names will outperform; the absence of an explicit
   percentage doesn't relieve the validity burden. Counter-example:
   our existing RS Leaders list is fine because the underlying
   momentum effect at 6-month horizons is one of the best-documented
   findings in cross-sectional equity research (Jegadeesh & Titman
   1993 and many replications including India-specific work).
2. **Cherry-picking the horizon where the excess is strongest.** If
   the claim is "outperforms at 20d," it should also be net positive
   at 5d and 60d. Sign-flipping across horizons (Test 4) usually
   means the effect is fragile.
3. **Re-using the same data for design and validation.** The validity
   study should sample dates from the FULL panel, including the
   period after the feature was designed. If you tuned thresholds on
   2015-2020 data, the validity study must include 2020-2025 too.
4. **Treating "the analog finder retired itself, so we're disciplined"
   as a one-time event.** New features will keep getting proposed.
   The protocol is the ongoing tax, not a single past event.

---

## Cross-references

- `ANALOG_STUDY.md` — original failure case that motivated the
  protocol
- `PATTERN_VALIDITY/{multi_year_breakout, pullback_to_50dma,
  sustained_uptrend}.md` — first three pattern studies under the
  protocol
- `pattern_validity_study.py` — the reusable harness (5.D.1)
- `kite-api/app/insights/conditional_dist.py` — the engine whose
  output is audited above
- `kite-api/app/insights/notes/commentary.py::_conditional_paragraph` —
  the copy layer that surfaces conditional-distribution content
