# Results — price-cap study (Phase 2)

Run 2026-09-06. Panel `nse500_data` through 2026-08-21, start 2020-01-01.
Three production portfolios tested against a Rs 4,000 per-share entry
ceiling. **No production config was changed.**

Reproduce:
```
python tasks/minimum_capital_2026/om25_cap_sweep.py --caps 1000 2000 3000 4000 6000 8000 12000
python tasks/minimum_capital_2026/om25_cap_placebo.py --n-seeds 40 --cap 4000
python tasks/minimum_capital_2026/om25_cap_placebo.py --n-seeds 30 --cap 2000
python tasks/minimum_capital_2026/l6_combo_cap_study.py --cap 4000 --placebo-seeds 30
python tasks/minimum_capital_2026/price_decile_study.py
python tasks/minimum_capital_2026/forced_exit_audit.py --cap 4000
```

## Bottom line

| portfolio | baseline CAGR | cap Rs 4,000 | delta | verdict |
|---|---|---|---|---|
| COMBO Defensive | 45.63% | 45.81% | +0.18pp, MaxDD -16.4% -> -14.7% | free on the numbers; **but see the forced-exit section** |
| OM25 v3 | 42.31% | 43.03% | +0.72pp | free; grandfathers winners correctly |
| L6 v2 | 50.28% | 48.93% | **-1.35pp**, MaxDD -29.9% -> -33.9% | a real cost |

The cap moves the minimum viable ticket from ~Rs 10L to ~Rs 2L. Ranked by
how cleanly it works: **COMBO > OM25 > L6.**

---

# Part A — OM25 v3

## Validation

The uncapped arm reproduces production to 0.008%:

| | end value | CAGR |
|---|---|---|
| production run `om25_v3_portfolio_20260823_172947` | Rs 7,278,614 | 42.30% |
| this harness, uncapped | Rs 7,279,214 | 42.31% |

## Headline: a price cap costs nothing measurable

| arm | CAGR | Sharpe | MaxDD | vol | end value | buys |
|---|---|---|---|---|---|---|
| baseline (no cap) | 42.31% | 1.70 | -25.32% | 21.9% | 7,279,214 | 469 |
| cap Rs 1,000 | 44.95% | 1.76 | -22.48% | 22.7% | 8,072,267 | 345 |
| cap Rs 2,000 | 47.71% | 1.91 | -23.51% | 22.4% | 8,977,278 | 386 |
| cap Rs 3,000 | 45.06% | 1.81 | -24.16% | 22.2% | 8,107,132 | 415 |
| **cap Rs 4,000** | **43.03%** | **1.73** | **-27.03%** | 22.0% | 7,488,992 | 431 |
| cap Rs 6,000 | 41.58% | 1.67 | -26.21% | 21.9% | 7,072,733 | 455 |
| cap Rs 8,000 | 42.58% | 1.71 | -24.69% | 21.9% | 7,359,111 | 460 |
| cap Rs 12,000 | 42.62% | 1.72 | -24.81% | 21.9% | 7,369,483 | 461 |

The sweep is **non-monotonic**: Rs 6,000 looks worse than baseline while
Rs 12,000 (which blocks almost nothing) does not converge back on it.
Some of this spread is path-dependence — dropping any name changes cash,
entries and every later rebalance, and those differences compound. But
the tight-cap arms turn out to have a second, real cause; see below.

## The placebo: Rs 4,000 is noise, Rs 2,000 is not

Excluding a RANDOM set of names the same size each cap blocks, everything
else identical:

| cap | names blocked | random-exclusion CAGR (mean / sd / range) | the cap's CAGR | verdict |
|---|---|---|---|---|
| Rs 4,000 | 56 | 41.07% / 3.06pp / 34.37-45.51% (40 seeds) | 43.03% (~p65, z=+0.6) | **inside noise** |
| Rs 2,000 | 105 | 38.33% / 3.73pp / 31.02-44.12% (30 seeds) | 47.71% (above max, z=+2.5) | **outside noise** |

Note the random mean *falls* from 41.07% to 38.33% as more names are
excluded at random — losing opportunity hurts. Excluding the same number
*by price* helped. That is a real effect, and it needed explaining.

### The Rs 2,000 edge is a low-price (size) tilt, not skill

Forward 63-day return by price decile across the Nifty 250, 148
rebalance dates, 2021-2026:

| decile | median price | mean fwd 63d |
|---|---|---|
| 1 (cheapest) | Rs 63 | +9.63% |
| 2 | Rs 145 | +9.06% |
| 3 | Rs 268 | +7.46% |
| 5 | Rs 666 | +6.67% |
| 7 | Rs 1,246 | +3.89% |
| 9 | Rs 3,252 | +5.41% |
| 10 (dearest) | Rs 6,514 | +3.67% |

