# Results — regime_allocation_2026

**Verdict:** No rule passed G1-G7 — `composite / D2_two_bucket` (direction of a
composite breadth rank, rising→1, falling→0) clears G1-G6 on the walk-forward
(1.02 Sharpe, 21.8% CAGR, −22.0% DD) but fails G7: its selection edge of 0.27
sits well inside the 0.40 that the maximum of 69 equal noise draws would
produce, and the one cell that does clear G7 (`pct_above_200 / 63 / D2`, edge
0.399 vs threshold 0.396, i.e. by 0.003) fails G1, G2, G3 and G4. Across the
whole grid the IS→OOS rank correlation of the 69 candidates is **−0.002** — the
in-sample decade carries no information about which regime rule works out of
sample — so breadth phase is recorded as a research observation, not a
tradeable overlay.

## Gate table

G1 WF Sharpe − always-on ≥ +0.15 · G2 WF Sharpe − own exposure control ≥ +0.15 ·
G3 |WF − static OOS| ≤ 0.15 · G4 WF maxDD ≤ 35% · G5 params ≤ 4 ·
G6 beats always-on in both alternate splits · G7 best cell > Gumbel E[max] of
the 69 trials (0.396 on the selection metric).

| candidate | G1 | G2 | G3 | G4 | G5 | G6 | G7 | pass |
|---|---|---|---|---|---|---|---|---|
| always on (control) | — | — | — | 43.1% | 0 | — | — | reference |
| composite / D2_two_bucket | **+0.30** ✓ | **+0.31** ✓ | **0.05** ✓ | **22.0%** ✓ | **2** ✓ | **both** ✓ | 0.27 vs 0.396 ✗ | **no** |
| pct_above_200 / D2_two_bucket | +0.08 ✗ | +0.09 ✗ | 0.29 ✗ | 37.9% ✗ | 2 ✓ | both ✓ | 0.399 vs 0.396 ✓ | no |
| pct_above_200 / D1_four_bucket (§8's rule) | −0.10 ✗ | −0.12 ✗ | 0.29 ✗ | 39.1% ✗ | 4 ✓ | both ✓ | 0.19 vs 0.396 ✗ | no |
| pct_above_50 / D2_two_bucket | −0.21 ✗ | −0.16 ✗ | 0.30 ✗ | 39.8% ✗ | 2 ✓ | both ✓ | 0.15 vs 0.396 ✗ | no |
| pct_above_200 / D3_continuous | −0.30 ✗ | −0.28 ✗ | 0.41 ✗ | 34.8% ✓ | 4 ✓ | both ✓ | 0.13 vs 0.396 ✗ | no |

Flagged impractical (>12 allocation changes a year) on the walk-forward:
composite/D2 at **31.4**, pct_above_50/D2 at 16.3, pct_above_200/D1 at 13.6,
pct_above_200/D3 at 97.5. Only pct_above_200/D2 (10.1) is inside the flag.

G7 is a coin flip and is reported both ways. On the selection metric (OOS
Sharpe minus own control) the grid's best cell clears the threshold by 0.003;
on raw OOS Sharpe it misses by 0.002 (best 1.086, threshold 1.088). Either
reading says the same thing: the best cell of this search is statistically
indistinguishable from the best of 69 noise draws.

## §1 smoke test

reproduced: **yes** — founder's rule (`pct_above_200`, 63, full-span median,
{EXPANSION 1, RECOVERY 1, TOPPING 0.5, CONTRACTION 0}), OOS 2016-2026:

| scheme | CAGR | maxDD | Sharpe | reference | max deviation |
|---|---|---|---|---|---|
| founder's rule | 21.6% | 36.7% | 0.92 | 21.6 / 36.7 / 0.92 | 0.01pp / 0.01pp / 0.002 |
| always on | 19.1% | 41.0% | 0.66 | 19.1 / 41.0 / 0.66 | 0.01pp / 0.04pp / 0.003 |
| half everywhere | 13.5% | 26.4% | 0.64 | 13.5 / 26.4 / 0.64 | 0.02pp / 0.03pp / 0.005 |

Two incidental checks the rest of the task depends on:

- `order="tight"` makes `build_book` **fully deterministic** — the rng is only
  consumed by `order="random"`, so three seeds return three byte-identical
  books (verified at seeds 0, 1, 7). The "3 seeds" of §1 is satisfied by
  construction; one seed is run everywhere else.
- `regime_series()`/`phase_labels()` reproduce the tape's own `phase` column on
  **100.0%** of OOS entries, so the grid's D1 shape is the same object §8 used.
- A4 `pct_above_50` was rebuilt from `adjusted_pr` panels on the same
  point-in-time universe (top 500 by trailing ADV inside the scaled-floor
  eligible set). Validation: `pct_above_200` recomputed by the same code
  matches `breadth.parquet` **exactly** (max |diff| 0.0e0 over all 5,349
  sessions), so A4 and A1 are measured on identical membership.
- `book_x` (the instrumented book used for §4's E2/E3 and §5's fills) in
  `mode="entry"` reproduces `build_book` to <1e-9 on CAGR and Sharpe.

## §2 grid (IS/OOS)

trials: **69** (60 = 5 signals × 4 windows × 3 shapes, plus 9 = top-3 × D4
hysteresis N∈{5,10,21}) · grid median OOS Sharpe: **0.67** (sd 0.173) ·
best: **1.09** (`pct_above_200 / 63 / D2_two_bucket`) · Gumbel E[max]: **1.09**
on raw Sharpe, **0.396** on the selection metric (best 0.399)
candidates beating always-on OOS: **35 of 69**; beating their own
exposure-matched control: **30 of 69**

Always-on reference: IS 24.7% / 47.4% / **0.95**; OOS 19.1% / 41.0% / **0.66**.

The family result, which is the finding: the grid median OOS Sharpe (0.67) is
the always-on Sharpe (0.66). Half the grid beats always-on, half does not, and
the median edge over the exposure-matched control is **−0.02**. The
**IS→OOS rank correlation across the 69 candidates is −0.002** (−0.001 on raw
Sharpe): knowing which regime rule won 2006-2015 tells you nothing about which
wins 2016-2026.

Top 10 by OOS edge (OOS Sharpe − own control). `ctl` = exposure-matched control.

| signal | win | shape | hyst | IS Sh | IS ctl | OOS CAGR | OOS DD | OOS Sh | OOS ctl | edge | mean w | chg/yr |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| always on | — | — | — | 0.95 | — | 19.1% | 41.0% | 0.66 | — | — | 1.00 | 0 |
| pct_above_200 | 63 | D2 | 0 | 1.03 | 0.84 | 24.3% | 37.1% | 1.09 | 0.69 | **0.399** | 0.62 | 8.4 |
| pct_above_200 | 42 | D2 | 0 | 0.66 | 0.82 | 23.6% | 34.4% | 1.05 | 0.67 | 0.372 | 0.59 | 12.1 |
| pct_above_200 | 42 | D2 | 5 | 0.93 | 0.83 | 23.9% | 35.5% | 1.02 | 0.69 | 0.334 | 0.62 | 4.7 |
| composite | 63 | D2 | 0 | 0.91 | 0.87 | 22.8% | 35.1% | 0.96 | 0.70 | 0.266 | 0.66 | 24.5 |
| composite | 63 | D2 | 5 | 1.14 | 0.83 | 22.2% | 35.1% | 0.94 | 0.69 | 0.243 | 0.64 | 4.1 |
| pct_above_200 | 42 | D1 | 0 | 1.05 | 0.88 | 21.6% | 36.3% | 0.91 | 0.71 | 0.192 | 0.72 | 15.1 |
| pct_above_200 | 63 | D1 | 0 | 1.19 | 0.88 | 21.4% | 37.4% | 0.90 | 0.72 | 0.188 | 0.73 | 11.2 |
| pct_above_200 | 21 | D2 | 0 | 0.64 | 0.82 | 20.4% | 32.3% | 0.85 | 0.69 | 0.161 | 0.62 | 18.2 |
| pct_above_50 | 63 | D2 | 0 | 0.89 | 0.84 | 19.5% | 34.5% | 0.81 | 0.66 | 0.148 | 0.56 | 15.5 |
| pct_above_200 | 63 | D3 | 0 | 1.00 | 0.84 | 18.2% | 32.4% | 0.82 | 0.69 | 0.135 | 0.63 | 136.3 |

