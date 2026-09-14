# universe_foresight — results

**Question:** could a universe built in real time have held the names that
turned out to be the survivors, and so recovered any of the CAGR the honest
point-in-time membership took away?

**Answer (final, after 13 phases): no. Nothing was adopted; MECHANICS is
unchanged.** Every construction that beat the shipped book on a backtest either
reversed once the price panel was made honest, or failed the window it was not
fitted to. The recurring cause is one error in different clothes — a statistic
computed over survivors, read as if it described the population.

> **Reading order.** This file was written phase by phase and later phases
> overturn earlier ones. Two sections below were corrected rather than deleted so
> the reasoning survives: **Phase 3's addendum** (the pool "works") is reversed by
> **Phase 4**, and **Phase 11's** production claim is corrected by **Phase 11b**.
> Both carry an inline pointer. There is no Phase 6 — it was planned, superseded
> before it ran, and the numbering was left alone.
>
> | phase | question | verdict |
> |---|---|---|
> | 1-2 | decompose the survivorship gap | survivorship ≈ 0; the gap was early access |
> | 3 | a wide investability pool | looked like +8.6pp — **reversed by Phase 4** |
> | 4 | same, on an honest 2519-symbol panel | the +8.6pp *was* the coverage hole |
> | 5 / 5b | NSE 500 PIT as the product universe | edge is stale; today's NSE 500 is fully liquid |
> | 7 | "once in NSE 500, always eligible" | best candidate: +5.5pp at equal drawdown |
> | 8 | why it fades, why MM cannot use it | sleeve rots; MM takes the vol without the return |
> | 9 | refit, recent window held out | **inverts** — shipped wins; the control proves the method overfits |
> | 10 | 12-month demotion window | worst hold-out of all, despite the best fit window |
> | 11 / 11b | is the hold-out cap-regime confounded? | partly yes — **11b corrects 11's production claim** |
> | 12 | does the book self-rotate into large caps? | no — ~29% large in every year, both regimes |
> | 13 / 13b | capped sleeve for dropped names | rejected; the premise is a conditioning error |
> | 13c | then why did the ex-member books look good? | the filter is real; the edge is 10 trades |

**The one number to carry out of this folder:** unconditionally, a name dropped
from the Nifty 250 underperforms the index by **28pp over three years** and only
**33%** ever return (Phase 13). Every ex-member construction here was buying from
that cohort.

## Baselines reproduce

| Book | Config | OOS 2016→ honest store | MECHANICS.md |
|---|---|---|---|
| MM | `mm_rebuild/MECHANICS.md` | 25.2% / 1.15 / −27% | 25.2% / 1.15 / −27% |
| OM25 v4 | `mm_rebuild/MECHANICS.md` | 24.9% / 1.21 / −29% | 24.9% / 1.21 / −29% |
| L6 v2 | legacy rules, honest store | 17.4% / 0.56 / −47% | — |

L6 on 2020→ comes out 27.6% against `market_data_spine` Phase 6's 27.8%, so the
ladder sits on the same basis as the re-baseline.

## The ladder — OOS 2016→, CAGR / Sharpe / MaxDD

| Rung | MM | OM25 v4 | L6 v2 |
|---|---|---|---|
| `b0` honest point-in-time | 25.2% / 1.15 / −27% | 24.9% / 1.21 / −29% | 17.4% / 0.56 / −47% |
| `b1` + immortality | 22.5% / 1.01 / −27% | 21.1% / 1.00 / −26% | 17.6% / 0.58 / −45% |
| `b1f` + blow-up avoidance only | 24.0% / 1.10 / −27% | 23.5% / 1.11 / −29% | 17.6% / 0.57 / −46% |
| `b2` + early access | 27.1% / 1.18 / −31% | 26.8% / 1.30 / −30% | 39.6% / 1.42 / −51% |
| `b3` backdated list (the bug) | 29.2% / 1.38 / −28% | 30.9% / 1.57 / −30% | 32.2% / 1.20 / −37% |
| `b4` PIT turnover, no foresight | 27.7% / 1.12 / −34% | 28.6% / 1.27 / −39% | 31.3% / 1.06 / −53% |

**Attribution of the OOS CAGR gap (pp):**

| Component | MM | OM25 v4 | L6 v2 |
|---|---|---|---|
| survivorship (`b0→b1`) | **−2.6** | **−3.8** | **+0.2** |
|   of which blow-ups only (`b0→b1f`) | −1.2 | −1.4 | +0.1 |
| early access (`b1→b2`) | +4.6 | +5.7 | **+22.0** |
| list narrowing (`b2→b3`) | +2.1 | +4.1 | −7.4 |
| **total hindsight (`b0→b3`)** | **+4.0** | **+6.0** | **+14.7** |
| recoverable without foresight (`b0→b4`) | +2.5 | +3.7 | +13.9 |
| irreducible foresight (`b4→b2`) | −0.5 | −1.8 | +8.2 |

On the 2020→ window the same shape holds and the reconciliation closes: L6
`b0→b3` is +16.8pp of the −22.7pp the re-baseline attributed to universe, the
rest being the production price panel rather than the membership file.

## Four findings

**1. Survivorship bias was worth nothing. It is slightly negative.**
Removing every name whose feed dies *costs* MM 2.6pp and OM25 3.8pp of OOS CAGR.
The reason is in the death census: of the 96 Nifty 250 ever-members that
disappear, only 38 die after a >60% drawdown — the other 58 die within reach of
their own peak, because they were acquired. A momentum book holding an
acquisition target collects the takeover premium. Never having held the dead is
a penalty, not a gift. Perfect blow-up avoidance (`b1f`) is also negative
(−1.2 / −1.4pp): dodging the 38 real failures does not pay for missing the 58
buyouts. **A governance or accounting negative screen has no measurable prize
here** — which retires the most intuitive version of the idea.

**2. The entire inflation was early access, not survival.**
Letting a book own eventual index members from their first priced session is
worth +4.6 / +5.7 / **+22.0**pp. For L6 on NSE 500 that single rung is larger
than the whole published gap. The old universe file was not protecting the book
from losers; it was handing it tomorrow's index constituents while they were
still small.

**3. Almost all of that is available in real time, because it is reach, not
foreknowledge.** `b4` — monthly top-N by trailing turnover, no index reference,
nothing but data available on the ranking date — recovers +2.5 / +3.7 / +13.9pp
of the +4.0 / +6.0 / +14.7pp. For MM and OM25 the residual foresight is
*negative*: the honest wide universe beats the one that knew the answer. The
useful fact behind this is that NSE adds a stock only after it has already
re-rated, so index membership is a lagging momentum signal and tracking it costs
the book the part of the move that pays.

**4. But the universe rule earns none of it — random does better.**
Twenty draws of a random N-name monthly universe, same breadth, drawn from names
clearing a Rs 1 cr median-turnover floor:

| Book | `b0` | `b4` | placebo mean (sd) | `b4` percentile | MaxDD `b0` → `b4` → placebo |
|---|---|---|---|---|---|
| MM | 25.2% | 27.7% | 30.0% (2.6) | **10th** | −27% → −34% → −33% |
| OM25 v4 | 24.9% | 28.6% | 31.9% (3.0) | **15th** | −29% → −39% → −29% |
| L6 v2 | 17.4% | 31.3% | 36.2% (1.4) | **0th** | −47% → −53% → −53% |

A random universe captures +4.9 / +7.0 / +18.8pp where the turnover rule captures
+2.5 / +3.7 / +13.9pp. Ranking by turnover is *worse than drawing names out of a
hat*, and for a legible reason: it sorts toward the largest and most-traded
names, rebuilding a large-cap universe, which is where momentum pays least. The
breadth is doing the work. The rule is a drag on it.

## What this means for the question as asked

There is no way to draw a list in 2021 that contains the 2026 survivors, and
this says you do not need one. The books already select survivors continuously —
that is what a momentum rank is — and the only thing the backdated file gave
them was permission to look further down the cap scale. That permission is
free and needs no forecast. What it is not is free of risk: every route to it
costs drawdown, −27% → −33/−39% for the Nifty 250 books and −47% → −53% for L6,
against a forward gate of −40% in MECHANICS.md. The choice is a risk-budget
choice, not a research finding, which is why it goes to the founder rather than
being resolved here.

## Limitations

- `b4` and the placebo rank inside the price panel, which holds ever-members of
  the four NSE indices, so names that never made any index cannot be picked and
  both are optimistic. Measured (`lib/coverage.py`): 1% of the universe missing
  at top-250 from 2016 (3% over the full span), 6% at top-500 (10% over the
  span). Negligible for the MM / OM25 conclusions; it caps confidence in the L6
  magnitude, not its direction.
