# Breakout-call research — product handoff

Written 2026-07-24 at branch close. This is the productization entry
point; full evidence trail in RESULTS.md (this folder) and
tasks/stress_reversal_calls/RESULTS.md. Shareable research note:
https://claude.ai/code/artifact/3359ce85-c538-476a-8fb4-91a8410c62a8

## The two configurations that survived everything

**India feed (flagship):** NSE 500 · fresh cross above prior 20-day
high · top-quartile momentum (126d return / vol, floor 5%) · cap 100
concurrent, slots by momentum rank · exit when momentum rank < 0.35 ·
no stop · next-day OHLC/4 +/- 20bps.
Full window 29.7% CAGR / 1.40 Sharpe / -35.3% MaxDD; 2023+ tail
34.6% / 1.49. ~128 calls/yr, 2.6/week, fresh call in 88% of weeks,
median hold ~7 months. Cap-50 variant: 32.2% / 1.49 at 62 calls/yr.
(With a 20% trail: Sharpe 1.57, MaxDD -24.6%, but median call goes
negative — a portfolio-vs-product trade the founder owns.)

**US variant (second market):** S&P 500 union NDX · same entry ·
cap 50 · exit rank < 0.35 · NO stop (three stop variants all cost
Sharpe in the US). 22.2% CAGR / 0.93 Sharpe vs SPY 14.9%; 59.2% win,
+3.6% median call. Monthly correlation with India feed: 0.34.

## Hard constraints on productization

1. **Validity gate: FAILED for forward-return claims.** Direction lift
   vs same-date baseline is negative (tail-carried economics). No
   "these calls returned X%" copy. Ship as a transparent trend-following
   journal (full loss distribution shown) or don't ship. Re-run
   `tasks/insight_engine/pattern_validity_study.py` + dedup vs
   multi_year_breakout before ANY claim.
2. **Survivorship**: research used current-snapshot universes. A
   production engine must use effective-dated membership
   (scripts/universe_membership pattern) and live prices.
3. Costs are slippage-only (20bps); no STT/taxes modeled.
4. US data: us_equities_data/ is a yfinance rebuild (EODHD lapsed);
   parity-verified vs surviving EODHD files. SP400 universe list:
   tasks/donchian_channel/us_expanded_universe.csv.

## What was rejected (do not re-litigate without new evidence)

Donchian exits on production portfolios (H2); George-Hwang 52w-high
ranking + blend (H1); Donchian breadth beyond the 55d family (H3);
unfiltered breakouts (H4 control); fast exits don10/mid20 (H4b);
fixed-20% and 10xATR stops in the US (H4e/f); US mid caps three ways
(H4f/g); cap 150 and signal-widening in India (H4h); stress-regime
reversal calls, both legs, two thresholds (stress_reversal_calls).

## Build list if green-lit

- Daily signal job (panels + score + slot state machine) — engine
  logic lives in h4c/h4f/h4h simulate(); port to kite-api service.
- Call ledger (entry/exit/effective prices, net P&L per house rule) +
  subscriber feed UI + watchlist tier (qualified-but-unslotted
  breakouts) for daily texture.
- Track record page = the artifact's tables regenerated from the live
  ledger (win rate, distribution, hold buckets — never bare means).

## Open thread

Fundamentals feed sourcing (founder) -> unlocks PEAD + multi-factor
calls, the surviving diversification candidates after stress-reversal
failed. Evaluate any feed for point-in-time correctness first.
