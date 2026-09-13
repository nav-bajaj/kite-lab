# Results — trigger_calls_2026

**Verdict:** month-end (T3) is the best of the three triggers per call under
every gate (+17.1% expectancy gated on hysteresis 40/60, against +15.5% for
T2 rank-entry and +11.9% for T1 state-entry), so firing on the stock's own
trigger costs 5.2pp per call rather than gaining — but not for the reason the
cadence argument assumes: on the 2,441 episodes both rules catch, T1 gets in
12.6 days earlier and is worth **+5.5pp** more per call, and the entire
deficit comes from the 48.4% of T1 episodes month-end never confirms, which
return +2.8% against +16.1%. The month-end delay is working as a confirmation
filter, not as a drag. The persistent gate helps the **call** (+1.6pp
expectancy, +1.4pp alpha on T3) and hurts the **book**: at 25 equal-weight
slots it takes CAGR from 19.6% to 15.2% and Sharpe from 0.70 to 0.52 over the
full span (18.6% → 9.1%, 0.64 → 0.21 OOS) while cutting drawdown only from
−54.1% to −44.6%, because it blocks entries without forcing exits and drops
exposure from 87% to 67%. Track B's C4 BROAD taxonomy does **not** beat
hysteresis 40/60 as the product gate on the winning trigger — on T3 it is
0.5pp worse on expectancy (+16.6% vs +17.1%) and 1.7pp worse on zero-month
share (38.2% vs 36.5%), and it only leads on T1, the trigger nobody should
ship. The reference exit survives its own sweep: ma150's +17.1% beats the
six-cell grid median of +6.2% and the Gumbel E[max of 5] of +14.8%, so it is
not a selection artifact.

## A1 reproduction — NO

> **Superseded.** The BRIEF specified the wrong gate for this check. Kept
> for the engine cross-check, which stands. See **A1 re-run** below.

T3 = each symbol's last eligible session per (year, month), top-20 by
`above_low` among LEADING/EXTENDED, one position per name at a time,
hysteresis 40/60 gate, reference exit.

| Cut | n | win | expectancy | vs target |
|---|---|---|---|---|
| Target (`trend_screen_2026` §7) | 757 | 45.0% | +20.71% | — |
| **T3, trigger year ≥ 2014** | **826** | **41.8%** | **+18.10%** | +69 / −3.2pp / −2.61pp |
| T3, entry year ≥ 2014 | 845 | 42.4% | +19.72% | +88 / −2.6pp / −0.99pp |
| T3, no same-name dedupe | 2,169 | 44.0% | +19.97% | +1,412 / −1.0pp / −0.74pp |

Tolerance is 5 calls / 1pp / 0.5pp. Every leg misses.

**The engine is not the problem.** 587 of the 1,275 gated T3 calls appear in
`calls_full_range_ohlc4.csv` at the identical (symbol, entry_date); across
those 587 the maximum absolute return difference is **4.4e-16**. Panels,
OHLC/4 fills, 0.2% slippage and the 150-day trail agree exactly. Of the 688
unmatched calls only 12 are on symbols the reference tape never touches, and
190 have a reference call on the same symbol within 45 days — the
disagreement is *which* calls are selected, not how they are priced.

**No top-20 cut of the reference tape reproduces 757.** Searching the
reference tape over three rank columns × seven thresholds × three gates for
2014-2026:

| Reference-tape cut | n | win | expectancy |
|---|---|---|---|
| rank ≤ 20 (stored full-universe rank), hysteresis | 363 | 44.4% | +25.96% |
| rank ≤ 20 (dense within month), hysteresis | 2,061 | 40.2% | +15.12% |
| rank ≤ 20 (dense within month), tape's own `wt` | 1,614 | 45.2% | +20.40% |
| rank ≤ 40 (stored rank), hysteresis | 754 | 42.3% | +20.72% |

