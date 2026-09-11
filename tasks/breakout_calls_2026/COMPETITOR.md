# bananapatterns.com — audit of the published VCP backtest

Audited 2026-09-11 against a logged-in account. Their `/api/backtest` returns
the full trade log as JSON, so every claim below is checked against their data
rather than read off the page.

Parameters audited: `screen=vcp, entry=pivot, stop=8, sell=ma50, risk=1.5,
maxpos=5, market=all, period=all, capital=1000000`.
Published result: ₹10L → ₹1,98,17,941 (19.82x), CAGR 64.5%, "worst fall" −12.3%.
The page carries a `PROVISIONAL` badge: "under a methodology review and will be
revised."

## Their engine, reproduced

Position size = risk ÷ stop of equity at entry (1.5% / 8% = 18.75%), capped at
30%. Equity updates **only when a trade closes**. Replicating exactly that:

| | replication | published |
|---|---|---|
| terminal | 19.75x | 19.82x |
| max drawdown | 12.3% | 12.3% |

The 0.4% residual is the 30 names absent from our store. The match on drawdown
to the decimal is what identifies the drawdown definition.

## Finding 1 — the drawdown is realised-only (material)

"WORST FALL −12.3%" sits beside CAGR with no tooltip. Open positions are never
marked. Marking the same book to market daily against our adjusted store:

| | reported | marked to market |
|---|---|---|
| worst fall | −12.3% | **~50%** |
| 2022 | +5.8% | −48% trough |
| 2023 | +38.3% | −53% trough |
| 2024 | +92.8% | +11.1% |

Reconstructed on 143 of 173 trades. A thinner book carries less exposure, so
~50% is a conservative floor, not an upper bound. MAR goes from 5.2 to ~1.3.

## Finding 2 — the stat strip counts a different population than its label

`total.n` is **760** (every signal the screen fired) while the UI prints
"**173** trades" beside the same row. On the Blue sky screen it is 5,671
signals labelled "191 trades".

Recomputed on the actual 173 taken trades:

| | shown | actual |
|---|---|---|
| won | 48% | 43.9% |
| average gain | +31.6% | +34.9% |
| average loss | −5.5% | −5.3% |
| median | −0.5% | −0.7% |

Side effect: taken-mean +12.4% vs all-signal mean +12.3%. Their "book full,
587 passed up" selection adds no skill — which of the signals you get is
ordering luck.

## Finding 3 — look-forward in the entry (the one that matters)

Not the fill price. Only 9 of 138 alignable trades (7%) are booked below the
breakout day's low, i.e. at a price that never traded — SMLMAH on 2025-12-02
is booked at 3259.30 on a day that opened, low'd and high'd at 3364.30, a
locked upper circuit. Repairing all nine costs 0.10pp per trade. Immaterial.

The bias is in **which days get taken**. A stop-buy resting at the pivot is a
pre-committed order: it fills on any day price touches the pivot, including
days that poke through and reverse. Their backtest books that order's fill
price but only on the subset of days end-of-day confirmation says worked.

Their own data model names the excluded population: `failedPokeDates` /
`pokesN`. A single current snapshot of the book carries **3,682 failed pokes
across 2,077 of 4,718 stocks**. None appear in the backtest. (Snapshot-scoped
and gated by the rest of the screen, so this is an order-of-magnitude
illustration, not a count of missed trades.)

Switching their own dial to "Breakout close" — which their tooltip calls
"(realistic)" — removes the bias and the result drops:

| entry | mult | max DD (realised-only) | 2022 |
|---|---|---|---|
| at the pivot (default) | 19.82x | 12.3% | +5.8% |
| breakout close | 12.36x | 26.5% | −10.3% |

## Finding 4 — survivorship

4,718 tracked names; **4,707 carry a 2026 price bar**. The 14 that do not are
all recent listings that went stale (`listedWk` ≤ 91 weeks), not historical
delistings. There is no company in the book that traded in 2020 and delisted
since. A 2020 scan can only ever see 2026 survivors.

## Finding 5 — concentration and bookkeeping

- Top 10 trades are 61% of summed return. Drop the top 3 → 19.8x becomes
  10.4x (CAGR 64%→48%). Drop the top 10 → 3.9x (25.5%).
- 5 of 173 are still open, marked to the 2025 year-end close and compounded.
  Excluding them: 14.1x.
- 5 pairs are the same stock bought twice within days, taking 2 of 5 slots —
  E2E on 13 and 14 Aug 2024, both held to 18 Dec, +124% and +112%.
  De-duplicated: 17.3x.
- 17 losses are worse than −8.5% against a stated 8% stop (gap-throughs), so
  realised risk per trade exceeds the advertised 1.5%.

## What checked out

Stated plainly because it bears on whether the pattern is real.

- **Corporate actions are handled correctly.** The three trades spanning a
  split: LAURUSLABS +163.35% (ours +159.31%), VBL +12.76% (+10.47%),
  TFCILTD +44.64% (+43.58%). On raw prices these would read −48%, −45%, −71%.
- **The liquidity floor is point-in-time**, not today's list — 24 of the 173
  traded names fail today's ₹5cr floor.
- **Position sizing is exactly as described** (risk ÷ stop, 30% cap).
- **The copy is honest where the engine is not**: `PROVISIONAL` badge, "85% of
  this period was a strong market", and a weak-market tooltip that volunteers
  "in a sustained uptrend this usually lowers returns — its value is dodging
  prolonged bears, which this 2020–2025 window doesn't contain."

## Sensitivity across their own dials

Every screen and every setting prints 26-76% CAGR over this window. When every
variant of a method looks extraordinary, the window is doing the work.

| variant | mult | CAGR | DD (realised-only) |
|---|---|---|---|
| VCP, pivot, ma50 (default) | 19.82x | 64.5% | 12.3% |
| VCP, close, ma50 | 12.36x | 52.0% | 26.5% |
| VCP, pivot, ma150 | 12.06x | 51.4% | 14.7% |
| VCP, pivot, +25% target | 11.06x | 49.3% | 18.4% |
| VCP, close, +25% target | 4.07x | 26.3% | 18.5% |
| Blue sky, pivot | 29.76x | 76.0% | 11.5% |
| Blue sky, close | 10.82x | 48.7% | 21.0% |
| Multi-year base, pivot | 13.19x | 53.7% | 16.7% |
| IPO base, pivot | 10.42x | 47.8% | 20.5% |
| maxpos 10 | 30.64x | 76.9% | 12.2% |
| maxpos 3 | 6.74x | 37.4% | 9.0% |

## Head-to-head with our own prior work

`vcp_l6_study` (Aug 2026), NSE 500, 2020+ subset: **27.5% win rate, +1.2% per
trade, 0.15R**. Their taken-173 over the same window: **43.9%, +12.4%**.

Same pattern, same window. The whole gap sits in four things, which is the
decomposition `PLAN.md` proposes to measure:

1. Universe — 4,718 names incl. microcap/SME vs our NSE 500.
2. Entry — pre-committed vs confirmation-selected (Finding 3).
3. Exit ladder — Minervini partials vs a pure 50DMA trail. `vcp_relook`
   already says this is the binding constraint (0.32R → 1.17R).
4. The portfolio layer — we measured per-trade only; they compound 5 slots at
   18.75% each. A modest per-trade edge run through that produces a large
   headline. This is the layer we have never built for this pattern.

## Reproducing this

`evidence/bp_backtest_vcp_pivot.json` is their trade log as fetched. The
22 MB `universe.json` is not committed; refetch from `/api/data/universe.json`
while logged in.
