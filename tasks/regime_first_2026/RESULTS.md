# Results — regime_first_2026

**Verdict:** One candidate clears R1-R3 and §4 — **C4, k-means k=2 on the eleven
standardised state variables, fitted 2007-2015 and decoded forward with a trailing
21-session majority vote**. C6 (GMM k=2, breadth-only) cleared R1-R3 but was rejected
at §4 with 77.2% real-time agreement against an 80% floor, and its R3 pass turns out
to be a pivot-clustering artifact. C1 is the benchmark and cannot pass by definition;
C2, C3, C4 k=3/k=4, C5 k=2/k=3 and C6 k=3 all fail R1. Recommended frozen taxonomy is
the two-state C4 map: **BROAD** and **NARROW**.

## §1 state variables

Daily, 2006-01-02 → 2026-09-09, point-in-time, on the point-in-time top-500-by-ADV +
eligibility universe (2,161 distinct names, median 419 members/day). Written to
`data/state_vars.parquet` with an expanding z-score (min 250 sessions) alongside each
raw column. Levels below are raw, not z.

| variable | mean | sd | min | max | n | first valid |
|---|---|---|---|---|---|---|
| `pct_above_200` | 0.5930 | 0.2346 | 0.0041 | 0.9915 | 5129 | 2006-01-02 |
| `pct_leading` | 0.2860 | 0.2385 | 0.0000 | 1.0000 | 5110 | 2006-01-31 |
| `net_highs` | 0.0228 | 0.0527 | −0.2925 | 0.2488 | 5129 | 2006-01-02 |
| `breadth_dd` | −0.3055 | 0.2517 | −0.9957 | 0.0000 | 4930 | 2006-10-18 |
| `divergence` | 0.2257 | 0.1831 | −0.3491 | 0.7117 | 4930 | 2006-10-18 |
| `dispersion` | 0.1185 | 0.0272 | 0.0652 | 0.3298 | 5129 | 2006-01-02 |
| `correlation` | 0.2597 | 0.0955 | 0.0801 | 0.5595 | 5129 | 2006-01-02 |
| `vol21` | 0.1724 | 0.1045 | 0.0443 | 0.8250 | 5129 | 2006-01-02 |
| `vol_ratio` | 1.1118 | 0.5661 | 0.3412 | 6.6323 | 5077 | 2006-03-21 |
| `trend_quality` | 0.6226 | 0.2257 | 0.0321 | 0.9892 | 5129 | 2006-01-02 |
| `part_skew` | 0.2687 | 1.3438 | −5.0000 | 5.0000 | 5129 | 2006-01-02 |

Definitions as specified in TASKS §1. `breadth_dd` = `pct_above_200 / max252 − 1`;
`divergence` = index distance from its 252-session high minus `breadth_dd`;
`dispersion` = cross-sectional sd of trailing 21-session returns over that day's
members; `correlation` = mean pairwise correlation of daily returns, rolling 63, over
a 100-name subsample re-drawn each calendar year (seed 20260913) from names in the
universe on every session of that year; `vol21` = annualised 21-session realised vol
of NIFTY 500 and `vol_ratio` its ratio to its own trailing-252 median;
`trend_quality` = share of members whose 200-day mean exceeds its own level 21
sessions earlier; `part_skew` = top-decile share of the universe's summed 63-session
return.

Two measurement notes. `part_skew` is unstable by construction — when the universe's
summed 63-session return crosses zero the ratio diverges; it is clipped to ±5 (a fixed
constant, no look-ahead) and 3.8% of sessions sit on the clip. `breadth_dd` and
`divergence` need 252 prior breadth observations, which is what pushes every
model-fitted candidate's first label to 2007-10-18 rather than 2006-01-02.

## §2-3 gate table

Reference turning points re-derived, not hard-coded: 15% zigzag on the NIFTY 500
close over 2006-01-02 → 2026-09-09 gives **14 peaks and 14 troughs**
(`data/turning_points.csv`). The very first pivot the walk produces is anchored on the
arbitrary first bar of the slice — no completed 15% swing precedes it — so it is
dropped; that is what takes the raw 14 peaks / 15 troughs to 14 / 14.

Detection lag = sessions from the turning point to the first session whose state
equals the post-turn state (RISK_OFF after a peak, RISK_ON after a trough); negative
if the state was already there, measured back to the start of that run. Forward search
is capped at the next opposite turning point — a top detected after the market has
already bottomed is not a detection, and those events are counted as censored rather
than given a flattering number. Each state is mapped to RISK_ON / RISK_OFF by its own
mean `pct_above_200` against the period median, computed **on the 2006-2015 window
only** so the mapping is not a full-sample read.