- Delisted positions exit at last traded price with no haircut (D-9), so finding
  1 understates the cost of blow-ups. Correcting it would make survivorship look
  *more* negative, not less.
- Price return throughout (D-12).
- The placebo pool averages ~600 names from 2016, so at top-500 breadth a random
  draw is most of the pool and the L6 placebo is closer to "L6 on everything
  investable" than to a true random control. The MM and OM25 placebos at
  top-250 are properly randomised.
- No fundamental or governance screen was tested. Everything here is computable
  from price and volume, which is the same information the ranking already uses;
  a screen on orthogonal data is the one version of the idea this folder does
  not rule out.

## Open calls for the founder

1. **Does any book widen?** The honest gain is real and sizeable (MM +2.5 to
   +4.9pp, L6 +13.9 to +18.8pp) but is bought entirely with drawdown, and OM25's
   `b4` −39% sits at the forward gate. Widening is a decision to spend risk
   budget, not a free improvement.
2. **If a book widens, on what rule?** The evidence says not turnover ranking.
   The defensible options are a plain investability floor with no ranking at all
   (closest to the placebo, which won), or leaving the index universe alone.
3. **Is the fundamentals feed worth opening for this?** It is the only untested
   direction with a mechanism — orthogonal information at a slower frequency.
   Finding 1 argues the obvious version of it (screening out bad governance) has
   no prize, which lowers the expected value.

Nothing here changes the MM or OM25 v4 rules, and nothing here is a reason to
restate a published number: the honest point-in-time figures remain the books'
true record.

---

# Addendum — the investability pool (2026-09-11, founder follow-up)

The placebo above said breadth pays and the selection rule hurts. The candidate
that follows from that is the pool the placebo was *drawing from*, used directly
as the universe: every name clearing a turnover floor, reviewed monthly, no
ranking and no breadth cap. That run was missing from Phase 2. It is `b5`.

Rules: 63-day median rupee turnover ≥ floor, ≥ 252 sessions of history, price
≥ Rs 10. Point-in-time, no index reference. Breadth at Rs 1 cr is 431-868 names
(median 701 from 2016) against the Nifty 250's 250.

## b5 by floor — OOS 2016→

| Universe | MM | OM25 v4 | L6 v2 |
|---|---|---|---|
| `b0` honest index | 25.2% / 1.15 / −27% | 24.9% / 1.21 / −29% | 17.4% / 0.56 / −47% |
| `b5` floor Rs 1 cr | 28.5% / 1.15 / −35% | **33.5% / 1.52 / −30%** | 36.7% / 1.27 / −54% |
| `b5` floor Rs 2 cr | 29.7% / 1.22 / −32% | 31.6% / 1.43 / −29% | 36.6% / 1.28 / −54% |
| `b5` floor Rs 5 cr | 27.6% / 1.13 / −33% | 30.1% / 1.38 / −30% | 30.6% / 1.06 / −48% |
| `b5` floor Rs 10 cr | 27.2% / 1.11 / −33% | 26.3% / 1.18 / −39% | 24.8% / 0.83 / −47% |

The pool beats both the index universe and the turnover-ranked `b4` on every
book, confirming the placebo's reading: **no rule beats no rule.**

## The G3 sub-window gate separates the books

| Book / universe | 2016-19 | 2020-22 | 2023-26 | G3 (all ≥ 0.6) |
|---|---|---|---|---|
| MM `b0` | 0.69 | 1.73 | 1.10 | PASS |
| MM `b5` Rs 1 cr | **0.46** | 1.91 | 1.27 | **FAIL** |
| MM `b5` Rs 2 cr | **0.50** | 2.15 | 1.26 | **FAIL** |
| OM25 `b0` | 0.66 | 1.40 | 1.57 | PASS |
| **OM25 `b5` Rs 1 cr** | **0.96** | **1.92** | **1.80** | **PASS** |
| OM25 `b5` Rs 2 cr | 0.84 | 1.97 | 1.62 | PASS |
| OM25 `b5` Rs 5 cr | 0.85 | 1.99 | 1.42 | PASS |
| L6 `b0` | −0.15 | 1.56 | 0.42 | FAIL |
| L6 `b5` Rs 1 cr | 0.48 | 2.10 | 1.50 | FAIL |

**Widening MM loads the gain into 2020-22 and makes 2016-19 worse** — its G3
Sharpe falls from 0.69 to 0.46. That is a regime bet, not an improvement.

**Widening OM25 improves every sub-window at once**: 2016-19 goes 12.9% → 21.7%
(Sharpe 0.66 → 0.96), 2020-22 32.7% → 45.7%, 2023-26 32.7% → 37.3% — with
drawdown unchanged at −30% vs −29%. Uniform across three different regimes, so
it is not the 2020-22 small-cap run.

There is a mechanism for the split, and it is the one MECHANICS already names.
A wider pool admits lower-quality names. MM's score is pure vol-adjusted
momentum and simply buys them; OM25's blend carries the capture-ratio term,
which is what discriminates among them. OM25 is the defensive twin (down-capture
0.70 vs 0.77), and a junkier universe is exactly where that earns its keep.

## Sector-cap ablation

The wide universe is less sector-labelled (90.6% vs 96.8%), and unlabelled names
bypass the cap, so the cap could have been silently loosening. It is not what is
driving the result:

| | with cap | without cap |
|---|---|---|
| MM `b0` | 25.2% / 1.15 | 21.2% / 0.93 |
| MM `b5` Rs 2 cr | 29.7% / 1.22 | 29.5% / 1.20 |
| OM25 `b5` Rs 2 cr | 31.6% / 1.43 | 32.3% / 1.48 |

The cap is worth ~4pp on the narrow universe and ~0 on the wide one — a wider
pool diversifies on its own. The wide book is just as good with the cap removed
entirely, so label coverage is not manufacturing the gain.

## The limitation is now binding, and it blocks a retune

`b5` selects inside `data/master/panels/pr`, which holds ever-members of the
four NSE indices. Names that never made an index cannot be picked — and those
are precisely the ones that did not work. Counting the true investable set from
the bhavcopy against what the panel can offer:

| Floor | through 2020 | 2021-2023 | 2024-2026 |
|---|---|---|---|
| Rs 1 cr | 3-15% missing | 20-27% | 35-37% |
| Rs 2 cr | 2-9% | 14-21% | 30-34% |
| Rs 5 cr | 0-4% | 6-11% | 21-26% |

At the Rs 1 cr floor that headline 33.5% is computed on a universe missing a
fifth to a third of its eligible names from 2021, all of them names that never
qualified for an index. **That is the same survivorship mechanism this folder
exists to measure, reintroduced through the panel rather than the membership
file.** The direction of the finding survives it — a hole that omits non-index
names cannot explain OM25's 2016-19 improvement, where the hole is 6-15% — but
the magnitude does not.

Phase 2 of TASKS.md wrote the panel extension off on the strength of the `b4`
placebo. That was premature: `b4` was the wrong candidate, and the right one
makes the extension the prerequisite for anything further.

## Revised recommendation

1. **Extend the price panel from the bhavcopy** to every name that clears the
   floor, not just ever-index-members, using `build_adjusted.py` and the
   existing CA table. This is the same machinery already built and it is the
   critical path. Re-run `b5` on the extended panel before believing any number
   above.
2. **Then retune OM25 v4 on the pool** under the standing IS/OOS methodology and
   gates, with trials registered. The retune is a genuine search and the
   existing MECHANICS record does not carry over to it.
3. **Do not widen MM.** It fails G3 and the gain is regime-loaded.
4. **Rs 5 cr is the most defensible floor on current data** (≤ 6% coverage hole
   through 2022, still passes G3, still +5.2pp over `b0` at equal drawdown). Use
   it as the reference case until the panel is extended; expect the choice of
   floor to change once it is.

---

# Phase 4 — the pool on the full panel (2026-09-11)

The addendum blocked a retune on extending the price panel beyond ever-members
of the four NSE indices. **The extension turned out to be free.**
`data/master/prices/adjusted_pr` already holds 2519 fully adjusted symbols, and
`data/master/panels/pr` is a filtered copy of it — byte-identical per file. So
`panels/pr_full` is the same files, symlinked whole, and coverage of the
investable set goes from 65-85% to **95-100%**.

Rebuilt the floors on it and re-ran. `b5` names go from 2072 ever-members at the
Rs 2 cr floor (against 1168 on the narrow panel), breadth median 831 from 2016.

## The result reverses

OOS 2016→, CAGR / Sharpe / MaxDD, with the G3 sub-window Sharpes:

