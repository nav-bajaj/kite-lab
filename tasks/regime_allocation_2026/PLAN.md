# Regime-conditioned allocation for the trend screen

## Why

`trend_screen_2026` §8 showed that sizing the trend book by breadth phase at
entry raises out-of-sample Sharpe from 0.66 to 0.92 (2016-2026), and that the
gain is selectivity, not exposure — halving every position scores *worse*
than always-on. It also showed the result is contaminated: the phase taxonomy
was designed on the full 2006-2026 sample, so the "out-of-sample" decade is an
upper bound, not a forward test. And one parameter, the TOPPING weight, ranks
its five candidate values in exactly opposite order in the two halves.

This task exists to find out whether a regime layer can be specified in a way
that would have survived being frozen in 2015 — and if so, what it is worth.

## The outcome

A single regime rule, with at most four parameters, that either

- clears the pre-committed gates in `TASKS.md §0` on a walk-forward basis and
  goes forward as the allocation layer for a trend-screen portfolio, or
- fails them, in which case the finding is that breadth phase is a research
  observation and not a tradeable overlay, and it is recorded as such.

Both are useful. The second is more likely and must be reported as plainly as
the first.

## What is fixed, and must not be changed by this task

| Fixed | Value | Why |
|---|---|---|
| Universe | top 500 by trailing turnover + scaled ₹10cr floor, PIT, survivorship-free | settled in `trend_screen_2026` |
| Signal | LEADING + EXTENDED state at month-end, ranked by % above 52-week low | settled, 135/135 thresholds |
| Exit | 150-day trail, no hard stop | settled §7 |
| Book | 25 slots, equal-weight 1/N, 10% ADV cap, daily mark-to-market | settled §7 |
| Trade tape | `tasks/trend_screen_2026/data/calls_full_range.csv`, 7,828 calls | do not regenerate |
| IS / OOS | 2006-2015 / 2016-2026 as primary; two alternates in §4 | fixed before any run |

Only the **regime layer** is under study. Anything that changes the rows above
is a different task.

## Ideas in scope — broad

The point is to find a regime definition that is *simple enough to have been
chosen a priori*. Every candidate is scored on the same harness.

**A. Regime signal** — what "the tape" is measured by
1. `pct_above_200` — share of the universe above its own 200-day (current)
2. `pct_leading` — share of the universe in the screen's own LEADING/EXTENDED
   states; the screen measuring its own opportunity set
3. `net_highs` — share at a 52-week high minus share at a 52-week low
4. `pct_above_50` — the faster analogue of (1)
5. A composite: mean rank of (1)-(3)

**B. Direction window** — how "improving" is measured: 21 / 42 / 63 / 126
sessions. §8 used 63 without testing alternatives.

**C. Level cut** — median (current), fixed 50%, or no level at all (direction
only). `trend_screen_2026` found direction carries 5.9× and level 1.6×, so
direction-only is the leading simplification.

**D. Allocation shape**
1. Four buckets with weights (current): {EXP, REC, TOP, CON} → {1, 1, w, 0}
2. Two buckets, direction only: rising → 1, falling → 0
3. Continuous: weight = clip((chg − lo) / (hi − lo), 0, 1), two parameters
4. Hysteresis: a regime must persist N sessions before it changes allocation,
   to cut whipsaw

**E. Where the rule acts**
1. Entry sizing only (current)
2. Entry + forced exit when the regime turns to the zero-weight state
3. Entry + reduce open positions to the new weight (rebalance down)

**F. Cross-signal check** — does the same rule help the *breakout* tape
(`tasks/breakout_calls_2026/data/book_trades.csv`)? A regime layer that only
works on one signal is fit to that signal.

## Non-negotiables — tight

- **Walk-forward is the verdict, not IS/OOS.** Refit the regime weights on a
  trailing 8-year window, apply to the next year, chain 2014-2026. A rule that
  only works when its weights are chosen with hindsight does not count.
- **The exposure control runs alongside every candidate.** For each rule,
  also run the same trades with a constant weight equal to that rule's mean
  weight. A rule must beat its own exposure-matched control, or the gain is
  de-risking, not timing.
- **Every candidate is counted.** The trial count feeds a deflation estimate
  (Gumbel expected max of N equal draws) reported next to the best cell. The
  best cell of a search is a selection artifact until shown otherwise.
- **Parameter budget: ≤ 4** for the regime layer, all-in — signal choice,
  window, level cut, and every weight or threshold.
- **No new signals, exits, universes or books.** If a result seems to want
  one, write it in RESULTS.md as a follow-up and stop.
- **Realised-only drawdown is never computed.** Marked to market daily, always.

## Critical files

| Path | Role |
|---|---|
| `tasks/trend_screen_2026/lib/run_isos.py` | The harness this extends — reuse `book()` |
| `tasks/breakout_calls_2026/lib/book.py` | `build_book`; honours a per-trade `wt` column and a `regime` date→bool series |
| `tasks/breakout_calls_2026/lib/exits.py` | `load_panel(sym)` |
| `tasks/trend_screen_2026/lib/breadth.py` | `build()`, `phases()` — extend for signals A2, A4 |
| `tasks/trend_screen_2026/data/breadth.parquet` | daily breadth, cols: `n, pct_above_200, at_high, at_low, net_highs, pct_above_200_chg, net_highs_chg, phase` |
| `tasks/trend_screen_2026/data/calls_full_range.csv` | the tape; cols: `symbol, entry_date, exit_date, entry, ret, bench_ret, alpha, hold, rnk, state, phase, pct_above_200, pct_above_200_chg, open` |
| `tasks/trend_screen_2026/data/features_t500_ranked.parquet` | month-end states per name, for signal A2 |
| `tasks/breakout_calls_2026/data/pit_universe.parquet` | `date, symbol, adv, eligible` — ADV for the participation cap |
| `data/master/benchmarks/NIFTY_500.csv` | trading calendar and benchmark |
