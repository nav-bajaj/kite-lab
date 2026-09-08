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
| 1996-09 .. 2020-09 | NSE `IndexInclExcl` workbook, one sheet per index (founder-supplied) | no, company names only |
| 2020-09 .. today | NSE press releases at niftyindices.com (PDF) | yes, name **and** symbol |
| 2022-03-31 | NSE index factsheets (founder-supplied) — an independent CHECKPOINT, not an input | yes, symbols |

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

Three independent checks, all of which must hold:

1. The constituent count is a continuous invariant — each index holds a fixed
   size, so any mis-joined rename or dropped event shows up immediately.
2. Replaying forward must reproduce today's published constituent list exactly.
3. The reconstruction must match NSE's March 2022 factsheets, a document
   neither source feeds, which tests the chain mid-way rather than only at
   its endpoint.

Only the Nifty 500 sheet opens with a seed. The other three start mid-stream,
so their membership at the first event has to be DERIVED by un-applying every
event backwards from today; the derived seed landing exactly on the index size
is itself a check.

## Scope boundary

- Four indices: Nifty 500, Nifty 50, Nifty 100 and Nifty LargeMidcap 250
  (= Nifty 100 + Nifty Midcap 150, the repo's `nifty250` universe).
- Does **not** overwrite `data/static/nse500_membership.csv`. Swapping real
  history into the production universe changes every published backtest
  number; that is a founder decision, not a side effect of this task.
- Does not fetch price history for reconstructed ex-members.

## Critical files

- `lib/parse_press_release.py` — PDF text -> Nifty 500 changes
- `lib/build_chain.py` — the replay
- `lib/renames.py`, `lib/revocations.py` — audited correction tables
- `lib/validate.py` — the acceptance suite