| Book / universe | narrow panel | **full panel** | subs (16-19 / 20-22 / 23-26) | G3 |
|---|---|---|---|---|
| MM `b0` index | 25.2% / 1.15 / −27% | 25.2% / 1.15 / −27% | 0.69 / 1.73 / 1.10 | PASS |
| MM `b5` Rs 2 cr | 29.7% / 1.22 / −32% | **22.9% / 0.78 / −39%** | 0.17 / 1.23 / 1.11 | FAIL |
| MM `b5` Rs 5 cr | 27.6% / 1.13 / −33% | **22.9% / 0.83 / −38%** | 0.58 / 1.08 / 0.88 | FAIL |
| OM25 `b0` index | 24.9% / 1.21 / −29% | 24.9% / 1.21 / −29% | 0.66 / 1.40 / 1.57 | PASS |
| OM25 `b5` Rs 2 cr | 31.6% / 1.43 / −29% | **23.7% / 0.91 / −34%** | 0.64 / 1.57 / 0.65 | PASS |
| OM25 `b5` Rs 5 cr | 30.1% / 1.38 / −30% | **24.9% / 1.04 / −32%** | 0.91 / 1.59 / 0.72 | PASS |
| L6 `b0` index | 17.4% / 0.56 / −47% | 17.4% / 0.56 / −47% | −0.15 / 1.56 / 0.42 | FAIL |
| L6 `b5` Rs 2 cr | 36.6% / 1.28 / −54% | **25.0% / 0.75 / −63%** | −0.04 / 1.59 / 0.99 | FAIL |

**`b0` is identical on both panels to the decimal on all three books.** It has to
be — index membership can only ever select names already in the narrow panel — and
it confirms the swap changed nothing except the wide universes.

**On an honest panel the pool does not beat the index universe.** OM25's Rs 5 cr
floor matches `b0` on CAGR (24.9% vs 24.9%) while losing 0.17 of Sharpe and 3pp
of drawdown; the Rs 2 cr floor is worse outright. MM is much worse and fails G3.
L6 keeps a CAGR gain but at −63% drawdown and a negative 2016-19 Sharpe.

**The entire +8.6pp was the coverage hole.** Widening the universe was measuring
the same survivorship the folder set out to remove, arriving through the panel
instead of the membership file.

If anything this understates the case against widening. The 1193 added symbols
are the ones nobody has QA'd for adjustment errors, and a missed reverse split
reads as a huge return that a momentum rank would buy — an error that biases the
wide universe *up*. It still loses.

## Answering the three objections directly

1. *"The panel was a wide enough sample — the NSE 500."* Wide enough in count;
   not neutral in composition. Every name in it was, at some point in twenty
   years, good enough for an NSE index. The names it omitted were not omitted by
   a rule you could run in 2021 — they were omitted by not having qualified by
   2026. That is a 2026-dated fact standing in for a 2021 decision, which is the
   definition of the bias. Now measured rather than argued: it was worth the
   whole result.
2. *"We tuned on Nifty 250 point-in-time."* Correct, and that is exactly why the
   comparison was unfair. `b0` draws only from index members, all of which are in
   the narrow panel by construction, so the baseline was always clean. The
   contamination sat entirely on the challenger's side of the comparison.
3. *"We can't have any and all stocks in the list."* Right, and a floor is the
   principled boundary — but the answer does not turn on where it is drawn.
   Every floor from Rs 2 cr to Rs 10 cr underperforms the Nifty 250
   point-in-time universe on the honest panel.

## Where this leaves the question

The universe is not a lever. Reach below the index floor looked like one only
while the wider universe was quietly survivorship-screened. **The Nifty 250
point-in-time membership stands, and MM and OM25 v4 keep their MECHANICS rules
unchanged.**

One thing is genuinely untested: these are the *locked* rules transplanted onto a
wider universe, not rules tuned for one. A retune could in principle find
something. The evidence argues against spending it — the wide universe is worse
in-sample, out-of-sample, and in every sub-window for both Nifty 250 books, so
there is no signal to tune toward — and a search over a new universe multiplies
the trial count that deflates the IS Sharpe under G1. That is a founder call, not
a research one.

## Artifact worth keeping

`data/master/panels/pr_full` — 2519 adjusted symbols, symlinks, zero bytes. Any
future study that needs names beyond the four NSE indices should point at it
rather than `panels/pr`, and should expect the adjustment QA to be thinner there.

---

# Phase 5 — NSE 500 point-in-time as the product universe (2026-09-11)

The well-posed version of the question: not an open pool, but **NSE 500
point-in-time** — a real index, curated and liquidity-screened by NSE,
governance-vetted, survivorship-free in our store. Is there extra return there?

Locked MM and OM25 v4 rules, universe varied, OOS 2016→:

| Universe | MM | OM25 v4 |
|---|---|---|
| nifty250 (as shipped) | 25.2% / 1.15 / −27% · G3 **PASS** | 24.9% / 1.21 / −29% · G3 **PASS** |
| nse500 straight swap | 22.5% / 0.93 / −35% · G3 FAIL | **26.8% / 1.27 / −33% · G3 PASS** |
| nse500 + Rs 2 cr floor | 23.4% / 0.99 / −34% · G3 FAIL | 24.2% / 1.13 / −32% · G3 FAIL |
| nse500 + Rs 5 cr floor | 22.3% / 0.93 / −34% · G3 FAIL | 22.9% / 1.05 / −33% · G3 FAIL |
| nifty250 core + 3 satellite | 21.5% / 0.97 / −27% · G3 FAIL | 21.4% / 1.08 / −26% · G3 PASS |
| nifty250 core + 5 satellite | 20.8% / 0.92 / −28% · G3 FAIL | 21.9% / 1.10 / −27% · G3 PASS |

**MM on NSE 500 fails G3** (2016-19 Sharpe 0.45), reproducing the rejection
already recorded in `mm_rebuild/RESULTS.md` §4/§8/§9. **Satellites lose** on both
books, reproducing §14.

**OM25 v4 on NSE 500 is the one combination that beats what shipped** — +1.9pp
of CAGR, +0.06 of Sharpe, both gates passed. Its universe was fixed at nifty250
in the §22 chained refit, so this specific comparison is genuinely new.

## It does not survive the recency check

Rolling 3-year Sharpe — the standing forward gate (≥ 0.6), year-ends:

| | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|
| OM25 nifty250 | 1.39 | 1.32 | 1.72 | 1.42 | 1.54 | **1.33** |
| OM25 nse500 | 2.38 | 2.02 | 1.97 | 1.06 | 0.79 | **0.73** |

| Trailing | OM25 nifty250 | OM25 nse500 |
|---|---|---|
| 3 years | **30.2% / 1.34 / −23%** | 15.3% / 0.57 / −33% |
| 1 year | 14.1% / 0.54 / −11% | 17.4% / 0.78 / −14% |