Near-monotonic, +5.96pp per 63 days cheapest-minus-dearest. But it is a
**regime bet, and it has already reversed twice**:

| year | D1 - D10 spread |
|---|---|
| 2021 | +3.16pp |
| 2022 | +13.08pp |
| 2023 | +18.79pp |
| 2024 | **-4.10pp** |
| 2025 | +2.69pp |
| 2026 | **-3.63pp** |

Decile 1 has a median price of Rs 63 — this is the Indian small/micro-cap
cycle of 2021-2023, not a durable price anomaly. A Rs 2,000 cap loads
onto it hard.

**Conclusion: Rs 2,000 must not be adopted.** Not because it is noise —
it is not — but because its edge is an unintended, cyclical size bet that
lost money in two of the last three years. A Rs 4,000 cap keeps the tilt
mild enough to be indistinguishable from noise.

Supporting evidence for the Rs 4,000 arm, same conclusion:
- Daily return correlation baseline vs cap: **0.9908**; tracking error
  2.98%/yr.
- Year-by-year differences alternate sign with no trend: +2.7, +0.7,
  +11.7, -9.4, +2.9, -3.0 pp.
- Trade character is unchanged: win rate 48.5% -> 50.9%, median hold
  77d -> 84d, mean round-trip return 16.6% -> 18.4%.

## What the cap buys: replicability

Applied to the current book at live prices — this is the reason to do it.

| capital | baseline: unbuyable / cash stranded / RMS wt err | Rs 4,000 cap: same |
|---|---|---|
| Rs 1L | 6 names / 32.1% / 50.9% | 0 / 8.1% / 11.5% |
| Rs 2L | 3 / 20.6% / 37.9% | 0 / 4.1% / 6.7% |
| Rs 3L | 2 / 14.4% / 30.1% | 0 / 3.5% / 6.4% |
| Rs 5L | 1 / 9.1% / 21.6% | 0 / 2.2% / 3.1% |
| Rs 10L | 0 / 3.4% / 5.6% | 0 / 0.7% / 1.0% |

Baseline book spans Rs 14 – 34,190 (median Rs 1,130). Capped book spans
Rs 14 – 3,185 (median Rs 413).

**A Rs 4,000 cap moves the minimum viable ticket from ~Rs 10L to ~Rs 2L.**
That is the entire finding: same returns within noise, a fifth of the
entry capital.

## Grandfathering is required, not optional

The cap must gate entry only. Positions bought under the cap that
appreciate through it must be held.

- 15 of 401 round trips (4%) crossed Rs 4,000 while held.
- Those trades earned **Rs 249,957 after crossing = 4.3% of all realised
  P&L**.
- Largest: APARINDS, entered at Rs 984 (2022-06-20), exited at Rs 8,941
  (2024-08-26) — Rs 336,641 of gain accrued above the cap.

A forced-exit-on-breach rule would sell exactly the winners a momentum
strategy exists to hold. The engine's existing grandfather rule
(`_relevant_ranking` retains `s in holdings`) already does this.

## Limitations — read before acting

1. **The panel is split/bonus back-adjusted.** Verified: IRCTC's 1:5
   split (ex 2021-10-29) shows no discontinuity in `nse500_data`.
   Historical panel prices are therefore *lower* than the prices that
   actually traded for any name that later split — and high-priced names
   are the ones most likely to split. The cap is therefore **more
   permissive in the backtest than it would have been live**, and the
   historical blocking rate is understated. Direction of the bias is
   known; magnitude is not, because we hold no split table. Only the
   VEDL 2026-04-30 demerger is tracked in `data/corporate_actions.json`.

2. **A fixed nominal cap tightens over time.** Rs 4,000 was the 94th
   percentile of the Nifty 250 in 2021 and is the 84th today. Names
   blocked rose from 6.4% of the universe (2021) to 16.3% (2026);
   blocked top-25 signal slots went from 34/yr to 114/yr. Over the
   sample the cap was loose for most of the period and is tight now, so
   the measured cost understates the forward constraint. Any adopted cap
   needs an annual review, or should be defined relative to the universe
   (a percentile) or to the advertised minimum ticket rather than as a
   frozen rupee figure.