Median OOS edge by axis — the grid is null on every axis except
`pct_above_200`, and only barely there:

| axis | value | median edge | best |
|---|---|---|---|
| shape | D1 four-bucket | −0.060 | 0.192 |
| shape | D2 two-bucket | **+0.007** | 0.399 |
| shape | D3 continuous | −0.076 | 0.135 |
| signal | pct_above_200 | **+0.083** | 0.399 |
| signal | composite | −0.069 | 0.266 |
| signal | net_highs | −0.045 | 0.104 |
| signal | pct_leading | −0.047 | 0.093 |
| signal | pct_above_50 | −0.077 | 0.148 |
| window | 21 | −0.057 | 0.161 |
| window | 42 | −0.059 | 0.372 |
| window | 63 | **+0.054** | 0.399 |
| window | 126 | −0.091 | 0.093 |

Convention note: for the grid, every fitted constant (the D1 level cut, the D3
lo/hi quantiles, fixed at the 20th/80th percentile of the change distribution)
is taken from the IS window only, so the OOS column carries no look-ahead. §8's
own convention was the full-span median, which is why the founder cell reads
0.90 here and 0.92 in §1. D1's TOPPING weight is fixed at 0.5 throughout.

## §3 walk-forward

Trailing 8-year fit, applied one year forward, chained 2014-2026. Two §2
candidates sharing a (signal, shape) family walk identically, so families were
de-duplicated and the slate filled to five from the next-best families. Each
year the fit chooses the direction window from {21, 42, 63, 126} (and for D3
the lo/hi quantile pair from four), and recomputes the level cut / quantile
levels on the fit window. Always-on and the exposure control are chained the
same way.

| candidate | WF CAGR | WF maxDD | WF Sharpe | WF ctl Sharpe | static OOS Sharpe | distinct cells (of 13 yrs) | chg/yr | cash | G1 | G2 | G3 | G4 | G5 | G6 | G7 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| always on (control) | 20.6% | 43.1% | 0.71 | — | — | 1 | 0 | 0% | — | — | — | ✗ | ✓ | — | — |
| composite / D2 | 21.8% | 22.0% | **1.02** | 0.71 | 0.96 | 4 | 31.4 | 49% | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✗ |
| pct_above_200 / D2 | 19.3% | 37.9% | 0.80 | 0.71 | 1.09 | 3 | 10.1 | 52% | ✗ | ✗ | ✗ | ✗ | ✓ | ✓ | ✓ |
| pct_above_200 / D1 | 16.0% | 39.1% | 0.61 | 0.73 | 0.91 | 3 | 13.6 | 29% | ✗ | ✗ | ✗ | ✗ | ✓ | ✓ | ✗ |
| pct_above_50 / D2 | 14.4% | 39.8% | 0.51 | 0.67 | 0.81 | 2 | 16.3 | 53% | ✗ | ✗ | ✗ | ✗ | ✓ | ✓ | ✗ |
| pct_above_200 / D3 | 10.8% | 34.8% | 0.42 | 0.70 | 0.82 | 8 | 97.5 | 33% | ✗ | ✗ | ✗ | ✓ | ✓ | ✓ | ✗ |

Three of the five walk forward **below their own exposure-matched control**, and
four of the five lose 0.29-0.41 of Sharpe relative to their static-OOS number —
which is G3 doing exactly the job it was written for: the static figure was a
hindsight figure. §8's own rule (`pct_above_200 / D1`) walks forward at 0.61
against always-on's 0.71, i.e. **the founder's rule, refit honestly each year,
is worse than doing nothing**.

Per-year picks, `composite / D2` (the closest miss). "cell" is the direction
window the trailing 8-year fit chose; `mean w` is the average allocation the
rule actually ran that year.