**The +1.9pp is stale.** It was earned in 2020-22 (sub-window Sharpe 2.40 against
nifty250's 1.40) and has been decaying ever since: the NSE 500 version has done
*half* the CAGR over the last three years, at a rolling Sharpe that has fallen
from 2.38 to 0.73 and is now approaching the forward gate from above. The
2023-26 sub-window is 0.84 against nifty250's 1.57. This is a midcap-regime
edge that the regime has already taken back.

The deflated IS Sharpe does not discriminate — both universes deflate to −1.32
against the 1,806 trials now standing across `mm_rebuild`, `om25_rebuild` and
this folder, because the 2006-2015 window is weak for both. It is not an argument
against NSE 500 specifically, only a reminder of how little an IS edge is worth
at this trial count.

## The liquidity screen finding, which cuts against the product instinct

A turnover floor applied *inside* NSE 500 — strictly a subset of the index, the
narrow direction, removing only its illiquid tail — **makes both books worse**,
and progressively worse as the floor rises (OM25: 26.8% → 24.2% → 22.9%). The
illiquid tail of NSE 500 is contributing return, not dragging on it.

That is worth stating plainly because it is uncomfortable: **the names a product
would most want to exclude on liquidity and governance grounds are part of where
the measured return comes from.** Two honest readings, and they are not
exclusive:

1. The return is real and the tail is genuinely where midcap momentum lives.
2. The return is an artefact of charging a flat 20 bps of slippage to names that
   could never absorb the book at that cost — in which case the backtest is
   overstating the whole NSE 500 case, including the +1.9pp above.

Nothing here distinguishes them, and reading 2 would require a
turnover-proportional slippage model the engine does not have. Until it does,
treat any NSE 500 result as an upper bound.

## Answer

**No — there is no extra return available in NSE 500 point-in-time today.** The
one candidate that looked like it (OM25 v4, +1.9pp, gates passed) is a
2020-22 midcap-regime edge that has decayed for three years and now runs at half
the Nifty 250 book's trailing-3y CAGR. MM fails outright, satellites fail, and
narrowing NSE 500 by liquidity makes it worse.

**Nifty 250 point-in-time stands for both books.** The founder's product instinct
against a wide universe and the measured evidence point the same way, and the
liquidity finding above says they point the same way for the same reason.

---

# Phase 5b — what the pool actually held (clarification, 2026-09-11)

The addendum's `b5` pool is easy to mistake for NSE 500 point-in-time. It is not.
Composition at the Rs 1 cr floor, on the narrow panel the addendum used:

| Date | NSE 500 PIT | pool | in NSE 500 | **ex-member** | future member |
|---|---|---|---|---|---|
| 2016-06-30 | 498 | 498 | 386 | 92 | 20 |
| 2018-06-30 | 500 | 619 | 464 | 115 | 40 |
| 2021-06-30 | 501 | 782 | 500 | **240** | 42 |
| 2024-06-30 | 501 | 878 | 501 | **347** | 30 |
| 2026-06-30 | 500 | 886 | 500 | **376** | 10 |

The pool is the whole NSE 500 **plus 240-376 names NSE had already demoted from
the index**, and only 10-42 names that would later join it. So the addendum's
33.5% was not a better NSE 500 — it was NSE 500 plus a second universe of
ex-constituents, roughly 1.8x the index by 2026.

That also relocates the bias precisely. Ex-members are fully present in our
panel, since being an ever-member is what put them there. What is missing is
the cohort that was **never** in any of the four indices across twenty years —
and Phase 4 showed that restoring them reverses the result. The pool was not
reaching into a neutral midcap space; it was reaching into the subset of demoted
names that had been vetted by an index at some point, with the never-vetted
names silently excluded.

## Is the 500th NSE 500 stock liquid enough?

63-day median turnover of NSE 500 members, Rs cr:

| Date | min | p5 | p25 | median | members below Rs 1 cr |
|---|---|---|---|---|---|
| 2016-06-30 | 0.07 | 0.34 | 1.12 | 3.9 | **110 of 496** |
| 2021-06-30 | 0.48 | 3.08 | 9.79 | 22.1 | 1 of 501 |
| 2026-06-30 | **4.80** | 9.97 | 27.43 | 77.9 | **0 of 500** |

**Today the NSE 500 has no illiquid tail.** The thinnest member trades Rs 4.8 cr
a day and the 5th percentile is Rs 10 cr — untroubling for a 25-name book at the
capital this product targets. The Rs 1 cr floor is therefore non-binding on the
current index; everything it did was add ex-members.

In 2016 the picture was different: a fifth of the index traded under Rs 1 cr a
day. That is why the "floor inside NSE 500" test in Phase 5 hurt — it cut the
2016-2018 tail, which was where those years' return sat.

**This narrows the slippage caveat from Phase 5.** The concern that a flat 20 bps
flatters untradeable names applies to the *historical* backtest, chiefly
2016-2019, and to the wide-pool runs. It does not apply to trading NSE 500 today.
A turnover-proportional slippage model is still the right thing to build, but it
is a question about the honesty of old backtest years, not about whether the
current index is investable.

---

# Phase 7 — "once in NSE 500, always eligible" (founder, 2026-09-11)

**The founder's construction, and it is the best thing in this folder.** A symbol
becomes eligible the day it first enters NSE 500 and never leaves, subject only
to an optional turnover floor. Keep a running list, never delete.

Two properties make it different from everything rejected above:

- **No foresight.** Unlike `b2` it grants nothing before first inclusion; unlike
  the `b5` pool it admits no name that had not yet qualified at the time. The
  10-42 future members that contaminated the pool are gone by construction.
- **Immune to the panel limitation.** The rule excludes never-members *by
  design*, so their absence from the narrow panel is the rule working, not a
  bias. Confirmed: **the no-floor result is identical to the decimal on the
  narrow and full panels.** That is why Phase 4's reversal does not apply.

Breadth 324-825 names, median 624 from 2016 — larger than NSE 500, bounded, and
every name vetted by NSE at some point.

## Result — OOS 2016→

| Book / universe | OOS | subs (16-19 / 20-22 / 23-26) | G3 |
|---|---|---|---|
| OM25 v4, nifty250 (shipped) | 24.9% / 1.21 / −29% | 0.66 / 1.40 / 1.57 | PASS |
| OM25 v4, nse500 PIT | 26.8% / 1.27 / −33% | 0.75 / 2.40 / 0.84 | PASS |
| **OM25 v4, once-in, no floor** | **30.4% / 1.43 / −29%** | **1.05 / 1.95 / 1.40** | **PASS** |
| OM25 v4, once-in + Rs 2 cr | 29.3% / 1.34 / −30% | 0.76 / 2.06 / 1.34 | PASS |
| MM, once-in, no floor | 24.8% / 1.01 / −34% | 0.38 / 1.96 / 0.93 | FAIL |

**+5.5pp of CAGR and +0.22 of Sharpe at identical drawdown**, with two of three
sub-windows improving and the third (1.57 → 1.40) giving a little back. MM fails
G3 again — the same split as everywhere in this folder: only the capture-ratio
book handles a wider pool, because it is the term that discriminates among the
lower-quality names a wider pool admits.

## It does not decay the way NSE 500 PIT did

Rolling 3-year Sharpe at year-ends (gate ≥ 0.6):

| | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|---|
| nifty250 | 0.81 | 0.32 | 1.39 | 1.32 | 1.72 | 1.42 | 1.54 | **1.33** |
| nse500 PIT | 0.96 | 0.89 | 2.38 | 2.02 | 1.97 | 1.06 | 0.79 | **0.73** |
| once-in | 1.25 | 0.82 | 2.28 | 1.72 | 1.87 | 1.37 | 1.27 | **1.02** |

| Trailing | nifty250 | once-in |
|---|---|---|
| 5 years | 26.8% / 1.20 / −23% | **26.8% / 1.22 / −29%** |
| 3 years | **30.2% / 1.34 / −23%** | 22.0% / 0.97 / −27% |
| 1 year | 14.1% / 0.54 / −11% | **19.7% / 1.01 / −10%** |

Never below 1.02 on the rolling gate. Dead even over five years, behind over
three, ahead over one — that reads as noise, not the one-way decay that killed
NSE 500 PIT.

## The delisting robustness test it had to pass

This universe deliberately holds names NSE demoted, and D-9 exits a delisted
position at last traded price with no haircut — an optimism it is more exposed to
than nifty250. Reconstructing round-trip P&L by FIFO from the trade logs:

| | nifty250 | once-in |
|---|---|---|
| distinct names traded (2016→) | 266 | 435 |
| of which eventually die | 12 (4.5%) | 36 (8.3%) |
| **exits ON a delisting date** | 1 | **0** |
| P&L from names that later die | 4.7% | 5.1% |

**Zero positions were closed by a name disappearing while held.** The 20% trailing
stop and the rank exit remove decaying names long before they delist, which is
what those devices are for. The D-9 optimism does not touch this result.

## What is not settled

1. **Trial count.** 1,806 trials stand across `mm_rebuild`, `om25_rebuild` and
   this folder, and this is one of roughly 35 universe variants tried here. It
   was reasoned to rather than grid-searched, which is a better epistemic
   position than a winning grid cell — but it is not a walk-forward result.
   G5 has not been run on it.
2. **The advantage is not currently active.** Over the trailing three years
   nifty250 is ahead, 30.2% / 1.34 against 22.0% / 0.97.
3. **Turnover is 22-27% higher** (717 round trips vs 586; 1,390 entries vs
   1,095). At a flat 20 bps that is already charged, but real cost scales with
   size and this universe reaches into thinner names.
4. **A loose end in the floored variants.** `once-in + Rs 2 cr` gives 29.3% on
   the narrow panel and 26.3% on the full one. The no-floor version is identical
   across both, so the discrepancy is in how the turnover panel is assembled, not
   in the universe. Until that is chased down, **only the no-floor result should
   be quoted.**
5. **The governance concern is unaddressed.** The universe holds demoted names
   by design. Nothing here screens them, and the floored variant that would is
   the one with the loose end.

## Recommendation

This is the first universe change in the folder that beats what shipped on an
honest construction, survives its robustness test, and is immune to the panel
limitation. It deserves a proper evaluation — a §-series treatment with G5
walk-forward, the full gate battery, a turnover and capacity analysis at the
Rs 5-10 L target, and founder sign-off — **not adoption on the strength of one
backtest.** It should not change MECHANICS today.

---

# Phase 8 — diagnosing the once-in universe (2026-09-11)

Four questions from the founder: refit for this universe, explain the recent
fade, explain why MM cannot use it, and test announcement-date inclusion.

## 8a — Why MM cannot use it: risk, not return

Same universe, same devices, only the score differs:

| Book / universe | OOS CAGR | OOS vol | Sharpe | MaxDD | 2016-19 CAGR | 2016-19 vol | Sharpe |
|---|---|---|---|---|---|---|---|
| MM / nifty250 | 25.2% | 17.6% | 1.15 | −27% | 14.2% | 13.4% | 0.69 |
| **MM / once-in** | **24.8%** | **19.7%** | 1.01 | −34% | 12.0% | **18.5%** | **0.38** |
| OM25 / nifty250 | 24.9% | 16.5% | 1.21 | −29% | 12.9% | 11.9% | 0.66 |
| **OM25 / once-in** | **30.4%** | **17.7%** | 1.43 | −29% | 22.9% | 17.1% | 1.05 |

Widening does opposite things to the two books. **MM: no extra return (24.8% vs
25.2%) and 12% more volatility — 38% more in 2016-19, where it fails.** OM25:
+22% return for +7% volatility.

The trade log shows the mechanism. On the ex-member sleeve MM's median hold is
**63 days against OM25's 90**, on more trips (406 vs 323) for less P&L (17.2m vs
34.6m). Pure vol-adjusted momentum buys the volatile demoted names, gets
whipsawed, and stops out. The capture-ratio term screens on down-participation,
so OM25 takes the same sleeve's upside without its churn. A wider universe is
an opportunity only to a score that can tell its members apart.

