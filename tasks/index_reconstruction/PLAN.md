# Nifty 500 index reconstruction

## Why

`data/static/nse500_membership.csv` carries `effective_from = 1900-01-01`
for all 500 current constituents. The effective-dated machinery from
`universe_membership` is live, but it has no actual history to work with:
every backtest before 2026-07 therefore runs today's index membership
backwards over the past, which is survivorship bias in its purest form.
A stock only appears in the universe because it is in the index *now*.

This task builds the real thing — a point-in-time membership record for
the Nifty 500 going back to the index's inception in 1998.

## Sources

| Period | Source | Has symbols? |
|---|---|---|
| 1998-08-01 .. 2020-09-14 | NSE `IndexInclExcl` export (2,495 rows, founder-supplied) | no, company names only |
| 2020-09-14 .. today | NSE press releases at niftyindices.com (PDF) | yes, name **and** symbol |

The join is the reason this is tractable: the modern half prints NSE
symbols next to company names, which is what pins ~1,200 historical
company names onto tradeable tickers.

## Outcome

1. An event log of every Nifty 500 inclusion/exclusion, 1998 to today.
2. A membership file in the existing `symbol,effective_from,effective_to,note`
   schema, loadable by `scripts/universe_membership.py` unchanged.
3. A validation suite proving the replay lands exactly on NSE's published
   constituent list for today.

## Acceptance test

Replaying every event forward from the 1998 seed must reproduce the current
`ind_nifty500list.csv` **exactly** — no missing names, no extras. The index
holds a fixed 500 constituents, so the count is a continuous check along the
whole chain, not just at the endpoint.

## Scope boundary

- Nifty 500 only. Nifty 50/100/250 use the same press releases and can reuse
  this pipeline, but are not built here.
- Does **not** overwrite `data/static/nse500_membership.csv`. Swapping real
  history into the production universe changes every published backtest
  number; that is a founder decision, not a side effect of this task.
- Does not fetch price history for reconstructed ex-members.

## Critical files

- `lib/parse_press_release.py` — PDF text -> Nifty 500 changes
- `lib/build_chain.py` — the replay
- `lib/renames.py`, `lib/revocations.py` — audited correction tables
- `lib/validate.py` — the acceptance suite
