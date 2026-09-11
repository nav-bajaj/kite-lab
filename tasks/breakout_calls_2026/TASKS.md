# Tasks

Owners: 👤 founder · 🤖 agent.

## §0 — pre-committed pass criteria — SIGNED 👤 2026-09-11

Nothing in §3 onward runs until these are signed, so that the answer cannot be
tuned toward a number we liked after seeing it. Two sets, because the per-trade
and portfolio layers are separate product decisions and either can pass alone.

**Per-trade — does this earn the right to be published as calls?**

| # | Criterion | Value |
|---|---|---|
| C1 | Expectancy per trade, full span 2006-2026, after 0.2% slippage each side | ≥ 0.25R |
| C2 | Expectancy in each of 2006-2012 / 2013-2019 / 2020-2026 | ≥ 0.10R, none negative |
| C3 | Alpha per trade vs the benchmark over the same holding window | ≥ +1.5pp |
| C4 | Signal rate sustains a publishable cadence | ≥ 5 calls/month median, ≥ 1 in the worst year |
| C5 | Edge survives the honest entry — E1 (every pivot touch) not only E2 | C1 met under E1 |

**Portfolio — can it be a book a client holds?**

| # | Criterion | Value |
|---|---|---|
| P1 | CAGR, 2006-2026, price return | ≥ 18% |
| P2 | Maximum drawdown, **marked to market daily**, never realised-only | no worse than −35% |
| P3 | Sharpe (rf 5%), full span | ≥ 0.80 |
| P4 | Sharpe in each of 2006-2012 / 2013-2019 / 2020-2026 | ≥ 0.50 |
| P5 | Beats production L6 v2 over the same span on return **and** drawdown | both |
| P6 | Capacity at the chosen liquidity floor | ≥ ₹25 cr without >10% ADV participation |
| P7 | Parameter count, all-in (base anatomy, pivot rule, stop, trail, partials, time stop, slots, sizing, regime) | ≤ 10 |