| candidate | states | median run | ≤5d share | flips/yr | lag@peaks | lag@troughs | R1 | R2 | R3 | pass |
|---|---|---|---|---|---|---|---|---|---|---|
| C1 hyst 40/60 `pct_above_200` (benchmark) | 2 | 99 | 0.0% | 1.55 | +32.0 | +62.0 | PASS | PASS | n/a | benchmark |
| C2 hyst 40/60 composite | 2 | 18 | 17.2% | 4.62 | +3.0 | +57.0 | FAIL | FAIL | FAIL | FAIL |
| C3 asymmetric divergence | 2 | 1 | 65.6% | 6.28 | +19.0 | +62.0 | FAIL | FAIL | FAIL | FAIL |
| **C4 k-means k=2** | 2 | 78 | 8.1% | 1.91 | +22.5 | +46.0 | PASS | PASS | PASS | **PASS** |
| C4 k-means k=3 | 3 | 59 | 4.2% | 2.49 | +17.5 | +65.0 | FAIL | PASS | FAIL | FAIL |
| C4 k-means k=4 | 4 | 58 | 0.0% | 2.54 | +17.0 | +64.0 | FAIL | PASS | FAIL | FAIL |
| C5 GMM k=2, all vars | 2 | 40 | 0.0% | 2.75 | +20.0 | +52.5 | FAIL | PASS | FAIL | FAIL |
| C5 GMM k=3, all vars | 3 | 36 | 2.2% | 2.38 | −130.0 | +90.5 | FAIL | PASS | FAIL | FAIL |
| C6 GMM k=2, breadth only | 2 | 81 | 4.0% | 1.27 | +23.5 | +40.0 | PASS | PASS | PASS | PASS |
| C6 GMM k=3, breadth only | 3 | 42 | 0.0% | 2.17 | −96.0 | +66.0 | FAIL | PASS | FAIL | FAIL |

R3 is scored against a **window-matched** C1: for every candidate, C1 is re-scored
over that candidate's own valid span, so a candidate starting in 2007 is never
compared against a benchmark that also saw the 2006 and early-2007 pivots. Over the
2007-10-18 span the matched benchmark is +34.0 at peaks and +65.0 at troughs with
0 / 4 censored. R3 passes when the candidate's median lag is lower **and** its
censored count is no worse, on at least one side.

**hmmlearn substitution (recorded per BRIEF).** `hmmlearn` is not installed in the
venv. C5 and C6 use `sklearn.mixture.GaussianMixture` (`covariance_type="full"`,
`n_init=10`, `reg_covar=1e-4`, seed 20260913) fitted on the in-sample window and
`predict` forward, with a 21-session majority-vote smoother. This drops the transition
matrix that an HMM would estimate — persistence comes only from the smoother, not from
the model — which is the most likely reason C5's median runs (40 and 36) sit below the
k-means runs at the same k and fail R1. An HMM with a sticky transition prior is the
obvious re-test and is listed as a follow-up, not run here.

**The majority vote is trailing, not centred.** A centred 21-session vote would use
10 sessions of future labels. Every smoothed label here is the mode of the raw labels
over `[T−20, T]` and is therefore known at T.

**Why C3 failed so completely, and it is a specification defect rather than a
result.** As pre-registered, C3 exits when the index is within 1% of its 52-week high
while breadth drawdown is worse than −20%, and re-enters on C1's enter rule
(`pct_above_200 > 0.60`). Those two conditions are not disjoint: breadth can sit at
62% of the universe (above the enter threshold) while still being 20% below its own
252-session peak. The machine exits on the divergence and re-enters the next session
on the level, so it dithers by construction — median run 1 session, 65.6% of runs ≤5.
This does not test the divergence idea; it tests a re-entry rule that cancels the exit.
A corrected C3 needs a re-entry conditional on breadth drawdown recovering, and that is
a new candidate, so it is a follow-up rather than a substitution made here.

**Negative peak lags are mostly a pivot-clustering artifact.** Six of the fourteen
peaks fall between 2008-01 and 2009-01, inside one continuous bear market. A state
that went RISK_OFF in January 2008 is credited with a −188 or −224 session "lead" at
the August and November 2008 pivots, because the run containing them started long
before. That is one detection being counted five times, not foresight. Restricting to
peaks at which the candidate had **not** already flipped:

| candidate | fresh peaks (n) | matched C1 | troughs (n) | matched C1 |
|---|---|---|---|---|
| C4 k-means k=2 | **+40** (7) | +43 | **+46** (8) | +65 |
| C6 GMM k=2 breadth | +101 (7) | +43 | +56 (5) | +65 |
| C5 GMM k=3 all | headline −130 is entirely this artifact | | | |

C4's R3 edge survives the cut on both sides — marginally at peaks (40 vs 43), by 19
sessions at troughs (46 vs 65). **C6's does not**: its headline +23.5 at peaks becomes
+101 once the 2008 cluster is removed, i.e. it is slower than the benchmark, not
faster. C6 was already rejected at §4; this is a second, independent reason.

