# Market Microstructure Engine — Plan

> Umbrella initiative for options analytics built ON TOP of the options
> data engine (tasks/options_data). Founder's vision doc: "MarketWorks
> Gamma Engine" (2026-07-29) + the decision to frame it broader from the
> start: gamma is one module of a Market Microstructure Engine that will
> also hold vanna/charm, IV surfaces, liquidity analytics, order-flow
> imbalance, and dealer positioning.

## Architecture (from the vision doc, kept strict)

    Zerodha -> Options Data Engine -> [Microstructure Engine] -> Dashboard

- The engine NEVER talks to Zerodha. Inputs are option_minute_bars,
  option_chain_snapshots, and (live, later) the worker's chain state.
- Each layer depends only on the layer beneath.
- Code home: `kite-api/app/microstructure/` — pure math modules + a
  materializer that persists derived values back to Postgres.

## Staging (doc's progression; each stage adds assumptions and must say so)

- **Stage 1 — measured math (BUILDING NOW):** per-minute IV (inverted
  from bar closes), delta, gamma, vega, theta for every option bar.
  Persisted to `option_greeks_minute` with the assumption set + engine
  version on every row.
- **Stage 2 — aggregation:** gamma by strike, aggregate gamma profile,
  max-gamma strike, concentration.
- **Stage 3 — estimated positioning:** dealer-gamma sign assumptions,
  gamma flip level, call/put walls. Everything labeled ESTIMATED.
- **Stage 4 — flow-adjusted positioning:** intraday OI deltas, book
  imbalance (we capture it), futures flow, option volume. Confidence
  levels surfaced to the user.

## Stage-1 assumptions (documented, versioned — never hidden)

- Black-Scholes on SPOT with flat r = 6.5% p.a., q = 0. For weekly
  expiries (T <= ~10 trading days) carry error is negligible vs quote
  noise; revisit with futures-implied forward (Black-76) in Stage 2.
- Expiry cutoff 15:30 IST on expiry date; T in calendar-days/365.
- IV inverted from bar CLOSE (last trade of the minute), not mid — bars
  carry bid/ask so a mid-based variant can be added and compared.
- Rows where close < intrinsic, or T <= 0, or no spot bar that minute:
  IV NULL (never fabricated).
- `engine_version` column on every row; recompute = new version, old
  rows replaced only deliberately (reproducibility principle).

## TDD

Spec tests first (kite-api/tests/test_greeks_math.py): known-value BS
prices, IV inversion round-trips, put-call parity (call delta - put
delta = 1 under q=0), gamma/vega CE==PE symmetry, intrinsic-floor and
expiry-edge rejection, materializer roundtrip on sqlite.

## Consumers queued behind Stage 1

- Straddle sim upgrades: delta-hedged variants, IV-percentile entry
  filters (tasks/options_data/research/straddle_sim.py).
- Straddle implied-vs-realized ledger in vol terms rather than points.
- OI-migration monitor gains gamma weighting (Stage 2 preview).