The closest fit to §7's triple is **rank ≤ 40**, which lands the count and
the expectancy and misses the win rate by 2.7pp. Separately, the reference
tape's `wt` column agrees with a 40/60 hysteresis gate on only **61.4%** of
rows, so `wt` is some other regime series. Either §7's "top 20" is not a
top-20 cut of this tape, or its gate is not the 40/60 hysteresis. Reported
as-is; nothing was tuned to close the gap.

## Regime gate — hysteresis 40/60 on % above the 200-day

| Metric | Value |
|---|---|
| Span | 2005-02 → 2026-09 (20.9 years) |
| Flips | 32 (**1.53 / year**) |
| On-runs | 17 |
| Median run, all | **99 sessions** |
| Median run, on | 155 sessions |
| Median run, off | 88 sessions |
| Time on | 65.0% |

Matches the expected ~1.6 flips/yr and ~99-session median run.

## Per-call, all triggers × gate

Reference exit (first close below the 150-day, no hard stop). Alpha is per
call against NIFTY 500 over the same hold.

| Trigger | Gate | n | win | avg win | avg loss | ratio | expectancy | alpha | median | med hold |
|---|---|---|---|---|---|---|---|---|---|---|
| T1 state-entry | on | 1,134 | 37.9% | +55.0% | −14.4% | 3.81 | +11.9% | +6.9% | −5.9% | 67 |
| T1 state-entry | none | 2,119 | 34.8% | +49.8% | −11.6% | 4.30 | +9.8% | +5.1% | −4.7% | 55 |
| T2 rank-entry | on | 1,982 | 41.1% | +60.4% | −15.9% | 3.80 | +15.5% | +10.0% | −5.1% | 85 |
| T2 rank-entry | none | 3,067 | 37.7% | +55.1% | −13.1% | 4.19 | +12.6% | +7.8% | −4.5% | 72 |
| **T3 month-end** | **on** | **1,275** | **42.0%** | **+64.6%** | **−17.4%** | **3.72** | **+17.1%** | **+11.7%** | **−5.8%** | **89** |
| T3 month-end | none | 1,828 | 41.2% | +59.1% | −15.1% | 3.92 | +15.5% | +10.3% | −5.0% | 83 |

Per era (n / win / expectancy):

| Trigger | Gate | 2006-12 | 2013-19 | 2020-26 |
|---|---|---|---|---|
| T1 | on | 471 / 32.9% / +5.3% | 297 / 42.1% / +15.1% | 366 / 41.0% / +17.9% |
| T1 | none | 800 / 30.5% / +4.7% | 686 / 35.4% / +8.8% | 633 / 39.7% / +17.2% |
| T2 | on | 720 / 37.1% / +8.5% | 560 / 44.8% / +19.8% | 702 / 42.3% / +19.3% |
| T2 | none | 1,072 / 32.7% / +6.3% | 1,004 / 38.1% / +13.2% | 991 / 42.7% / +18.7% |
| T3 | on | 425 / 41.4% / +11.9% | 365 / 39.5% / +18.6% | 485 / 44.3% / +20.4% |
| T3 | none | 598 / 37.0% / +9.0% | 625 / 38.9% / +13.9% | 605 / 47.9% / +23.6% |

The ordering T3 > T2 > T1 holds in every era and under both gate settings.
The gate adds expectancy to every trigger in every era except T3 2020-26,
where the un-gated tape is better (+23.6% vs +20.4%) because the gate was off
through the March 2020 bottom.

## Cadence

Span 2006-01 → 2026-09, 249 months.

| Trigger | Gate | calls | mean/month | median/month | zero months | busiest month | longest empty run |
|---|---|---|---|---|---|---|---|
| T1 | on | 1,134 | 4.6 | 3.0 | 33.3% | 2008-01 (36) | 15 months |
| T1 | none | 2,119 | 8.5 | 6.0 | 2.4% | 2006-07 (36) | 2 months |
| T2 | on | 1,982 | 8.0 | 6.0 | 30.9% | 2016-11 (50) | 15 months |
| T2 | none | 3,067 | 12.3 | 10.0 | 0.0% | 2008-01 (48) | 0 months |
| T3 | on | 1,275 | 5.1 | 5.0 | 36.5% | 2012-02 (21) | 15 months |
| T3 | none | 1,828 | 7.3 | 7.0 | 1.6% | 2006-01 (20) | 2 months |

