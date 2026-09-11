# Breakout calls — per-trade edge and portfolio viability

## Why this work

A competitor (bananapatterns.com) publishes a VCP/breakout backtest showing
19.82x over 2020-2025 (64.5% CAGR, "worst fall" −12.3%). Their signals are
real and many of the individual calls are good. Their *presentation* is not:
the analysis in `COMPETITOR.md` reproduces their engine exactly and shows the
drawdown is measured on closed-trade equity only — marked to market the same
book draws down ~50%.

We have run VCP before (`vcp_l6_study`, Aug 2026) and killed it: 2020+ subset
on NSE 500 gave 27.5% win rate, +1.2% per trade, 0.15R. `vcp_relook` concluded
the kill was right *for the exit tested*, and that the exit ladder is the real
constraint (0.32R → 1.17R).

Two things have changed since, which is why this is worth reopening:

1. **`market_data_spine` exists.** Point-in-time membership, a corporate-actions
   table, and raw bhavcopy back to 2005 for 4,839 symbols. Survivorship was the
   explicit open caveat in `vcp_l6_study`; it is now fixable.
2. **The competitor's numbers locate where the difference lives** — universe,
   entry, exit ladder, and the portfolio layer, which we have never built for
   this pattern.

## The outcome

Two measurements, deliberately separate, because they answer different
product questions:

| Layer | Question it answers |
|---|---|
| **Per-trade** | Is there an edge per signal, and how many calls a month can we honestly publish? |
| **Portfolio** | Can this be a compounding book, and what drawdown does a client actually live through? |

The decision this feeds: publish breakout calls, run a breakout portfolio,
both, or neither. We do not pre-commit to any of those.

## Non-negotiable: no look-forward entry

This is the founder's call and it defines the study.

The competitor's default entry books a fill at the pivot price on days their
screen confirmed a breakout. A stop-buy resting at the pivot is a
*pre-committed* order: it fills on **any** day price touches the pivot,
including the days that poke through and fail. Their backtest keeps the
pre-committed order's fill price but only on the subset of days that
end-of-day information says worked. Their own book carries 3,682 failed pokes
across 2,077 stocks in a single current snapshot; none are in the backtest.

Our entry rule must be decidable with information available at the moment of
the order. Two admissible forms, both to be measured:

- **E1 — stop-buy at the pivot.** Take *every* fill, including failed pokes
  that reverse the same day. Larger sample, closer to how a trader works.
- **E2 — next open after a confirmed close above the pivot.** Smaller sample,
  pays away the confirmation.

E1 vs E2 is itself a finding: the gap between them is the price of
confirmation, and it is the honest version of the competitor's 19.82x → 12.36x.

Slippage 0.2% each side on both, per `vcp_l6_study` precedent.

## Scope

**Universe.** Names above a **₹10cr/day** median-turnover floor (👤 2026-09-11),
applied point-in-time, never as today's list. That is 806 names on our store
today, 615 of which already have adjusted panels; the remaining 191 are a
re-run of `tasks/market_data_spine/lib/build_adjusted.py` against the existing
corporate-actions table, not a data acquisition job.

The floor is set above the competitor's ₹5cr deliberately: it is the liquidity
a real book needs, and it makes P6 (capacity) a test we can actually pass.

**The floor is turnover-scaled** (👤 2026-09-11). A flat ₹10cr does not travel
backwards: point-in-time it gives 690-722 names today but only **113 in 2006**,
because nominal market turnover has grown roughly sixfold. That would make the
early era a large-cap-only test and the recent era an all-cap test, confounding
the era gates C2 and P4. So the floor is ₹10cr in 2026 money deflated by
aggregate market turnover — ~₹1.6cr in 2006 — holding the universe near
500-700 names in every era. See TASKS.md §0 for the consequences this carries
into published figures and the capacity gate.

**Span.** 2006 → 2026, per D-11. The competitor's 2020-2025 window is reported
as a labelled sub-window, never as the headline.

**Basis.** Price return (D-12).

**Delisted names stay in.** D-9, delisting at last traded price. This is the
one thing the competitor structurally cannot do and it is where our number
should differ most.

## Scope boundary — not in this task

- Any change to production portfolios or `data/static/*.csv`.
- Any published claim or marketing figure. This task produces a finding, not
  copy.
- The pattern-detection spec itself is inherited from `vcp_l6_study`
  (standard tier) and is not re-derived. If the anatomy needs work, that is a
  follow-up, not this.
- Options, intraday, and anything requiring tick data.

## Open questions for the founder

1. **What a "call" is as a product** — count per month, and whether an exit is
   published alongside the entry. Deferred until the per-trade layer has a
   number; the answer should follow the signal rate, not lead it. C4 is set at
   5/month as a target, not a kill criterion.

## Critical files

| Path | Role |
|---|---|
| `tasks/market_data_spine/` | Price store, PIT membership, corporate actions |
| `data/master/prices/adjusted_pr/` | Adjusted panels (615/806 built at the ₹10cr floor) |
| `data/master/bhavcopy_eq.parquet` | Raw store, 4,839 symbols, 2005→ |
| `tasks/vcp_l6_study/trades_standard.csv` | Prior trade tape, the comparison baseline |
| `tasks/breakout_calls_2026/COMPETITOR.md` | The competitor audit and its evidence |
