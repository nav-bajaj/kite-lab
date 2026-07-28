# First positioning patterns — 2026-07-28 (day one of live capture)

Data: 455k minute bars in option_minute_bars — day-one live/replay bars
(WITH depth: spread, whole-book imbalance) + ~2-5 weeks historical bars
(OHLC/volume/OI). One day of depth data: everything below is a
hypothesis to re-test as days accumulate, not a signal claim.

## Q1 — Whole-book depth imbalance vs next-minute option returns

Weak in aggregate (CE median corr -0.064, PE median -0.066, futures
~0), but with a coherent cluster: **ITM puts (24250-24500 strikes, spot
~24000) showed corr -0.35 to -0.38** — bid-heavy resting books
preceded next-minute price DECLINES, consistently across five adjacent
strikes. Contrarian read: passive limit buyers in thin ITM contracts
getting adversely selected on expiry day. The aggregate CE-minus-PE
imbalance vs next-minute spot: -0.07 (noise). Re-test daily; the
adjacent-strike coherence is what makes this worth following.

## Q2 — How the expiry pin actually formed intraday

The single most striking result. 24000-strike OI (CE+PE) more than
**TRIPLED intraday**: 14.6M at 9am -> 340% by the 14:00 hour, then
unwound to 239% into the close. Wings (±300+) stayed flat all day
(~100-125%) and bled to 90% at the end. The Sunday backfill showed the
pin as an overnight structure; the live capture shows it was **actively
constructed during expiry day itself** — writers piled into the pin
strike hour after hour while spot oscillated ±30 points around it.
Implication: pin formation is observable in real time via the ATM-OI
accumulation rate relative to wings. That is a concrete detector to
build once we have several expiry days.

## Q3 — Straddle premium into the 08-04 expiry

ATM straddle implied-to-expiry decayed monotonically 2.38% (Jul 15) ->
1.25% (Jul 28) with no realized-vol scare repricing it. Verdict on
rich/cheap lands after 08-04 expires and realized is known — the
tracker now updates itself daily from live bars.

## Q4 — Execution cost by time of day (expiry day, ATM±100)

Absolute spreads are nearly FLAT all day (0.24-0.27 pts) — but as a
percentage of premium they explode into the close: 0.29% (open) ->
0.62% (13:30) -> 2.44% (15:00-15:30), driven entirely by premium
collapse, not spread widening. Practical: on expiry day, late-session
exits of near-ATM longs pay ~8x the relative friction of morning
trades. Positions should be sized/exited with that curve in mind.

## Next analysis steps (as data accumulates)

1. Re-run Q1 daily; track whether the ITM-put contrarian cluster
   persists out of sample.
2. Pin-formation detector: intraday ATM-vs-wings OI accumulation rate;
   needs 4-6 expiry Tuesdays for a first read.
3. Straddle implied-vs-realized ledger per expiry (auto-updating).
4. Volume-tape studies once several days of live bars exist (bar-level
   volume + book totals together).

Script: analyze_positioning.py (this folder). Reads prod
option_minute_bars via DATABASE_URL.