## 8b — Why it fades recently: the sleeve grows and rots

The once-in rule never removes anyone, so the ex-member sleeve compounds:

| | 2016 | 2019 | 2021 | 2023 | 2025 | 2026 |
|---|---|---|---|---|---|---|
| universe size | 914 | 1016 | 1073 | 1141 | 1204 | 1243 |
| ex-member share | 46% | 51% | 53% | 56% | 58% | **60%** |

And its quality decays. OM25's ex-sleeve round trips by entry year:

| year | 2016 | 2017 | 2018 | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| win rate | 62% | 63% | 37% | 20% | 63% | 52% | 39% | 70% | 55% | **39%** | **47%** |
| mean return | +20% | +49% | −7% | −11% | +24% | +37% | +9% | +39% | +12% | **−1%** | **−1%** |
| p90 return | +80% | +182% | +6% | +9% | +96% | +131% | +28% | +97% | +43% | **+35%** | **+40%** |

By 2026 the sleeve is 60% of the universe and its right tail — the part a
momentum book lives on — has gone from +80/+182% to +35/+40%. **The fade is
structural, not regime noise: an ever-growing pool of names demoted longer and
longer ago.**

## 8c — The obvious fix does not work

If old demotions are the problem, cap their age: eligible while a member, plus a
grace period after demotion. Derived from the diagnosis, not grid-searched.

OM25 v4, OOS Sharpe by grace period:

| grace | 0m | 12m | 24m | 36m | 60m | 120m | none |
|---|---|---|---|---|---|---|---|
| OOS Sharpe | 1.27 | 1.33 | **1.35** | 1.21 | 1.21 | **1.43** | **1.43** |
| trailing 3y Sharpe | 0.57 | 0.58 | 0.73 | 0.71 | 0.78 | 1.23 | 0.97 |

**The response is non-monotonic** — up to 24m, down at 36-60m, up again at 120m.
A real lever produces a ridge, not a sawtooth. The 120m cell is indistinguishable
from no expiry over this window anyway. For MM, 24m grace is the only variant
that passes G3 (0.67/1.69/0.88) while 36m and 60m fail — 24 working and 36
failing is a fluke, not a finding, and it is still below nifty250 regardless.

**No grace period fixes the recent fade.** Reported as a negative result rather
than harvesting the 24m or 120m cell.

## 8d — Announcement date instead of effective date

NSE publishes reconstitutions ahead of effectivity: **median 35 days for
Nifty 250**, 9 for NSE 500. Admitting a name from the publication date is
point-in-time legitimate. Corpus carries both dates only from 2020-08, so this
is a 2020→ test. 135 Nifty 250 and 336 NSE 500 inclusions pulled forward.

| Book / universe | 2020→ effective-date | 2020→ **announcement** |
|---|---|---|
| MM / nifty250 | 32.4% / 1.41 / −27% | **31.1% / 1.36 / −28%** |
| MM / nse500 | 28.9% / 1.16 / −35% | 29.3% / 1.16 / −33% |
| OM25 / nifty250 | 34.1% / 1.64 / −23% | 35.0% / 1.67 / −23% |
| OM25 / nse500 | 32.8% / 1.52 / −33% | 33.9% / 1.57 / −33% |

Nothing, and slightly negative for MM — the book the idea was aimed at.

