# universe_foresight — can a real-time universe capture the survivors?

**Opened:** 2026-09-11 · **Status:** in-progress

## The question

The published OM25 / L6 / TL25 / COMBO track records were built on a universe
file that backdated today's index list over all history. On the honest
point-in-time universe the numbers fell a long way
(`tasks/market_data_spine/RESULTS.md`: OM25 −16pp, TL25 −18pp, L6 −23pp,
COMBO −31pp of CAGR).

The founder's question: was any of that lift *real* — that is, could an
investable universe built in real time, with no knowledge of the future, have
held the names that turned out to be the survivors? Concretely: standing in
2021, how would we have drawn a 250- or 500-name list that contained the
winners?

This folder answers it as a **diagnostic**, not a search. Nothing here is a
strategy candidate; the two books are fixed at their `mm_rebuild/MECHANICS.md`
rules and only the universe underneath them changes.

## Method — a ladder of hindsight

Every variant is expressed as a membership CSV
(`symbol,effective_from,effective_to`) and fed to the unchanged engine through
`scripts.universe_membership.resolve_universe`. No engine change, no new score,
so the CAGR step between two rungs prices exactly the one thing that differs.

| Rung | Universe | Isolates |
|---|---|---|
| `b0` | honest point-in-time membership | the truth — baseline |
| `b1` | `b0` minus every symbol whose feed dies | survivorship: never having to hold a name that disappears |
| `b1f` | `b0` minus only symbols that die after a >60% drawdown | perfect blow-up avoidance — the ceiling for a negative screen |
| `b2` | `b1` with every surviving ever-member eligible from its first priced session | early access: knowing in advance who would eventually qualify |
| `b3` | today's member list, eligible over all history | the legacy bug itself |
| `b4` | monthly top-N by trailing 63-day median turnover, no index reference | the honest alternative — reach without foresight |

`b0 → b1 → b2` is monotone in hindsight. `b3` is the actual historical error and
should land near `b2`; the residual prices the extra hindsight in narrowing to
exactly the names that are large today.

`b4` is the one rung that could be run live. Whatever it recovers of the
`b0 → b3` gap is keepable; `b2 − b4` is irreducible foresight.

## Control

`b4` reaches further down the cap scale than the index does, so its lift could
be reach rather than rule. The random-exclusion placebo from
`tasks/minimum_capital` is the control: 20 draws of a random N-name monthly
universe from names clearing a Rs 1 cr median-turnover floor, same breadth,
same book. If a random universe of the same breadth does as well, the turnover
rule earned nothing.

## Limitations

1. **Panel coverage.** `b4` ranks inside `data/master/panels/pr`, which holds
   ever-members of the four NSE indices. Names that never made any index are
   unselectable, and those skew toward the ones that did not work, so `b4` is
   optimistic. Measured in `lib/coverage.py`: at top-250 the hole is 3% of the
   universe over the span and 1% from 2016; at top-500 it is 10% and 6%. Small
   at Nifty 250 breadth, material at NSE 500 breadth.
2. **Delisting convention.** Positions in a delisted name exit at the last
   traded price with no haircut (D-9). Optimistic for bankruptcies, so the
   survivorship rung `b0 → b1` is, if anything, understated.
3. **Merger vs failure.** Most index exits are acquisitions, not collapses.
   `b1` removes both; `b1f` separates them.
4. **Price basis.** Price return throughout (D-12), as for every other honest-
   store result.

## Gate

If `b4` clears `b0` by a margin the placebo does not also produce, the next step
is extending the price panel from the bhavcopy to close limitation 1 and pricing
a real investability screen. If it does not, the answer is that the universe is
not a lever and the honest numbers stand as the books' true record.

## Critical files

- `lib/buckets.py` — builds the membership variants
- `lib/run_ladder.py` — runs MM, OM25 v4 and L6 v2 across the rungs
- `lib/coverage.py` — measures limitation 1
- `lib/placebo.py` — the random-exclusion control
- `runs/` — per-config backtests, `ladder_summary.json`, `placebo_*.json`

Runs are written here rather than to `tasks/mm_rebuild/runs` so the trial
registry that deflates that search's Sharpe is not polluted by diagnostics.
