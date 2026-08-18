# Does the gamma profile help POSITION a trade?

**Date:** 2026-08-18 (after the 08-18 expiry) · **Ledger:** n=15 rows /
16 sessions · **Probe:** `gamma_positioning_probe.py` (+ 25 unit tests)

**REVISED same day at n=15 — see "Correction" below.** The first pass ran
on the 12 sessions `gamma_profile_daily` happened to hold. Backfilling
the profile over every session with greeks (the Stage 2b upgrade this
document argued for) added the three earliest sessions, and the panel's
one positive finding did not survive them.

**Verdict after a full day of testing: four negative results, no usable
gamma signal for positioning, sizing or holding — and a diagnosis of why
that is unsurprising (the measure is unsigned). Three convincing false
positives are recorded below so nobody finds them twice.**

| | Test | Result |
|---|---|---|
| Q1 | centre the straddle on the wall | coin flip, 5/15 |
| Q2 | centre on the prior close's wall | directional bet (r=0.84), not gamma |
| Q3 | concentration slope as risk conditioner | **retracted** — boundary artifact |
| Q4 | concentration level | runs backwards (-0.409), n.s. |
| Q5 | wall stickiness (pre-registered) | **falsified**, Welch t=0.68 |
| Q6 | the regime label the advisory uses | not significant; PIN branch rests on n=1 |

---

## The question

The Stage-2 gamma profile gives us, three times a session, a max-gamma
strike ("the wall"), a concentration, and a total GEX. The obvious
strategic use is positioning: center the straddle on the wall rather
than on spot, because that is where the structure is. This probe tests
that, plus two adjacent uses, against the paper-straddle ledger.

## Method, and the one thing that decides the answer

Four straddle variants, all scored the ledger's way — credit taken at
the **bid**, exit paid at the **ask**, marks in between at closes:

| | Entry | Strike |
|---|---|---|
| **A** | 09:20 | ATM (the ledger baseline) |
| **B** | 10:00 | ATM (entry-time control) |
| **C** | 10:00 | max-gamma strike at 10:00 |
| **D** | 09:20 | prior session's 15:15 max-gamma strike |

B exists only so that C can be read. A and C differ in *two* things
(entry time and strike); B and C differ in **one**, so the paired B-vs-C
comparison is the actual strike-selection test.

**Every conditioning variable must be readable at or before the decision
it informs.** The first pass of this probe ignored that and scored the
whole session's P&L against the 10:00→15:15 concentration change. It
reported `corr = 0.468` and looked like a finding. It was lookahead: a
trade that exits at 15:15 cannot be conditioned on the 15:15 reading.
Re-run honestly — the 10:00→13:00 slope, scoring only P&L earned
**after** 13:00 — the same number is `0.083`. The apparent signal was
entirely the hindsight. `test_split_at_excludes_morning_pnl` is the
regression guard.

## Q1 — Centering on the wall does not beat centering ATM

| Variant | n | Total | Mean | Median | W/L | Worst MAE |
|---|---|---|---|---|---|---|
| A 09:20 @ ATM | 15 | +141.3 | +9.42 | +13.15 | 11/4 | -78.35 |
| B 10:00 @ ATM | 15 | +157.0 | +10.47 | +13.95 | 13/2 | -133.15 |
| C 10:00 @ WALL | 15 | +179.2 | +11.95 | +10.70 | 13/2 | -86.80 |

Paired (B vs C, only the strike differs): **the wall wins 5 of 15**,
mean difference **+1.48 pts** on credits of 80-280. That is a coin flip,
and the effect is far inside the friction the ledger already measures.
The wall's higher total comes with a *lower* median — a couple of large
days, not a repeatable edge. **There is no strike-selection signal
here**, and the extra sessions made the record worse (5/15 vs 5/12), not
better.

## Q2 — The best-looking variant is a directional bet in disguise

Variant D — center on yesterday's closing wall — posts the best numbers
in the study: **+208.5 total, +13.90 mean**, against the baseline's
+141.3. It is spurious, three ways:

1. Head-to-head the baseline **wins 7 to 5** (3 ties). D's total comes
   from margin on a few days, not from being right more often.
2. `corr(D - A, prior-wall offset x spot move) = **+0.838**`. Most of
   the variance is explained by whether spot happened to travel toward
   the strike the stale wall pushed you onto.
3. At n=12 it was 4-4 with `corr = 0.959`; the extra sessions moved the
   head-to-head against it.