| year | cell | fit Sharpe | year return | always-on year return | taken | exposure | mean w |
|---|---|---|---|---|---|---|---|
| 2014 | 21 | 0.85 | +73.0% | +85.4% | 44 | 95% | 0.82 |
| 2015 | 126 | 1.11 | +4.6% | +16.1% | 25 | 13% | 0.07 |
| 2016 | 63 | 0.88 | +0.8% | −13.8% | 58 | 72% | 0.82 |
| 2017 | 42 | 0.84 | +58.3% | +63.2% | 42 | 87% | 0.82 |
| 2018 | 42 | 0.99 | −12.3% | −27.2% | 41 | 21% | 0.18 |
| 2019 | 42 | 0.85 | +13.4% | +2.0% | 70 | 78% | 0.76 |
| 2020 | 42 | 0.97 | +38.5% | +55.9% | 32 | 52% | 0.58 |
| 2021 | 21 | 0.76 | +45.2% | +47.6% | 38 | 81% | 0.52 |
| 2022 | 63 | 1.04 | +7.3% | −4.2% | 37 | 40% | 0.43 |
| 2023 | 21 | 0.66 | +57.6% | +71.5% | 42 | 71% | 0.78 |
| 2024 | 63 | 1.08 | +4.2% | +12.1% | 49 | 74% | 0.61 |
| 2025 | 63 | 1.08 | +2.6% | −15.2% | 53 | 51% | 0.62 |
| 2026 | 42 | 0.60 | +17.3% | +33.8% | 50 | 72% | 0.64 |

The chosen cell changes in **8 of 12 year-to-year transitions** and visits 4 of
the 4 available windows — this rule is unstable in its own only parameter. The
pattern of returns is one-sided by construction: it gives up 5-16pp in every up
year and saves 10-18pp in 2016, 2018, 2022 and 2025. It is a de-risking rule
that happens to be timed well on this decade, and G7 says that timing is inside
the range of luck for a 69-cell search. 2015 is the extreme case: the trailing
fit chose a 126-session window and the book sat **87% in cash for a full year**
that always-on made +16% in.

Caveat on the chaining, which the BRIEF prescribes and which applies equally to
every row: yearly segments are chained from mark-to-market year-end equity, so
each year's book starts flat and no position is carried across 1 January. That
truncates cross-year holds and depresses January exposure for rule and control
alike.

## §4 robustness

**Alternate splits** — every fitted constant refit on the alternate IS window;
the direction window is the one §2 chose on the primary split, which
contaminates this check and is why G6 is the weakest of the seven gates.

| candidate | primary OOS 2016- | alt 2013- | alt 2019- | always-on (primary / 2013 / 2019) | sign holds |
|---|---|---|---|---|---|
| pct_above_200 / D2 | 1.09 | 1.15 | 1.41 | 0.66 / 0.67 / 0.95 | both ✓ |
| composite / D2 | 0.96 | 0.98 | 1.17 | 0.66 / 0.67 / 0.95 | both ✓ |
| pct_above_200 / D1 | 0.91 | 0.98 | 1.22 | 0.66 / 0.67 / 0.95 | both ✓ |
| pct_above_50 / D2 | 0.81 | 1.01 | 1.11 | 0.66 / 0.67 / 0.95 | both ✓ |
| pct_above_200 / D3 | 0.82 | 0.96 | 1.10 | 0.66 / 0.67 / 0.95 | both ✓ |

All five pass G6. They also all beat their own exposure control on all three
splits. This is the one place the regime idea looks robust, and it should be
discounted accordingly: the three splits share 2019-2026, all of them are
static rather than walked, and the windows were picked on the primary split.

**Where the rule acts** (`composite / 63 / D2`, primary OOS, 25 slots):

| where | CAGR | maxDD | Sharpe | taken | exposure |
|---|---|---|---|---|---|
| E1 entry sizing only | 22.8% | 35.1% | **0.96** | 424 | 72% |
| E2 entry + forced exit at zero weight | 9.7% | 26.1% | 0.41 | 1,086 | 32% |
| E3 entry + rebalance open positions down | 9.7% | 26.1% | 0.41 | 1,086 | 32% |

E2 and E3 are identical here because a two-bucket rule's only downward move is
to zero, so "scale down to the new weight" *is* liquidation. Acting on open
positions **destroys the result** — it more than halves CAGR for a 9pp
drawdown saving and triples the number of entries (liquidation frees slots
which are then refilled). Whatever the regime layer is doing, it is not
"get out of the market".

**Slot count** (`composite / 63 / D2`, primary OOS):