The reason is that **eligibility was never the binding constraint**. Of 150
announced inclusions, only **22 ever entered the book inside a pub→eff window**
(22 of MM's 389 buys, 5.7%). A new index entrant still has to out-rank 45
incumbents on vol-adjusted momentum; arriving 35 days early rarely changes that.

**Caveat on power.** With 22 affected entries over six years, this test cannot
resolve an effect smaller than roughly ±1.5pp of CAGR. It is an underpowered
null, not a demonstrated zero. Worth revisiting if the press-release corpus is
ever extended back before 2020.

## Where the candidate stands after Phase 8

The Phase 7 headline is intact — OM25 v4 on once-in is 30.4% / 1.43 / −29%
against 24.9% / 1.21 / −29% — but it is now better understood and less
attractive:

- Its engine is the ex-member sleeve (62% of P&L on 46% of trips).
- That sleeve is **structurally decaying** as the never-delete pool accumulates,
  and the decay is not fixable by the one parameter that should have fixed it.
- Its edge is **episodic**: strong 2016-17, 2020-21, 2023; absent 2018-19 and
  2025-26.
- MM cannot use it for a reason that is now mechanical, not mysterious.

A full refit — score weights, lookback, top-N, buffers tuned *for* this universe —
is still untested. Two cautions before spending it. The grace sweep's sawtooth
says this universe's parameter surface is noisy, and a refit aimed at "does not
deteriorate recently" is targeting 2025-2026, which is roughly 300 observations.
At the 1,806 trials already standing, a search that optimises a two-year window
will find something, and it will not be real.

**Recommendation unchanged: do not touch MECHANICS.** If the refit is run, run it
with the recent window held out rather than targeted.

---

# Phase 9 — refit with the recent window held out (2026-09-11)

Protocol pre-registered in `lib/refit.py` before any hold-out number existed:
fit on 2006-2023, select on 2016-2023 Sharpe after G3/G4 screening, then score
2024→ exactly once. Grid: `mix_w` × `top_n` × `exit_buffer` × `sector_cap`, 60
cells. **Both universes got the same grid** — refitting the wide universe against
an untuned narrow book is the unfair comparison that has already misled this
folder twice.

## Selection — fit window only

| | cells surviving G3+G4 | winner | fit 2016-2023 | grid median Sharpe |
|---|---|---|---|---|
| nifty250 | 27 of 60 | mix 0.4 / n20 / buf20 / sec5 | 26.0% / **1.29** / −29% | 1.11 |
| once-in | **59 of 60** | mix 0.6 / n30 / buf20 / sec5 | 33.9% / **1.69** / −29% | **1.45** |

On the fit window this looks overwhelming. **once-in's grid *median* (1.45) beats
nifty250's grid *maximum* (1.29)**, and 59 of 60 cells clear the gates against 27.
The `mix_w` response is a clean ridge, not a spike — 0.3:1.45, 0.4:1.49, 0.5:1.58,
**0.6:1.69**, 0.7:1.54 — which is what a real parameter is supposed to look like.

One honest correction: the ridge peaks at **more** momentum weight (0.6) on the
wide universe and **less** (0.4) on the narrow one. Phase 8a's mechanism story
predicted the opposite. That story explains why MM at mix 1.0 fails, but it does
not survive as a directional prediction inside the tested range.

## Hold-out 2024→ — and it inverts

| | fit 2016-2023 | **hold-out 2024→** | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|
| **shipped OM25 v4 (nifty250)** | 23.7% / 1.21 | **28.3% / 1.21 / −23%** | +55.9 | +15.1 | +9.7 |
| shipped rules on once-in | 33.9% / 1.63 | 20.3% / 0.86 / −27% | +65.7 | −12.0 | +13.7 |
| REFIT nifty250 | 26.0% / 1.29 | 23.9% / 0.97 / −26% | +54.6 | +3.8 | +11.6 |
| REFIT once-in | 33.9% / **1.69** | 22.9% / 0.98 / −25% | +59.6 | −4.8 | +15.7 |

**The shipped book wins the hold-out outright**, and every once-in variant loses
it. once-in's apparent edge — 1.69 against 1.21 on the fit window — becomes 0.98
against 1.21 on data neither was fitted to. A complete inversion.

## The control is the real finding

**The same procedure applied to nifty250 made a book we know is good worse.**
Refit nifty250 beats shipped on the fit window (1.29 vs 1.21) and loses on the
hold-out (0.97 vs 1.21). Nothing about that cell is exotic — it is a mild
reweighting of a book with an 1,800-trial pedigree — and the search still picked
a loser.

That is the strongest evidence in this folder, and it is evidence about the
*method*, not the universe: **at this trial count, on this data, fit-window
improvements do not carry.** It applies with equal force to once-in's 1.69, to
the Phase 7 headline, and to anything else in these pages selected on a fit
window. It is also exactly why the control was worth spending half the compute on.

The refit did do the narrow thing it was asked to: once-in's 2025 goes from
−12.0% to −4.8%. But it bought that with fit-window fitting, and the nifty250
control says that kind of improvement does not generalise here.

**Power caveat.** The hold-out is 2.7 years, roughly 670 observations, and is
dominated by 2025. Sharpe gaps of 0.2-0.3 over that span are not statistically
separable, so this does not *prove* once-in is worse. What it does is fail to
support it, while the control independently shows the selection machinery is
unreliable at this scale.

## Verdict on the whole folder

**Do not adopt. MECHANICS is unchanged.** MM and OM25 v4 keep the Nifty 250
point-in-time universe and their locked rules.

The question the folder opened with — could a real-time universe have held the
survivors — is answered: not by predicting membership, not by widening to a
liquidity pool, not by NSE 500, and not by keeping demoted names. The one
construction that beat the shipped book on an honest backtest failed the only
test it was not fitted to, and the control says that is what should have been
expected.

---

# Phase 10 — demotions kept for 12 months only, held out (2026-09-11)

Founder's last variant: NSE 500 point-in-time plus demoted names for 12 months,
then dropped. Motivated by 8b — the ex-member sleeve rots with age, so keep only
fresh demotions. Same sealed protocol as Phase 9.

## Selection — fit window only

42 of 60 cells survive G3+G4; grid median Sharpe 1.38, max 1.66. **The winning
cell is mix 0.5 / n25 / buffer 20 / sector cap 5 — the shipped configuration
exactly.** The grid, given a free hand, reproduced OM25 v4's own parameters. So
this is a clean universe test: no parameter overfitting is available to explain
the result either way.

## Hold-out 2024→

| | fit 2016-2023 | **hold-out 2024→** | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|
| **shipped OM25 v4 (nifty250)** | 23.7% / 1.21 | **28.3% / 1.21 / −23%** | +55.9 | +15.1 | +9.7 |
| shipped rules on once-in | 33.9% / 1.63 | 20.3% / 0.86 / −27% | +65.7 | −12.0 | +13.7 |
| **decay12 (= refit winner)** | 32.9% / **1.66** | **13.5% / 0.47 / −32%** | +31.3 | −3.0 | +11.1 |

**Worst of everything tested.** On the fit window decay12 is indistinguishable
from once-in (1.66 vs 1.63); out of sample it is half of it.

The idea did exactly what it was designed to do and lost anyway. **2025 improves
as predicted — −3.0% against once-in's −12.0% — but 2024 collapses, +31.3%
against +65.7%.** Aging the sleeve out removed the names that drove the good year
along with the ones that caused the bad one. The ex-member sleeve is a single
exposure: you cannot keep its upside and drop its downside by trimming on age.
That is the same lesson as 8c's sawtooth, now with a mechanism.

## The rank inversion is complete

Four constructions, all scored on a window none was fitted to:

| | fit Sharpe | hold-out Sharpe |
|---|---|---|
| decay12 | **1.66** (1st) | 0.47 (4th) |
| once-in | 1.63 (2nd) | 0.86 (3rd) |
| refit nifty250 | 1.29 (3rd) | 0.97 (2nd) |
| **shipped OM25 v4** | 1.21 (4th) | **1.21 (1st)** |

**The fit-window ranking is exactly reversed out of sample. Four for four.**
(**Phase 11 corrects this reading: three of the four differ in cap exposure and
the hold-out is a less small-cap-favourable regime than the fit window, so much
of the inversion is mechanical. The clean control is the nifty250 refit, which
holds the universe fixed.**) As originally written: on this data, the better a
variant looked on the window it was chosen on, the worse it did on the window it
was not. The only construction that held its Sharpe across the boundary is the
one that was never selected here at all.

**Verdict unchanged, now with a third independent failure. MECHANICS stands.**
This closes the folder: no universe change survives an honest hold-out, and the
consistent pattern across ten phases is that the apparent gains were selection
artefacts rather than anything the books could have traded.

---

# Phase 11 — is the hold-out a cap-regime artefact? (founder, 2026-09-11)

Equal-weight point-in-time cap bands built from our own membership and panel:
LARGE = Nifty 100, MID = Nifty 250 minus Nifty 100, SMALL = NSE 500 minus
Nifty 250. Disjoint, survivorship-free, mutually consistent.

## The founder is right: the hold-out is regime-confounded

| window | SMALL-leading days | mean SMALL−LARGE spread |
|---|---|---|
| fit 2016-2023 | **60%** | **+3.2pp** |
| HOLD-OUT 2024-26 | **43%** | **+0.9pp** |

Cap-band CAGR: fit window LARGE +12.9 / MID +16.3 / SMALL +12.4; hold-out
LARGE +9.2 / MID +10.7 / SMALL +8.8; and **2025 alone is a small-cap crash** —
LARGE +7.8%, SMALL −6.5%.

And the books are cap bets of different leverage. Conditional on trailing-12m
leadership, OOS 2016→:

| universe | SMALL leading (56% of days) | LARGE leading (44%) |
|---|---|---|
| nifty100 | 23.0% / 1.09 | **0.3% / −0.24** |
| shipped (nifty250) | 38.9% / 1.77 | **10.3% / 0.37** |
| once-in | **52.3% / 2.10** | 8.4% / 0.27 |

**once-in is a levered small-cap-leadership bet.** It was therefore going to look
worse in the hold-out than in the fit window for regime reasons alone, before any
question of selection.

## Correction to Phase 10

Phase 10 presented the four-way rank inversion as a clean illustration of
selection artefact. **That claim was overstated.** Three of the four
constructions differ in cap exposure, the fit window was 60% small-led and the
hold-out 43%, so much of the inversion is mechanical rather than evidence about
overfitting.

The part of Phase 9 that survives untouched is the **nifty250 refit control**:
same universe, same cap exposure, fit Sharpe 1.29 against shipped's 1.21,
hold-out 0.97 against 1.21. Holding the universe fixed removes the confound, and
that cell still degraded out of sample. Parameter overfitting is demonstrated;
*universe* overfitting is not, and Phases 9-10 cannot separate it from regime.

**Revised verdict on once-in: not established either way, rather than failed.**
The 2.7-year hold-out happens to contain the one regime it is most exposed to,
and is too short to resolve a cap-cycle-conditional book. Still not adopted —
adoption needs positive evidence and there is none — but the case against it is
weaker than Phase 10 claimed.

## The large-cap worry is real, and the universe is not the lever

| universe | OOS 2016→ | hold-out 2024→ | 2025 |
|---|---|---|---|
| nifty100 | 12.1% / 0.47 / −24% | **6.0% / 0.07 / −24%** | −1.1% |
| shipped (nifty250) | 24.9% / 1.21 / −29% | 28.3% / 1.21 / −23% | +15.1% |
| once-in | 30.4% / 1.43 / −29% | 20.3% / 0.86 / −27% | −12.0% |

Two things follow, and the second matters more than anything else in this folder.

**Narrowing to large caps is not protection — it is much worse.** Momentum on
Nifty 100 barely functions: 0.47 OOS Sharpe, 0.07 on the hold-out, and
**0.3% / −0.24 in exactly the large-led regimes it was supposed to hedge.** There
is no large-cap refuge to rotate into.

**The shipped book is itself cap-cycle dependent, and this is a live production
risk.** (**Phase 11b corrects this: the regime classifier was lagged, and on a
contemporaneous split "large caps lead" turns out to mean "the market is weak" —
LARGE averaged +1.8% in those years. The book's weakness there is ordinary beta,
not a cap bet. Read 11b, not this paragraph.**) OM25 v4 on Nifty 250 makes 38.9% / 1.77 when small leads and
**10.3% / 0.37 when large leads — below its own 0.6 forward gate — across 44% of
OOS days.** That is not a tail scenario. The founder's worry was aimed at the
universe choice; it applies to the book we already run, and no universe tested
here fixes it. If cap-cycle risk is to be addressed, the lever is the regime
overlay, the score, or exposure — not the universe.

That is the one genuinely actionable finding in this folder, and it is about
production rather than about any candidate.

---

# Phase 11b — correcting the cap-regime test (founder, 2026-09-11)

The founder asked why 2025 is called a small-cap crash when the shipped book
made +15.1% in it. Two separate things were wrong with how Phase 11 put it.

## The direct answer: 2025 was not a crash in the shipped book's universe

Calendar 2025: **LARGE +8.2%, MID +6.4%, SMALL −5.6%.** The shipped book holds
LARGE + MID only, so its universe was *up* about 7% and the book made +15.1% by
outperforming it. The −5.6% was confined to the 251-500 band, which is precisely
what once-in adds and why once-in did −12.0%. No contradiction — the "crash"
label described the band added by the candidate, not the book's own universe.

## The flaw: the regime classifier lagged

Phase 11 split days by the **trailing** 12-month SMALL−LARGE spread, which is
observable but badly lagged:

| year | LARGE | MID | SMALL | actual leader | days my rule called SMALL-leading |
|---|---|---|---|---|---|
| 2019 | +3.1% | −4.5% | −15.7% | LARGE | 0% |
| 2022 | +1.3% | 0.0% | +0.9% | LARGE | **71%** |
| 2025 | +8.2% | +6.4% | −5.6% | LARGE | **31%** |

In 2025 the rule spent a third of the year calling SMALL-leading because it was
looking back into 2024's small-cap run. So Phase 11's "LARGE leading" bucket was
not "during a large-cap year" — it was "after twelve months of large-cap
leadership", and the two buckets were contaminated with each other.

Re-split on **contemporaneous** (same-year) leadership — descriptive, not
tradeable, since it uses the year's own realised returns:

| universe | SMALL-led years | LARGE-led years |
|---|---|---|
| nifty100 | 23.2% / 1.04 | 1.2% / −0.21 |
| **shipped (nifty250)** | **46.8% / 1.98** | **4.8% / 0.05** |
| once-in | 68.9% / 2.80 | −2.0% / −0.30 |

SMALL-led: 2017, 2020, 2021, 2023, 2024, 2026. LARGE-led: 2016, 2018, 2019,
2022, 2025.

## And the reframing that matters

Look at what LARGE itself did in each bucket. **In the LARGE-led years it
averaged +1.8%** (+6.2, −9.7, +3.1, +1.3, +8.2); in the SMALL-led years it
averaged +21.5%. In this sample **"large caps lead" is very nearly synonymous
with "the market is weak."**

So the shipped book's 4.8% / 0.05 in those years is mostly ordinary beta to a
weak market, not a hidden cap bet. That is a normal property of a long-only
momentum book, not a defect — and Phase 11's framing of it as a specific
cap-rotation vulnerability was wrong.

It also means **the founder's actual question cannot be answered from this
data.** The scenario is a *strong* cycle led by large caps. There is no such year
in 2016-2026: no year where LARGE led and LARGE returned more than 8.2%. The
sample contains large-cap-led weak markets and small-cap-led strong ones, and
nothing else. Within it, the shipped book's best LARGE-led year is 2025 at
+15.1% — its four others are +6.5%, −6.5%, +2.9%, +6.5%.

**Corrected conclusions:**

- 2025 is not evidence against anything. The book's universe rose; only the band
  it does not hold fell.
- The shipped book is not shown to carry a cap-rotation risk. It carries ordinary
  market-weakness exposure, which every version tested shares.
- The one claim that survives is the negative one about the alternatives:
  **Nifty 100 is not a refuge** (1.2% / −0.21 in LARGE-led years, 23.2% / 1.04 in
  SMALL-led — a worse version of the same shape), and once-in is strictly more
  cap-levered than what ships (68.9% / 2.80 against −2.0% / −0.30).
- A large-cap-led *bull* market is genuinely untested. If that is the worry, it
  cannot be resolved by backtest on this sample and should be treated as an
  open risk rather than a settled one.

---

# Phase 12 — does the book rotate into large caps when large caps lead? (2026-09-11)

The founder's argument: Nifty 100 sits inside Nifty 250, so if large caps become
the RS leaders the ranking picks them and the book adapts by itself. Testable
directly — reconstruct month-end holdings from the trade log and classify each by
point-in-time band.

## It does not rotate. It tilts the wrong way.

Shipped OM25 v4, share of the book in Nifty 100 names:

| | by count | by weight | universe | tilt |
|---|---|---|---|---|
| LARGE-led years | 29% | **29%** | 40% | **−12pp** |
| SMALL-led years | 29% | 35% | 40% | −5pp |

By count the book is **26-30% large in every single year, 2016 through 2026,
regardless of regime** — always about 7 of 25 names from the Nifty 100. The
composition is essentially a constant. And by weight the tilt is *more* negative
in large-led years, not less.

## Why: leading on average is not the same as producing the top performers

The tilt is only mildly in the score. Top-25 by vol-adjusted momentum against the
universe's own composition:

| regime | universe large | top-25 large | tilt |
|---|---|---|---|
| LARGE-led | 40% | 36% | −5pp |
| SMALL-led | 40% | 37% | −3pp |

So the ranking is close to cap-neutral and — the key point — **barely moves
between regimes.** It does not tilt toward large caps when large caps lead.

The reason is dispersion. Cross-sectional standard deviation of the 12-month
return:

| regime | LARGE band | MID band | ratio |
|---|---|---|---|
| LARGE-led years | 26% | 39% | **1.47x** |
| SMALL-led years | 42% | 48% | 1.13x |

A momentum rank selects the extremes of a cross-section, and extremes come from
the wider distribution. Even when the large-cap band leads *on average*, the
individual best twelve-month performers are still disproportionately midcaps,
because midcap outcomes are more spread out. **And the dispersion gap is widest
precisely in large-led years (1.47x against 1.13x)** — so the pull toward
midcaps is strongest exactly when large caps are winning.

The remaining gap between the score's −4pp and the book's −11pp is the portfolio
devices: the exit buffer holds names down to rank 45, so the book is a trailing
average of past top-25s and accumulates whatever is stickiest in the 25-45 band.

## Answer

**Partly, but much less than the argument assumes.** Large caps do enter the book
— about seven names at any time — and they are not excluded. But the ranking is
near cap-neutral, it does not shift toward large caps when large caps lead, and
the book's cap composition has been flat for eleven years across both regimes.
The self-adjusting mechanism is real in principle and close to inert in practice.

So in the untested scenario — a strong, large-cap-led cycle — the book would most
likely remain roughly 70% midcap and lag the leading band. That is inference from
mechanism, not measurement: Phase 11b established there is no strong large-cap-led
year in 2016-2026 to check it against.

**Caveats.** The score reconstruction here is pure vol-adjusted momentum, not the
shipped 50/50 blend with the capture ratio, so the −4pp is indicative rather than
exact. And every "LARGE-led" year in the sample is also a weak year, so the 1.47x
dispersion ratio may be a property of weak markets rather than of large-cap
leadership as such.

**What it changes.** Phase 11b concluded the book carries ordinary market-weakness
exposure rather than a cap bet. Phase 12 qualifies that: there *is* a persistent
structural midcap tilt of roughly 11pp against its own universe, it does not
respond to regime, and it cannot be relied on to self-correct. If the founder
wants large-cap-cycle protection, the ranking will not supply it — it would have
to be an explicit constraint, and nothing in this folder has tested one.

---

# Phase 13 — a capped sleeve for dropped names, and why the premise fails (2026-09-11)

Founder's idea: keep the core on Nifty 250 point-in-time and reserve 20-25% of
the book for **dropped** names, on the argument that a dropped name can surge and
NSE re-includes it only after the move. Structurally different from once-in — the
cap bounds exactly the exposure that produced once-in's −12.0% in 2025 — and a
different pool from the sleeve rejected in `mm_rebuild` §14, which drew from the
current 251-500 band.

## The portfolio test

| | fit 2016-2023 | subs | hold-out 2024→ | 2024 | 2025 | 2026 |
|---|---|---|---|---|---|---|
| **shipped OM25 v4** | **23.7% / 1.21 / −29%** | 0.66/1.68 | **28.3% / 1.21 / −23%** | +55.9 | +15.1 | +9.7 |
| core + 4 dropped (16%) | 21.3% / 1.09 / −28% | 0.63/1.48 | 23.5% / 1.12 / −20% | +50.8 | +12.3 | +4.4 |
| core + 5 dropped (20%) | 22.3% / 1.13 / −30% | 0.56/1.61 | 20.4% / 0.94 / −21% | +52.7 | +3.9 | +4.3 |
| core + 6 dropped (24%) | 23.0% / 1.18 / −30% | 0.61/1.65 | 24.0% / 1.12 / −21% | +63.2 | +4.3 | +5.2 |
| nifty250 once-in, uncapped | 20.9% / 1.04 / −31% | 0.33/1.64 | 20.7% / 0.84 / −28% | +55.0 | −5.1 | +13.6 |

**Every variant loses on both windows** — unlike once-in, which at least won the
fit window, so there is no selection-versus-regime ambiguity here. The cap does
work as designed (capped beats uncapped, 21-23% against 20.9%), just not enough.

One clarification this produces: `nifty250 once-in` (20.9% / 1.04) is far worse
than `nse500 once-in` (33.9% / 1.63). **Phase 7's headline was driven mainly by
the 251-500 band, not by the demotion-recovery mechanism.** Isolated, the dropped
names do not carry it.

## Why — the premise is true only in hindsight

Testing the mechanism directly, independent of any portfolio. Every
drop → re-inclusion round trip in Nifty 250:

- 175 round trips, 144 names, median **728 days** out of the index
- return while out: median **+71.7%** against Nifty 500's +22.7%
- **median excess +40.5%, 70% win rate, +14.9pp annualised**
- and it is back-loaded: only **13%** of the full-gap median return lands in the
  first half of the gap

So the founder's description is exactly right about these names. They surge, and
the surge is concentrated right before NSE brings them back.

**But that sample is conditioned on coming back.** Running it over *every* drop,
including the ones that never returned:

| cohort | n | 1y median | 2y median | **3y median** | 3y win |
|---|---|---|---|---|---|
| **ALL dropped (honest)** | **523** | **−11.5pp** | **−20.9pp** | **−28.2pp** | **35%** |
| later re-included | 175 (33%) | −1.0 | +10.2 | +15.2 | 57% |
| never re-included | 348 (**67%**) | −15.0 | −30.4 | **−37.2** | 24% |

**Only a third of dropped names ever come back. The median dropped name loses
28pp to the index over three years.** The surge is not a property of dropped
names — it is a property of the third that recovered, and *recovering is what
gets them re-included*. Re-inclusion is the surge, not a lagging acknowledgement
of it. There is no way to tell the two cohorts apart at the drop date.

This is the same conditioning error the folder opened with, arriving on the last
idea in it: a statistic computed over survivors, read as if it described the
population.

It also explains every earlier result. The capped sleeve loses because the cohort
it buys from has a −28pp median. once-in's ex-member sleeve showed +18.4% mean
trip return because the momentum rank does real filtering work on that cohort —
just not enough to beat staying inside the index. And Phase 8c's grace period
removed good and bad together because age does not separate the two cohorts
either.

**Verdict: rejected on both the portfolio test and the premise. MECHANICS
stands.**

## Phase 13b — what "back-loaded" means, and whether it can be captured

**The shape.** One median name, indexed to 100 at the day it leaves the index:

| elapsed | cumulative return | share of the eventual move |
|---|---|---|
| drop date | 0.0% | 0% |
| ~6 months (25% of the gap) | +5.5% | 8% |
| ~1 year (50%) | +9.2% | **13%** |
| ~18 months (75%) | +27.1% | 37% |
| re-inclusion (~2 years) | +72.8% | 100% |

It drifts for about eighteen months, then does most of its move in the last six.

**Why that shape is close to tautological.** NSE re-includes a name when its
market-cap rank has recovered, so the re-inclusion date is *defined* by the surge
having already happened. A case where the surge came after re-inclusion cannot
appear in the sample, because the surge is what causes the re-inclusion. The
back-loading is a property of how the sample is cut, not a rhythm to time.

**Is the book already capturing it? Yes — and well.** Among once-in's ex-member
entries in names that did later return:

| entry point in the gap | entries | mean trip return | win rate |
|---|---|---|---|
| first 25% (the drift) | 1 | +3.9% | 100% |
| 25-50% | 1 | −1.1% | 0% |
| 50-75% | 3 | +3.4% | 67% |
| **last 25% (the surge)** | **8** | **+138.6%** | 50% |

Median entry point: **79% of the way through the gap.** The momentum rank ignores
the drift and buys the surge, exactly as intended. The mechanism works.

**Why it still does not pay.** Those 13 entries are 7% of the sleeve's activity:

| | trips | mean | median | win |
|---|---|---|---|---|
| in names that later returned | 22 | +53.2% | +0.7% | 59% |
| **in names that never returned** | **301 (93%)** | +15.8% | +1.2% | 51% |

To collect those 13 entries the book took 310 others. Note both medians sit near
zero — the sleeve's return is a handful of outliers, not a broad edge. Momentum
detects a surge equally well in a name that will recover and one that will not,
and 93% of the time it is the latter.

So the +40.5% median excess is out of reach not because the entry timing is
wrong — the timing is right — but because **nothing observable at the surge
separates the 33% that recover from the 67% that do not.** Distinguishing them
would need information about *why* the business is recovering, which is the
fundamentals feed left open since `tasks/breakout_calls_2026`. That is the only
remaining avenue, and this folder has not tested it.

**Caveat:** 13 entries, 8 of them in the final quarter, is a very small sample.
The +138.6% is an illustration of where the money is, not an estimate of anything.

---

# Carried forward — input to a future multi-cap / flexi-cap book

Founder's call, 2026-09-11: no cap constraint is added to MM or OM25 v4. The
Phase 12 analysis is deferred as design input for a multi-cap / flexi-cap
portfolio, if and when that is built. What to pick up from here:

- **`lib/capbands.py`** builds disjoint point-in-time LARGE / MID / SMALL baskets
  (Nifty 100 / 250-minus-100 / 500-minus-250) from our own membership files, all
  equal-weight and survivorship-free. Reusable as the band definition.
- **`lib/rotation.py`** reconstructs month-end holdings from a trade log and
  classifies them by point-in-time band. Reusable for any cap-exposure audit.
- **The finding a flexi-cap design has to answer**: a cross-sectional momentum
  rank does not tilt toward a band when that band leads, because it selects
  extremes and extremes come from the wider distribution. Midcap dispersion runs
  1.47x large-cap dispersion in large-led years against 1.13x in small-led ones,
  so the pull toward midcaps is strongest exactly when large caps are winning. A
  multi-cap book that expects the ranking to rotate for it will not get that; the
  allocation has to be explicit.
- **The untested scenario**: a strong large-cap-led cycle does not exist in
  2016-2026 (Phase 11b). Any flexi-cap design aimed at it is reasoning from
  mechanism, not from backtest, and should be labelled that way.
- **Do not reuse**: the trailing-12m regime classifier of Phase 11 — it lags by
  most of a year (Phase 11b). Same-year classification is descriptive only and is
  not tradeable, so a live flexi-cap book needs a regime signal neither of these
  provides.

Nothing in this folder changes production. MM and OM25 v4 keep the Nifty 250
point-in-time universe and their `mm_rebuild/MECHANICS.md` rules.

## Phase 13c — why the ex-member books looked good anyway

A fair objection to Phase 13: if the ex-member cohort is −28pp, how did once-in
return 30.4% / 1.43 against the shipped book's 24.9% / 1.21?

**Because the book never bought the cohort.** On the *same 59 names* it actually
traded:

| | holding period | mean | median | win |
|---|---|---|---|---|
| cohort stat: buy at the drop, hold 3 years | 3 years | −11.5pp | **−37.3pp** | 29% |
| what the book did: buy on strength | **90 days** | **+18.4%** | +1.0% | 52% |

The momentum rank turns a −37pp median into a +18.4% mean on identical names. It
waits (median entry 79% of the way through the gap), buys only what has reached
the top 45, and is out in a quarter. The cohort statistic describes a buy-and-hold
nobody ran. **The filter is doing real work and Phase 13 should not be read as
saying otherwise.**

**But what the filter extracts is a tail, not a broad edge.** Ex-member trip
returns: p10 −25%, p25 −11%, **p50 +1%**, p75 +29%, p90 +72%, p95 +116%,
p99 +269%.

**The top 10 trips of 323 produce 68% of the sleeve's P&L** — V2RETAIL, GVT&D,
MTARTECH, CGPOWER, TTML, APARINDS, ELECON, RAMKY, UJJIVAN. The median ex-member
trip made +1%. For context the core sleeve is concentrated too (top 10 of 375 =
59% of core P&L), so fat tails are normal here; the ex-member sleeve is more
extreme, not categorically different.

**And that is exactly why it failed the hold-out.** An edge that is 68% ten trades
over eight years needs roughly one CGPOWER a year to stay alive. 2025 did not
supply one — the sleeve did −1% mean on a 39% win rate and the book did −12.0%.

This is a more sympathetic reading of once-in than Phase 10 gave it. Not "the idea
is worthless" but **"the edge is about one trade a year, and nothing in this data
can distinguish a real effect from having been lucky twice."** A thin tail is
precisely what a 2.7-year hold-out cannot validate and a fit window can flatter.
It is also why no amount of refitting rescued it: there is no parameter that
manufactures outliers.