Mechanically: a wall left overhead by yesterday's chain centers today's
straddle above spot. In the 08-13/14/17 down-trend that paid three times
running; on 08-18 the identical construction lost **-30.1**. This is a
bet on direction relative to a stale strike wearing a gamma costume, and
at n=11 it is exactly the shape that survives a naive backtest. **Do not
trade it.**

## Q3 — The concentration slope: RETRACTED

Ex-ante test: bucket on the 10:00->13:00 concentration slope (dead band
+-0.01), score only what happens after 13:00.

**At n=12 this looked like the study's one positive result.** Every
building-concentration session held its afternoon drawdown inside -7.05,
while both afternoon blowouts sat outside that bucket. It was reported
here as a tail-risk conditioner.

**At n=15 it is gone.**

| Morning slope | n | P&L after 13:00 (mean / median) | Worst drawdown after 13:00 |
|---|---|---|---|
| building | 6 | +6.44 / +6.55 | **-31.05** |
| flat | 4 | +9.35 / +12.00 | -30.55 |
| decaying | 5 | +10.78 / +5.35 | -51.00 |

- **Return: still nothing.** `corr(slope, P&L after 13:00) = -0.044`.
- **Risk: the separation was an artifact of the truncated history.** The
  building bucket's worst afternoon drawdown moves from -7.05 to
  **-31.05**, level with the flat bucket's -30.55. Only the decaying
  bucket's -51.00 stands apart, and that is the single 08-04 session
  that was already known to be the ledger's worst day.

The session that breaks it is **2026-07-28** — the program's very first
day, the archetype pin. It has the steepest building slope in the whole
panel (+0.104 over the morning, R^2 0.93) and an afternoon drawdown of
-31.05. It is the single most on-thesis "concentration is building"
session on record, and its afternoon was the second-worst measured.

It was invisible to the first pass only because `gamma_profile_daily`
started on 07-31. **The finding was a boundary artifact of where the
profile table happened to begin.**

### Correction

The Q3 result published in the first version of this document should not
be used. It survived one lookahead check (§ "Method") and then failed the
first honest out-of-sample sessions it met — which arrived within hours,
from a backfill this very document requested. Recorded rather than
quietly edited: this is the second false positive in one short study, and
the pattern in both is the same — a small panel whose boundaries were set
by data availability rather than by anything about the market.

### What the upgrade did to the measurement itself

With the per-minute profile the slope stops being a two-point guess:

- Fitted by regression over the ~220-minute morning window, the slope
  carries a standard error. **Median |t| = 14.6**, so it is
  distinguishable from zero on most days — but **median R^2 = 0.49**, so
  a straight line explains only half the movement in the concentration
  path. "Slope" is a weak summary of a genuinely wiggly series.
- **4 of 15 sessions change bucket label** between the two-point estimate
  and the regression.
- On 2026-08-05 the two-point estimate reported *decaying* (-0.012); the
  regression gives a slope indistinguishable from zero (R^2 0.003,
  |t| 0.87). The old method manufactured a direction where the data has
  none. That is precisely the measurement error the upgrade removes —
  it just happens to remove the finding too.

## Q4 — Concentration LEVEL runs the wrong way

- `corr(level at 13:00, P&L after 13:00) = **-0.409**` (n=15)
- `corr(level at 10:00, full-day MAE) = **-0.319**` (MAE is negative, so
  more concentration went with *deeper* drawdowns)

The intuitive reading — high concentration means a pin is forming, so
premium is safer to sell — is **backwards in this sample**. It is
consistent with OBSERVATIONS obs. 39, where the highest concentration
ever recorded (47.6% on the 08-18 expiry) produced no pin at all and
spot settled 45 pts below the wall at the day's low.

## Q5 — Wall stickiness: PRE-REGISTERED, and falsified

The Q3 null has an innocent explanation worth testing: concentration
rising means two opposite things depending on whether the wall is
*standing still* (a pin forming) or *moving* (a trend being chased), and
averaging them would produce exactly the zero we measured.

Thesis: **a growing gamma pile only pins price if the pile is standing
still.** Registered before looking, with a stated kill condition:

- state (09:20-13:00): `beta` of wall on spot — ~0 anchored, ~1 tracking
- outcome (13:00-15:15): does spot move toward where the wall WAS at
  13:00 (reference fixed, or a chasing wall scores as convergence by
  coming to price — the opposite of the claim)
- split at median beta; control for morning range
- **falsified if convergence is the same in both buckets**

Run once, n=37:

| Bucket | n | Mean convergence | Median |
|---|---|---|---|
| sticky | 27 | +6.87 pts | +3.35 |
| tracking | 10 | -2.25 pts | -6.70 |