**On the founder's lead requirement.** No candidate that clears R1 and R2 leads either
side. The best available is C4 cutting the trough lag from 65 sessions to 46 and
holding roughly level at peaks. The PLAN's premise — that breadth's own peak precedes
the index peak by a median 90 sessions — is not contradicted by this, but no taxonomy
built here converts that raw lead into a persistent state label. Persistence still
costs responsiveness; C4 buys back about a third of the trough lag at the same
persistence, and that is the whole of the R3 gain.

## §4 real-time identifiability

Retrospective labels come from a fit on the whole 2007-2026 span. Real-time labels
refit at each year end on all trailing data and decode the following year only, with
cluster identity re-aligned to the reference fit by Hungarian matching on centroids.
Decoding starts in 2011 so the first fit has at least 750 sessions.

| survivor | agreement % | median catch-up lag | pass |
|---|---|---|---|
| C4 k-means k=2 | **93.4%** (n=3,889 days) | 0 sessions | **PASS** |
| C6 GMM k=2, breadth only | 77.2% (n=3,889 days) | 0 sessions | FAIL (<80%) |

C1, C2 and C3 have no fitted parameters and are causal recursions over
already-point-in-time inputs, so their real-time and retrospective labels are
identical by construction; none of them reached §4 anyway.

C6's failure is the interesting one. On breadth variables alone the two mixture
components are not stably separated: refitting on a different trailing window moves
the boundary enough to relabel roughly one day in four. Adding dispersion,
correlation, volatility, trend quality and participation skew — C4's feature set — is
what makes the partition reproducible across fits. The breadth-only taxonomy is not
usable in real time.

Catch-up lag of 0 in both rows means that when a state begins retrospectively, the
real-time label is already there on day one; the 6.6% disagreement in C4 is not a
timing lag but scattered single-day relabelling inside runs, which the trailing
majority vote does not fully absorb.

## §5 survivor characterisation

C4, k-means k=2, 4,681 labelled sessions from 2007-10-18. Names assigned from the
centroids, not from anything a strategy did.

| | **S0 — BROAD** | **S1 — NARROW** |
|---|---|---|
| days / frequency | 3,141 / 67.1% | 1,540 / 32.9% |
| runs / median duration | 19 / **78 sessions** | 18 / **61.5 sessions** |
| `pct_above_200` | 0.716 | 0.321 |
| `trend_quality` | 0.712 | 0.414 |
| `correlation` | 0.221 | 0.327 |
| `vol21` | 0.141 | 0.226 |
| `dispersion` | 0.117 | 0.116 |
| index return, annualised | +15.6% | +3.0% |
| index vol, annualised | 16.7% | 25.1% |
| mean index drawdown in state | −3.7% | −17.5% |
| worst index drawdown in state | −39.5% | −64.1% |

Transition matrix (rows = from, daily):

| from \ to | S0 BROAD | S1 NARROW |
|---|---|---|
| S0 BROAD | 0.9943 | 0.0057 |
| S1 NARROW | 0.0117 | 0.9883 |

Expected dwell from the transition matrix is 175 sessions in BROAD and 85 in NARROW,
against observed medians of 78 and 61.5 — the distribution is right-skewed, a few long
occupations and many shorter ones.

Centroids in expanding-z units (fit window):

| variable | S0 BROAD | S1 NARROW |
|---|---|---|
| `z_pct_above_200` | +0.567 | −1.212 |
| `z_net_highs` | +0.446 | −0.964 |
| `z_pct_leading` | +0.498 | −0.763 |
| `z_breadth_dd` | +0.574 | −1.159 |
| `z_divergence` | −0.418 | +1.280 |
| `z_dispersion` | −0.144 | −0.413 |
| `z_correlation` | −0.622 | +0.299 |
| `z_vol21` | −0.486 | +0.279 |
| `z_vol_ratio` | −0.471 | +0.126 |
| `z_trend_quality` | +0.389 | −1.062 |
| `z_part_skew` | +0.256 | −0.305 |

**S0 — BROAD.** Two thirds of the record. Most of the universe is above its own
200-day and most 200-days are rising; names move apart rather than together (mean
pairwise correlation 0.22) and index volatility sits a third below its NARROW level.
The index is within 4% of a rolling high on average. This is a tape where the
cross-section is doing the work.

**S1 — NARROW.** One third of the record. Breadth is a third of the universe and
falling, the divergence variable is the single most separated feature at +1.28z —
the index is holding up better than its own constituents — correlation jumps by half
and realised vol by 60%. The index still returns +3.0% annualised here, so this is not
a "market falls" state; it is a state in which the average name has stopped
participating and everything moves together. Dispersion is the one variable that does
*not* separate the two states (0.117 vs 0.116), which is worth knowing before anything
is built on it.

