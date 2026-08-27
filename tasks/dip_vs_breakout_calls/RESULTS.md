# Dip vs breakout call feeds — results (2026-08-23)

Window 2010-06 → 2026-08-19, NSE 500 minus 33 cliff-artifact symbols,
top-quartile 126d momentum filter, momentum-rank slot priority, exit at
momentum rank < 0.35, next-day OHLC/4 ± 20bps. Tail = 2023-07 onward.
Regression gate vs h4g passed (Sharpe 1.494 vs 1.489 published).

## Grid

| arm | calls/yr | %wks w/ call | win% | mean | median | p5 | p95 | hold (td) | CAGR | Sharpe | MaxDD | tail CAGR | tail Sharpe |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| bo25 | 30.6 | 43.1 | 56.2 | +33.9 | +4.4 | -26.2 | +187.9 | 150 | 31.2 | 1.41 | -32.5 | 23.8 | 0.86 |
| bo25_ts20 | 48.4 | 48.9 | 49.2 | +16.0 | -0.5 | -21.7 | +96.1 | 101 | 27.2 | 1.32 | -27.2 | 27.2 | 1.16 |
| dip25 | 34.4 | 49.0 | 53.9 | +37.7 | +2.2 | -28.6 | +228.0 | 118 | 38.4 | 1.63 | -37.7 | 37.7 | 1.44 |
| **dip25_ts20** | **58.5** | **56.0** | 51.6 | +20.1 | +1.1 | -21.2 | +120.7 | **76** | **37.8** | **1.65** | -34.6 | **37.2** | **1.49** |
| dip25_trend | 34.7 | 49.8 | 53.1 | +38.1 | +1.3 | -29.7 | +221.9 | 118 | 36.7 | 1.56 | -36.8 | 33.8 | 1.28 |
| bo50 | 61.8 | 64.9 | 55.5 | +33.0 | +4.1 | -26.8 | +185.3 | 147 | 31.1 | 1.44 | -34.7 | 32.2 | 1.31 |
| dip50_ts20 | 115.6 | 75.8 | 49.6 | +18.5 | -0.5 | -21.2 | +114.5 | 76 | 34.2 | 1.56 | -34.0 | 33.1 | 1.34 |

## Question 1 — the breakout config at cap 25

Viable but the weakest configuration tested, and the wrong direction
for the founder's flow brief:

- **30.6 calls/yr, fresh call in only 43% of weeks** — half the flow
  of cap 50 for the same portfolio economics (31.2% vs 31.1% CAGR).
- The tail is its weak spot: 23.8% CAGR / 0.86 Sharpe post-2023-07,
  and the recent yearly line is ugly — 2025 port return -10.9% (25.7%
  win), 2026 YTD -0.1% with 0/23 closed winners. The "looked broken
  for 18 months" problem from H4 persists at tight caps.
- Adding the 20% trail at cap 25 hurts everywhere (27.2% CAGR, median
  call negative) — opposite of the cap-50 finding in h4g. At a tight
  cap the trail ejects winners that the thin slot list can't replace
  with equal quality. The trail's value is cap-dependent.

## Question 2 — dip entry into the momentum sleeve

**The hybrid wins on every portfolio metric.** Same universe, same
momentum filter, same exit; only the entry timer changes from "fresh
20d-high cross" to "5-day return < -5%":

- dip25 vs bo25: CAGR 38.4% vs 31.2%, Sharpe 1.63 vs 1.41, tail
  37.7%/1.44 vs 23.8%/0.86. Mean call +37.7% vs +33.9%.
- **dip25_ts20 is the headline arm**: 58.5 calls/yr (~1.1/wk, fresh
  call 56% of weeks), median hold 76td (~3.6 months), win 51.6%,
  median call +1.1%, portfolio 37.8% CAGR / 1.65 Sharpe / -34.6%
  MaxDD, tail 37.2% / 1.49. Unlike the breakout arms, the trail
  *helps* here (Sharpe 1.65 vs 1.63, DD -34.6 vs -37.7, calls/yr
  58.5 vs 34.4) — dips into momentum names catch falling knives
  often enough that a disaster brake pays, and the faster recycling
  raises flow ~70%.
