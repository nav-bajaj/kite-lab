# Historical-data probe — 2026-07-27

Question: can we pull options history from Zerodha, and is there anything
in a few days of it worth modeling?

## Capability findings

- The account HAS the historical-data add-on. `historical_data()` returns
  minute candles for index, futures, and options, with `oi=True` giving
  minute-level OI. Verified at least 30 days back for a live weekly option
  (7,875 candles = 21 sessions).
- No depth/bid-ask anywhere in this API — confirmed. Spread/liquidity/
  imbalance history remains exclusively what our live worker records.
- Backfilled 7 days x 87 contracts (today's selection) = 162,290 minute
  rows -> `data/options/history/minute_2026-07-27_7d.parquet` in ~40s at
  the 3 req/s throttle. Backfill is cheap.

## What five sessions (Jul 21-27) showed — descriptive, not signal claims

Spot path: 24193 -> 23991 -> 23872 -> 23787 -> 24004 (sell-off, then
Monday bounce). Near expiry 2026-07-28 (Tuesday).

1. **PCR tracked, didn't lead.** Near-expiry OI PCR fell with the market
   (1.24 -> 0.63) and jumped back to 1.04 on the bounce. In this window it
   was a coincident positioning gauge, not a predictor.
2. **Textbook pin forming into expiry.** Expiry-eve walls: 24000 is the
   biggest strike on BOTH sides (13.8M CE / 15.4M PE OI) with a 24200 call
   wall (14.9M). Spot closed 24003.7.
3. **Max pain nailed expiry eve.** Max pain sat at 24100 all week while
   spot diverged as far as -313 pts below it; on expiry eve max pain moved
   to 24000 and spot closed 3.7 pts from it. One expiry — no claim — but
   exactly the structure worth accumulating across expiries.
4. **Straddle premium ran rich.** ATM straddle implied-to-expiry move vs
   next-session realized range: 1.32%/0.85%, 1.29%/0.77%, 1.08%/0.91%,
   0.95%/0.50%. Caveat: implied is to-expiry while realized shown is one
   session, so early-week rows aren't apples-to-apples — but the expiry-eve
   compression (0.52% implied for expiry day) and the persistent gap are
   the variance-risk-premium shape you'd expect. Worth a proper study once
   we have many expiries.
5. **Basis flipped hard.** Near-futures close basis went -8 pts (below
   spot, dividend-season backwardation) early week to +43/+36 pts contango
   right as spot bottomed and bounced — a day before futures expiry, when
   basis should be converging to zero. Could be genuine roll/short-covering
   pressure; could partly be a close-timestamp artifact between index and
   futures. Needs the live capture's synchronized ticks to distinguish —
   which is precisely a V1 use case.
6. **Naive dOI/dSpot is empty.** 30-min OI changes vs spot moves: corr
   -0.07 (CE) / +0.10 (PE), n=64. No linear intraday relation at this
   granularity — consistent with the premise that the interesting
   microstructure lives in depth/flow, which only the live engine records.

## Implications for the engine

- **Backfill becomes a feature.** Phase 3's `option_minute_bars` can be
  seeded from the historical API for OHLC/volume/OI columns (depth-derived
  columns stay live-only and NULL for backfilled rows). That means the
  analysis layer starts with ~a month of history on day one instead of
  empty tables. Added to TASKS.md Phase 3.
- The pin/max-pain and straddle-premium structures are the first analytics
  candidates once V2 opens — both need many expiries, which argues for
  starting capture (and daily backfill) now.

Scripts: `backfill_history.py`, `explore_history.py` (this folder).