| slots | rule CAGR | rule maxDD | rule Sharpe | ctl Sharpe | always-on CAGR | always-on maxDD | always-on Sharpe |
|---|---|---|---|---|---|---|---|
| 15 | 21.9% | 40.0% | 0.83 | 0.53 | 15.1% | 51.4% | 0.44 |
| 25 | 22.8% | 35.1% | 0.96 | 0.70 | 19.1% | 41.0% | 0.66 |
| 35 | 22.8% | 33.4% | 1.03 | 0.71 | 19.3% | 35.9% | 0.71 |

The rule's edge over always-on is +0.39 / +0.31 / +0.32 and over its own
exposure control +0.29 / +0.27 / +0.32 — flat to slightly declining in slot
count, largest at 15 slots where always-on itself is worst (0.44 Sharpe,
−51.4% drawdown). Not slot-fragile. But note what the 35-slot row says: simply
running 35 slots always-on scores 0.71, i.e. the same Sharpe the walk-forward
gives always-on and more than three of the five walked candidates managed —
diversification is a cheaper, zero-parameter route to most of what the regime
layer is being credited with.

**Cross-signal** — the same rule on the breakout tape
(`breakout_calls_2026/data/book_trades.csv`), primary OOS, same harness:

| tape | rule CAGR | rule maxDD | rule Sharpe | ctl Sharpe | always-on Sharpe | edge vs always-on |
|---|---|---|---|---|---|---|
| trend screen | 22.8% | 35.1% | 0.96 | 0.70 | 0.66 | **+0.30** |
| breakout | 11.4% | 17.9% | 0.54 | 0.41 | 0.50 | **+0.04** |

This is the most damaging number in §4. A market-wide breadth regime should
help any long-only momentum tape; on the breakout tape the same rule is worth
+0.04 of Sharpe, a quarter of the +0.15 bar and a seventh of what it is worth
on the tape it was searched on. It does beat its own exposure control there
(+0.13), so some de-risking value survives, but the *timing* value is specific
to the trend tape — which is what "fit to that signal" looks like.

## §5 cost

`composite / 63 / D2` vs always-on, primary OOS 2016-2026, measured from the
book's own fills rather than estimated.

| | rule | always on |
|---|---|---|
| CAGR / maxDD / Sharpe | 22.8% / 35.1% / 0.96 | 19.1% / 41.0% / 0.66 |
| time in cash (weight = 0) | **46.5%** of sessions | 0% |
| mean allocation weight | 0.66 | 1.00 |
| average exposure | 72% | 90% |
| allocation changes per year | **24.5** (flag: >12) | 0 |
| entries taken | 424 | 620 |
| turnover (entry notional / mean equity / yr) | 1.37× | 2.02× |
| median hold (days) | 121 | 105 |
| share of realised legs taxed as STCG | 92.7% | 95.0% |
| tax paid (Rs, on Rs 1cr start) | 1.52cr | 1.11cr |
| CAGR after tax | **19.5%** | 16.4% |
| tax drag | **3.33pp** | 2.71pp |

The rule trades *less*, not more — turnover falls a third because skipped
entries are entries not made — but it pays 37% more tax in rupees, because it
compounds faster, and its tax drag is 0.6pp worse. Holds lengthen slightly
(121 vs 105 days) rather than shortening: the rule suppresses entries, it does
not cut exits (E1 is entry-only). After tax the rule is still ahead, 19.5% vs
16.4%.

The churn is the practical problem. 24.5 allocation changes a year means the
signal crosses zero about every two weeks, and **222 of those flips reversed
inside 21 sessions** over 10.7 years (20.7 a year). Of the 222 round trips,
138 gave up return and 84 dodged a fall; summed they net to **−75%** of one
unit of book return, with the harmful ones summing to −243%.

Ten worst whipsaws (cost = (interim weight − prior weight) × always-on return
over the round trip; negative = the flip gave up return):

