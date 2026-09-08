# Market data spine

## Why

`index_reconstruction` produced a correct point-in-time universe and the price
history to go with it, and in doing so established that the price panel itself
cannot support what the platform is about to promise. Three findings force this
work (evidence in `CONTEXT.md`):

1. **Refetching Kite is not idempotent.** Its API back-adjusts for dividends,
   so 510-591 of 668 days change on a re-pull.
2. **The stored panel is inconsistent with itself.** The 15-day refetch cuts
   bands of dividend-adjusted prices into an otherwise raw series.
3. **Published rebalances have already been restated** — five times, each
   inside that 15-day window, one of them cascading a −2.44% price revision
   into four other position sizes. This is leak 1 in
   `adjusted_price_series/PLAN.md` firing in production, with evidence.

None of this matters much while the numbers are internal. All of it matters the
moment they are not. The pre-registration window is the only time these
foundations can be changed, so they get changed now.

The end state: a portfolio decision made on a given day can be reproduced
exactly, forever, from data as it was known that day — while the research
series stays free to be corrected.

## Outcome

1. A master historical data file that is the single input to backtests.
2. All four production portfolios re-run over the dated universe and that file,
   with every difference against today's published numbers attributed to a
   cause.
3. An append-only ledger of every rebalance since each strategy's lock date,
   and a check that fails if a recorded entry ever changes.
4. A standing procedure so index membership stays correct without anyone
   remembering to do it.

## Decisions already taken

See `DECISIONS.md`. In short: Kite is the day-to-day source and GDF the
supplement for delisted history Kite structurally cannot serve (D-1); the store
holds raw rows append-only (D-2); the panel is **price-return, ex-dividend** —
the founder's call, owned by `adjusted_price_series` (D-3); the ledger starts
at each strategy's own lock date (D-4); nothing published is ever recomputed
(D-5).

## What belongs here, and what does not

`tasks/adjusted_price_series/` already owns the price store and the corporate
actions — it was opened the same day with the founder's ex-dividend call, and
its plan is further along than anything drafted here. It covers freezing the
pre-flip panel, writing the price-data contract, sealing the three leaks that
let dividend-adjusted rows into the panel, and the enforcement that makes the
contract stick.

**This folder does not duplicate that.** Price history and corporate actions
are prerequisites, tracked here as dependencies and nothing more.

What is genuinely this folder's:

1. **Master historical data file** — one input to backtests, covering all-ever
   members across the four reconstructed indices, source-tagged. Depends on
   the price store being settled.
2. **Portfolios on the dated universe** — the first real test of the whole
   stack together, and the moment any published number moves.
3. **The immutable ledger** — start dates already established (D-4), no
   re-derivation and no downloads needed.
4. **Standing membership procedure** — `adjusted_price_series` handles
   corporate actions; nothing yet keeps index membership correct going forward,
   and that is the half this branch just proved is hard.

## Scope boundary

- Does not change any strategy logic. If a published number moves, it must be
  attributable to data, and that attribution is part of the deliverable.
- Does not touch `nse500_data/` until phase 1 defines the replacement; the
  backfill directories stay separate meanwhile.
- Does not merge to `beta_gtm_mvp`. This branch is 39 commits behind it and
  production reads none of this yet.
- Options data is out of scope.

## Critical files

- `tasks/index_reconstruction/` — the membership and price reconstruction
- `scripts/history_utils.py` — `lookback_days = 15`, the refetch that rewrites
- `scripts/apply_corporate_actions.py`, `data/corporate_actions.json` — the
  event system to be built out (one row today)
- `scripts/universe_membership.py`, `data/static/*_membership.csv` — the
  effective-dated universe the reconstruction feeds
- `lib/audit_immutability.py` — the regression that catches restatements