**Welch t = 0.68. `corr(beta, converge) = -0.092`. Not supported.**

The pre-registered control passed — stickiness is not a quiet-day proxy
(`corr(beta, morning range) = +0.087`) — so that is not the explanation.

Two things make it worse than merely insignificant:

1. **The split was near-degenerate.** beta was exactly 0.000 on **27 of
   37** sessions. Strikes sit on a 50-pt grid and a typical morning range
   is ~100 pts, so the wall usually never moves at all within a morning.
   The state variable barely varies. This costs the test power, and is a
   design weakness rather than a reprieve.
2. **The unregistered confound is fatal to the mechanism.** Wall distance
   from spot at 13:00: **sticky 122 pts, tracking 30 pts.** "Sticky" does
   not mean *anchored magnet holding price*. It mostly means *the wall is
   parked on a big-OI strike far from where price is, so of course it
   does not move.* Converging 6.87 pts out of a 122-pt gap is 5% — noise.

And on expiry days, where the pin should be strongest, spot moved AWAY
from the 13:00 wall on **3 of 4** — including 07-28, the archetype day
that inspired the thesis:

| Session | gap 13:00 | converge |
|---|---|---|
| 07-28 | 4.75 | **-14.55** |
| 08-04 | 5.05 | **-31.50** |
| 08-11 | 55.20 | +5.45 |
| 08-18 | 8.80 | **-24.85** |

07-28 closed 3.7 pts from max pain, but not because an afternoon wall
pulled it there — price and wall were already together at 13:00 and
drifted slightly apart. The thesis was built on that session and that
session does not support it.

*Probe: `wall_stickiness_probe.py` (+9 unit tests, including a regression
guard that a chasing wall must not score as convergence).*

## Q6 — The label the advisory actually branches on

`day_plan.recommend_structure` branches on the 10:00 concentration regime
**first, for 100% of sessions**; concentration is the sole input to that
label. Against the 15 sessions with outcomes:

| 10:00 regime | n | mean P&L | mean MAE |
|---|---|---|---|
| DIFFUSE | 11 | +15.13 | -17.23 |
| MIXED | 3 | -12.75 | -36.15 |
| PIN-GRAVITY | 1 | +13.15 | -19.05 |

Nothing here is distinguishable from noise: `conc vs P&L r=-0.281
(|t|=1.06)`, `conc vs MAE r=-0.230 (|t|=0.85)`. And the branch carrying
the most specific logic — PIN-GRAVITY, which selects between short
straddle and iron fly via the thin-credit rule — **fires on 3 of 37
sessions and has exactly one outcome behind it (07-28)**.

**The cutoffs are imported intuition, not measured.** Across all 37
sessions the 10:00 concentration runs 0.151-0.363, median 0.236:

- `CONC_PIN = 0.35` sits above **92%** of all morning reads
- `CONC_DIFFUSE = 0.25` splits at the 57th percentile
- terciles of the realized distribution would fall at **0.200 / 0.259**

There are now 37 sessions of concentration history to set cutoffs from
instead of guessing. Whether the label deserves to survive at all is a
separate question — see the diagnosis below.

## The diagnosis: the measure is UNSIGNED

All four negative results above test functions of one quantity, and that
quantity is a magnitude.

The engine computes, per contract per minute, Black-76
`gamma = e^(-rT)·phi(d1)/(F·sigma·sqrt(T))` on a parity-implied forward,
then aggregates `gex_cr = gamma x OI x F^2 x 0.01 / 1e7`, summing CE and
PE at each strike. Two consequences that are easy to miss:

- **B76 gamma is positive for calls and puts, and identical for both at
  the same strike.** Summing CE+PE is adding two positive numbers. There
  is no sign anywhere.
- **Because gamma is identical for both, the CE/PE split contributes
  nothing except through OI.** The OI-migration section tracks calls and
  puts separately; the gamma profile discards that distinction at the
  aggregation step.

This is deliberate — `gamma_profile.py`: *"Measured quantities only;
dealer-sign assumptions are Stage 3."* The US convention (dealers assumed
long calls / short puts) was explicitly rejected because NIFTY writers
are structurally net short gamma (`NOTE_stage3_signed_gex.md`).

But it has a consequence for everything above. **An unsigned measure
cannot distinguish stabilizing from destabilizing gamma.** If the holders
at a strike are long gamma they buy dips and sell rallies and price
compresses (pin); if short, they sell dips and buy rallies and price
extends (trend). **Both produce the identical unsigned number.**

