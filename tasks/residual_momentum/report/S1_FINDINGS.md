# §1 — scores built and sanity-checked, 2026-09-11

129 monthly rebalances, 2016-01-01 to 2026-09-01, point-in-time Nifty 250.
Factors: NIFTY 100 as market, leave-one-out sector as the second factor.

Run: `python tasks/residual_momentum/lib/diag_scores.py`
Score module: `lib/residual.py`

Five arms. M12 and MM are both baselines and answer different questions —
M12 (plain 12-1 total return) is the paper's own comparison arm, MM
(vol-adjusted) is what we actually run.

## Coverage — RM-12's central claim holds

| Score | Names scored per rebalance |
|---|---|
| M12 | 246.7 |
| MM | 246.7 |
| **RM-12** | **246.7** |
| RM-24 | 240.9 |
| RM-36 | 234.3 |

RM-12 scores **exactly** the same names MM does. The PLAN claim that it adds
no eligibility cost is confirmed, not merely argued. RM-24 and RM-36 lose 5.8
and 12.4 names per rebalance.

(These differ slightly from §0's 7.8 and 14.8 because the rules differ: §0
counted total priced sessions ever, §1 requires 86.9% of the trailing
estimation window priced. Same direction, same order of magnitude.)

## The degeneracy tell — PLAN.md's ratio argument is confirmed empirically

Rank correlation against the **skipped** trailing 21 sessions. A residual
score pinned by its own estimation window shows up here as negative — it
inherits minus the residual of whatever part of the estimation window sits
outside the formation window.

| Score | Formation as share of estimation | Tell (mean) | Min |
|---|---|---|---|
| M12 | — | +0.038 | −0.457 |
| MM | — | +0.040 | −0.451 |
| RM-12 | 100%, but reads the intercept | **+0.259** | −0.168 |
| RM-24 | 252/504 = 50% | **−0.168** | −0.486 |
| RM-36 | 252/756 = 33% | **−0.083** | −0.483 |

Monotone in exactly the way PLAN.md predicted. The paper's ratio is 11/36 =
31%, which is RM-36, and RM-36's contamination is the mildest of the two
paper-faithful arms. **RM-24 at 50% carries measurable reversal
contamination** and should be read as a compromised arm in §2, not as a
clean control. RM-12, reading the intercept, shows no negative pinning at
all — the construction does what it was designed to do.

## An unplanned finding worth carrying into §2

RM-12's tell is **+0.259**, far above M12's and MM's +0.04. It is not
degeneracy — the sign is wrong for that — but it means RM-12 tilts toward
names that also rose during the skipped month, six times more strongly than
conventional momentum does.

That partly defeats the purpose of the skip-month, which exists to avoid
short-term reversal. If short-term reversal is live on Nifty 250, RM-12
carries an adverse exposure MM does not. RM-24 and RM-36 tilt the other way
(negative tell), which under reversal would be mildly favourable.

This is a testable §2 question, not a verdict: it may cost RM-12 nothing, or
it may show up as a drag. Flagging it now so it is not read as a surprise
later. A skip of 42 sessions on RM-12 is the obvious sensitivity if it bites.

## What the scores actually are

Mean Spearman rank correlation:

```
        M12     MM   RM12   RM24   RM36
M12   1.000  0.979  0.835  0.551  0.654
MM    0.979  1.000  0.854  0.562  0.662
RM12  0.835  0.854  1.000  0.534  0.654
RM24  0.551  0.562  0.534  1.000  0.830
RM36  0.654  0.662  0.654  0.830  1.000
```

- M12 and MM are near-identical rankings (0.979). The vol-adjustment
  reorders very little on this universe. Useful to know independently: it
  means MM's edge over plain momentum is not coming from the ranking.
- RM-12 is a **tilt** on conventional momentum (0.835 / 0.854), not a
  different signal. Expect a modest delta in §2, not a transformation.
- RM-24 and RM-36 are genuinely different signals (0.55-0.66 against MM) and
  resemble each other (0.830) more than either resembles momentum. Whatever
  they do in §2, they will do it for different reasons than RM-12.

## Implementation notes

- **Sector factor is leave-one-out.** Without it a thin sector regresses a
  stock partly on itself and the residual collapses toward zero. Stocks whose
  sector has fewer than 2 other priced members that day fall back to
  market-only.
- **Sector factors are built from point-in-time members only.** Building them
  over every symbol in the panel pulled in listing-day artifacts on names not
  in the universe at the time — CHEMPLASTS prints +3507% on 2021-08-24, which
  would have corrupted its sector's mean for a year. Fixed before any result
  above was produced.
- **Sector labels are not point-in-time.** `load_sector_map` returns one
  label per symbol, the latest snapshot in the highest-priority scheme. This
  is the same map the engine's sector cap uses, so the two agree, but a name
  that changed sector carries its current label backwards. Inherited
  limitation, not introduced here.
- **No winsorising.** A single ±58% session (YESBANK, March 2020) leans on a
  231-day fit. The score divides by residual sd, which partly self-corrects.
  Left as a §2 sensitivity rather than a parameter.
- **Accelerate BLAS emits spurious matmul FP warnings** on this machine.
  Verified cosmetic: zero non-finite or exploded betas across 95k fits, and
  `X @ beta` is bit-identical to the elementwise product. Suppression is
  scoped to `residual.py`.
