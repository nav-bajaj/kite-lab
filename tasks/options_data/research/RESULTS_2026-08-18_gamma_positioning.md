# Does the gamma profile help POSITION a trade?

**Date:** 2026-08-18 (after the 08-18 expiry) · **Ledger:** n=15 rows /
16 sessions · **Probe:** `gamma_positioning_probe.py` (+ 25 unit tests)

**REVISED same day at n=15 — see "Correction" below.** The first pass ran
on the 12 sessions `gamma_profile_daily` happened to hold. Backfilling
the profile over every session with greeks (the Stage 2b upgrade this
document argued for) added the three earliest sessions, and the panel's
one positive finding did not survive them.

**Verdict: no positioning edge, and no risk-conditioning signal either.
Two convincing false positives, both recorded below so nobody finds them
twice.**

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

## What this means for the program

1. **Do not move the strike for gamma.** Center ATM. Strike selection
   comes off the table as a lever; that is a real result, not a null one
   — it removes a degree of freedom that would otherwise get tuned. This
   held and strengthened when the panel grew.
2. **The gamma profile has no demonstrated use as a trading input.** Not
   for entry (Q1), not for strike (Q1/Q2), and — after the retraction —
   not for hold/size either (Q3). What it retains is descriptive value:
   it is how the day-type library labels a regime, and obs. 32/39 read
   pin mechanics off it. That is worth keeping. It is not worth trading
   off yet.
3. **Never read concentration level as permission to sell more.** The
   one relationship that has strengthened as the panel grew points the
   *other* way (Q4). This is already the flagged weakness in
   `day_plan`'s PIN-GRAVITY branch.
4. **The founder framework's caution is doing real work.** Its rule —
   thresholds must be state-conditioned and derived from measured base
   rates, never fixed or predictive — is the reason this study looked for
   a conditioner rather than a signal, and the reason the conditioner was
   tested ex-ante instead of assumed. Two candidate edges died on those
   two checks. Neither would have died on a naive backtest.
5. **Both false positives came from panel boundaries, not from the
   market.** One from scoring with a future reading, one from a table
   that began three sessions late. At n=15 the honest posture is that
   this panel can *reject* claims and cannot yet *establish* any. Obs. 38
   (thin credit is dangerous when concentration decays) leans on the same
   mechanism as the retracted Q3 and should be treated as weaker than its
   already-hedged "n=2, weak" label.

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