| flip | back | sessions | w from → to | always-on return | cost |
|---|---|---|---|---|---|
| 2024-06-04 | 2024-06-12 | 6 | 1.0 → 0.0 | +12.8% | −12.8% |
| 2024-06-03 | 2024-06-04 | 1 | 0.0 → 1.0 | −10.7% | −10.7% |
| 2022-02-28 | 2022-03-22 | 14 | 1.0 → 0.0 | +8.2% | −8.2% |
| 2023-11-01 | 2023-11-20 | 13 | 1.0 → 0.0 | +7.8% | −7.8% |
| 2016-09-29 | 2016-10-03 | 2 | 1.0 → 0.0 | +7.7% | −7.7% |
| 2016-02-09 | 2016-02-12 | 3 | 0.0 → 1.0 | −7.2% | −7.2% |
| 2018-09-19 | 2018-09-24 | 2 | 0.0 → 1.0 | −5.7% | −5.7% |
| 2023-10-10 | 2023-11-01 | 15 | 0.0 → 1.0 | −5.4% | −5.4% |
| 2017-11-09 | 2017-11-15 | 4 | 0.0 → 1.0 | −4.4% | −4.4% |
| 2025-12-30 | 2026-01-08 | 7 | 0.0 → 1.0 | −4.4% | −4.4% |

The June 2024 pair is the signature failure: the rule went flat for one session
on 3 June into a −10.7% day, came back on 4 June, then went flat again for six
sessions through a +12.8% rebound. Two adjacent whipsaws, −23.5% of one unit of
exposure, inside eight sessions.

Hysteresis is the obvious fix and §2 tested it: `composite / 63 / D2` with a
5-session persistence requirement cuts changes from 24.5 to **4.1** a year for
0.03 of OOS Sharpe (0.96 → 0.94). It costs a fifth parameter, so under G5 the
five-parameter version is out of budget for a D1-shaped rule but fine for
D2 (2 + 1 = 3). It was not walked forward — only the top-3 families were
hysteresis-tested, and only statically.

## Blocked

Nothing failed. Two departures from the literal instruction, both recorded here
rather than silently:

1. **Seeds.** §1 asks for 3 seeds. `order="tight"` makes `build_book`
   deterministic (the rng is only consumed on `order="random"`), verified at
   seeds 0/1/7 to <1e-12 on Sharpe, so the median over 3 seeds is the single
   seed and only one is run. No result depends on this.
2. **A4's build.** `breadth.py` is outside this task folder, so
   `symbol_flags`/`build` were reproduced in
   `tasks/regime_allocation_2026/lib/build_pct50.py` with the `c > s50` flag
   added rather than edited in place. The reproduction is exact: recomputed
   `pct_above_200` matches `breadth.parquet` to 0.0e0 on all 5,349 sessions.

The one file touched outside this folder is
`tasks/breakout_calls_2026/lib/book.py`, which gained the additive
`force_exit: pd.Series | None = None` parameter described in TASKS §1. Absent
(the default) the book is byte-identical to before — the §1 smoke test
reproduces §8's numbers through the modified file.

## Follow-ups

Do not run these; they are what the results asked for and were refused.

- **Hysteresis, walked forward.** The single highest-value unrun experiment:
  `composite / 63 / D2` with N = 5 keeps 0.94 of 0.96 static OOS Sharpe at
  4.1 allocation changes a year instead of 24.5. §2 only tested hysteresis
  statically on the top 3. If a regime layer is ever revisited, the
  specification to walk forward is the *hysteretic* one, and the question to
  pre-commit is whether N counts as the third parameter or is fixed a priori
  at one month.
- **A regime signal that is not breadth.** Every signal here is a breadth
  count, and the grid's null result is a statement about breadth counts
  specifically. Index-level trend, realised-volatility regime, and the cross
  sectional dispersion of the screen's own ranks are all outside PLAN §A and
  would be new signals.
- **The exit, not the entry.** §4's E2/E3 result — acting on open positions
  halves CAGR — says the 150-day trail already does the regime layer's work on
  the way out, and that the only place a regime rule can add is entry
  suppression. That points at the exit ladder as the live constraint, which is
  `trend_screen_2026` §7's territory, not a regime task.
- **Why 2015 was catastrophic for the walked rule.** The trailing fit chose a
  126-session window and sat 87% in cash through a +16% year. A fit criterion
  that penalises time-in-cash (or a cap on the minimum annual mean weight)
  would have prevented it, but that is a fifth parameter and a new fit
  objective.
- **Cross-signal, properly.** The breakout-tape check was a single static run
  of one cell. If the regime idea is revived, the honest version is to run the
  whole §2 grid on both tapes and require a candidate to clear the gates on
  both — a rule that needs its own tape is not a market regime.