The trigger tapes do not smooth delivery — they concentrate it. T2 un-gated
is the only definition that never goes a month without a call. Every gated
variant has the same 15-month silence (the 2008-09 bear), which is a product
problem the trigger choice cannot fix.

## Entry timing and overlap — T1 vs T3

2,441 of 4,733 T1 episodes (51.6%) are also fired by month-end within 31 days.

| Metric | T1 | T3 | T1 − T3 |
|---|---|---|---|
| Mean return | +16.1% | +10.6% | **+5.5pp** |
| Median return | −2.4% | −5.6% | +2.3pp |
| Win rate | 44.0% | 37.0% | +7.0pp |
| Mean hold (bars) | 95 | 88 | +7 |
| T1 the better of the pair | — | — | 66.3% of pairs |

Lateness: mean 12.6 calendar days, median 12; 11.8% of pairs fire the same
day. The cost scales with the wait:

| Days late | pairs | mean T1 − T3 |
|---|---|---|
| 0 | 288 | 0.0pp |
| 1-7 | 681 | +2.3pp |
| 8-14 | 481 | +5.4pp |
| 15-21 | 442 | +7.2pp |
| 22+ | 549 | +11.2pp |

**Overlap — this is the whole result.** 2,292 of 4,733 T1 calls (**48.4%**,
48.5% under the gate) are episodes month-end never fires on. Of those misses,
**79.2% had left LEADING/EXTENDED by the next month-end** and 20.8% were
still in state but out of the top 20. Splitting the T1 tape on that flag:

| T1 subset | n | win | expectancy | alpha | med hold |
|---|---|---|---|---|---|
| Month-end also fires | 2,441 | 44.0% | +16.1% | +10.2% | 71 |
| Month-end never fires | 2,292 | **23.5%** | **+2.8%** | **+0.5%** | 34 |

Half of what a state-entry trigger produces is names that cannot hold the
state for three weeks, and they are worth almost exactly zero alpha. The
21-session wait is not a latency cost to be engineered away; it is the
filter that makes the tape work. A trigger product wanting T1's timing has
to replace that filter with something else — a persistence requirement, not
a faster fill.


## A1 re-run (corrected gate) — PASS

Gate = composite breadth **direction**, ON when `composite(T) > composite(T−63
sessions)`, from `regime_allocation_2026/data/signals.parquet`. Everything
else — daily table, universe, top-20 rank among LEADING/EXTENDED, per-symbol
month-end row, OHLC/4 T+1 fill with 0.2% slippage, 150-day trail, one
position per name — is unchanged from the first run.

| Cut | n | win | expectancy | vs 757 / 45.0% / +20.71% |
|---|---|---|---|---|
| **T3, entry year ≥ 2014** | **760** | **45.9%** | **+20.64%** | **+3 / +0.9pp / −0.07pp — PASS** |
| T3, trigger year ≥ 2014 | 755 | 45.6% | +20.01% | −2 / +0.6pp / −0.70pp |
| T3, no same-name dedupe | 1,717 | 44.4% | +21.11% | +960 / −0.6pp / +0.40pp |

Tolerance is 5 calls / 1pp / 0.5pp. The entry-year cut clears all three legs,
which is also the convention the reference tape records its dates on. **The
daily build is validated**; §3 and §4 below therefore ran.

Confirming it is the right series: this gate flips **27.1 times a year** with
a 3-session median run, which is exactly the "raw direction switch … flips 26
times a year" PLAN.md rejects for the product. It is on 51.1% of sessions.

| Gate | time on | flips/yr | median run |
|---|---|---|---|
| Composite direction, w=63 (A1 only) | 51.1% | 27.09 | 3 sessions |
| Hysteresis 40/60 (product gate) | 65.0% | 1.53 | 99 sessions |
| C4 k=2, BROAD (Track B) | 67.1% | 1.91 | 78 sessions |

