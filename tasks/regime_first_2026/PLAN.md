# Regime-first: define the states, then find what works inside them

## Why this inverts the last three tasks

`breakout_calls_2026` → `trend_screen_2026` → `regime_allocation_2026` all ran
the same way: fix a strategy, then search for a regime filter that improves
it. That order has a defect we measured rather than guessed. Sixty-nine regime
rules were tried against one fixed strategy; the winner's edge sat inside the
range the best of sixty-nine coin flips would produce, and the in-sample
decade's ranking of those sixty-nine correlated **−0.002** with the
out-of-sample decade's. The regime rule was fit to the strategy.

Inverting fixes exactly that, and only that. If regimes are defined from
market structure with **zero reference to any strategy's returns**, the
taxonomy cannot be fit to a strategy, because no strategy was consulted.

## The trap this creates, and the rule that contains it

Inverting does not reduce the search — it moves it. Four regimes times a menu
of setups is four times the tests, and "which setup wins in regime 3" is a
selection problem with a smaller sample than the whole period. Regime-specific
overfitting is easier than ordinary overfitting, not harder.

Three constraints make the inversion honest. They are not negotiable:

1. **Regimes are frozen before any setup is tested.** The taxonomy is
   validated on properties of the market states themselves — persistence,
   separability, stability across eras — never on strategy P&L. Once signed,
   the definition does not change no matter what the setups show.
2. **The setup menu is pre-registered.** A fixed, written list of candidate
   setups, declared before the first regime-conditional run. Anything added
   afterwards is a new trial and counts against deflation.
3. **A setup must win its regime by more than the regime's own sample allows.**
   With four regimes the per-regime sample is roughly a quarter, so the
   deflation bar is higher, not lower. Report the bar alongside the result.

## Phase 1 gates — signed 👤 2026-09-13

A candidate taxonomy is **rejected before any strategy touches it** unless it
clears all three. These are state properties, so selecting on them does not
contaminate the later phases.

| # | Criterion | Value |
|---|---|---|
| R1 | Median state duration | ≥ 60 sessions |
| R2 | Share of state changes that last ≤ 5 sessions | ≤ 15% |
| R3 | Detection lag at reference turning points, reported and beaten | see below |

**Why R1 and R2 exist.** Every definition built so far dithers. Thresholding
`% above the 200-day` at its median gives a median run of **4 sessions** and
7.5 changes a year. That is a property of the threshold, not the market: runs
of ≤5 sessions are 57% of all changes but only **3.8% of all days**, while
runs over 60 sessions are 15% of changes and **79% of all days**. The market
does sit in regimes for months. The measurement crosses back and forth while
it does. R1 and R2 reject measurements that dither.

Smoothing 21 sessions before thresholding gives 1.9 changes a year and a
median run of 91 sessions at identical time-in-state. Hysteresis (enter above
60%, exit below 40%) gives 1.6 and 99. Either clears R1/R2; neither was among
the 69 candidates in `regime_allocation_2026`, because that grid swept the
lookback window and the allocation shape and never the state's persistence.

## R3 — responsiveness, and the asymmetry that makes it possible

The founder's requirement is that the regime **lead** rather than lag.
Measured against 14 index peaks and 14 troughs (15% zigzag on the NIFTY 500),
every threshold rule tested lags:

| method | flips/yr | median run | lag at peaks | lag at troughs |
|---|---|---|---|---|
| raw threshold | 7.5 | 4 | +15d | +90d |
| smooth 21d | 1.9 | 91 | +30d | +119d |
| smooth 42d | 1.7 | 109 | +46d | +136d |
| hysteresis 45/55 | 2.2 | 64 | +30d | +69d |
| hysteresis 40/60 | 1.6 | 99 | +44d | +96d |

Persistence costs responsiveness monotonically, and **hysteresis dominates
smoothing** on the trade-off — at matched persistence it detects troughs 40
days sooner. (The `smooth 63d` row appearing to lead at troughs is a
small-sample artifact: it is so slow it never turned off for half the
episodes.)

**But the raw signal does lead, and thresholding destroys it.** Breadth's own
peak preceded the index peak by a **median 90 sessions**, leading in 10 of 14
cases. At troughs it leads in only 5 of 14, median 0 days. So:

> Breadth leads at tops and coincides at bottoms.

A level threshold throws the lead away, because breadth must fall all the way
to its threshold before the state flips — by which time the index has already
turned. **Measuring deterioration from breadth's own recent peak preserves
it.** A first test of that: on days when the index is within 0.5% of a 52-week
high while breadth sits below 80% of its own 52-week peak, forward 6-month
index return is **−2.5% against +7.9%**, and 12-month **−5.9% against +15.8%**.
Only 67 such days (1.3% of sessions) and they cluster in a few episodes, so
this is a direction to test, not a result.

