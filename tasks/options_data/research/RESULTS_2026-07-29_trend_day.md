# Day 2 (trend day) — first out-of-sample tests + trend-day OI mechanics

2026-07-29: gap up ~155pts over the morning anchor, rally to 24,225,
close 24,241 (+253 on the day). Engine handled its first gap + widen +
expiry-rollover day flawlessly (2 widens -> 107 contracts, 39,744 live
bars, 0 db errors). Two days of depth data — still diagnostic.

## A. NEGATIVE: day-1's ITM-put imbalance cluster did not replicate

Day 1 (expiry day): ITM puts corr -0.35..-0.38. Day 2, same zone: mean
+0.005, median -0.037 — gone. All aggregate imbalance->next-minute
correlations collapsed toward zero on the trend day (CE mean -0.027,
PE +0.004). Read: the cluster was either expiry-day-specific
microstructure or noise. Parked as "re-test conditioned on day type
once we have several of each." This is the out-of-sample discipline
working as intended.

## B. STAR RESULT: trend-day OI migration is cleanly visible

As the rally ran through strikes, 08-04 call OI drained at overrun
strikes and re-formed above spot:

    strike   24000  24100  24200  24300
    12:00      85%    88%   113%   125%   (vs 9am base)
    15:00      69%    55%    74%    98%

Overrun strikes (24000/24100) bled to 55-69% — call writers covering —
while 24300 built to 125% before the late unwind. Combined with day 1's
pin signature (ATM OI tripling, wings flat), we now have TWO clean,
opposite intraday OI regimes captured at minute resolution:

- PIN: OI concentrates INTO one strike, wings flat.
- TREND: OI drains at overrun strikes, re-forms one rung above spot.

This is the most buildable structure so far: an intraday OI-migration
monitor that classifies the day live (covering-fuel vs pin-gravity) from
per-strike OI flow. Needs more days to calibrate thresholds, but the
computation is fully specified by these two days.

## C. Friction baseline: two regimes confirmed

Trend day: absolute spreads wider (0.41 vs 0.24 pts — vol premium) but
FLAT at ~0.23% of premium all day. Expiry day: absolute spreads flat but
relative cost exploding into the close (0.30% -> 1.84% in this cut).
Practical rule emerging: relative friction is a function of premium
decay, not book width — time exits on expiry days, not on normal days.

## D. Widen data quality

Gap-day widen #1 fired on the FIRST spot tick (09:15:04), so the
24500-24600 strikes have full-day coverage (376 bars). Only widen #2's
strikes (10:16) have partial days — by design, never unsubscribed.

## E. Straddle ledger

08-04 implied now 1.06% (spot 24241, ATM 24250, straddle 256.6) after a
+223pt intraday move — realized is landing against last week's ~2%
implieds. Verdict rows complete when each expiry settles.

## What to build next (in order)

1. **OI-migration monitor** (from B): daily per-strike OI flow map +
   live pin-vs-trend classification. Computation specified; calibration
   accrues automatically with each session.
2. **Daily auto-analysis**: run these studies after EOD flush, write a
   dated report (and later a /admin card).
3. **Straddle implied-vs-realized ledger**: auto-verdict per completed
   expiry (first verdict lands 08-04).
4. **Imbalance re-test**: conditioned on the day-type classifier from
   (1), once several days of each regime exist.

Script: analyze_day2_trend.py (this folder).