C4 mapping used: **S0 = BROAD**, per `regime_first_2026` RESULTS.md
"Recommended taxonomy" step 5 (higher mean `pct_above_200` over the
2007-10-18 → 2015-12-31 fit window: 0.718 for S0 against 0.275 for S1).

## Per-call, three gates

Supersedes the two-gate table above; the `none` and `hyst` rows are identical
to it. Reference exit throughout. Alpha is per call vs NIFTY 500 over the
same hold. Cadence columns are over the same 249-month span.

| Trigger | Gate | n | win | avg win | avg loss | ratio | expectancy | alpha | median | med hold | calls/mo | zero months |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| T1 state-entry | none | 2,119 | 34.8% | +49.8% | −11.6% | 4.30 | +9.8% | +5.1% | −4.7% | 55 | 8.5 | 2.4% |
| T1 state-entry | hyst 40/60 | 1,134 | 37.9% | +55.0% | −14.4% | 3.81 | +11.9% | +6.9% | −5.9% | 67 | 4.6 | 33.3% |
| T1 state-entry | C4 BROAD | 1,092 | 38.4% | +55.6% | −13.6% | 4.09 | **+13.0%** | +7.9% | −5.2% | 67 | 4.4 | 35.7% |
| T2 rank-entry | none | 3,067 | 37.7% | +55.1% | −13.1% | 4.19 | +12.6% | +7.8% | −4.5% | 72 | 12.3 | **0.0%** |
| T2 rank-entry | hyst 40/60 | 1,982 | 41.1% | +60.4% | −15.9% | 3.80 | **+15.5%** | +10.0% | −5.1% | 85 | 8.0 | 30.9% |
| T2 rank-entry | C4 BROAD | 1,899 | 41.2% | +56.6% | −15.1% | 3.76 | +14.5% | +9.3% | −4.7% | 83 | 7.6 | 33.7% |
| T3 month-end | none | 1,828 | 41.2% | +59.1% | −15.1% | 3.92 | +15.5% | +10.3% | −5.0% | 83 | 7.3 | 1.6% |
| **T3 month-end** | **hyst 40/60** | **1,275** | **42.0%** | **+64.6%** | **−17.4%** | **3.72** | **+17.1%** | **+11.7%** | **−5.8%** | **89** | **5.1** | **36.5%** |
| T3 month-end | C4 BROAD | 1,226 | 42.7% | +60.8% | −16.3% | 3.73 | +16.6% | +11.4% | −5.1% | 86 | 4.9 | 38.2% |

Per era (n / win / expectancy):

| Trigger | Gate | 2006-12 | 2013-19 | 2020-26 |
|---|---|---|---|---|
| T1 | none | 800 / 30.5% / +4.7% | 686 / 35.4% / +8.8% | 633 / 39.7% / +17.2% |
| T1 | hyst | 471 / 32.9% / +5.3% | 297 / 42.1% / +15.1% | 366 / 41.0% / +17.9% |
| T1 | C4 | 306 / 38.9% / +6.0% | 406 / 35.5% / +11.1% | 380 / 41.1% / +20.6% |
| T2 | none | 1,072 / 32.7% / +6.3% | 1,004 / 38.1% / +13.2% | 991 / 42.7% / +18.7% |
| T2 | hyst | 720 / 37.1% / +8.5% | 560 / 44.8% / +19.8% | 702 / 42.3% / +19.3% |
| T2 | C4 | 478 / 40.0% / +4.7% | 708 / 40.8% / +15.7% | 713 / 42.5% / +19.9% |
| T3 | none | 598 / 37.0% / +9.0% | 625 / 38.9% / +13.9% | 605 / 47.9% / +23.6% |
| T3 | hyst | 425 / 41.4% / +11.9% | 365 / 39.5% / +18.6% | 485 / 44.3% / +20.4% |
| T3 | C4 | 292 / 43.8% / +5.9% | 459 / 38.1% / +16.0% | 475 / 46.3% / +23.7% |