## Recommended taxonomy

**C4-k2, frozen as follows.** Two states, BROAD and NARROW.

1. Build the eleven §1 variables daily on the point-in-time top-500 + eligibility
   universe, per `lib/build_state_vars.py`.
2. Standardise each by its **expanding** z-score, minimum 250 sessions.
3. `KMeans(n_clusters=2, n_init=20, random_state=20260913)` fitted on the in-sample
   window only — 2,032 complete-case sessions, 2007-10-18 → 2015-12-31. Assign every
   later session to the nearer centroid; never refit on data the label is used for.
4. Apply a **trailing** 21-session majority vote to the raw assignment.
5. The state with the higher mean `pct_above_200` over the fit window is BROAD.

**Parameter count: 22 fitted** (2 centroids × 11 dimensions), plus 2 fixed
hyperparameters (the 250-session z-score minimum and the 21-session vote window) and
the §1 window constants (21 / 63 / 200 / 252), which are inherited from
`trend_screen_2026` and were not searched here.

Phase 3's setup menu may now be run against this map under PLAN's constraint 3 — the
per-state samples are 3,141 and 1,540 sessions, so the deflation bar must be computed
on those, not on 4,681.

## Blocked

- **`hmmlearn` is not installed.** C5 and C6 ran as `GaussianMixture` + trailing
  21-session majority vote, per the BRIEF's instruction. The substitution removes the
  estimated transition matrix, which is the mechanism an HMM uses to produce
  persistence; both C5 variants failed R1 on median run. The HMM versions of C5/C6 are
  therefore **untested**, not rejected. Recorded, not worked around.
- **C3 as pre-registered is untestable** — its exit and re-entry conditions overlap,
  so it dithers by construction (median run 1 session). The divergence idea behind it
  has not been evaluated. No substitute candidate was run, per the no-additions rule.
- **Fitted candidates start 2007-10-18, not 2006-01-02**, because `breadth_dd` and
  `divergence` need 252 prior breadth observations. C4/C5/C6 are scored on 12 peaks and
  12 troughs against C1's 14 and 14. R3 uses a window-matched benchmark to keep the
  comparison fair, but the fitted candidates genuinely have two fewer events on each
  side.
- **Four of the twelve troughs are censored for every candidate**, C1 included — no
  candidate re-entered RISK_ON before the next peak in those episodes. Trough medians
  are taken over the 8 uncensored events and are optimistic to that extent.
- **`part_skew` clips on 3.8% of sessions.** Its z-score is fed to the clustering as
  specified, and it is the weakest-separating variable after dispersion, so this is
  unlikely to be load-bearing — but it is not a clean input.

## Follow-ups

- **Re-run C5/C6 with a real HMM** once `hmmlearn` is available, with a sticky
  transition prior. Persistence coming from the model rather than from a post-hoc
  smoother is the one structural difference between what was specified and what ran.
- **A corrected asymmetric candidate.** C3's intent — exit on breadth divergence at an
  index high, re-enter on something else — is untested. The re-entry rule must be
  disjoint from the exit: re-entry conditional on `breadth_dd` recovering above, say,
  −10%, rather than on the breadth level. This is a new candidate and counts against
  deflation in whatever phase runs it.
- **Deflation bar for Phase 4.** BROAD has 3,141 sessions and NARROW 1,540. Write the
  per-state bar before the first conditional run, per PLAN constraint 3.
- **Dispersion does not separate the states** (0.117 vs 0.116). Either it is the wrong
  construction — 21-session trailing returns may be too short — or cross-sectional
  spread genuinely does not vary with breadth regime in this market. Worth one probe
  before it is used as an input anywhere else.
- **The clustered-pivot problem in R3.** Six of fourteen peaks sit inside 2008. Any
  future responsiveness measurement should either de-cluster the reference turning
  points or report the fresh-event cut alongside the headline, as done here; the raw
  median is easy to game with a slow rule.
- **Hysteresis for trigger-based firing** (PLAN's second open question) is now
  answered for the regime layer: C4 flips 1.91 times a year with a median 78-session
  run, which is within the range month-end sampling was hiding. No additional
  hysteresis layer is needed on top of the majority vote.

---

Artefacts, all under `tasks/regime_first_2026/` and uncommitted:
`data/state_vars.parquet`, `data/candidate_labels.parquet`, `data/turning_points.csv`,
`data/gate_table.csv`, `data/gate_detail.json`, `data/realtime_table.csv`,
`data/characterisation.json`, `data/s1_state_vars.csv`;
code in `lib/build_state_vars.py`, `lib/regimes.py`, `lib/run_gates.py`.