3. **Any cap is a mild size tilt.** Price correlates with market cap, so
   capping price tilts the book smaller. At Rs 4,000 the tilt is too
   small to detect against noise; at Rs 2,000 it dominates. Expect a
   Rs 4,000-capped book to lag slightly in large-cap-led regimes (as
   price deciles did in 2024 and 2026) and lead slightly in small-cap
   ones. This is an accepted, quantified cost of replicability — not a
   free improvement.

4. **OM25 only.** TL25, L6 and COMBO are untested. L6 and TL25 hold more
   expensive names (NEULANDLAB Rs 23,301) and turn over far faster, so
   the result should not be assumed to carry across.

5. **One universe, one 5.6-year path.** The placebo bounds the noise on
   this path; it does not establish that no price effect exists in
   general — and the decile table shows one that does.


---

# Part B — L6 v2 and COMBO Defensive

## Injection points differ by strategy

**L6 v2** — the score is a cross-sectional z-score over the whole
universe and `run_strategy` takes the top-24 from it, so the cap goes in
`membership_fn`, exactly as for OM25. Score untouched, buy list narrowed,
grandfathering preserved (a held name keeps its true score rank).

**COMBO** — `make_combo_score_fn` truncates EACH component to its top-12
and returns only those 24 names. A membership-level cap would let
expensive names consume component slots and then be filtered out by
`_relevant_ranking`, leaving the book holding **fewer than 24 names** —
an under-invested portfolio, not a fair test. So the cap wraps each
component score_fn to drop capped names from its ranking *before* the
composite truncates. Component scores are computed first and filtered
after, so the L6 z-score and OM25 pct-ranks are identical to production.

## Validation

| | production | this harness | delta |
|---|---|---|---|
| L6 v2 CAGR | 50.45% | 50.28% | 0.17pp |
| L6 v2 Sharpe / MaxDD | 1.76 / -29.89% | 1.76 / -29.92% | — |
| COMBO CAGR | 45.60% | 45.63% | 0.03pp |
| COMBO Sharpe / MaxDD | 2.01 / -16.39% | 2.01 / -16.36% | — |

## Headline

| arm | CAGR | Sharpe | MaxDD | vol | buys |
|---|---|---|---|---|---|
| L6 v2 baseline | 50.28% | 1.76 | -29.92% | 25.8% | 1180 |
| **L6 v2 cap Rs 4,000** | **48.93%** | **1.71** | **-33.88%** | 25.8% | 1163 |
| COMBO baseline | 45.63% | 2.01 | -16.36% | 20.2% | 700 |
| **COMBO cap Rs 4,000** | **45.81%** | **2.04** | **-14.71%** | 20.0% | 697 |

L6 loses 1.35pp of CAGR and 3.96pp of max drawdown. COMBO is unchanged
on return and *better* on drawdown.

Daily return correlation to baseline: L6 0.9925 (TE 3.16%/yr), COMBO
0.9911 (TE 2.68%/yr). Year-by-year differences alternate sign in both;
L6's worst year is 2025 (-3.8pp), COMBO's is 2026 (-2.4pp).

## Placebo: is the L6 cost a price effect?

Random exclusion of the same number of names, everything else identical.

| strategy | universe | names blocked | % | random-exclusion CAGR | cap CAGR | position |
|---|---|---|---|---|---|---|
| OM25 | 262 | 56 | 21.4% | 41.07% (sd 3.06) | 43.03% | +0.64 sd |
| L6 v2 | 534 | 82 | 15.4% | 46.87% (sd 2.77) | 48.93% | +0.74 sd |
| COMBO | 534 | 80 | 15.0% | 42.39% (sd 2.27) | 45.81% | +1.51 sd |

**The right comparison is cap vs random exclusion, not cap vs baseline.**
Removing *any* 82 names costs L6 3.41pp of CAGR on average (50.28 ->
46.87); the price cap costs only 1.35pp. The same pattern holds
everywhere — capping by price consistently beats removing the same
number of names at random:

| strategy | cost of random exclusion | cost of the price cap | cap advantage |
|---|---|---|---|
| OM25 | -1.24pp | +0.72pp | +1.96pp (+0.64 sd) |
| L6 v2 | -3.41pp | -1.35pp | +2.06pp (+0.74 sd) |
| COMBO | -3.24pp | +0.18pp | +3.42pp (+1.51 sd) |

All three point the same way. COMBO's cap beat all 30 random draws
(z=+1.51, p~0.07 alone); OM25 and L6 sit inside their bands. The three
are NOT independent — overlapping universes, the same 5-6 year window,
and COMBO is literally built from L6 and OM25 components — so they
cannot be pooled into a stronger claim. The consistent direction is
best explained by the in-sample low-price premium documented in
`RESULTS.md` (cheapest price decile +9.63% vs dearest +3.67% per 63
days), which **reversed in 2024 and 2026**. Treat the cap's apparent
edge as a size tilt that is currently out of favour, not as alpha.

