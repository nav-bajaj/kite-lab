# §0 — eligibility diagnostic, 2026-09-11

129 monthly rebalances, 2016-01-01 to 2026-09-01, point-in-time Nifty 250,
MM's standing score window (252/21) and eligibility rule (>= 219 priced
sessions). Close-to-close forward returns; indicative, not P&L.

Run: `python tasks/residual_momentum/lib/diag_eligibility.py`

## What a longer estimation window would cost

Mean Nifty 250 members per rebalance 250.5, scoreable under MM's rule 246.7.

| | RM-24 (504 sessions) | RM-36 (756 sessions) |
|---|---|---|
| Dropped from the scoreable pool | 7.8 (3.2%) | 14.8 (6.0%) |
| Dropped from the top-45 buffer | 1.64 (max 8) | 3.21 (max 11) |
| Dropped from the top-25 book | 1.00 (max 5) | 2.08 (max 9) |
| Rebalances with zero names dropped | 28% | 13% |
| Median rank of a dropped name | 18 | 17 |

The attrition is real and it is not at the margin. Under RM-36 roughly **8%
of the book** is structurally unavailable, in 87% of months, and the median
excluded name ranks 17 — inside the core of a 25-name book, not at the
rank-44 edge where an exclusion would be free.

Attrition is concentrated in 2018-2022 (5-7 buffer names per month under
RM-36) and is mild at both ends of the sample, which is what the
reconstitution and IPO calendar implies.

## The names are exactly the ones the premise named

Most frequently excluded under RM-36, with mean 12-month forward return:

| Symbol | Months | Median rank | fwd 12m |
|---|---|---|---|
| VBL | 20 | 29.5 | +23.6% |
| GUJENERGY | 18 | 16.0 | +71.2% |
| ATGL | 17 | 6.0 | +194.9% |
| ADANIGREEN | 16 | 1.0 | +166.0% |
| LTM | 15 | 6.0 | +7.0% |
| DMART | 14 | 21.0 | +18.9% |
| MAXHEALTH | 14 | 17.0 | +32.1% |
| LTTS | 14 | 20.0 | +1.1% |
| IRCTC | 14 | 23.5 | +53.0% |
| POLYCAB | 14 | 20.0 | +34.4% |

Post-2016 mid-cap growth listings, as expected. ADANIGREEN sits at median
rank 1 and ATGL at 6 — these would have been top book positions.

## But the forward-return claim does not survive de-overlapping

The headline looks decisive and is not:

| | RM-24 | RM-36 |
|---|---|---|
| fwd 12m, mean excess over buffer | +6.06 pp | +9.55 pp |
| fwd 12m, **median** excess | +2.01 pp | +2.58 pp |
| Excluded beat the buffer at | 54% of rebalances | 55% |
| fwd 12m, **non-overlapping** (every 12th) | **−2.68 pp** (4/8 positive) | **+0.96 pp** (4/10 positive) |
| fwd 1m, mean excess | −1.42 pp | +0.54 pp |

129 monthly rebalances over 10.7 years give only ~10 independent 12-month
windows. Sampling every 12th rebalance, the RM-36 edge falls from +9.55 pp
to +0.96 pp, positive in 4 of 10 — and RM-24's goes negative. The mean is
carried by ATGL and ADANIGREEN during one 2020-22 episode, counted
repeatedly across overlapping windows. Median excess is ~2.5 pp against a
55% hit rate, and at the 1-month horizon the sign is not even stable between
the two rules.

The mixed tail supports this reading: ENDURANCE −11.9%, DALBHARAT −15.3%,
HDFCAMC −0.6%, LTTS +1.1%.

## Conclusion

The premise is **half confirmed, and the half that holds is the one that
matters less for the argument but more for the decision.**

- Confirmed: a 36-month history requirement bites, it bites every month,
  and it bites in the middle of the book. The names it removes are exactly
  the mid-cap growth listings named.
- Not confirmed: that excluding them costs return. On the only
  near-independent test available the excess is ~1 pp on a coin-flip hit
  rate, and it rests on one Adani episode. Anyone quoting the +9.55 pp is
  quoting an overlap artifact.

This does not change the plan, but it changes the reason. The case for
RM-12 is not "we would miss winners" — that is not demonstrable here. It is
that RM-12 costs **nothing**: it scores off the same 252/21 window MM
already requires, so it distorts nothing, while RM-24 and RM-36 impose a
structural ~8% book distortion for reasons unrelated to the signal.

That sets the §2 bar asymmetrically, and it is the useful output of §0:
**RM-12 needs only to match RM-24/RM-36 on score quality to be preferred.
The longer windows have to beat it by enough to earn the distortion they
impose.** Had the forward-return gap been real, the longer windows would
have started with a handicap to overcome; they do not, but neither do they
get the benefit of the doubt.

Also worth carrying into §2: ADANIGREEN at median rank 1 under a rule that
would have excluded it is a concentration observation as much as a
missed-return one. Whether a book wants that position at that size is a
separate question from whether the score can see it.