- Recent era is healthy: 2024 +49.1%, 2025 +5.2%, 2026 YTD +14.8%
  (vs bo25's +60.7 / -10.9 / -0.1). Worst years 2011 -7.8%, 2018
  -4.9% — shallower than any breakout arm's worst.
- The 200DMA gate on the dip (dip25_trend) adds nothing — the
  top-quartile momentum score already enforces trend health.
- dip50_ts20 buys flow (115.6 calls/yr, fresh call 76% of weeks) for
  ~3.6pp CAGR and a negative median call — same dilution pattern as
  the breakout cap ladder in h4h. Cap 25 keeps the median positive.

**Mechanism.** Two effects compound: (a) entry prices — buying the
same momentum-sleeve names ~5-10% below their highs instead of at
fresh highs shifts every call's cost basis; (b) counter-cyclical slot
refill — in corrections, breakout signals dry up exactly when slots
free (the bo25 tail problem: 96% days-at-cap holding stale winners),
while dip signals are *most* abundant then, so the dip feed reloads
into the recovery. That is why the gap widens in the tail window.

## Exit mix and open book

dip25_ts20: 67% of closed calls exit on the trail, 33% on momentum
decay; 25 open calls at study end carry +39.7% mean unrealized.
bo25 open book: +23.1% mean. Skipped-for-capacity: ~19k dip signals
over 16 years — the system is slot-bound, not signal-bound (same
h4h conclusion).

## Caveats

- Survivorship (current constituents); winner-of-7 selection —
  between-arm deltas are indicative, headline numbers optimistic.
- 20bps slippage only; no STT/taxes.
- **Validity gate not run for the dip entry.** The donchian gate
  failure (negative direction lift) applied to breakout entries; the
  dip arm must pass `tasks/insight_engine/pattern_validity_study.py`
  before any subscriber-facing forward-return claim. Until then the
  same constraint holds: transparent journal framing only.
- 33 symbols excluded for data artifacts (PLAN.md); the underlying
  corporate-action gaps in `nse500_data_merged` are an open pipeline
  bug affecting all research on this data.

## Addendum (2026-08-23): validity-protocol study

`validity_study.py` replicates the pattern_validity_study.py
methodology (stride-21 sampling 2012 → 2026-01, top-25 by momentum
score per date, same-date universe baseline) for both entries on the
artifact-cleaned universe. Full report: `VALIDITY.md`, copied to
`tasks/insight_engine/PATTERN_VALIDITY/dip_momentum_entry.md`;
protocol audit table updated.

| Entry | 20d excess | 20d lift | 60d excess | 120d excess | Tier |
|---|---|---|---|---|---|
| dip_momentum | **+1.02pp** | **+3.8pp** | +3.45pp | +7.66pp | **VALIDATED** |
| breakout_momentum | +0.31pp | +2.5pp | +1.15pp | +1.73pp | Names-only |

- Dip passes all runnable checks: n=978; excess ≥ +1.0pp at 20d; lift
  positive; sign consistent at 5/20/60d (positive and growing with
  horizon); persistence positive in both sample halves (H1 +1.49pp,
  H2 +0.74pp). Check 5 carries the standing current-constituent
  caveat shared by every study in PATTERN_VALIDITY/.
- Honest fine print: the 20d excess sits exactly at the bar and the
  second-half excess alone (+0.74pp) is below it — the claim should
  quote the longer horizons (60/120d) where the edge is 3-7x the bar
  and stable. At 5d the dip shows the strongest direction lift
  (+9.0pp) — the bounce is most reliable immediately.
- The breakout control independently reproduces the donchian gate
  verdict on clean data (excess below bar at 20d; direction lift here
  mildly positive vs negative in the original study — different
  detector variant and data cleaning, same conclusion): breakout
  calls cannot carry forward-return copy; dip calls can.

## Addendum (2026-08-23): IS/OOS windows and regime split

`window_study.py` — dip25_ts20 vs L6 v2 / OM25 v3 (h2-base engine
shapes) over the house windows (IS clipped to 2010-06 for panel
coverage; OOS-C extended to data end). Output `window_comparison.csv`,
pooled calls in `calls_all_windows.csv`.

| Window | Dip CAGR/Sharpe/DD | L6 v2 | OM25 v3 |
|---|---|---|---|
| IS 2010-16 | **30.3 / 1.45 / -24.7** | 27.6 / 1.06 / -29.7 | 25.8 / 1.24 / -26.0 |
| OOS-A 2017-19 | 25.8 / 1.15 / **-20.2** | **36.2 / 1.50** / -28.8 | 22.6 / 1.09 / -22.3 |
| OOS-B 2020-22 | 59.0 / 2.18 / -35.2 | 65.8 / 2.14 / -38.2 | **60.2 / 2.33** / -32.8 |
| OOS-C 2023-26 | 36.1 / 1.46 / -24.3 | 34.6 / 1.18 / -29.4 | **43.4 / 1.79** / -23.4 |

- Dip is never the top performer and never the broken one: Sharpe
  1.15-2.18 across all four windows, shallowest drawdown in 3 of 4.
  Leadership among the three rotates by window (L6 in OOS-A, OM25 in
  OOS-C, dip in IS). Call flow is stable: 53-77 calls/yr in every
  window, median hold 48-83td.
- OOS-A is dip's weakest window (win 46.4%, median call -1.6%): a
  grinding low-volatility bull suits fresh-high strategies better
  than dip-buying.
- **Regime split (pooled closed calls): bear-regime entries are the
  better cohort** — win 52.9% vs 46.2%, median +2.15% vs -2.51%, mean
  +19.0% vs +15.6% (OM25 confirmed-200DMA regime at signal date).
  Consistent with the validated STRESS-regime buy-panic base rate.
  The feed's counter-cyclical character is measurable, not narrative.
- Cold-start deployment is fast: the Jan-2023 investor sim went 0 -> 25
  positions in 10 trading days (dip-rich stretch; slower in quiet
  tapes but signals are abundant).

## Addendum (2026-08-23): healed-data re-run

After the corporate-action repair (tasks/corporate_actions_fix), the
grid re-ran on the FULL universe (NO_CLIFF_EXCLUDE=1, no exclusions,
repaired panels). Headline arm dip25_ts20: 66.0 calls/yr, win 51.9%,
36.91% CAGR / 1.77 Sharpe / -35.9% MaxDD, tail 36.3% / 1.50 — vs
37.8% / 1.65 / -34.6% on the excluded universe. All arm orderings
unchanged; dip still beats breakout everywhere (bo25 tail Sharpe 0.89
vs dip25_ts20 1.50). The exclusion list is retired; healed-panel
numbers are the quotable set going forward.

## Verdict

The cap-25 breakout re-sim answers question 1 with "works, but wrong
shape" — half the flow, fragile recent era. The dip-timed momentum
feed answers question 2 with the strongest configuration this
research line has produced: **dip25_ts20 — 25 slots, ~58 calls/yr,
3.6-month median hold, always-on, 37.8% CAGR / 1.65 Sharpe, healthy
2024-2026**. Recommended next steps: (1) run the dip entry through
the validity protocol; (2) re-run on effective-dated membership once
the corporate-action fix lands; (3) founder call on cap 25 vs 50
(median-call quality vs flow).

## Follow-on findings (2026-08-26/27)

Two open questions from this study were closed in
`tasks/hourly_dip_swing/` — full write-ups in `QUARTILE_STUDY.md` and
`RESULTS.md` Addendum 8.

**The momentum sleeve is where the edge lives; the dip only times entry
into it.** Swapping the top quartile for the third quartile, one thing
changed, costs 12.1pp of CAGR (36.7 → 24.6) under a sleeve-consistent
exit. The third-quartile entry cohort has no forward excess at all
(−0.01pp @20d, t_clust −2.03) against this study's +1.02pp / t 9.20, so
it fails the validity protocol and can carry no forward-return copy. Q2
sits in between on every measure — the gradient is smooth, so the
top-quartile cut is not a tuned parameter perched on a cliff.

**The rank-0.35 exit is specific to the top-quartile sleeve.** For a
Q2/Q3 entry the floor sits inside the entry band, so positions get
ejected on entry-adjacent noise (median hold 6 days, −53% drawdown).
Twenty-two hysteresis variants — trail-only, low absolute floor,
entry-relative, rank-ratchet, and a "must be promoted within N days"
rule — repair that pathology but none close the gap. The same rules
applied to the top sleeve do not beat the published exit either.

**"Buy the momentum rebuild" was tested and killed.** The best
lower-quartile arm works by discarding names that fail to climb back
into the upper sleeve, which suggested a rebuild entry. As a signal in
its own right it has no excess (+0.01pp @20d, t_clust 0.33), and
requiring a prior dip makes a plain rank crossing *worse* than leaving
it out — the small amount of signal there belongs to momentum
acceleration, not to the dip.

**Correlation to production, measured and persisted.** The figure this
line kept citing was computed on 2026-08-23 but never saved —
`compare_production.py` printed the matrix and dropped it. It now writes
`correlation_daily.csv` and `correlation_monthly.csv`. Daily: 0.90 vs L6
v2, 0.87 vs OM25 v3. Monthly (n=43): 0.92 vs L6 v2, 0.83 vs OM25 v3.
Monthly being higher than daily is the wrong direction for a
diversification story — the dip feed's case remains the product surface
(timestamped calls), not portfolio diversification.

