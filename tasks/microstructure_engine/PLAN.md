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

- UPGRADED 2026-07-29 to `b76-parityfwd-v1`: Black-76 on the
  PARITY-IMPLIED FORWARD — per (expiry, minute), F = median over strike
  pairs of K + (C-P)e^{rT} (>=3 pairs; else spot-carry fallback,
  labeled in `underlying_src`). Model-free and self-validating: the
  same-strike CE/PE IV gap collapsed from ~+3.4 vol pts (spot/q=0 v1)
  to ~0.00 across all 23 days; futures de-carry was rejected (AUG basis
  noise over-corrected to -1.8). IV coverage rose to 99.7%.
- Expiry cutoff 15:30 IST on expiry date; T in calendar-days/365.
- IV inverted from bar CLOSE (last trade of the minute), not mid — bars
  carry bid/ask so a mid-based variant can be added and compared.
- Rows where close < intrinsic, or T <= 0, or no spot bar that minute:
  IV NULL (never fabricated).
- `engine_version` column on every row. Decision: exactly ONE
  materialized version at a time (replace is deliberate, per-day);
  reproducibility lives in engine_version + git history, not parallel
  table copies.

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