**C4 vs hysteresis.** On T3, the winning trigger, hysteresis wins on both
axes the coordinator asked about: expectancy +17.1% vs +16.6%, zero months
36.5% vs 38.2%. Same on T2 (+15.5% vs +14.5%, 30.9% vs 33.7%). C4 leads only
on T1 (+13.0% vs +11.9%). C4's whole advantage sits in 2020-26 (T3 +23.7% vs
+20.4%) and it is markedly worse in 2006-12 (+5.9% vs +11.9%) — the era before
its k-means centroids were fitted is the era it handles worst, which is the
wrong sign for a gate about to be shipped. Hysteresis 40/60 stays the product
gate.

## Exit sweep

On **T3 × hysteresis 40/60** — the best gated expectancy in the table above.
Same 1,275 calls into every cell; only the trail changes. No partials, no
time stops, no hard stop.

| Exit | n | win | avg win | avg loss | ratio | expectancy | alpha | median | med hold |
|---|---|---|---|---|---|---|---|---|---|
| **ma150 (reference)** | 1,275 | 42.0% | +64.6% | −17.4% | 3.72 | **+17.1%** | +11.7% | −5.8% | 89 |
| ma100 | 1,275 | 40.1% | +52.5% | −14.0% | 3.75 | +12.7% | +9.1% | −4.8% | 56 |
| ATR 4× | 1,275 | 40.9% | +35.6% | −12.7% | 2.80 | +7.0% | +5.1% | −4.4% | 34 |
| swing low (±5-bar pivot) | 1,275 | 36.0% | +34.9% | −11.3% | 3.10 | +5.3% | +3.8% | −4.8% | 30 |
| ATR 3× | 1,275 | 38.4% | +23.0% | −9.9% | 2.32 | +2.7% | +1.9% | −3.7% | 20 |
| ATR 2× | 1,275 | 38.7% | +13.8% | −7.4% | 1.86 | +0.8% | +0.7% | −3.0% | 11 |

| Summary | Value |
|---|---|
| Grid median expectancy | **+6.2%** |
| Best cell | ma150, +17.1% |
| Grid mean / sd | +7.6% / 6.2pp |
| Gumbel E[max of 5 draws] | **+14.8%** |
| Gumbel E[max of 6 draws] | +15.5% |

The best cell clears the Gumbel expectation by 2.3pp, so ma150 is not the
grid's luckiest draw — it is a real ranking. The axis that explains the grid
is **hold length**, monotonically: 11 bars → +0.8%, 20 → +2.7%, 30 → +5.3%,
34 → +7.0%, 56 → +12.7%, 89 → +17.1%. Every tighter trail cuts the right tail
(avg win falls from +64.6% to +13.8%) faster than it saves on losses (avg
loss only improves from −17.4% to −7.4%). Consistent with `vcp_relook`: the
exit is the binding constraint, and on this pattern the answer is to hold
longer, not tighter.

Per era, ma150: 2006-12 425 / 41.4% / +11.9% · 2013-19 365 / 39.5% / +18.6% ·
2020-26 485 / 44.3% / +20.4%. ma100 is the only other cell above the grid
median in all three eras.


## Portfolio

T3 × ma150 × 25 slots, equal weight, daily mark-to-market, cash earns
nothing. **Sizing note:** with no hard stop (stop = 1% of entry) `build_book`'s
risk sizing puts only ~1.5% of equity per name and the book never invests, so
`risk_pct` was raised until the 1/25 weight cap binds — this is the
equal-weight book TASKS.md §4 asks for, not a risk-sized one. The control is
the same trigger and exit with the gate off, which is the only clean
always-on comparison.