That is precisely the distinction Q3 and Q5 needed. Level, slope and wall
velocity are all functions of the same magnitude-only quantity. The four
nulls may not mean "gamma is useless" — they may mean **we measured the
half of gamma that cannot answer the question.**

This is a specification gap, not a promise that signing it will work.
`research/signed_gex_probe.py` (steps 1-3, 18 tests) estimates the sign
empirically from our own tape — Lee-Ready aggressor classification
against the recorded book, writer modelled as the passive side, dOI
splitting opened/closed, aggregated as signed gamma FLOW (not level: the
book standing before recording began is unknowable and is not assumed).
Step 4, the out-of-sample sign test against the journal's behavioural
labels, is the pass/fail gate and **has never been run** — blocked on
tick-file access on the worker volume. It is the only gamma work left
with a defensible premise.

## One descriptive finding worth keeping

Wall distance from spot is **bimodal**. The wall either sits on top of
price (~15-30 pts, and then it tracks ATM near-mechanically and carries
little information) or it is parked 100-400 pts away (and then it never
moves, because it is not ATM-driven at all). These are two different
objects sharing one name, and any future gamma work should separate them
before anything else. Descriptive, not a trade idea.

## What this means for the program

1. **Do not move the strike for gamma.** Centre ATM. Strike selection
   comes off the table as a lever — a real result, not a null one, since
   it removes a degree of freedom that would otherwise get tuned. It held
   and strengthened as the panel grew.
2. **Demote the regime label out of the day-plan's primary branch.** It
   currently selects the structure for 100% of sessions on evidence that
   is not significant, and its most specific branch rests on a single
   outcome. If it is kept, its cutoffs should come from the realized
   distribution (terciles 0.200/0.259), not from imported intuition.
3. **Never read concentration level as permission to sell more.** The one
   relationship that strengthened as the panel grew points the *other*
   way (Q4).
4. **Stop generating gamma trade theses until the ledger grows.** Three
   died today. Two from panel boundaries, one from a mechanism that is
   not there. At n=15 outcomes this panel can *reject* and cannot
   *establish*; a fourth thesis now would be pattern-matching on noise.
5. **The founder framework's caution is doing real work.** Its rule —
   state-conditioned thresholds from measured base rates, never fixed or
   predictive — is why this study looked for a conditioner rather than a
   signal, and why conditioners were tested ex-ante. Every candidate died
   on those checks. **None would have died on a naive backtest.**
6. **What has earned evidence, by contrast**: overnight carry as the
   dominant risk (59% of the trend cycle's damage arrived in gaps), and
   the implied-vs-realized regime distinction across four cycles. Those
   are strong enough to drive an advisory. Concentration is not.
7. **The one gamma thread left with a defensible premise is Stage 3**
   (signed/dealer gamma), and unblocking it is an ops task — tick-file
   access — not a research one.

## The resolution upgrade this probe justified — DONE, same day

`gamma_profile.store_daily()` computes from `option_greeks_minute` +
`option_minute_bars`, both already **per-minute for every contract**. The
profile was therefore computable at 1-minute resolution from data already
held — no new capture, and the 10-second chain snapshots were not needed.

Shipped as Stage 2b (`gamma_profile_minute` + `store_intraday()`, wired
into the EOD hook, both writers sharing one `profile_series()` core, 15
spec tests red-first, the refactor reproducing all 39 pre-existing daily
rows exactly). Backfilled over every session with greeks:

- **Resolution: 3 snapshots -> 13,978 minute rows across 37 sessions**
  (375-386 per session), which is what made the slope diagnostics in Q3
  possible.
- **History: 13 sessions -> 37.** `option_greeks_minute` runs back to
  2026-06-29 while `gamma_profile_daily` began 2026-07-31, so every
  history-based consumer had been reading a third of the record.
  `day_plan.iv_percentile` now ranks today's ATM IV against ~36 prior
  days instead of ~12.
- **And it immediately falsified the finding that justified it** (Q3).
  That is the upgrade working, not the upgrade failing.

The ledger cannot be extended the same way: pre-07-28 sessions are `hist`
source with no book, so straddle fills would have to be fabricated. It
stays at n=15 and the 08-11 hole stays empty — same rule as the outage
row. **The panel's constraint is now outcomes, not measurement.** No
further conditioning study is worth running until the ledger grows.

---

*Probe: `gamma_positioning_probe.py`. Unit tests:
`test_gamma_positioning_probe.py` (25, covering the fill convention, the
ex-ante split, and the slope dead band). Numbers reproduce against prod
via `railway run --service Postgres`.*