The L6 cost is therefore **opportunity-set shrinkage, not a price
effect**. But it is a real cost to the product regardless of its cause:
narrowing a 534-name universe by 15% costs L6 more than narrowing a
262-name universe by 21% costs OM25, because L6 has exit_buffer 0 and
depends on picking the very best 24 from a wide field.

Drawdown: L6's cap is -33.88% vs random-exclusion mean -31.54%
(sd 1.78) — 1.3 sd worse, with only 10% of random draws worse. That is
the one number in this study pointing the wrong way; marginal, not
significant, worth watching rather than dismissing. COMBO runs the other
way: -14.71% vs a random-exclusion mean of -16.49% (sd 1.38), better
than 93% of draws.

## COMBO cannot grandfather winners — structural, and it matters

Days a position survives after its price first crosses Rs 4,000:

| arm | n | median | mean | max | exits within 21d |
|---|---|---|---|---|---|
| OM25 cap | 15 | 80d | 111d | 381d | 0% |
| L6 cap | 13 | 31d | 38d | 128d | 31% |
| **COMBO cap** | **17** | **6d** | **18d** | **84d** | **71%** |
| COMBO baseline | 92 | 23d | 45d | 210d | 48% |

COMBO's composite emits exactly 24 names at exit_buffer=0, so a holding
that appreciates through the cap drops out of the composite and is sold
at the next rebalance. OM25 grandfathers fully; L6 partially; COMBO
barely at all.

Full audit (`forced_exit_audit.py --cap 4000`), including the uncapped
arms, which corrects the first reading of this:

| arm | crossings | median days held after crossing | exits <=21d | P&L earned above the cap | % of realised |
|---|---|---|---|---|---|
| OM25 baseline | 67 | 60d | 16% | +Rs 249,982 | 4.4% |
| OM25 cap | 15 | 80d | 0% | +Rs 249,957 | 4.3% |
| L6 baseline | 94 | 21d | 57% | **+Rs 557,888** | **5.1%** |
| L6 cap | 13 | 31d | 31% | -Rs 68,720 | -0.7% |
| COMBO baseline | 92 | 23d | 48% | **+Rs 300,501** | **3.3%** |
| COMBO cap | 17 | 6d | 71% | -Rs 112,825 | -1.2% |

**Above-Rs 4,000 territory was profitable in all three uncapped books** —
4.4%, 5.1% and 3.3% of realised P&L. It is not the case that expensive
holdings "happened to be losers"; the negative figures in the capped arms
are a selected remnant, the handful of names that crossed while held and
were then sold, with the genuine winners never entered at all.

That is the real cost of the cap, and it shows up exactly where expected:
OM25 recovers it elsewhere (net +0.72pp) because it grandfathers what it
does hold; L6 does not (net -1.35pp).

For COMBO the concern is structural rather than in-sample. It gave up
3.3% of P&L in above-cap territory in the baseline and cannot grandfather
a winner through the cap. It came out flat overall this time; a single
APARINDS-type run inside COMBO would expose the mechanism.

## Replication payoff

| capital | L6 baseline (unbuyable / cash / wt err) | L6 capped | COMBO baseline | COMBO capped |
|---|---|---|---|---|
| Rs 1L | 6 / 38.0% / 53.3% | 0 / 18.2% / 23.2% | 1 / 17.3% / 28.2% | 0 / 14.7% / 20.6% |
| Rs 2L | 3 / 25.8% / 39.8% | 0 / 11.8% / 14.8% | 1 / 11.8% / 23.3% | 0 / 8.4% / 11.6% |
| Rs 3L | 2 / 16.9% / 31.0% | 0 / 7.6% / 9.5% | 1 / 8.9% / 21.5% | 0 / 5.1% / 7.1% |
| Rs 5L | 1 / 11.0% / 23.6% | 0 / 3.7% / 5.3% | 0 / 3.3% / 5.8% | 0 / 2.6% / 4.4% |
| Rs 10L | 0 / 5.5% / 10.9% | 0 / 1.8% / 2.6% | 0 / 2.1% / 4.5% | 0 / 1.4% / 2.3% |

L6 book spans Rs 228-23,301 uncapped, Rs 228-3,476 capped. COMBO spans
Rs 14-16,856 uncapped, Rs 14-3,476 capped. Both capped books are clean
from about Rs 2-3L, versus Rs 10L uncapped for L6.
