# Does the gamma profile help POSITION a trade?

**Date:** 2026-08-18 (after the 08-18 expiry) · **Ledger:** n=15 rows /
16 sessions · **Panel:** 12 sessions with both a gamma profile and a
ledger row · **Probe:** `gamma_positioning_probe.py` (+ 25 unit tests)

**Verdict: no positioning edge. A weak risk-conditioning signal. One
convincing false positive, recorded below so nobody finds it twice.**

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
| A 09:20 @ ATM | 12 | +104.2 | +8.68 | +12.27 | 8/4 | -78.35 |
| B 10:00 @ ATM | 12 | +88.8 | +7.40 | +14.30 | 10/2 | -133.15 |
| C 10:00 @ WALL | 12 | +114.8 | +9.56 | +12.32 | 10/2 | -86.80 |

Paired (B vs C, only the strike differs): **the wall wins 5 of 12**,
mean difference **+2.17 pts** on credits of 80-280. On the 9 sessions
where the wall was a different strike from ATM it is 5 of 9. That is a
coin flip, and the effect is far inside the friction the ledger already
measures. **There is no strike-selection signal here.**

## Q2 — The best-looking variant is a directional bet in disguise

Variant D — center on yesterday's closing wall — posts the best numbers
in the study: **+140.7 total, +12.79 mean, +25.80 median**, against the
baseline's +104.2. It is spurious, three ways:

1. Head-to-head it is **4-4** (3 ties).
2. `corr(D - A, prior-wall offset x spot move) = **+0.959**`. Almost all
   the variance is explained by whether spot happened to travel toward
   the strike the stale wall pushed you onto.
3. Remove its two best days and it makes **+72.1 where the baseline made
   +108.0** on the same sessions.

Mechanically: a wall left overhead by yesterday's chain centers today's
straddle above spot. In the 08-13/14/17 down-trend that paid three times
running; on 08-18 the identical construction lost **-30.1**. This is a
bet on direction relative to a stale strike wearing a gamma costume, and
at n=11 it is exactly the shape that survives a naive backtest. **Do not
trade it.**

## Q3 — The concentration slope tracks risk, not return

Ex-ante test: bucket on the 10:00→13:00 concentration slope (dead band
±0.01), score only what happens after 13:00.

| Morning slope | n | P&L after 13:00 (mean / median) | Worst drawdown after 13:00 |
|---|---|---|---|
| building | 5 | +9.54 / +10.60 | **-7.05** |
| flat | 3 | +12.68 / +24.65 | -30.55 |
| decaying | 4 | +12.14 / +15.28 | **-51.00** |

- **Return: nothing.** `corr(slope, P&L after 13:00) = +0.083`, and the
  three buckets earn the same. If anything the *decaying* bucket earns
  slightly more per session.
- **Risk: the tails do not overlap.** Every building session's afternoon
  drawdown sits inside -7.05 (all five: -7.1, -3.7, -2.6, -0.9, -0.4).
  Both afternoon blowouts in the library (-51.0, -30.6) are outside that
  bucket.

Honest limits: the medians barely separate (-2.60 vs -7.65); 08-04 alone
drives the worst tail (drop it and not-building's worst is -30.55, mean
-8.50); n is 5 vs 7. **This is a statement about tails, not means, on a
sample too small to size from.**

## Q4 — Concentration LEVEL runs the wrong way

- `corr(level at 13:00, P&L after 13:00) = **-0.348**`
- `corr(level at 10:00, full-day MAE) = **-0.319**` (MAE is negative, so
  more concentration went with *deeper* drawdowns)

The intuitive reading — high concentration means a pin is forming, so
premium is safer to sell — is **backwards in this sample**. It is
consistent with OBSERVATIONS obs. 39, where the highest concentration
ever recorded (47.6% on the 08-18 expiry) produced no pin at all and
spot settled 45 pts below the wall at the day's low.

## What this means for the program

1. **Do not move the strike for gamma.** Center ATM. Strike selection
   comes off the table as a lever; that is a real result, not a null one
   — it removes a degree of freedom that would otherwise get tuned.
2. **Gamma is a sizing/hold input, not an entry input.** Building
   concentration is the state in which the afternoon tail has not yet
   appeared; decaying is the state that has produced every large one.
   This is precisely the founder framework's shape
   (`NOTE_risk_thresholds.md`): gamma configures risk, it does not
   forecast price.
3. **Never read concentration level as permission to sell more.** It
   points the other way here, and it is already the flagged weakness in
   `day_plan`'s PIN-GRAVITY branch.
4. **The binding constraint is measurement resolution, not sample size.**
   A "slope" built from 3 snapshots a day is a two-point estimate across
   three hours. Before spending anything more on this panel, the profile
   should be computed per minute — see below.

## The resolution upgrade this probe justifies

`gamma_profile.store_daily()` computes from `option_greeks_minute` +
`option_minute_bars`, both of which are already **per-minute for every
contract**. The profile is therefore computable at 1-minute resolution
from data we already hold — the 10-second chain snapshots are not needed
and neither is any new capture.

Two things fall out, both free:

- **Resolution: 3 snapshots → 375+ per session**, which turns the
  concentration slope from a two-point guess into something with a
  standard error.
- **History: 13 sessions → 37.** `option_greeks_minute` runs back to
  2026-06-29, but `gamma_profile_daily` only starts 2026-07-31, so every
  history-based consumer is reading a third of the available record.
  `day_plan.iv_percentile` currently ranks today's ATM IV against ~12
  prior days; it could be ranking against 37. That directly addresses
  the DTE-blindness criticism in obs. 40 — with 37 sessions there are
  enough same-DTE days to condition on.

Note the ledger cannot be extended the same way: the pre-07-28 sessions
are `hist` source with no book, so straddle fills would have to be
fabricated. It stays at n=15, and the 08-11 hole stays empty — same rule
as the outage row.

---

*Probe: `gamma_positioning_probe.py`. Unit tests:
`test_gamma_positioning_probe.py` (25, covering the fill convention, the
ex-ante split, and the slope dead band). Numbers reproduce against prod
via `railway run --service Postgres`.*