**R3 therefore requires:** report detection lag at the reference turning points
for every candidate, and the taxonomy must beat `hysteresis 40/60` at matched
persistence on at least one side (peaks or troughs). **Asymmetric definitions
are explicitly permitted and expected** — a divergence-based exit paired with a
different re-entry rule is the shape the evidence points at, and forcing one
symmetric rule to do both jobs is what has failed so far.

Add to the Phase 1 candidate state variables:
- **breadth drawdown** — % above the 200-day relative to its own trailing
  252-session maximum
- **divergence** — index distance from its 52-week high minus breadth's
  distance from its own

## Phase 1 — what regimes exist

Unsupervised, on market-structure variables only. No returns of any strategy
enter this phase.

**Candidate state variables**, all point-in-time, all computed on the same
top-500 universe:
- breadth level and direction (% above 200-day, % leading, net new highs)
- **dispersion** — cross-sectional standard deviation of trailing returns
- **correlation** — mean pairwise correlation of daily returns, rolling
- **volatility** — index realised vol, and the ratio of realised to its own
  trailing median
- **trend quality** — share of the universe whose 200-day is rising
- **participation skew** — how concentrated the advance is, e.g. share of
  total universe return coming from the top decile

**Method**: cluster on standardised state variables (k-means and a hidden
Markov model, both, as a cross-check), k ∈ {2..6}. Choose k on *state*
criteria only — persistence of cluster membership, separation between cluster
centroids, and whether the same clusters appear when the method changes.

**Deliverable**: a labelled daily state series, and a one-page description of
each state in market terms, written before any strategy touches it.

## Phase 2 — characterise the states

Still no strategy. What does each state look like, and can you tell you are in
one at the time?

- Frequency, median duration, transition matrix, and how long after a state
  begins it can be identified with the data available then.
- Index return, dispersion, vol and drawdown within each state — descriptive,
  not a strategy result.
- **The critical test**: are the states identifiable in real time? A state
  defined by a rolling window is known at its edge with a lag; measure the lag
  and re-label everything with a real-time-only version. If the real-time
  labels diverge badly from the retrospective ones, the taxonomy is not
  usable and Phase 3 does not run.

## Phase 3 — the pre-registered setup menu

Written and signed before the first conditional run. Each setup is a complete
entry and exit specification, drawn from what already exists so nothing new is
searched here:

| # | Entry | Exit |
|---|---|---|
| S1 | trend-screen LEADING, top-20 by % above 52w low | 150-day trail |
| S2 | same entry | ATR trail, 3× ATR20 |
| S3 | same entry | swing-low structure stop |
| S4 | VCP pivot breakout (`breakout_calls_2026` E1) | 150-day trail |
| S5 | pullback to the 50-day within a LEADING name | 150-day trail |
| S6 | mean-reversion: oversold inside an uptrend | fixed-horizon exit |
| S7 | cash | — |

S7 matters: "nothing works here" must be an available answer for a state.

## Phase 4 — which setup for which state

- Each setup run inside each state, in-sample only (2006-2015).
- The map is then frozen and applied forward to 2016-2026.
- Walk-forward as the verdict, per `regime_allocation_2026`'s precedent.
- Deflation bar computed on the per-regime sample size, not the full one.

## Scope boundary

- No new universe, no new price store, no production changes.
- Setups come from the pre-registered menu. A new setup idea is written into
  RESULTS.md as a follow-up, not run.
- The existing breadth composite is **one candidate among several** in Phase 1,
  not the starting point. It carries the contamination of having been found
  the other way round.

## Two open specification questions this task should also settle

These came out of `trend_screen_2026` and are in scope because they change
what a setup even is:

**The exit ladder is under-tested.** Only ma50 / ma150 / chandelier(3×ATR)
were ever swept. The 150-day trail is slow — median hold 91 sessions, and it
gives back a large share of open profit before triggering. S2 and S3 exist to
test that directly.

**Month-end firing is an artifact.** The trend screen fires on the last
session of each month because the feature table was built as monthly snapshots
for compute, not because the signal is monthly. A calls product should fire
when the stock's own condition triggers. Consequence already measured: the
breadth signal flips 26 times a year raw (median run 3 sessions), and
month-end sampling hides it — trigger-based firing samples that signal far
more often, so **hysteresis is mandatory** in any real-time regime rule.
Phase 2 must specify the hysteresis before Phase 4 runs.