| Book | Span | calls | taken | CAGR | max DD | Sharpe | vol | exposure | avg open |
|---|---|---|---|---|---|---|---|---|---|
| T3 gated (hyst 40/60) | 2006-2026 | 1,275 | 718 | 15.2% | −44.6% | 0.52 | 19.6% | 66.8% | 15.0 |
| **T3 always-on** | 2006-2026 | 1,828 | 1,037 | **19.6%** | −54.1% | **0.70** | 21.0% | 87.2% | 20.2 |
| NIFTY 500 | 2006-2026 | — | — | 11.4% | −64.3% | 0.32 | 20.3% | — | — |
| T3 gated (hyst 40/60) | 2016-2026 OOS | 703 | 428 | 9.1% | −42.2% | 0.21 | 19.8% | 69.2% | 15.9 |
| **T3 always-on** | 2016-2026 OOS | 1,001 | 593 | **18.6%** | −48.7% | **0.64** | 21.3% | 90.2% | 21.2 |
| NIFTY 500 | 2016-2026 OOS | — | — | 12.1% | −38.3% | 0.44 | 16.1% | — | — |

Era Sharpe: gated 0.66 / 0.16 / 0.73 (2006-12 / 2013-19 / 2020-26), always-on
0.39 / 0.40 / 1.30.

**The gate reverses sign between the call and the book.** It adds 1.6pp of
per-call expectancy and subtracts 4.4pp of CAGR and 0.18 of Sharpe over the
full span; OOS it subtracts 9.5pp and 0.43. Two mechanisms, both visible in
the table: exposure falls from 87% to 67% and average open positions from
20.2 to 15.0, so two-thirds of the deficit is simply being out of the market;
and the drawdown it buys back is small (−54.1% → −44.6% full, −48.7% → −42.2%
OOS) because the gate blocks *entries* without forcing *exits*, so the book
still rides its open positions down. A gate that is going to earn its
exposure cost on this tape has to liquidate, not just stop buying —
`build_book` already takes a `force_exit` series for exactly that test.

Both books beat NIFTY 500 on CAGR over the full span; only always-on beats it
OOS, and neither beats it on drawdown over the full span.

## Blocked

- Nothing outstanding. Gate A1 failed on the BRIEF's stated gate (hysteresis
  40/60) and passed on the corrected one (composite direction, w=63) at
  760 / 45.9% / +20.64%, so §3 and §4 ran.
- `exits.py` gained two additive trail branches for §3 — `trail="ma100"` and
  `trail="swing"` — plus `s100` and a confirmed ±5-bar `piv_lo` array in
  `load_panel`. Absent those `trail` values nothing changes; the ma150 and
  chandelier paths are byte-identical and the §3 ma150 column reproduces the
  §2 T3-hysteresis row exactly.

## Follow-ups

1. **The gate needs a `force_exit` arm before it ships.** Blocking entries
   alone costs 4.4pp CAGR full-span and 9.5pp OOS and buys back under 10pp of
   drawdown. The pre-registered test is one line: pass the hysteresis series
   as `build_book(force_exit=~gate)` and re-run the same two spans. If
   liquidating does not close the gap, the persistent gate is a per-call
   statistic with no book-level use and should be dropped from the product.
2. **Resolve the BRIEF's gate error upstream.** `trend_screen_2026` §7 was
   computed on the composite direction rule — 27 flips a year, 3-session
   median run — which PLAN.md explicitly rejects as unfollowable. Every
   published number resting on §7 inherits that gate, not the hysteresis one.
3. The real trigger question is not T1 vs T3 but whether T1's 12.6-day timing
   edge can be kept while its 48% junk tail is removed. One-parameter family,
   both endpoints already measured: T1 plus an N-session persistence
   requirement, N ∈ {5, 10, 21}; N = 0 is T1 (+11.9%), N = 21 collapses to T3
   (+17.1%).
4. The exit sweep says hold longer, not tighter, and ma150 is the loosest
   trail tested. ma200 and "close below the 150-day for two consecutive
   sessions" are the two cells that would tell us whether +17.1% is a
   plateau or still climbing.
5. T2 un-gated is the only definition with no empty months (12.3 calls/month,
   +12.6% expectancy, +7.8% alpha). If delivery cadence is a product
   constraint it is the trigger to price, not T1.
6. C4 BROAD is worth one more look on T1 only, where it beats hysteresis by
   1.1pp — but its 2006-12 weakness (+5.9% vs +11.9% on T3) in the era
   preceding its fit window should be understood before it is used anywhere.