**C4 is a target, not a kill criterion** (👤 2026-09-11: "number of signals can
be changed later, I have no idea what it will produce right now"). The signal
rate is a measured output that shapes the product — it sets how many calls we
publish and whether slots are ever full. §3 reports it; missing 5/month
re-scopes the calls product rather than failing the study. The "≥ 1 in the
worst year" half *is* a kill criterion, because it tests robustness, not
cadence. Every other criterion in §0 is a hard gate.

**The liquidity floor is turnover-scaled (F2)** — 👤 2026-09-11. A flat ₹10cr
applied point-in-time yields 690-722 names today but only 113 in 2006, because
nominal market turnover has grown ~6x; C2 and P4 would then compare a
large-cap-only early era against an all-cap recent era and report composition
as if it were edge stability.

The rule: ₹10cr in 2026 money, deflated by aggregate market turnover, so the
floor is ~₹1.6cr in 2006 and the universe holds at roughly 500-700 names in
every era. The deflator is built once in §1 from the bhavcopy store's own
aggregate daily turnover and frozen — it is data, not a parameter, and does
not count against P7.

Consequences to honour:
- The floor is a moving number. Any published figure states it as "₹10cr
  equivalent, turnover-scaled", never as a flat rupee threshold.
- Flat ₹10cr (F1) is reported alongside for 2020-2026 only, where the two
  nearly coincide, so the recent-window headline matches a floor we can state
  plainly.
- P6 (capacity) is evaluated at the *nominal* floor of each era, not the
  scaled one — a ₹1.6cr name in 2006 cannot carry a ₹25cr position, and the
  capacity answer must reflect that rather than the sample-size convenience.

Turnover and tax drag reported at every stage; no gate, but a candidate that
wins only on turnover-blind metrics is flagged. Trial count tracked for
deflation, per `om25_rebuild` precedent.

## §1 — data layer 🤖

- [x] **Widen the per-symbol layer — 1,193 symbols built, not the ~191
      estimated in PLAN.**  (DONE 2026-09-11) The spine's `prices/bhavcopy/` is index-members-only
      (1,326 files, driven by `kite_targets.csv`), so the gap is in the raw
      per-symbol export, not just the adjusted view. 2,398 symbols were ever
      eligible at the scaled floor over 2006-2026; 1,205 are exported, 1,193
      are not. **41% of the 2020-2026 eligible universe has no panel today.**
      Run `export_bhavcopy_series.py` with the ever-eligible list in place of
      `kite_targets.csv`, then `build_adjusted.py`. Source data is already in
      `bhavcopy_eq.parquet` — no fetching, but this roughly doubles the store.
      §2 must not run before this lands: an index-members-only tape reproduces
      exactly the composition bias this task exists to remove.
      **Result:** 2,519 series exported (14 with no rows), 2,519 adjusted.
      Delisted names carried: 290 → **560**. Panel coverage of the eligible
      universe is now **100% in all three eras** (1,093 / 1,125 / 1,562).
      Additive and verified: of the 1,340 pre-existing manifest entries,
      **zero** changed sha256; `bhavcopy/INFY.csv` and `adjusted_pr/INFY.csv`
      are byte-identical to before the run. `export_bhavcopy_series.py` gained
      one backwards-compatible hook (`extra_targets.csv`, absent → prior
      behaviour); the ever-eligible list is `data/master/extra_targets.csv`.
- [x] Build a point-in-time liquidity series: rolling median turnover per
      symbol per day, so the ₹10cr floor is applied as of the signal date and
      never as today's list.  (DONE — `lib/universe.py`)
      63-session rolling median, shifted one day so a name can never qualify on
      the session being traded. Deflator is a **trailing 252-session** market
      turnover mean, not calendar-annual: an annual deflator is itself
      look-ahead (in March 2020 you do not know 2020's full-year turnover), and
      a mean keeps the incomplete final year from distorting the anchor.
      Resulting floor: ₹0.53cr in 2006 → ₹3.16cr in 2020 → ₹8.91cr in 2026.
      Universe holds at 347-846 names per era vs 101-721 on a flat ₹10cr.
- [x] Carry delisted names to their last traded price (D-9). Assert that the
      universe on any 2020 date contains names that are gone by 2026.
      **GATE PASSED.** Share of each era's universe that has since stopped
      trading: 2008 42.8%, 2012 34.6%, 2016 21.9%, 2020 11.5%, 2022 8.4%.
      The competitor's book carries zero such names (4,707 of 4,718 have a
      2026 bar). This is the single structural advantage we hold over them and
      it is now demonstrated, not assumed.
- [x] QA: old-study store vs the new panels.  (DONE — and the framing in PLAN
      was wrong: exact reproduction was never achievable, because
      `nse500_data_merged/` is a different adjustment vintage, per the
      price-panel-vintage finding.)
      All 255 `trades_standard` entry dates compared. **Median ratio exactly
      1.0000** — no systematic shift — but dispersion widens going back:
      within 0.5% on 95% of 2021-2026 prices, 51% of 2016-2020, and only
      **34% of 2010-2015**. Eight names disagree by >10%, all corporate-action
      heavy (HEG 0.37, BSOFT 1.77, MFSL 1.42, SIEMENS 0.75, BEML, KARURVYSYA,
      BANKBARODA).
      **Consequence for §6:** `vcp_l6_study`'s tape is the stated comparison
      baseline, but in 2010-2015 the two stores disagree on two-thirds of
      prices. Any pre-2016 difference between our result and that study must
      be attributed to the store before it is attributed to method. The new
      store is the defensible one — built from NSE filings plus bhavcopy raw
      with an auditable per-row factor — so where they differ, it wins.

## §2 — signal tape 🤖

- [x] Port the `vcp_l6_study` base/pivot detector onto the spine.  (DONE) The anatomy
      is inherited, not re-derived (see PLAN scope boundary). Source recovered
      from commit `82d42ef` into `lib/vcp_reference.py` — the file had been
      archived out of the working tree.
      **Inherit the `standard_no_l6` tier, not `standard`.** That study's own
      finding 2 was that the L6 top-quartile gate subtracts (0.31R with it,
      0.45R without, on double the sample) because the trend template already
      enforces momentum and stacking 6-month momentum on top selects extended
      names. Carrying the gate forward would import a known-bad filter.
      Spec: fractal ±5-bar swing pivots, 2-6 contractions, first leg 10-50%,
      final leg < 12%, base 15-325 bars, prior advance ≥ 30%, vol dry-up 0.75,
      5-bar tightness < 7%, Stage-2 trend template on the breakout day.
- [x] Emit **every** pivot event, labelled, not only the ones that worked:  (DONE)
      - `E1` — price touched the pivot intraday (a resting stop-buy fills)
      - `E2` — close above the pivot confirmed (buy next open)
      - `failed_poke` — E1 fired, E2 never did
      The failed-poke share is a headline number in its own right; it is the
      quantity the competitor's backtest drops.
- [x] Sanity gate: failed-poke share materially non-zero.  **PASSED.**

**§2 result — 2,787 events, 829 symbols, 2006-2026** (`data/signals_standard_no_l6.csv`)

| | E1 (stop-buy at pivot) | E2 (next open after close) |
|---|---|---|
| events | 1,751 | 1,036 |
| per year, 2006-2012 | 56.0 | 31.4 |
| per year, 2013-2019 | 85.0 | 48.3 |
| per year, 2020-2026 | 109.1 | 68.3 |

- The E1 tape is **+69% larger** than E2. They are not the same trade set.
- **19.0% of E1 fills land on a base that never confirmed** — the failed
  pokes. This is the population the competitor's engine drops while keeping
  the E1 fill price.
- **52.9% of E1 fills happen on a bar that closed below the trigger.** More
  than half of stop-buy fills are on days that looked like breakouts
  intraday and were not by the close.

**Finding — the volume filter and the pivot fill are mutually exclusive.**
The inherited spec confirms a breakout with volume ≥ 1.5× the 50-day average.
That is an end-of-day quantity. E2's signal *is* the close, so it may use it;
a stop-buy triggering intraday cannot, because the day's volume does not exist
yet. Gating E1 on it produced **zero** E1 events in the first run — the bar
before a breakout is typically the dry-up bar. So E1 is placed on base anatomy
and the prior close alone, with no volume confirmation available to it.
This is not a modelling nuisance, it is the crux: you cannot have the pivot
fill price *and* the volume filter in the same trade. The competitor's default
setting takes both.

**C4 — missed on the median, and it is a product constraint, not a failure**
(C4 is a target per §0, not a kill criterion). E1 median **4/month** against a
5 target (mean 7.0); E2 median **2/month** (mean 4.2). The mean-median gap is
the point: signals bunch in strong tapes and vanish otherwise — **13% of
months produce zero E1 signals, 22% zero E2**. A "5 calls a month" promise is
not deliverable on this tape at this anatomy; an honest product either varies
the count or widens the screen. The "≥ 1 in the worst year" half passes:
2008 gives 3 E1 / 1 E2.

## §3 — per-trade measurement 🤖

- [x] Fixed reference exit (8% stop, 50DMA trail), no partials, so the entry
      comparison is clean. Per-trade stats under E1 and E2 separately.  (DONE)
- [x] Cut by year, base depth, base length, contraction count, hold time.
      (Sector / mcap / liquidity-decile cuts deferred to §4 — nothing in the
      anatomy cuts suggested they would change the verdict.)
- [x] R-multiple distribution.  (DONE)
- [x] Benchmark-matched alpha per trade vs NIFTY 500 over the same window.
- [x] **Gate C1-C5.**

**§3 result — 2,787 trades** (`data/trades_standard_no_l6.csv`)

| | E1 (stop-buy at pivot) | E2 (next open after close) |
|---|---|---|
| n | 1,751 | 1,036 |
| mean R | **0.467** | 0.324 |
| median R | −0.59 | −0.63 |
| win rate | 30.0% | 29.9% |
| avg win / avg loss | +22.50% / −5.47% | +22.74% / −6.21% |
| mean alpha | +1.70% | +1.10% |
| median hold | 15d | 16d |

| Gate | Target | E1 | E2 |
|---|---|---|---|
| C1 expectancy, full span | ≥ 0.25R | **0.467 PASS** | 0.324 PASS |
| C2 each era | ≥ 0.10R, none negative | 0.324 / 0.518 / 0.501 **PASS** | 0.144 / 0.441 / 0.325 PASS |
| C3 alpha per trade | ≥ +1.5pp | **+1.70% PASS** | +1.10% **FAIL** |
| C4 signal rate | ≥ 5/mo median | 4/mo (target, not kill) | 2/mo |
| C5 edge survives E1 | C1 under E1 | **PASS** | n/a |

**The per-trade layer passes on E1.** E2 fails C3 only.

**Headline — what dropping the failed pokes is worth.** Split the E1 tape:

| | n | mean R | win | mean return |
|---|---|---|---|---|
| base confirmed | 1,418 | 0.664 | 33.6% | +4.25% |
| failed poke | 333 | −0.371 | 15.0% | −2.70% |

Keeping the pivot fill price but dropping the failed pokes reads **0.664R
instead of 0.467R — a 42% overstatement of expectancy.** That is the direct
measurement of the competitor's entry bias, on our own honest tape.

**E1 beats E2 even after paying for the pokes** (0.467R vs 0.324R). The
cheaper fill more than covers a 19% failed-poke rate, so waiting for
confirmation is not the safer trade — it is the more expensive one. Worth
saying because it inverts the intuition, and because it means the honest
version of the competitor's entry is the *good* one; what is dishonest is
taking the price without the population.

**Tighter final contraction is the one anatomy feature that predicts.**
Mean R by final-contraction-depth quartile: **0.95R** (1.8-6.0%), 0.27R,
0.41R, 0.24R (9.0-12%). Contraction count does not discriminate (every trade
falls in one bucket at this tier). Base length does not (0.55 / 0.43 / 0.31 /
0.56). This is Minervini's own claim and it survives — it is the obvious §4
lever and the obvious way to raise the calls bar if C4 has to give.

**Shape is a lottery, and this is the product problem.** Median R is −0.59;
p25 and p10 sit at a full −1.02R stop. The top 5% of trades account for
**113% of total R** — the other 95% collectively lose money. 30% of calls win.
A published-calls product on this tape is honest only if it says that out
loud; a client who takes four calls and loses three has had a normal quarter.

**Five losing years of 21**: 2008 (−0.92R, n=3), 2011 (−0.58), 2015 (−0.03),
2022 (−0.32), 2024 (−0.13). The regime overlay in §5 should be tested against
these specifically.

*Not a finding:* the hold-time cut (0-2d −0.87R rising to 80d+ +8.2R) is
tautological — the 50DMA trail holds winners and cuts losers, so hold time is
an outcome, not a predictor. Recorded so nobody mistakes it for one later.

## §4 — exit ladder 🤖

The known binding constraint: `vcp_relook` moved 0.32R → 1.17R on the exit
alone. This is where the work should pay, and where overfitting is most likely,
hence the parameter budget in P7.

- [x] Grid: initial stop × trail × partial at +nR × breakeven × time stop.  (DONE)
- [x] Report the grid median, not only the best cell.  (DONE)
- [x] Walk-forward the exit choice.  (DONE)

**§4 result — 144 cells run, 108 tradeable** (`data/exit_grid.csv`,
`data/exit_walkforward.csv`)

`trail="none"` (36 cells) was dropped from every summary. It is not an exit
rule: with no trail a winner is held until it falls back to the *original*
stop, so hold time is unbounded and capital never frees. It printed a
seductive 4.16R median and 25R in the 2006-2012 era; a book cannot run it.

| | mean R |
|---|---|
| §3 reference exit (ma50, 8% structure stop) | 0.467 |
| **grid median, 108 tradeable cells** | **0.329** |
| grid best cell — ma150 / structure / 8% / no partial / no timestop | 1.062 |
| walk-forward, exit chosen only on the past | 1.114 |

**The trail is the axis that matters.** Median mean-R by trail: **ma150
0.587**, ma50 0.322, chandelier 0.266 (36 cells each). This reproduces
`vcp_relook`'s finding (0.32R → 1.17R) almost exactly, on a different
universe and twice the span.

**Partials hurt**: no-partial 0.422 median vs 0.323 (half at +3R) and 0.284
(half at +2R). Given the shape §3 found — top 5% of trades are >100% of total
R — cutting the right tail is the one thing you cannot afford. A time stop is
neutral (0.332 vs 0.326).

**Walk-forward is stable but is NOT independent validation.** Choosing the
best cell on data through year Y-1 and applying it to Y picks
`ma150|structure|0.08|None|None` in **all 16 years**, from the first decision
point in 2011. Walk-forward (1.114R) and hindsight (1.114R) therefore coincide
*by construction*. That is strong evidence the choice is not hindsight-
dependent — you would have picked it in 2011 and never revised — but it is not
an out-of-sample test of the number.

**Deflation — the honest brake.** The 108-cell search has cell-mean sd 0.211R
around a 0.422R grid mean. The best cell at 1.062R sits 3.03 sd above that,
but the Gumbel expected maximum of 108 equal draws is **1.068R**. The best
cell therefore does **not** exceed what pure search would produce. The
defensible number is the **ma150 axis median, 0.587R** — the effect is in the
trail, which is 36 cells wide, not in the winning cell. Quote 0.587R; quote
1.06R only with this paragraph attached.

**Year shape of the chosen exit**: mean 0.89R but **median year 0.29R**, six
negative years of sixteen, and the **top 3 years are 78%** of the summed
yearly mean. Trade level: win rate 27.5%, median R −1.02, top 5% of trades
= 101% of total R. The exit ladder raises expectancy; it does not make the
distribution any less of a lottery.

**Note for §6:** the competitor's own dial shows `ma150` *worse* than `ma50`
(12.06x vs 19.82x) — the opposite of our per-trade result. Their ma150 run
takes only 74 trades against 173, so a slower trail holds slots longer and
starves their 5-slot book. That is a portfolio-capacity effect masquerading as
an exit result, and it is precisely why §3 and §5 are measured separately.

## §5 — portfolio layer 🤖

The layer we have never built for this pattern, and the one that turns a
per-trade edge into a headline.

- [x] Book simulator: N slots, risk-based sizing (risk ÷ stop, capped), cash
      drag when slots are empty, no same-name double positions, participation
      cap vs ADV.
- [x] **Daily mark-to-market equity curve.** Realised-only drawdown is not
      reported anywhere in this task, including in passing.
- [x] Slot sweep N ∈ {3, 5, 8, 10, 15, 20} — this is the question that decides
      "how many calls", so it is measured, not assumed.
- [x] Signal-ordering robustness: when more signals fire than slots, randomise
      the tie-break and report the distribution across seeds. The competitor's
      single path takes 173 of 760; the spread across orderings is the honest
      error bar on any such number.
- [x] Regime overlay as a switch, off by default — `vcp_l6_study` finding 4 and
      `vcp_relook` disagree on whether it does anything, so it is tested, not
      assumed.
- [x] **Gate P1-P7.**

**§5 result — the book does NOT clear the bar.**

Slot sweep, E1 tape, ma150 exit, 1.5% risk, position capped at 1/N of equity,
12 random orderings per cell, drawdown marked to market daily:

| slots | CAGR | max DD | Sharpe | taken | avg open |
|---|---|---|---|---|---|
| 3 | 14.5% | 33.0% | 0.53 | 168 | 2.3 |
| 5 | 16.7% | 39.4% | 0.59 | 267 | 3.7 |
| 8 | 16.6% | 32.7% | 0.63 | 405 | 5.5 |
| **10** | **16.0%** | **30.5%** | **0.64** | 480 | 6.5 |
| 15 | 14.9% | 27.3% | 0.62 | 659 | 8.5 |
| 20 | 13.0% | 27.3% | 0.56 | 804 | 10.0 |

| Gate | Target | Result | |
|---|---|---|---|
| P1 CAGR | ≥ 18% | 16.7% best (16.0% at 10 slots) | **FAIL** |
| P2 max DD, marked to market | ≥ −35% | −30.5% at 10 slots | PASS |
| P3 Sharpe | ≥ 0.80 | 0.64 | **FAIL** |
| P4 era Sharpe | ≥ 0.50 each | 0.62 / 0.50 / 0.83 | PASS, marginal |
| P5 beats L6 v2 on both | both | below the MM/OM25 chained stack (~0.85 / ~20%) | **FAIL** |
| P6 capacity | ≥ ₹25cr | CAGR collapses to 7.2% at ₹25cr | **FAIL** |
| P7 parameters | ≤ 10 | ~14 all-in once base anatomy is counted | **FAIL** |

**Capacity is the hard stop.** The 10% ADV participation cap is never breached
— it binds by shrinking positions instead, so the book runs structurally
under-invested as size grows:

| capital | CAGR | max DD |
|---|---|---|
| ₹0.1cr | 16.4% | 31.5% |
| ₹1cr | 15.2% | 29.3% |
| ₹5cr | 11.0% | 28.3% |
| ₹25cr | **7.2%** | 24.3% |
| ₹100cr | 4.0% | 16.4% |

The edge lives in names too small to hold at size. That is not a tuning
problem; it is what the strategy is.

**Slot count answers "how many calls": about 10.** Sharpe peaks at 10 slots
(0.64) and the drawdown is lowest there among cells that still return
anything. Below 8 the book is too concentrated (39.4% DD at 5 slots); above
15 cash drag eats the return. Note this contradicts the competitor's 5-slot
default, which their own dial shows is return-maximising only because it
concentrates into the survivors.

**Ordering does not matter, which is good news.** Random tie-break 0.64
Sharpe vs tightest-base-first 0.64 (CAGR 16.0% vs 16.1%). No selection skill
is required to reproduce the result, and none is available either — so a
published call list does not need to rank its calls.

**The regime overlay hurts**: Sharpe 0.65 → 0.56, CAGR 16.3% → 14.5%. Third
independent look at this (after `vcp_l6_study` finding 4 and `vcp_relook`) and
the answer is settled — it is not a lever. Left off.

**Against the index it is a real portfolio; against ours it is not.** NIFTY
500 over the identical span: 11.4% CAGR, −64.3% DD, Sharpe 0.32. The book
doubles the index Sharpe and halves its drawdown. It just does not reach the
MM/OM25 stack we already run, and it cannot be run at size.

## §6 — decomposition against the competitor 🤖

Start from our honest tape and add their assumptions one at a time, to
attribute their 64.5% to its sources. Each step is one line in the table:

- [ ] honest baseline → + their universe → + pivot-price entry → + their exit
      → + realised-only drawdown → + the 2020-2025 window → + survivorship
- [ ] The residual, if any, is the part we cannot explain and must investigate.

## §7 — product decision 👤🤖

- [ ] Write RESULTS.md against §0 as signed, stating pass/fail per criterion.
- [ ] Recommendation: calls, portfolio, both, or neither — with the number of
      calls per month falling out of §5, not chosen.
- [ ] If anything ships, a published-figures note stating window, universe,
      basis, entry rule and drawdown definition, so we never have to add a
      `PROVISIONAL` badge later.
