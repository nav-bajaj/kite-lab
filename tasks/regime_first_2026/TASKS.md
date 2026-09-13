# Tasks

Owners: 👤 founder · 🤖 agent. Gates R1-R3 are in PLAN.md and are signed.

## §1 — state variables, daily, 2006-2026 🤖

All point-in-time, all on the top-500 + floor universe. Written to
`data/state_vars.parquet`, daily index.

- [ ] breadth: `pct_above_200`, `pct_leading`, `net_highs` (from
      `trend_screen_2026/data/breadth.parquet` and `regime_allocation_2026/data/signals.parquet`)
- [ ] **breadth drawdown**: `pct_above_200 / rolling_max(252) − 1`
- [ ] **divergence**: `(index / index_hi252 − 1) − (pct_above_200 / breadth_hi252 − 1)`
- [ ] dispersion: cross-sectional std of trailing 21-session returns
- [ ] correlation: mean pairwise correlation of daily returns, rolling 63, on a
      fixed random 100-name subsample re-drawn yearly (full pairwise is too slow)
- [ ] volatility: index realised 21-session vol, and its ratio to its own
      trailing-252 median
- [ ] trend quality: share of universe whose 200-day is above its level 21 ago
- [ ] participation skew: share of the universe's summed 63-session return
      contributed by the top decile of names
- [ ] Each variable standardised by its **expanding** z-score (min 250
      sessions) — never full-sample.

## §2 — candidate taxonomies 🤖

Each candidate produces a daily state label. Every one is scored on R1-R3
before anything else. Pre-registered list; nothing added after the first run.

- [ ] C1 hysteresis 40/60 on `pct_above_200` (the benchmark R3 must beat)
- [ ] C2 hysteresis 40/60 on the composite (from `signals.parquet`)
- [ ] C3 **asymmetric**: exit on divergence (index within 1% of 52w high AND
      breadth drawdown < −20%), re-enter on C1's enter rule
- [ ] C4 k-means, k ∈ {2,3,4}, on all §1 variables, with a 21-session
      majority-vote smoother applied *after* labelling
- [ ] C5 Gaussian HMM, 2 and 3 states, on all §1 variables, fitted on
      2006-2015 only and decoded forward with `predict` (never `fit` on the
      full span); if `hmmlearn` is missing use sklearn `GaussianMixture` +
      a 21-session majority vote and record the substitution
- [ ] C6 HMM on breadth variables only (the three breadth series + drawdown +
      divergence), same protocol as C5

## §3 — R1-R3 scoring 🤖

- [ ] For every candidate and every state: median run, share of runs ≤5
      sessions, flips/yr, time-in-state.
- [ ] Reference turning points: 15% zigzag on NIFTY 500 → 14 peaks, 14 troughs
      (code in PLAN's measurement; re-derive it, do not hard-code the dates).
- [ ] Detection lag per candidate at peaks and at troughs, median and per-event.
- [ ] **Gate R1-R3**. Report pass/fail per candidate. Candidates that fail do
      not proceed to §4.

## §4 — real-time identifiability 🤖

For survivors only. For clustering/HMM candidates, retrospective labels use
the whole window; real-time labels use only data through each day.

- [ ] Re-label with a strictly expanding fit (refit yearly on trailing data,
      decode the next year). Agreement rate with retrospective labels, and
      the lag between when a state begins retrospectively and when the
      real-time label catches it.
- [ ] A survivor whose real-time labels agree with retrospective ones on
      <80% of days is **rejected**. Record it.

## §5 — characterise the survivors 🤖

Still no strategy. Per state: frequency, median duration, transition matrix,
index return / vol / drawdown inside the state, and a two-line description in
market terms.

## §6 — RESULTS.md 🤖 then 👤

Template in BRIEF.md. The deliverable is a frozen taxonomy (or the finding
that none clears the gates), signed by the founder before Phase 3 of PLAN.md
— the setup menu — is run as a separate task.
