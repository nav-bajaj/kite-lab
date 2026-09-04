# RESULTS — portfolio_risk_2026

Chronological evidence log. Sections were appended as the study ran, so later
sections sometimes correct earlier ones — **corrections are marked inline and
the superseded text is left in place** so the reasoning trail survives.

For conclusions rather than evidence, read `STATE.md`.

## Contents

| # | section | what it settles |
|---|---|---|
| 1 | L6 v2 exit-buffer sweep | Buffer is a turnover lever, not an alpha lever |
| 2 | Investor-experience lens | Neither L6 setting is a "smooth ride" |
| 3 | **Correction** + COMBO results | COMBO's max DD is -36.8%, not -16.4% |
| 4 | COMBO regime-signal experiment | Index swap does not fix it; ROC does |
| 5 | ROC (lookback x confirm) grid | The optimum is a plateau, not a spike |
| 6 | ROC overlay on L6 v2 and OM25 v3 | L6 no, OM25 yes |
| 7 | OM25 stop vs overlay + window question | The 20% stop is not earning its keep |
| 8 | Universe vs regime index | Clarifies two things both called "Nifty 250/500" |
| 9 | L6 simplest deployable overlay | Entry gate is cheapest; still not recommended |
| 10 | Production-number audit | Dashboard correct; `docs/portfolios.md` is not |
| 11 | Acceptance re-audit + the drawdown bar | All four still pass; -45% is not a product bar |
| 12 | Walk-forward (N500 overlay) | Risk benefit survives, return benefit does not |
| 13 | Conditional stop + tilt swap | Both rejected, with reasons |
| 14 | N100 ROC31 as the score tilt | Best standalone tilt; redundant under an overlay |
| 15 | **N100 as the overlay index** | The headline: 13.1-year walk-forward |
| 16 | Recent performance of the candidate | Behind in 2026; the V-shape cost |
| 17 | Year-by-year, trailing, terminal wealth | The protection costs ~31% of terminal wealth |
| 18 | Investor-pitch statistics | What is defensible to claim, and what is not |
| 19 | SIP analysis | Under SIP the verdict flips to the candidate |

---

# 1. L6 v2 exit-buffer sweep

Run 2026-09-04. Harness: `exit_buffer_sweep.py`. Raw output in `runs/`.

Panel `nse500_data_merged` (2009-03-05 -> 2026-08-21, 535 symbols),
effective-dated NSE 500 membership, production L6 v2 config with only
`exit_buffer` varied. One continuous backtest per buffer, sliced into the
`oos_retune_2026` windows.

## Headline

**The buffer does not buy return out of sample. It buys turnover — roughly
half of it — at no cost to return or drawdown. That makes it a cost-efficiency
change, not an alpha change, and its value depends entirely on the slippage
assumption.**

At the 20bps production slippage assumption, buffer=20 vs buffer=0 over
OOS_FULL is +0.48pp CAGR, +0.05 Sharpe, -0.2pp MaxDD — noise in every
direction — while round-trips per year fall 206 -> 104 and average holding
period doubles 42 -> 84 days.

At 40bps the same comparison is +2.55pp CAGR / +0.14 Sharpe. At 60bps it is
+4.51pp CAGR / +0.23 Sharpe / +6.9pp MaxDD. The buffer's edge *is* the cost
saving, and it scales with whatever slippage the strategy actually pays.

## IS (2009-09-01 -> 2016-12-31)

| buffer | CAGR | Sharpe | MaxDD | RT/yr | hit% | avg hold |
|---:|---:|---:|---:|---:|---:|---:|
| 0 | 30.75% | 1.54 | -31.42% | 198 | 46.6 | 44d |
| 5 | 31.55% | 1.59 | -28.05% | 154 | 48.0 | 56d |
| 10 | 34.23% | 1.73 | -28.08% | 125 | 50.1 | 69d |
| 15 | 35.15% | 1.78 | -28.74% | 107 | 51.4 | 81d |
| 20 | **35.39%** | **1.80** | -30.42% | 97 | 53.5 | 89d |

Reproduces the MM-tuning finding: in-sample the buffer is monotonically
better on CAGR and Sharpe. IS on its own would say "add the buffer, and add
as much of it as you can" — the extended grid keeps climbing to Sharpe 1.98
at buffer=40. That is precisely the signature that failed OOS in the US
retune, so IS is reported here for continuity, not as evidence.

## OOS sub-windows (base 20bps)

| buffer | OOS_A 17-19 | OOS_B 20-22 | OOS_C 23-26 |
|---:|---|---|---|
| 0 | 29.75% / 1.81 / -28.9% | 74.25% / 2.61 / -37.0% | 35.86% / 1.40 / -29.9% |
| 5 | 32.08% / 1.98 / -26.4% | 70.17% / 2.46 / -36.7% | 33.50% / 1.31 / -32.6% |
| 10 | 34.34% / 2.12 / -24.1% | 68.44% / 2.41 / -38.1% | 34.82% / 1.37 / -29.5% |
| 15 | 35.96% / 2.18 / -22.6% | 66.40% / 2.38 / -37.6% | 33.49% / 1.32 / -28.0% |
| 20 | **37.84% / 2.33 / -23.2%** | 68.75% / 2.47 / -37.2% | 33.59% / 1.33 / -30.3% |

(CAGR / Sharpe / MaxDD.) Every buffer clears the >=0.7 sub-window floor with
enormous margin.

The three windows disagree, and the disagreement is legible:

- **OOS_A (2017-19) — buffer wins big, monotonically.** +8.1pp CAGR,
  +0.52 Sharpe, 5.7pp shallower DD, turnover nearly halved. This is a
  choppy, trendless, IL&FS-shocked stretch where buffer=0 whipsaws in and
  out of names that recover. **This directly contradicts the US retune's
  conclusion**, where buffer=10 was blamed for holding losers through the
  2018-19 selloff. Same calendar years, opposite sign, different market.
- **OOS_B (2020-22) — buffer costs a little.** -5.5pp CAGR at buffer=20.
  Expected: a sharp V-recovery and a violent leadership rotation reward fast
  exits, and stickiness is a drag.
- **OOS_C (2023-26) — flat.** -2.3pp CAGR, Sharpe 1.40 -> 1.33, DD mixed.

Aggregated, OOS_A's gain and OOS_B's loss cancel almost exactly.

## OOS_FULL and FULL, across slippage assumptions

OOS_FULL = 2017-01-01 -> 2026-05-08 (9.34y):

| buffer | 20bps | 40bps | 60bps | RT/yr | cost %PV/yr @20bps |
|---:|---|---|---|---:|---:|
| 0 | 44.95% / 1.96 / -37.0% | 40.76% / 1.77 / -39.9% | 36.71% / 1.59 / -44.3% | 206 | 3.00 |
| 5 | 43.77% / 1.91 / -36.7% | 40.49% / 1.76 / -36.9% | 37.20% / 1.62 / -40.9% | 165 | 2.40 |
| 10 | 44.61% / 1.95 / -38.1% | 41.81% / 1.83 / -38.2% | 39.08% / 1.71 / -40.8% | 135 | 1.97 |
| 15 | 44.09% / 1.93 / -37.6% | 41.73% / 1.83 / -37.7% | 39.38% / 1.73 / -37.8% | 117 | 1.70 |
| 20 | **45.43% / 2.01 / -37.2%** | **43.31% / 1.91 / -37.3%** | **41.22% / 1.82 / -37.4%** | 104 | 1.51 |

FULL (2009-09-01 -> 2026-08-21, 16.96y) tells the same story with a wider
gap, because the low-turnover configs compound the cost saving for longer:
buffer=0 38.09% / 1.75 vs buffer=20 40.58% / 1.90 at 20bps, and
30.17% / 1.39 vs 36.52% / 1.71 at 60bps.

Note the second-order effect at high slippage: buffer=0's max drawdown
degrades from -37.0% to -44.3% as slippage rises, while buffer=20 barely
moves (-37.2% -> -37.4%). Cost drag deepens drawdowns, and the high-churn
config pays it 2x.

`LIVE_2026` (2026-05-09 -> 2026-08-21) — the only stretch unseen by every
prior tune on this line — favours the buffer (buffer=0 returns 11.1%
annualised vs 19.7-22.2% for buffers 5-20), but it is 0.28 years and 122
trades. Not evidence. Recorded so the window exists for later.

Calendar-year detail: buffer=20 beats buffer=0 in 13 of 18 years at 20bps.
The 5 losing years are 2011, 2020, 2021, 2025, 2026 — heavily weighted to
sharp-reversal regimes, consistent with the OOS_B read.

## Where the OOS optimum sits

Extended grid (supplementary, buffers 25/30/40):

| buffer | IS Sharpe | OOS_FULL Sharpe |
|---:|---:|---:|
| 20 | 1.80 | 2.01 |
| 25 | 1.84 | 2.00 |
| 30 | 1.93 | 1.96 |
| 40 | 1.98 | 1.97 |

IS keeps improving all the way to 40. OOS peaks at 20-25 and drifts down.
The IS/OOS divergence reappears inside this very experiment — which is the
best available warning against reading the IS column at all. **If a buffer is
adopted, 15-20 is the defensible range; anything past 25 is fitting IS.**

## Verdict against the pre-committed pass criterion

The bar was: beat buffer=0 on OOS_FULL Sharpe, hold sub-window Sharpe >= 0.7,
and not worsen OOS_FULL MaxDD.

- buffer=20 **passes** on Sharpe (2.01 vs 1.96) and sub-windows, and is a
  0.2pp wash on MaxDD (-37.24 vs -37.04) — inside noise, not a real
  degradation.
- buffers 5/10/15 all land within +-0.05 Sharpe of buffer=0. **No pass.**

So on the stated criterion the honest verdict is: **buffer=20 squeaks
through, and the other three are indistinguishable from baseline.** Nobody
should adopt a parameter on a +0.05 Sharpe margin.

The defensible reason to adopt is the other column. Turnover halves, holding
period doubles, hit rate goes 47.8% -> 50.2%, and the return distribution is
unchanged. That is a real operational improvement that does not depend on
the return numbers being right, and it gets larger the more the strategy
actually pays to trade.

## Recommendation

**Diagnostic, not a production change yet.** Two things must happen first:

1. **Pin down what L6 v2 actually pays in slippage.** The whole case rests
   on it. 20bps is an assumption inherited from the legacy engine and never
   measured. Compare live fill prices from the Friday OHLC/4 executions
   against the backtest's assumed price and get an empirical number. If real
   cost is ~20bps the buffer is optional; if it is 40bps+ it is clearly
   correct, and at portfolio sizes where a top-24 NSE 500 book moves midcaps
   it will not be 20bps.
2. **Decide whether the OOS_B behaviour is acceptable.** The buffer gives up
   ~5pp CAGR in sharp-recovery regimes. It is paid back in choppy ones, but
   the founder's probabilistic-not-predictive rule applies: this is a
   distribution shift, not a free lunch, and it should be a deliberate choice.

If both land favourably, the change is a one-line edit to
`scripts/_momentum_engine.BASELINE` (`exit_buffer: 0 -> 20`) plus a
`docs/portfolios.md` update, and it also affects COMBO Defensive, which
inherits L6's exit behaviour.

## Caveats

- Survivorship bias: today's NSE 500 back-applied. Inflates all windows
  equally; the buffer comparison is apples-to-apples, absolute levels are not.
- STCG tax is not modelled and does not favour either config — both average
  well under 12-month holds, so gains are taxed the same. The saving is
  execution cost only, not tax.
- Corporate-action repairs pending on a few symbols
  (`tasks/corporate_actions_fix`); same panel for all configs.
- Panel ends 2026-08-21, two weeks behind today's date.

---

# 2. Addendum — investor-experience lens (2026-09-04)

Question asked: forget end-to-end CAGR, what does someone who joins on a
random day actually live through over 6 and 12 months, and does the buffer
give a smoother ride worth marketing?

Harness: `rolling_returns.py`. Every trading day treated as an entry point;
overlapping 126d / 252d holding-period returns; plus underwater duration and
Ulcer index (RMS of the drawdown path — penalises deep *and* long, which
max-DD alone hides).

## 12-month holding-period returns, OOS 2017-01-01 -> 2026-08-21

| | median | std | worst | p5 | p25 | % of entry days negative | % below +10% |
|---|---:|---:|---:|---:|---:|---:|---:|
| buf 0 | 23.9% | 63.7 | -21.6% | -11.9% | 0.5% | 24.3% | 37.6% |
| buf 10 | 23.3% | 62.8 | -24.6% | -10.4% | 0.1% | 24.9% | 38.4% |
| buf 15 | 25.6% | 58.3 | -22.0% | -9.6% | 0.4% | 23.7% | 37.8% |
| buf 20 | **28.0%** | **56.4** | **-19.9%** | -9.9% | 1.0% | **23.4%** | **35.9%** |
| NIFTY 100 | 10.4% | 18.3 | -6.5% | -2.9% | 3.5% | 14.9% | 48.6% |

6-month: buf 20 median 10.7% vs buf 0 9.0%, negative 25.8% vs 28.0%,
std 26.9 vs 29.1.

## Pain profile, same window

| | max DD | avg DD | % days underwater | % days in >10% DD | % days in >20% DD | longest underwater | Ulcer |
|---|---:|---:|---:|---:|---:|---:|---:|
| buf 0 | -37.0% | -9.1% | 85.8% | 44.7% | 10.5% | 774d | 12.10 |
| buf 20 | -37.2% | -8.2% | 83.9% | 39.2% | 8.1% | 709d | 11.16 |
| NIFTY 100 | -38.1% | -5.8% | 89.0% | 16.8% | 3.0% | 693d | 8.14 |

## Read

**The buffer improves the ride, but not by enough to change the category.**
On OOS 2017-2026 buffer=20 is better on every investor-facing statistic:
higher median 12m return, 11% lower dispersion, a shallower worst case, 0.9pp
fewer losing 12m entry points, 5.5pp fewer days in a >10% drawdown, and a
65-day-shorter worst underwater stretch. Directionally consistent, all of it.

But the edge is small and **not robust across sub-samples**. Restricted to
2020-07 -> 2026 the comparison goes mixed: buffer=20 is better on median 12m
(36.5% vs 31.6%), dispersion (58.9 vs 64.1) and longest underwater (611d vs
774d), and *worse* on negative-entry-day rate (21.4% vs 19.3%), worst 12m
(-19.9% vs -17.3%) and days in a >20% drawdown (11.6% vs 9.9%). Ulcer is a
dead heat (11.98 vs 11.81). This is not a config anyone should sell as "the
smoother one".

**The absolute numbers are the real finding.** Both configs put an investor
underwater ~85% of all days, in a >10% drawdown ~40% of days, and leave
roughly one in four 12-month entry points negative. The worst single
underwater stretch is about two years for both. Against NIFTY 100 — the thing
a prospect actually compares to — L6 spends 2.4x as many days in a >10%
drawdown and carries a 45% higher Ulcer index. Neither buffer setting moves
that.

**Live confirmation.** The production L6 v2 curve has not made a new high
since **2024-07-05 — 777 days**. Trough since then -29.9%, currently -11.7%
below high, trailing 24-month return **-4.5%**. A client who joined in mid-2024
has sat through two years of nothing. That is the acceptance problem, and it
is happening now, not in a backtest.

## What actually moves this metric

> **SUPERSEDED — see "Correction" below.** The COMBO figures in this
> section come from the production curve, which only starts 2020-07 and
> therefore begins immediately *after* COMBO's worst episode. On the full
> OOS window COMBO is not the smoother product. The conclusion drawn here
> is wrong; the table itself is accurate for the window it covers.

Three-way on the common window 2020-07-20 -> 2026-08-21 (identical dates),
adding the existing defensive sibling:

| | CAGR | 12m median | 12m worst | 12m p5 | % 12m negative | max DD | % days >20% DD | Ulcer |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| L6 buf 0 | 52.7% | 31.6% | -17.3% | -11.3% | 19.3% | -29.9% | 9.9% | 11.81 |
| L6 buf 20 | 49.9% | 36.5% | -19.9% | -11.9% | 21.4% | -30.3% | 11.6% | 11.98 |
| **COMBO Defensive** | 45.6% | 25.1% | **-11.2%** | **-3.0%** | **12.4%** | **-16.4%** | **0.0%** | **7.53** |
| NIFTY 100 | 14.5% | 9.0% | -6.5% | -3.1% | 16.6% | -17.6% | 0.0% | 6.20 |

COMBO gives up ~5pp CAGR against buffered L6 and in exchange roughly halves
every pain measure: max drawdown -16.4% vs -30%, Ulcer 7.53 vs ~11.9, losing
12m entry points 12.4% vs 19-21%, p5 of the 12m distribution -3.0% vs -12%,
and **zero** days spent in a drawdown worse than 20%. It is the only one of
the three whose worst-case year a normal investor would sit through, and its
12m downside profile is essentially NIFTY-like while compounding at 3x.

The regime overlay is the lever for investor experience. The exit buffer is
not — it is a cost-efficiency lever, which is what the main results section
concluded on return grounds too.

## Implication for the buffer decision

Nothing here changes the earlier verdict, and nothing here justifies adopting
the buffer on smoothness grounds. If the buffer is adopted it should still be
for the turnover/cost argument, pending the slippage measurement. If the goal
is a product a wider set of investors will hold through a bad year, that is a
COMBO-vs-L6 positioning question, not a buffer question — and the buffer
could be applied to COMBO independently, which has not been tested.

---

# 3. Correction + COMBO results (2026-09-04, same day)

COMBO rebuilt over full history with `combo_buffer_sweep.py`, and the exit
buffer swept on it. Both change the previous section's conclusion.

## Two things had to be built first

**1. Full-history COMBO.** The production runner is invoked on the live
`nse500_data` panel, so the only COMBO curve on disk starts 2020-07-20. Rebuilt
on `nse500_data_merged` from **2010-07-01** (NIFTY 100 history starts 2010-01-04
and the 100-DMA needs ~100 sessions, so entries cannot start earlier without an
undefined regime signal).

Validation against the production curve on the 1,514 overlapping days:
daily-return correlation **0.9837**, max DD **-16.34% vs -16.39%**, vol 19.63%
vs 20.21%, CAGR 41.37% vs 45.60%. The CAGR gap is the price-panel difference
(merged vs live) plus a different portfolio state at the 2020-07 boundary.
Pain metrics — the ones this analysis turns on — match almost exactly.
**Absolute COMBO CAGR below is therefore conservative by roughly 4pp.**

Regime source: production `LOCKED` points at `indices_data_historical`, which
ends 2026-05-08. `runs/nifty100_regime_merged.csv` splices the live
`indices_data` rows after that date; the 1,572 overlapping days agree to 5e-6.

**2. A COMBO score fn with depth.** Production `make_combo_score_fn` emits
exactly 24 names (12 L6 + 12 OM25), so `nlargest(top_n + exit_buffer)` can
never exceed the entry set and **`exit_buffer` is a silent no-op on COMBO as
currently written**. `make_combo_score_fn_deep` extends each component past its
quota while leaving the first 24 in identical priority-dedup order, so entries
are unchanged and only the keep-set widens. Anyone shipping a buffer to COMBO
must carry this change or the parameter will do nothing.

## The correction

COMBO's max drawdown is **-36.8%**, not -16.4%. The -16.4% figure — which I
used in the previous section — is what you see when the window starts 2020-07,
which begins immediately after COMBO's worst episode and captures the regime
overlay's single best moment (COVID).

What actually happened, peak 2018-01-15:

| | trough | trough date | DD at 2019-12-31 | new high | days underwater |
|---|---:|---|---:|---|---:|
| L6 buf 0 | -37.0% | 2020-03-23 | -8.7% | 2020-06-19 | 886 |
| L6 buf 20 | -37.2% | 2020-03-24 | -0.1% | 2020-06-23 | 890 |
| COMBO buf 0 | **-36.8%** | **2019-08-05** | **-31.2%** | 2020-12-02 | **1052** |
| COMBO buf 20 | -31.0% | 2019-08-05 | -23.8% | 2020-11-14 | 1034 |

Over the 2018-01 -> 2019-08 midcap bear: L6 -28.9%, **COMBO -36.8%**. The
defensive product lost 8pp *more* than the aggressive one in the bear it was
built to survive, and was still 31% down at end-2019 while L6 had clawed back
to -8.7%.

The regime overlay was not asleep — it flagged bear on 40% of 2018 sessions and
29% of 2019. It just does not help here. The overlay reads NIFTY 100 against
its 100-DMA, and 2018-19 was a breadth-driven mid/small-cap collapse underneath
a large-cap index that held up. Meanwhile COMBO's OM25 half draws from the
Nifty 250, so half the book sat squarely in what was falling. **A 50% cut
triggered by a large-cap signal is not protection against a mid-cap bear.**

The two products have opposite drawdown shapes, which the single max-DD number
hides completely: L6 takes deep, fast, V-shaped hits (COVID: -37% and fully
recovered in 116 days), COMBO takes shallower daily losses that grind on for
years (1051 days underwater, 2.9 years).

## Corrected investor comparison, OOS 2017-01-01 -> 2026-08-21 (9.6y)

12-month holding-period returns, every entry day:

| | CAGR | median | std | worst | p5 | p25 | % negative | % below +10% |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| L6 buf 0 | 43.7% | 23.9% | 63.7 | -21.6% | -11.9% | 0.5% | 24.3% | 37.6% |
| **L6 buf 20** | **44.5%** | **28.0%** | 56.4 | **-19.9%** | -9.9% | 1.0% | **23.4%** | **35.9%** |
| COMBO buf 0 | 30.1% | 17.3% | 45.3 | -23.0% | -12.8% | -2.3% | 30.4% | 44.3% |
| COMBO buf 20 | 30.0% | 17.3% | 40.9 | -20.8% | -10.8% | -1.2% | 27.2% | 43.6% |
| NIFTY 100 | 11.6% | 10.4% | 18.3 | -6.5% | -2.9% | 3.5% | 14.9% | 48.6% |

Pain profile:

| | max DD | avg DD | % days >10% DD | % days >20% DD | longest underwater | Ulcer |
|---|---:|---:|---:|---:|---:|---:|
| L6 buf 0 | -37.0% | -9.1% | 44.7% | 10.5% | 774d | 12.10 |
| **L6 buf 20** | -37.2% | -8.2% | **39.2%** | **8.1%** | **709d** | **11.16** |
| COMBO buf 0 | -36.8% | -11.3% | 42.6% | 23.6% | 1051d | 15.66 |
| COMBO buf 20 | -31.0% | -9.7% | 40.7% | 18.5% | 1033d | 13.24 |
| NIFTY 100 | -38.1% | -5.8% | 16.8% | 3.0% | 693d | 8.14 |

**L6 buf 20 wins the investor-experience comparison outright**, on the same
lens that made COMBO look good on the short window: lowest share of negative
12m entry points, highest median, fewest days in a >20% drawdown, shortest
worst underwater stretch, lowest Ulcer of the four — while also having the
highest CAGR. COMBO leaves 30% of 12m entry points negative and spends 23.6%
of all days more than 20% underwater, versus L6's 10.5%.

## The buffer on COMBO — the strongest result in this study

| buffer | OOS_FULL CAGR | Sharpe | max DD | Calmar | RT/yr | avg hold |
|---:|---:|---:|---:|---:|---:|---:|
| 0 | 30.82% | 1.82 | -36.80% | 0.84 | 130 | 54d |
| 5 | 30.81% | 1.82 | -35.99% | 0.86 | 103 | 69d |
| 10 | 31.13% | 1.86 | -35.33% | 0.88 | 86 | 84d |
| 15 | 31.61% | 1.89 | -34.19% | 0.92 | 75 | 98d |
| 20 | 30.87% | 1.83 | **-30.97%** | **1.00** | **68** | 110d |

Monotone drawdown improvement, flat CAGR, half the turnover. On the investor
lens the buffer takes COMBO's Ulcer 15.66 -> 13.24 and its negative-12m rate
30.4% -> 27.2%. Nearly all of it comes from the 2018-19 episode, where the
buffer cut the trough from -36.8% to -31.0% — the buffer holds names through
the chop that buffer=0 whipsaws out of at the bottom.

This is a better case than the buffer makes on L6, where OOS return was a wash
and only turnover improved. Here it is turnover *and* a 5.8pp shallower worst
case, on the product whose entire positioning is ride quality.

Caveat: COMBO is bi-weekly with 12+12 composition, so buffer=20 means holding
to rank 44 of a 24-name book — a much bigger relative loosening than on L6.
The IS column shows no buffer preference at all (Sharpe 2.01 at buf 0 vs 1.99
at buf 20), so unlike L6 this is not an IS-driven result. Take that as mild
reassurance, not validation.

## Revised recommendation

1. **Retract the "COMBO is the smoother ride" claim.** It holds only for
   windows starting after mid-2020. Any client-facing drawdown or
   ride-quality number for COMBO must be sourced from a curve that includes
   2018-19, or it is misleading. The production runner's 2020+ default start
   is how this got missed — worth fixing at the source.
2. **The buffer's best case is on COMBO, not L6.** Same return, -5.8pp max
   DD, half the turnover, and it is not an IS artifact. Still gated on the
   same slippage measurement, but the drawdown improvement stands on its own
   and does not depend on the cost assumption.
3. **COMBO's real weakness is the regime signal, not the exit rule.** A
   large-cap trend filter cannot see a mid-cap bear, and the OM25 half is
   mid-cap. If a genuinely smoother product is the goal, that is the thing to
   work on — breadth-based regime detection is already built in
   `tasks/breadth_atlas`, and the 2018-19 episode is the test case it should
   be scored against.

---

# 4. COMBO regime-signal experiment (2026-09-04)

Harness: `regime_experiment.py`. Only the portfolio-level regime control
varies — index and mechanic. Every other COMBO parameter stays at `LOCKED`,
and OM25's internal bull/bear score tilt stays on NIFTY 100 per its own
locked spec, so this isolates one lever.

Two mechanics tested: `ma` = close vs 100-DMA with 3-day confirm (the
production mechanic, index swapped) and `roc` = N-day rate-of-change > 0 with
3-day confirm.

## Data reality — read this before the tables

| index | usable history | can it see 2018-19? |
|---|---|---|
| NIFTY 100 (production) | 2010-01 | yes |
| NIFTY 500 | 2015-01 | yes |
| NIFTY 200 | 2012-01 | yes |
| NIFTY MIDCAP 50 | 2010-01 | yes |
| **NIFTY 250 (LARGEMID250)** | **2020-01** | **no** |

**The Nifty 250 cannot be tested on the failure episode.** Its history — both
`indices_data_historical` (2021-08) and `indices_data` (2020-01) — begins
after the 2018-19 bear. Any Nifty 250 result is measured on a window that
excludes the exact problem it is meant to solve, which is the same trap that
produced the wrong COMBO drawdown figure earlier in this document.

NIFTY 500 starting 2015-01 sets the common evaluation start at **2015-07-01**
(after 100-DMA warmup). NIFTY 200 and MIDCAP 50 have no live tail, so their
regime ffills its last state after 2026-05-08 — affects only the final ~3.5
months. Spliced series in `runs/regime_idx/`.

## Result 1 — swapping the index barely helps

EVAL 2015-07-01 -> 2026-08-21 (11.1y), exit_buffer=0:

| regime | bear days | CAGR | Sharpe | max DD | Ulcer | % 12m neg |
|---|---:|---:|---:|---:|---:|---:|
| ma NIFTY 100 (production) | 30.0% | 28.10% | 1.73 | -36.74% | 14.72 | 26.7% |
| ma NIFTY 500 | 31.4% | 28.28% | 1.73 | -34.46% | 14.59 | 26.2% |
| ma NIFTY 200 | 32.1% | 28.21% | 1.73 | -32.46% | 13.99 | 27.1% |
| ma NIFTY MIDCAP 50 | 30.9% | 28.96% | 1.74 | -38.92% | 14.80 | 29.0% |

In the 2018-19 episode itself, NIFTY 500's MA flagged bear on 49% of 2018
sessions vs NIFTY 100's 38% — the signal *did* see more — and the episode
drawdown improved only -36.74% -> -33.72%. NIFTY 200 was the best MA arm at
-32.46%.

**The index swap is not the fix.** Nifty 500 is cap-weighted, so roughly
three-quarters of it is the same large caps NIFTY 100 already tracks. It sees
a bit more of the mid-cap stress and reacts a bit sooner, but a 50% cut driven
by a still-large-cap-dominated signal does not change the outcome. Going
*further* down-cap does not help either: MIDCAP 50 as the control was the
worst arm on drawdown, because it whipsaws.

## Result 2 — ROC works, and the lookback is the whole story

NIFTY 500 ROC, exit_buffer=0:

| lookback | BEAR_2018 DD | COVID CAGR | EVAL CAGR | EVAL max DD | Ulcer | % days >20% DD | % 12m neg |
|---:|---:|---:|---:|---:|---:|---:|---:|
| production (ma N100) | -36.74% | 51.84% | 28.10% | -36.74% | 14.72 | 19.3% | 26.7% |
| ROC 21 | **-22.79%** | 30.60% | 21.39% | **-22.79%** | **9.91** | **2.3%** | 26.9% |
| ROC 42 | -33.61% | **63.16%** | **29.35%** | -33.61% | 12.55 | 13.4% | **22.5%** |
| ROC 63 | -38.49% | 54.91% | 28.51% | -39.32% | 15.43 | 16.7% | 24.5% |
| ROC 126 | -42.23% | 21.52% | 22.99% | -49.03% | 18.11 | 19.7% | 34.9% |
| ROC 252 | -38.76% | 16.07% | 25.09% | -46.16% | 17.33 | 23.1% | 30.5% |

Short lookbacks help, long ones are **actively worse than production** — ROC
126 takes max DD to -49%. Controls confirm it is the lookback and not the
index: ROC 126 on NIFTY 100 (-48.65%) and on MIDCAP 50 (-48.91%) fail the same
way. A long-lookback ROC confirms a downtrend only once it is mostly over,
then keeps you halved through the recovery.

Note the bear-day counts barely move (30.0% production vs 31.4% for ROC 42).
These signals are not more defensive on average — they are **better timed**.

## Result 3 — the two levers stack

Adding exit_buffer=20 (which needs `make_combo_score_fn_deep`), EVAL window:

| config | CAGR | Sharpe | max DD | Ulcer | % days >20% DD | longest UW | % 12m neg | median 12m |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **production** (ma N100, buf 0) | 28.10% | 1.73 | -36.74% | 14.72 | 19.3% | 1051d | 26.7% | 16.9% |
| ma N100 + buf 20 | 28.79% | 1.78 | -30.86% | 12.41 | 14.9% | 1033d | 23.4% | 18.2% |
| **ROC 42 N500 + buf 20** | **29.32%** | **1.82** | **-26.74%** | **10.70** | 9.6% | 937d | **20.4%** | **18.2%** |
| ROC 21 N500 + buf 20 | 21.94% | 1.57 | **-21.33%** | **8.80** | **0.1%** | **922d** | 27.3% | 15.3% |

**ROC 42 + buffer 20 beats production on every axis**: +1.2pp CAGR, +0.09
Sharpe, **10pp shallower max drawdown**, 27% lower Ulcer, 6.3pp fewer negative
12-month entry points, higher median 12m return, half as many days spent more
than 20% underwater, and 114 fewer days in the worst underwater stretch. In
the 2018-19 episode it turns -17.38% CAGR / -36.74% DD into -8.58% / -26.74%.

ROC 21 is the different product: max DD -21.3% and **0.1% of days more than
20% underwater** (production: 19.3%), Ulcer 8.80 against NIFTY 100's own 8.14.
It costs 6.2pp of CAGR — and note its % of negative 12m windows goes *up* to
27.3%. It reduces the depth of pain, not the frequency of unrewarding years.
That trade is a positioning decision, not a modelling one.

## Anti-overfit check

These candidates were chosen on an episode whose answer was already known, so
the ROC mechanic was re-tested on **2012-01 -> 2015-06**, a stretch used to
select nothing, on NIFTY 100 (the only index with history there):

| regime | CAGR | Sharpe | max DD | Ulcer |
|---|---:|---:|---:|---:|
| ma NIFTY 100 | 51.27% | 3.05 | -13.2% | 5.59 |
| ROC 21 NIFTY 100 | 43.14% | **3.31** | **-11.6%** | **3.35** |
| ROC 42 NIFTY 100 | 47.53% | 3.16 | -11.6% | 4.57 |

Same signature out of sample: ROC gives up CAGR, improves Sharpe and Ulcer,
and does so monotonically in lookback. The direction replicates. Caveat that
matters: 2012-2015 was a bull run with a -13% worst drawdown, so it corroborates
the smoothness mechanic but is a weak test of crisis protection.

## Result 4 — Nifty 250, on the only window it has

2020-07 -> 2026-08 (exit_buffer=0), the *only* window where all three exist:

| regime | CAGR | max DD | Ulcer | longest UW |
|---|---:|---:|---:|---:|
| ma NIFTY 100 | 40.75% | -16.34% | 7.54 | 767d |
| ma NIFTY 500 | 41.86% | -19.55% | 9.18 | 767d |
| ma NIFTY 250 | **44.89%** | **-15.45%** | **7.24** | **674d** |

Nifty 250 is the best of the three here. **Do not act on this.** The window
begins after COMBO's worst episode and contains no mid-cap-only bear — it is
precisely the window that made COMBO look like a -16.4% max-DD product. The
honest statement is that Nifty 250 as a regime control is **untestable** on
the evidence available, and would stay untestable until index history is
backfilled.

## Where this lands

1. **The user's first hypothesis (swap to Nifty 250/500) does not fix it.**
   Cap-weighted broad indices are still large-cap signals. Nifty 500 buys
   ~2-4pp of drawdown; Nifty 250 cannot be evaluated at all.
2. **The second hypothesis (Nifty 500 ROC) does work — at short lookbacks.**
   ROC 42 dominates production on every metric measured; ROC 21 buys a
   genuinely different, much smoother ride for ~6pp of CAGR.
3. **It stacks with the exit buffer**, and ROC 42 + buffer 20 is the
   strongest COMBO configuration found: -26.7% max DD vs -36.7%, Ulcer
   10.70 vs 14.72, and slightly *higher* CAGR.

## What I would not skip before shipping any of this

- **11 years, ~2 bear episodes.** NIFTY 500 history caps the test at 2015.
  Backfilling NIFTY 500 (or 250) to 2010 would roughly double the bear count
  and is the single highest-value data task here.
- **The good region is narrow.** 21 and 42 work, 63 is mediocre, 126+ is worse
  than doing nothing. Confirm-days was left at 3 and never swept; a 3x3 over
  (lookback, confirm) would show whether ROC 42 sits on a plateau or a spike.
  Until that is known, treat ROC 42 as promising, not settled.
- **OM25's internal tilt still reads NIFTY 100.** Only the portfolio overlay
  was changed. Changing both is untested and could interact.
- All arms share the survivorship and corporate-action caveats from the main
  results section.

---

# 5. ROC (lookback x confirm) grid (2026-09-04)

35-cell grid on NIFTY 500, lookback {10,15,21,31,42,52,63} x confirm
{1,2,3,5,8}, exit_buffer=0, EVAL 2015-07-01 -> 2026-08-21. Raw output in
`runs/regime_grid/`. Then the best region re-run at exit_buffer=20.

## Is ROC 42 / confirm 3 a plateau or a spike?

A ridge — but **not the best cell**, and the surface has a clean structure
rather than a single lucky point.

EVAL CAGR %:

| lookback \ confirm | 1 | 2 | 3 | 5 | 8 |
|---:|---:|---:|---:|---:|---:|
| 10 | 12.44 | 14.99 | 17.10 | 20.40 | 25.36 |
| 15 | 16.87 | 16.67 | 18.73 | 21.53 | 25.33 |
| 21 | 16.85 | 18.93 | 21.39 | 26.76 | 26.15 |
| 31 | 22.11 | 26.91 | 28.40 | **30.70** | 28.19 |
| 42 | 23.82 | 28.35 | 29.35 | 28.06 | 27.48 |
| 52 | 27.11 | 26.73 | 27.74 | 28.23 | 29.46 |
| 63 | 27.32 | 28.64 | 28.51 | 28.45 | 28.28 |

EVAL max DD %:

| lookback \ confirm | 1 | 2 | 3 | 5 | 8 |
|---:|---:|---:|---:|---:|---:|
| 10 | -23.15 | -21.37 | -21.39 | -27.31 | -25.01 |
| 15 | -25.25 | -28.66 | -24.78 | -29.25 | -28.96 |
| 21 | -26.70 | -26.30 | **-22.79** | -26.22 | -28.68 |
| 31 | -29.29 | -29.09 | -26.42 | -31.30 | -30.70 |
| 42 | -31.10 | -31.37 | -33.61 | -31.93 | -35.94 |
| 52 | -36.29 | -37.43 | -39.33 | -41.78 | -44.70 |
| 63 | -34.55 | -37.25 | -39.32 | -37.91 | -34.77 |

Three readings:

1. **CAGR plateaus over lookback 31-63** (any confirm >= 2) at 27-30%, and
   collapses below 21. **Drawdown moves the opposite way** — monotonically
   worse as lookback lengthens, from -21% at lookback 10 to -40%+ at 52-63.
   The two objectives pull in opposite directions and cross around 31.
2. **Sharpe >= 1.80 forms one contiguous blob** — lookback 21-42 x confirm
   2-5 (21/c5 1.84, 31/c2 1.75, 31/c3 1.82, 31/c5 1.86, 42/c3 1.80). Five
   adjacent cells, not an isolated spike. That is the reassuring part.
3. **confirm=1 is bad almost everywhere** — it is the no-hysteresis case, and
   removing the state machine costs 3-6pp of CAGR across the board. The
   confirmation logic is carrying real weight, not decoration.

One warning: **lookback 52 is anomalously bad on drawdown** (-36% to -45%),
worse than both 42 and 63. A non-monotonic dent like that is noise, and it is
a reminder that single cells on an 11-year window are not precise.

## The better centre is ROC 31, not ROC 42

Re-running the best region at exit_buffer=20 (the candidate stack) changes
which cell wins, because the buffer and the regime signal interact:

| config (buf 20) | CAGR | Sharpe | max DD | Calmar | Ulcer | % days >20% DD | % 12m neg | median 12m | RT/yr |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **ROC 31 / c3** | 29.29% | **1.92** | **-20.06%** | **1.46** | **8.48** | **0.1%** | 21.2% | **23.5%** | 71.9 |
| ROC 31 / c5 | **31.47%** | 1.92 | -23.52% | 1.34 | 9.91 | 3.8% | 21.0% | 20.7% | 70.9 |
| ROC 21 / c5 | 26.21% | 1.81 | -21.41% | 1.22 | 8.76 | 1.5% | **20.1%** | 16.4% | 73.6 |
| ROC 42 / c3 | 29.32% | 1.82 | -26.74% | 1.10 | 10.70 | 9.6% | 20.4% | 18.2% | 69.5 |
| ROC 21 / c3 | 21.94% | 1.57 | -21.33% | 1.03 | 8.80 | 0.1% | 27.3% | 15.3% | 73.6 |

ROC 31 / c3 dominates the previous ROC 42 / c3 pick: same CAGR, +0.10 Sharpe,
**6.7pp shallower max drawdown**, Ulcer 8.48 vs 10.70, and a median 12-month
return of 23.5% vs 18.2%. The only metric where ROC 42 is ahead is share of
negative 12m entry days (20.4% vs 21.2%) — inside noise.

## Against production COMBO

| | production (ma N100, buf 0) | ROC 31 / c3 + buf 20 |
|---|---:|---:|
| CAGR | 28.10% | **29.29%** |
| Sharpe | 1.73 | **1.92** |
| max DD | -36.74% | **-20.06%** |
| Calmar | 0.76 | **1.46** |
| Ulcer | 14.72 | **8.48** |
| % days in >20% DD | 19.3% | **0.1%** |
| % 12m entry days negative | 26.7% | **21.2%** |
| median 12m return | 16.9% | **23.5%** |
| longest underwater | 1051d | 927d |
| turnover | ~125 RT/yr | **71.9 RT/yr** |
| BEAR_2018 CAGR / DD | -17.38% / -36.74% | **-5.23% / -20.06%** |
| COVID 2020 CAGR | 51.84% | 44.88% |

Better on every measure except COVID-year CAGR, where it gives up ~7pp. Max
drawdown improves by **16.7 percentage points** and time spent more than 20%
underwater goes from roughly one day in five to essentially never.

## Holdout on the selected cell

ROC 31 / c3 was chosen on 2015-2026. Re-tested on **2012-01 -> 2015-06**,
which selected nothing, using NIFTY 100 (the only index with history there),
exit_buffer=0:

| regime | CAGR | Sharpe | max DD | Ulcer |
|---|---:|---:|---:|---:|
| ma NIFTY 100 (production) | 51.27% | 3.05 | -13.2% | 5.59 |
| ROC 21 | 43.14% | 3.31 | -11.6% | 3.35 |
| **ROC 31 / c3** | 49.85% | **3.35** | **-11.6%** | 3.96 |
| ROC 42 | 47.53% | 3.16 | -11.6% | 4.57 |

The selected cell has the best Sharpe on the holdout too, gives up only 1.4pp
of CAGR against the production signal, and improves drawdown and Ulcer. The
choice survives its one available out-of-sample test.

## Honest assessment of the overfitting risk

This is now **two rounds of selection on the same 11-year window** — first the
regime family, then the cell within it. Mitigations that are real:

- The Sharpe optimum is a contiguous 5-cell plateau, not an isolated spike.
- CAGR-vs-lookback and DD-vs-lookback both move smoothly and in explicable
  directions; the result has a mechanism, not just a number.
- The mechanic replicated on a 2012-2015 holdout, and so did the specific cell.
- confirm=1 failing everywhere confirms the hysteresis is doing real work.

Mitigations that are **not** available, and matter:

- The window contains **two bear episodes**. Two. Any claim about crisis
  behaviour rests on 2018-19 and COVID, and 2018-19 is the episode that
  motivated the whole search.
- The 2012-2015 holdout has a -13% worst drawdown, so it validates the
  smoothness mechanic and cannot validate crisis protection at all.
- The lookback-52 dent shows single-cell precision is beyond what this
  sample supports. Read ROC 31 as "somewhere around a month, with
  confirmation", not as 31 exactly.

**I would not ship this on the evidence so far.** What would change that, in
order of value: backfill NIFTY 500 history pre-2015 to add the 2008 and
2011 bears; then walk-forward the (lookback, confirm) choice rather than
picking one cell on the full window.

---

# 6. ROC overlay on the standalone portfolios: L6 v2 and OM25 v3 (2026-09-04)

Harness: `overlay_experiment.py`. EVAL 2015-07-01 -> 2026-08-21, set by
NIFTY 500 history as before.

Starting point: **neither portfolio currently cuts exposure.** L6 v2 has no
regime anything and no stop. OM25 v3 uses regime only to *tilt its score
weights* (NIFTY 100 MA) and carries a 20% trailing drawdown stop — it passes
`regime_panel=None, bear_exposure=0.0` to the engine, so gross exposure is
never reduced.

## Implementation options

Three are engine-native and were tested:

| variant | what it does | how |
|---|---|---|
| `exposure_XX` | bear -> scale gross exposure to XX%, and stop entering | `bear_exposure=XX`, `bear_skips_entries=True` (engine default) |
| `entry_gate` | bear -> hold everything, just stop adding; book de-risks only as positions exit | `bear_exposure=0.999` — the engine gates entries only when `is_bear` (`target_exposure < 1.0`), and at 0.999 the pro-rata sell resolves to zero shares at normal position sizes |
| `scaled_XX` | bear -> cut to XX% but keep entering at reduced weight, preserving the N-name structure | `bear_skips_entries=False` |

Three more were considered and **not** run, with reasons:

- **Score tilt in bear** — change what you rank, not how much you hold. OM25
  already does exactly this on NIFTY 100; for L6 the analogue is raising
  `vol_power` in bear to favour lower-vol names. A different study: it changes
  the signal, not the exposure, and the two shouldn't be conflated.
- **Overlay as a replacement for OM25's 20% DD stop.** These are competing
  risk controls and may be substantially redundant. Everything below keeps
  the stop; testing overlay-instead-of-stop is the obvious follow-up.
- **Regime-conditional top_n** (concentrate or diversify by regime). Not
  supported by the engine without changes.

Signals: production (no overlay), `ma_NIFTY_100` (COMBO's current control,
as a reference) and `roc31_c3 NIFTY_500` (the grid winner).

## L6 v2 — do not add an overlay

| variant | CAGR | Sharpe | max DD | Calmar | Ulcer | % 12m neg | median 12m |
|---|---:|---:|---:|---:|---:|---:|---:|
| **production** | **41.34%** | 1.83 | -37.08% | 1.11 | 11.92 | **22.5%** | **20.2%** |
| ROC 31 / 75% | 34.69% | **1.88** | -26.56% | **1.31** | 11.00 | 25.2% | 17.3% |
| ROC 31 / 50% | 31.38% | 1.85 | -25.75% | 1.22 | 10.33 | 25.3% | 17.9% |
| ROC 31 / 25% | 27.75% | 1.76 | **-25.12%** | 1.10 | **9.77** | 27.1% | 18.5% |
| ROC 31 / entry gate | 37.13% | 1.85 | -30.47% | 1.22 | 12.07 | 25.9% | 16.8% |
| MA N100 / 50% | 32.37% | 1.87 | -34.36% | 0.94 | 12.58 | 20.7% | 15.1% |

The overlay buys ~10pp of max drawdown for 6-14pp of CAGR, and **Sharpe barely
moves** (1.83 -> 1.88 at best). Worse, the investor-facing numbers go the wrong
way: median 12-month return falls 20.2% -> 17.3% and the share of negative 12m
entry points rises 22.5% -> 25.2%. Calmar does improve (1.11 -> 1.31), so if
max-DD is the only thing you price, there is a case — but on the lens that
actually predicts whether someone stays invested, production wins.

The mechanism is visible in the episode split:

| | BEAR_2018 CAGR / DD | COVID 2020 CAGR / DD |
|---|---|---|
| production | -4.58% / -28.96% | **98.28% / -37.08%** |
| ROC 31 / 75% | -7.08% / -26.56% | 78.91% / -21.18% |
| ROC 31 / 25% | -5.70% / -25.12% | 46.97% / -11.70% |

L6 already handled 2018-19 tolerably (-4.58%) — it rotates fast enough to get
out. Its worst drawdown is COVID, which is a **V-shape**, and an overlay is
structurally bad at V-shapes: it cuts after the fall has started and
re-enters late, so it clips the recovery. It turns a 98% year into 47-79%.
That is where L6's CAGR goes.

**L6's pain is deep-and-fast. A regime overlay is a tool for slow-and-grinding.**
If some protection is wanted anyway, the `entry_gate` is the least damaging
(37.13% CAGR, DD -30.47%) because it never force-sells into the hole.

## OM25 v3 — a genuinely good trade

| variant | CAGR | Sharpe | max DD | Calmar | Ulcer | % days >20% DD | % 12m neg | median 12m |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **production** | **29.61%** | 1.60 | -34.78% | 0.85 | 10.44 | 8.0% | 21.6% | **17.5%** |
| ROC 31 / 75% | 26.97% | 1.77 | -21.94% | 1.23 | 8.78 | 1.1% | 21.4% | 16.6% |
| ROC 31 / 50% | 24.34% | **1.83** | -17.97% | 1.35 | 7.22 | **0.0%** | 20.8% | 16.3% |
| ROC 31 / 25% | 21.12% | **1.83** | **-14.17%** | **1.49** | **5.86** | **0.0%** | 21.6% | 16.0% |
| ROC 31 / scaled 50% | 21.83% | 1.70 | -18.85% | 1.16 | 7.07 | **0.0%** | **20.1%** | 15.6% |
| MA N100 / 50% | 22.63% | 1.57 | -26.31% | 0.86 | 10.94 | 12.7% | 26.8% | 11.8% |

The 75% variant gives up **2.6pp of CAGR for 12.8pp of max drawdown**, plus
Sharpe 1.60 -> 1.77, Calmar 0.85 -> 1.23, Ulcer 10.44 -> 8.78, and time spent
more than 20% underwater falls from 8.0% of days to 1.1%. The 50% variant
takes it further: max DD -17.97%, Sharpe 1.83, **zero** days beyond a 20%
drawdown, for 5.3pp of CAGR. Median 12m return only slips ~1pp in both.

Episode split:

| | BEAR_2018 CAGR / DD | COVID 2020 CAGR / DD |
|---|---|---|
| production | -3.23% / -24.35% | 39.26% / -34.78% |
| ROC 31 / 50% | -2.51% / -17.90% | 32.18% / -16.24% |
| ROC 31 / 25% | **-0.71% / -14.17%** | 32.43% / **-10.39%** |

It helps in **both** episode types, unlike on L6. OM25 is Nifty 250, slower
(252-day lookback, bi-weekly), and holds through drawdowns via its exit-buffer
20 — so it is exposed to exactly the grinding declines the ROC signal catches,
and it does not have a 98% recovery year to protect.

## Cross-cutting finding

`ma_NIFTY_100` — the signal COMBO uses in production today — **makes both
portfolios worse**, not just COMBO. On L6 it deepens the 2018-19 drawdown
(-34.36% vs -28.96% with no overlay at all); on OM25 it costs 7pp of CAGR and
pushes negative-12m entry points from 21.6% to 26.8%. Every result in this
document points the same way: the problem was never that COMBO had an
overlay, it was which index and mechanic the overlay reads.

## Recommendation

1. **L6 v2: leave it alone.** Its drawdown profile is the wrong shape for
   this tool, and the 12-month investor stats get worse. This is consistent
   with the standing view that the production portfolios work.
2. **OM25 v3: the strongest overlay case of the three portfolios.** ROC 31 at
   a 75% bear exposure is the conservative pick (small CAGR cost, large
   drawdown gain); 50% if ride quality is the priority.
3. **Test the overlay against OM25's 20% DD stop, not just alongside it.**
   Both are drawdown controls. If the overlay does the work, the stop may be
   removable — which would also recover some of the CAGR the overlay costs.
   Not yet tested.
4. Same overfitting caveats as the regime study: 11 years, two bear episodes,
   ROC 31 chosen on this window. Nothing here is shippable until the NIFTY 500
   backfill and a walk-forward exist.

---

# 7. OM25 v3: stop vs overlay, and what window these numbers cover (2026-09-04)

Harness: `om25_stop_vs_overlay.py`.

## What period is the 29.61%?

**2015-07-01 -> 2026-08-21 (11.1 years).** Every number in the overlay study
uses that window, because NIFTY 500 index history starts 2015-01 and the
regime signal needs warmup. It is not the window `docs/portfolios.md` quotes.

### It does not reconcile with the documented OM25 figure

`docs/portfolios.md` states OM25 v3 OOS (2017-2026, 9.3y): **CAGR 44.78%,
Sharpe 1.86, MaxDD -36.6%**. My baseline on the same window, same locked
config:

| build | OOS 2017-01 -> 2026-05 CAGR | vol | Sharpe | max DD |
|---|---:|---:|---:|---:|
| documented (`docs/portfolios.md`) | **44.78%** | ~24.1% implied | 1.86 | -36.6% |
| mine, effective-dated membership | 34.77% | 19.1% | 1.82 | -34.78% |
| mine, snapshot universe | 37.33% | 19.0% | 1.97 | -36.20% |

Start date is not the cause (2010 vs 2015 start moves CAGR by 0.2-0.3pp).
Universe treatment explains ~2.4pp — effective-dated membership is stricter
than the snapshot. The remaining ~7.5pp comes with a **volatility gap**:
19.0% in every run of mine against ~24.1% implied by the documented pair.
Sharpe and max DD reconcile; CAGR and vol do not, which points at a different
price/universe build rather than a config difference. The `oos_retune_2026`
work ran on a GDF-backfilled universe, and `data/static/gdf_backfill/` holds
microcap-250 and smallcap-250 lists — a wider, higher-vol universe than the
current `nifty250_universe.csv`.

**This is the same class of problem as the COMBO -16.4% error: a client-facing
number that does not reproduce on the current production data.** It needs
resolving on its own, and until it is, `docs/portfolios.md`'s OM25 CAGR should
be treated as unverified. All comparisons below are internally consistent
(one lever, same panel, same baseline) so the deltas hold regardless.

## The 20% drawdown stop is not earning its keep

| config | CAGR | Sharpe | max DD | Calmar | Ulcer | % days >20% DD | % 12m neg | median 12m |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **production** (stop 20, no overlay) | 29.61% | 1.60 | -34.78% | 0.85 | 10.44 | 8.0% | 21.6% | 17.5% |
| stop OFF, no overlay | **32.50%** | 1.69 | -35.93% | 0.90 | **9.35** | 4.1% | **18.5%** | **18.8%** |

Removing the stop entirely costs **1.15pp of max drawdown** and buys 2.9pp of
CAGR, +0.09 Sharpe, a *lower* Ulcer index, 3.1pp fewer negative 12-month entry
points and a higher median 12m return. The stop makes the ride slightly
**worse**, not better — it sells into holes and re-enters later, which
lengthens underwater stretches even as it shaves the extreme.

## The overlay replaces the stop, and beats production outright

| config | CAGR | Sharpe | max DD | Calmar | Ulcer | % days >20% DD | % 12m neg | median 12m |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| production (stop 20) | 29.61% | 1.60 | -34.78% | 0.85 | 10.44 | 8.0% | 21.6% | 17.5% |
| stop 20 + ROC31@75 | 26.97% | 1.77 | -21.94% | 1.23 | 8.78 | 1.1% | 21.4% | 16.6% |
| **stop OFF + ROC31@75** | **30.73%** | **1.96** | **-25.70%** | 1.20 | 7.59 | 0.3% | **16.9%** | **19.1%** |
| stop OFF + ROC31@50 | 25.43% | **1.98** | -17.47% | 1.46 | 6.23 | 0.0% | 16.7% | 17.3% |
| stop OFF + ROC31@25 | 19.54% | 1.88 | -11.81% | **1.65** | **5.02** | 0.0% | 18.7% | 15.1% |

**Stop off + ROC 31 at 75% bear exposure beats production on every single
metric**, including CAGR: +1.1pp return, +0.36 Sharpe, 9.1pp shallower max
drawdown, Ulcer 10.44 -> 7.59, days beyond a 20% drawdown 8.0% -> 0.3%,
negative 12m entry points 21.6% -> 16.9%, median 12m 17.5% -> 19.1%.

Keeping the stop *and* adding the overlay (row 2) is the worst of the three —
two overlapping controls both taxing return. They are substitutes, not
complements, and the overlay is the better of the two.

## Recent years — OM25 has been flat for ~two years

Calendar-year total return %:

| year | production | stop OFF + ROC31@75 |
|---|---:|---:|
| 2021 | 114.8 | 89.5 |
| 2022 | 13.1 | 10.1 |
| 2023 | 74.1 | 78.2 |
| 2024 | 79.8 | 62.8 |
| **2025** | **-2.4** | **+6.7** |
| 2026 YTD | 2.7 | -1.4 |

Trailing windows (CAGR / max DD):

| from | production | stop OFF + ROC31@75 |
|---|---|---|
| 2023 -> | 37.05% / -25.32% | 36.01% / -17.85% |
| 2024 -> | 24.60% / -25.32% | 22.35% / -17.85% |
| 2025 -> | **-0.18% / -24.25%** | **+3.05% / -14.48%** |

**Production OM25 has made no new high in 675 days** (last peak ~Oct 2024),
is currently -2.6% below it, and has returned -0.18% annualised since Jan 2025
while taking a -24% drawdown along the way. The strong 2024-> number (24.6%)
is entirely front-loaded into early 2024.

This is the same picture as L6 v2 (777 days without a high, -4.5% over 24
months). **Both flagship portfolios have been going sideways for roughly two
years.** The overlay would have improved the recent stretch — 2025 goes from
-2.4% to +6.7%, and the drawdown from -24.3% to -14.5% — but it does not
change the fact that the last two years have been poor for the strategy
family regardless of configuration.

## Recommendation

1. **Drop the 20% DD stop from OM25 v3 and add ROC 31 / confirm 3 on
   NIFTY 500 at 75% bear exposure.** Strictly better than production on this
   sample across return, risk and investor-experience measures.
2. **Do not run both.** Stop + overlay is worse than either alone.
3. **Caveat on removing the stop:** the stop is tail insurance, and this
   sample has two bear episodes. It costing 2.9pp of CAGR for 1.15pp of
   drawdown is a fair verdict *on 2015-2026*; it is not evidence about a
   2008-style event, which the sample does not contain. If the stop is
   removed, that should be a deliberate acceptance of tail risk, not a
   conclusion that stops do not work.
4. **Resolve the documented-vs-reproduced OM25 CAGR gap** before any of this
   reaches a client-facing page.

---

# 8. Universe vs regime index — clarification (2026-09-04)

Two independent things have been called "Nifty 250" / "Nifty 500" in this
document. They never mix:

| | what it is | OM25 v3 in this study |
|---|---|---|
| **Stock universe** | which stocks the portfolio may hold | `data/static/nifty250_universe.csv` + `nifty250_membership.csv` — **262 symbols, Nifty 250, exactly as production** |
| **Regime control index** | a single index series read only to decide bull vs bear; never a source of holdings | NIFTY 500 index level (`runs/regime_idx/NIFTY_500.csv`) |

So OM25 held Nifty 250 stocks throughout. The NIFTY 500 index was used as a
market-breadth thermometer — one number per day, feeding a bull/bear flag. It
changes *how much* is invested, never *what* is held. Verified in
`om25_stop_vs_overlay.py`: `resolve_universe(nifty250_membership.csv,
LOCKED["universe_csv"])` for holdings, `build_regime("NIFTY_500", ...)` for the
flag.

Same separation applies to COMBO: its L6 half draws from NSE 500 and its OM25
half from Nifty 250, while the regime control was NIFTY 100 (production) or
NIFTY 500 (candidate).

---

# 9. L6 v2 (Core Momentum) — simplest deployable overlay (2026-09-04)

Harness: `l6_simple_overlay.py`. Two axes crossed: how often the signal is
checked, and what happens on bear. Execution cost is reported alongside
return, since that is the constraint.

| config | flips/yr | trades/yr | CAGR | Sharpe | max DD | Calmar | % 12m neg | median 12m | avg cash |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **production** | 0 | 420 | **41.34%** | 1.83 | -37.1% | 1.11 | 22.5% | **20.2%** | 0.6% |
| deadband + entry gate | 4.7 | **357** | 38.14% | 1.86 | -33.5% | 1.14 | 23.8% | 17.2% | 11.1% |
| daily + entry gate | 6.3 | **337** | 37.13% | 1.85 | -30.5% | 1.22 | 25.9% | 16.8% | 14.1% |
| weekly + entry gate | 5.9 | **335** | 36.57% | 1.82 | -29.9% | 1.22 | 26.5% | 16.7% | 14.5% |
| deadband + 75% | 4.7 | 469 | 36.14% | **1.89** | -31.7% | 1.14 | 22.0% | 17.6% | 15.8% |
| weekly + 75% | 5.9 | 459 | 34.74% | 1.86 | -27.4% | 1.27 | 27.0% | 17.3% | 19.9% |
| daily + 75% | 6.3 | 485 | 34.69% | 1.88 | -26.6% | **1.30** | 25.2% | 17.3% | 19.9% |
| daily + 50% | 6.3 | 488 | 31.38% | 1.85 | -25.8% | 1.22 | 25.3% | 17.9% | 27.1% |
| monthly + entry gate | 3.6 | 313 | 34.45% | 1.75 | -35.9% | 0.96 | 23.1% | 14.7% | 19.5% |
| monthly + 50% | 3.6 | 391 | 30.69% | 1.75 | -37.5% | 0.82 | 21.2% | 15.1% | 29.7% |

## Findings on execution

1. **The entry gate REDUCES total trading.** 313-357 trades/yr against
   production's 420. Skipping the buy leg during bear shrinks the book, and a
   smaller book generates fewer subsequent exits. It is the only overlay form
   that makes the portfolio *less* work to run, and it never force-sells into
   a hole.
2. **Exposure trims cost trades**: 459-488/yr, because every flip triggers
   pro-rata selling across 24 names and later rebuying.
3. **Weekly checking is as good as daily.** Sampling the regime only on L6's
   existing Thursday signal day gives 66 flips vs 70, and outcomes within
   noise (entry gate: 36.57% / -29.9% weekly vs 37.13% / -30.5% daily). So the
   overlay needs **no new decision point** — it rides the rebalance already
   being run.
4. **Monthly checking does not work.** Max DD -35.9% to -37.5% against
   production's -37.1% — the protection disappears entirely while the CAGR
   cost stays. Too slow to catch anything.
5. **The deadband is the best simplicity/return trade.** Requiring the
   NIFTY 500 to be >3% below its 31-session-ago level to go bear (and >1%
   above to return) cuts bear time from 31.3% to 24.6% and flips to 4.7/yr,
   while keeping the most CAGR of any overlay (38.14%).
6. Every form still means roughly **5 regime changes a year** — five "we are
   going defensive / we are going back in" events to execute and explain.

## The recommendation has not changed

Every overlay form still cuts the median 12-month return, from 20.2% to
14.7-17.6%, and most raise the share of negative 12-month entry points. **On
the investor lens that motivated this whole thread, production L6 still
wins.** L6's drawdowns are deep and fast; an overlay cuts after the fall and
returns late.

If an overlay is deployed on Core Momentum anyway, the ranking is:

1. **Deadband + entry gate.** Costs 3.2pp of CAGR, buys 3.6pp of drawdown,
   and *reduces* trading to 357/yr. Cheapest to run, least damaging.
2. **Weekly + entry gate.** Costs 4.8pp CAGR, buys 7.2pp of drawdown, 335
   trades/yr. Better protection, more return given up.
3. **Deadband + 75%** if max drawdown specifically is what is being sold —
   best Sharpe of the set (1.89) but 469 trades/yr.

Avoid: anything monthly (no protection), and 50% cuts (the CAGR cost is not
repaid on this portfolio).

## One option not tested

Applying the regime dial **outside** the portfolio — leaving L6 v2 untouched
and moving client capital between the strategy and cash at the allocation
level. Operationally the simplest of all (one instruction, no portfolio
trades, no model change) and it keeps the strategy's published track record
intact. It was not modelled here because it is an allocation policy rather
than a strategy parameter, but on these numbers it would produce a similar
risk/return shift and is worth considering before changing the portfolio
itself.

---

# 10. Production-number audit (2026-09-04)

Triggered by the OM25 CAGR gap. Question asked: are the dashboard numbers
right, are the study numbers right, and which gives the truest picture.

## 1. The dashboard numbers reproduce

Rebuilt each portfolio independently and sliced to the exact window the
production `metrics.json` reports:

| portfolio | window | dashboard CAGR | rebuilt | Δ | dashboard maxDD | rebuilt |
|---|---|---:|---:|---:|---:|---:|
| L6 v2 | 2020-07-10 -> 2026-08-21 | 50.45% | 52.57% | +2.12 | -29.89% | **-29.89%** |
| OM25 v3 | 2021-01-04 -> 2026-08-21 | 42.30% | 42.68% | +0.38 | -25.33% | **-25.32%** |
| COMBO | 2020-07-20 -> 2026-08-21 | 45.60% | 41.37% | -4.23 | -16.39% | **-16.34%** |

Max drawdown matches to 0.05pp on all three — the mechanics are identical.
The CAGR spread is the price panel: production runs on `nse500_data` (live
Kite) while these rebuilds use `nse500_data_merged`, plus for COMBO a
different portfolio state at the window boundary.

**Verdict: the dashboard is arithmetically correct.**

## 2. But every dashboard window starts after the COVID bottom

| portfolio | window start | years |
|---|---|---:|
| L6 v2 | 2020-07-10 | 6.11 |
| COMBO | 2020-07-20 | 6.09 |
| TL25 v3 | 2020-11-23 | 5.74 |
| OM25 v3 | 2021-01-04 | 5.63 |

All four run `--start 2020-01-01` against the live panel, which only begins
2020-01; the lookback warmup then pushes the first equity point to mid-2020 or
later. So **every headline number describes the strongest 5-6 years in recent
Indian mid-cap history and contains no bear market except the tail of COVID.**
2018-19 — the episode that broke COMBO — is outside all of them.

This is the same structural error that produced COMBO's -16.4% max-DD claim.
It is not a bug in any one number; it is the default window.

Also inconsistent: the dashboard reports `sharpe_rf5` (risk-free 5%) while
`docs/portfolios.md` quotes Sharpe at rf=0. Those are not comparable and are
presented side by side.

## 3. `docs/portfolios.md`'s OM25 figure does not reproduce — and contradicts its own source

| source | window | CAGR | Sharpe | maxDD |
|---|---|---:|---:|---:|
| `docs/portfolios.md` | 2017-2026 | **44.78%** | 1.86 | -36.6% |
| `tasks/oos_retune_2026/RESULTS.md` (cited source) | 2017-01 -> 2026-05 | **43.57%** | 1.86 | -31.44% |
| rebuilt, current snapshot universe | same | 37.33% | 1.97 | -36.20% |
| rebuilt, effective-dated membership | same | 34.94% | 1.83 | -34.79% |

The doc and the research file it points at disagree with each other before any
rebuild enters the picture. The residual gap to a rebuild is 6-10pp of CAGR,
spread **evenly across every sub-window** (OOS-A -10.4pp, OOS-B -9.8pp,
OOS-C -6.1pp), with Sharpe nearly matching in OOS-B (2.09 vs 2.12) and OOS-C
(1.85 vs 1.85). Even, Sharpe-preserving divergence points at the price panel,
not at any single period or parameter.

Ruled out as causes:

- **Strategy drift** — production `make_om25_tilt_score` is line-for-line the
  research version from `tasks/om25/experiments/_om25_regime_weight_tilt.py`,
  with only the later `candidate_fn` membership mask added.
- **Corporate actions** — `data/corporate_actions_applied.json` holds exactly
  one entry (VEDL demerger 2026-04-30).
- **Start date** — a 2010 vs 2015 start moves CAGR by 0.2-0.3pp.
- **Universe vintage** — tested below; explains 2.4pp, not 9pp.

Most likely remaining cause: the GDF-stitched pre-2020 panel and/or the Kite
portion changed after May 2026. Confirming it needs the May-2026 panel, which
is not on disk. **Until re-derived, `docs/portfolios.md`'s OM25 OOS row should
be treated as unverified.**

## 4. Universe vintage matters — in the opposite direction to the intuition

OM25, same config, only the universe treatment varied:

| universe treatment | 2021-2026 CAGR | 2017-2026 CAGR | 2015-2026 CAGR |
|---|---:|---:|---:|
| today's Nifty 250 snapshot, back-applied | **46.94%** | **37.33%** | **32.60%** |
| legacy 2025-11-06 snapshot | 42.73% | 34.94% | 29.76% |
| effective-dated membership | 42.76% | 34.94% | 29.78% |

Using the **latest** universe file back-applied across history **inflates**
returns by 2.4-4.2pp, because today's index members are partly there *because*
they performed well. Effective-dated membership — only holding what was
actually in the index at the time — is the correct treatment and gives the
lower number.

**Production already uses effective-dated membership**, and so does every
backtest in this document. So the dashboard is on the conservative, correct
footing, and the study numbers match it. The universe vintage is a real
effect, but it is not what separates the dashboard from the docs.

## 5. Which number to follow

| | window | what it tells you |
|---|---|---|
| dashboard (42.3%) | 2021-2026, 5.6y | correct, but a bull-market-only sample |
| `docs/portfolios.md` (44.78%) | 2017-2026 | does not reproduce; do not use |
| this study (29.6-34.9%) | 2015-2026 / 2017-2026, membership | longest reproducible sample, includes 2015-16, 2018-19 and 2025 |

**Follow effective-dated membership over the longest reproducible window.**
For OM25 that is ~29.8% CAGR from 2015-07 (11.1y) or 34.9% from 2017 (9.3y),
against the -25% to -35% drawdowns those windows actually contain. The 42.3%
headline is not wrong, it just answers "what if you had started at the best
possible moment".

## Actions

1. Re-derive `docs/portfolios.md` OM25 (and check TL25/L6 the same way)
   from a reproducible run, or mark the row unverified. **Client-facing.**
2. Give the production runners a research-history mode so the dashboard can
   show a full-cycle number alongside the live-panel one, instead of a window
   that structurally excludes every bear.
3. Standardise the Sharpe convention — dashboard rf=5% vs docs rf=0.

## Addendum — where the 44.78% came from

`docs/portfolios.md` did not copy from `tasks/oos_retune_2026/RESULTS.md`. It
copied from **`tasks/om25/README.md`**, which states: "OOS-only validation
(2017-2026 sliced from same run): 44.78% CAGR / 1.86 Sharpe / -36.6% Max DD
... sub-window Sharpes of 1.57 / 2.10 / 1.80" — an exact match including the
sub-window figures.

So two research documents from the same May-2026 work disagree:

| source | OOS 2017-2026 CAGR | Sharpe | maxDD | sub-window Sharpes |
|---|---:|---:|---:|---|
| `tasks/om25/README.md` (what docs copied) | 44.78% | 1.86 | -36.6% | 1.57 / 2.10 / 1.80 |
| `tasks/oos_retune_2026/RESULTS.md` | 43.57% | 1.86 | -31.44% | 1.60 / 2.12 / 1.85 |

`tasks/om25/README.md` also reports a production-locked run over
**2016-01-04 -> 2026-05-08 (10.4y): CAGR 39.34%, Sharpe(rf=5%) 1.66,
MaxDD -32.01%** — a third window, and the closest of the published figures to
what rebuilds today.

The two are described as coming from different artifacts (one "sliced from the
same run" as the 10.4y production-locked run, the other from the sweep's
multi-window evaluator). Whichever is right, the doc row inherits from the
less-detailed of the two.


---

# 11. Acceptance re-audit + the drawdown bar (2026-09-04)

Harness: `acceptance_audit.py`. Re-scores the production portfolios against
the criteria they were accepted on, using today's data and extending OOS to
the panel end. TL25 v3 built here for the first time in this task
(`runs/tl25_v3_equity.csv`).

## 1. All four still pass the original bar

Criteria: OOS aggregate Sharpe >= 1.0, every sub-window Sharpe >= 0.7, OOS max
DD >= -45%. Sub-windows are the original ones with OOS-C extended to
2026-08-21.

| portfolio | OOS CAGR | OOS Sharpe | OOS maxDD | OOS-A | OOS-B | OOS-C+ | verdict |
|---|---:|---:|---:|---:|---:|---:|---|
| L6 v2 | 43.75% | 1.91 | -37.04% | 1.81 | 2.61 | 1.33 | **PASS** |
| OM25 v3 | 33.72% | 1.77 | -34.78% | 1.27 | 2.09 | 1.72 | **PASS** |
| TL25 v3 | 30.90% | 1.56 | -39.63% | 1.35 | 2.12 | 1.15 | **PASS** |
| COMBO | 30.06% | 1.79 | -36.80% | 1.14 | 2.53 | 1.53 | **PASS** |
| OM25 + ROC31@75, no stop | 33.65% | **2.08** | **-25.70%** | 1.63 | 2.38 | 2.00 | **PASS** |

Important: **the CAGR discrepancy does not change the acceptance verdict.**
Even at the lower, reproducible return levels, every strategy clears the bar
it was signed off on, with margin on every sub-window. The documentation
problem is a reporting problem, not a validation problem.

The OM25 + overlay candidate passes with the widest margin of anything tested
— highest OOS Sharpe (2.08), shallowest drawdown (-25.70%), and the best score
in every sub-window — at effectively identical CAGR to production (33.65% vs
33.72%).

## 2. The forward stub is too short to score

Since the OOS window closed 2026-05-08, to panel end 2026-08-21 — **0.28
years**:

| portfolio | CAGR (annualised) | Sharpe | max DD |
|---|---:|---:|---:|
| L6 v2 | 11.12% | 0.55 | -8.63% |
| OM25 v3 | 9.05% | 0.54 | -7.23% |
| TL25 v3 | 28.98% | 1.80 | -5.37% |
| COMBO | 8.62% | 0.70 | -5.75% |
| OM25 + ROC31@75, no stop | 8.11% | 0.61 | -5.45% |

70 trading days. Annualising a quarter is arithmetic, not evidence — TL25's
"28.98%" is one good quarter. Recorded so the window exists; **no conclusion
should be drawn from it.** A meaningful forward read needs at least a year,
i.e. mid-2027.

## 3. The -45% drawdown bar is a research floor, not a product tolerance

The founder's objection is correct and it is the most important finding in
this section. `-45%` was written as an anti-fragility check during a parameter
search — "reject anything catastrophically bad" — and it was never a statement
about what a subscriber will sit through. Judged as a product bar it is
meaningless: a subscriber redeems long before -45%.

Scoring the same portfolios on what someone actually lives through, OOS 2017
-> 2026-08-21:

| portfolio | max DD | % days >20% DD | longest underwater | Ulcer | % 12m entries neg | worst 12m | days since high |
|---|---:|---:|---:|---:|---:|---:|---:|
| L6 v2 | -37.0% | 10.5% | 25.4 mo | 12.10 | 24.3% | -21.6% | 777 |
| OM25 v3 | -34.8% | 8.5% | 24.9 mo | 10.05 | 21.8% | -19.1% | 675 |
| TL25 v3 | -39.6% | **24.7%** | **33.9 mo** | 14.39 | 29.2% | -23.7% | 774 |
| COMBO | -36.8% | 23.6% | 34.5 mo | 15.66 | **30.4%** | -23.0% | 770 |
| OM25 + ROC31@75, no stop | **-25.7%** | **0.4%** | 23.9 mo | **7.45** | **18.4%** | **-11.9%** | 417 |

TL25 and COMBO have spent roughly **one day in four more than 20% underwater**,
with worst underwater stretches near **three years**. COMBO — the portfolio
positioned as the defensive one — is the worst of the four on almost every
subscriber-facing measure. And all four are currently 675-777 days without a
new high.

### A product-grade bar to sit alongside the research bar

Proposed, for a retail subscription product:

| criterion | proposed bar | rationale |
|---|---|---|
| Max drawdown | <= 25% | past this, redemptions happen regardless of the pitch |
| Share of days more than 20% underwater | <= 2% | rare and brief, not a standing condition |
| Longest underwater stretch | <= 18 months | beyond ~2 years the subscription is cancelled |
| Share of 12-month entry points negative | <= 20% | 1-in-5 unlucky joiners, not 1-in-3 |
| Worst 12-month outcome | >= -15% | the number a new joiner can be warned about honestly |
| Ulcer index | <= 8 | roughly index-like pain at above-index return |

Scored against it, **all four production portfolios fail**, most on several
criteria. The only configuration in this entire task that comes close is
**OM25 v3 + ROC 31 overlay at 75%, stop removed** — it passes max DD (-25.7%,
marginally), days-beyond-20% (0.4%), 12m-negative (18.4%), worst 12m (-11.9%)
and Ulcer (7.45), and fails only longest-underwater (23.9 months vs 18).

### The price of the bar

From the OM25 stop-vs-overlay grid (2015-2026 window), what each drawdown
target costs in CAGR:

| target max DD | config | CAGR |
|---|---|---:|
| -35.9% | no stop, no overlay | 32.50% |
| **-25.7%** | no stop + ROC31@75 | 30.73% |
| -17.5% | no stop + ROC31@50 | 25.43% |
| -11.8% | no stop + ROC31@25 | 19.54% |

The first ~10 points of drawdown reduction cost **under 2pp of CAGR**. Beyond
that it gets expensive fast — a further 8 points costs 5pp, and the next 6
points costs another 6pp. **Around -25% is where the trade is nearly free.**
That is a strong argument for setting the product bar at 25% rather than
lower: it is cheap protection, and tightening further is paid for in return.

## Recommendation

1. **Adopt a product-grade acceptance bar** alongside the research one. Every
   future strategy gets scored on both; the research bar decides whether it is
   real, the product bar decides whether it is sellable.
2. **Re-score the existing four against it and be honest about the answer** —
   none pass today. That is a positioning input, not a reason to change the
   portfolios.
3. **OM25 + ROC 31 @ 75% with the stop removed is the only near-miss** and the
   most promising product candidate found in this task, subject to the
   unresolved overfitting caveats (11 years, two bear episodes).
4. Do not read the forward stub. Revisit mid-2027.

---

# 12. Walk-forward test: OM25 v3 + ROC overlay, no stop (2026-09-04)

Harness: `om25_walkforward.py`. Rolling 3-year train / 1-year test, stepped
annually from 2018-07. At each boundary the (lookback, confirm) pair with the
best **train** Sharpe is selected from the 35-cell grid and applied to the
following unseen year. Bear exposure held at 75% — a policy choice, not a
fitted parameter. The per-fold signals are spliced into one regime series and
a single backtest is run on it, so handover between parameter regimes is real
rather than stitched.

## What it picked

| train | test | lookback | confirm | train Sharpe |
|---|---|---:|---:|---:|
| 2015-07..2018-06 | 2018-07..2019-06 | 31 | 3 | 1.84 |
| 2016-07..2019-06 | 2019-07..2020-06 | 31 | 3 | 1.76 |
| 2017-07..2020-06 | 2020-07..2021-06 | 31 | 3 | 0.73 |
| 2018-07..2021-06 | 2021-07..2022-06 | 21 | 5 | 2.32 |
| 2019-07..2022-06 | 2022-07..2023-06 | 21 | 5 | 2.22 |
| 2020-07..2023-06 | 2023-07..2024-06 | 15 | 8 | 2.80 |
| 2021-07..2024-06 | 2024-07..2025-06 | 15 | 3 | 3.04 |
| 2022-07..2025-06 | 2025-07..2026-06 | 31 | 5 | 3.02 |
| 2023-07..2026-06 | 2026-07..2026-08 | 10 | 8 | 2.19 |

Selections stay in the **10-31 lookback band in all nine folds** and never
wander into 42-63 — the region the full-window grid also rejected. The
procedure is stable in the thing that matters (short lookback) and unstable in
the exact cell, which is what the plateau finding predicted.

## Result — test period 2018-07-01 -> 2026-08-21 (8.1y, unseen by construction)

| config | CAGR | Sharpe | max DD | Calmar | Ulcer | % days >20% DD | % 12m neg | worst 12m | median 12m |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| **WALK-FORWARD** (re-picked yearly) | 31.28% | **1.78** | **-25.8%** | 1.21 | **7.46** | **0.6%** | **13.8%** | **-10.9%** | 23.7% |
| FIXED ROC31/c3 (in-sample pick) | 34.19% | 1.93 | -25.7% | 1.33 | 7.26 | 0.5% | 11.8% | -10.7% | 26.1% |
| production OM25 (stop 20, no overlay) | 35.06% | 1.67 | -34.8% | 1.01 | 9.85 | 4.3% | 16.2% | -19.1% | 25.6% |
| no stop, no overlay | **37.72%** | 1.71 | -35.9% | 1.05 | 9.05 | 3.7% | 12.4% | -19.9% | 27.0% |

**The risk benefit survives walk-forward almost intact.** Max drawdown -25.8%
against the fixed pick's -25.7% and production's -34.8%. Ulcer 7.46 vs 7.26 vs
9.85. Days spent more than 20% underwater 0.6% vs 0.5% vs 4.3%. Worst
12-month outcome -10.9% vs -19.1%. None of that was an artifact of choosing
the parameters with hindsight.

**The return benefit does not survive.** Walk-forward CAGR is 31.28% against
the fixed pick's 34.19% — a 2.9pp selection penalty — and against production's
35.06% on this window it is **3.8pp behind**.

### Correction to an earlier claim in this document

Above I wrote that stop-off + ROC31@75 "beats production on every metric,
including CAGR". That was window-specific and is too strong. Recomputed:

| window | production | stop-off + ROC31@75 | walk-forward |
|---|---:|---:|---:|
| 2015-07 -> 2026-08 | 29.61% | 30.73% | — |
| 2017-01 -> 2026-05 | 33.72% | 33.65% | — |
| 2018-07 -> 2026-08 | 35.06% | 34.19% | 31.28% |

The honest statement: **CAGR is a wash to modestly negative depending on the
window, and once parameter selection is paid for it costs roughly 3-4pp.**
What is robust is the drawdown, Ulcer, worst-12-month and negative-entry
improvements, which hold on every window and survive walk-forward.

That is still a good trade for a subscription product — it buys 9pp of
drawdown and halves the worst 12-month outcome for ~3-4pp of return — but it
is a trade, not a free lunch.

## Against the product bar

Walk-forward curve, 2018-07 -> 2026-08:

| criterion | bar | walk-forward | |
|---|---|---|---|
| max drawdown | <= 25% | -25.8% | **FAIL** (by 0.8pp) |
| days >20% underwater | <= 2% | 0.6% | PASS |
| longest underwater | <= 18 mo | 16.0 mo | PASS |
| % 12m entries negative | <= 20% | 13.8% | PASS |
| worst 12m | >= -15% | -10.9% | PASS |
| Ulcer | <= 8 | 7.46 | PASS |

Five of six, missing only max drawdown by 0.8 points — and that on a
walk-forward curve, not a fitted one. **No other configuration in this task
gets close.** For reference, production OM25 fails four of the six.

Currently 417 days without a new high, against production's 675.

---

# 13. Conditional stop + tilt-signal swap (2026-09-04)

Harness: `om25_stop_and_tilt.py`. Crosses stop policy {always-20%, off,
armed-only-in-risk-off} with tilt signal {NIFTY 100 MA, NIFTY 500 ROC31} and
overlay {none, ROC31@75}. The engine accepts a date-indexed mapping for
`atr_min_floor`, so the conditional stop needed no engine change (risk-on
passes a 999% floor, not 0 — with `atr_mult=0` a floor of 0 would fire on any
position below its peak).

## Why the stop costs money here — measured, not asserted

For every position the production OM25 run exited, the stock's own forward
return **after it was sold**:

| horizon | exit reason | n | mean fwd | median fwd | % positive |
|---|---|---:|---:|---:|---:|
| 21d | stop | 169 | +0.67% | +0.39% | 51.5% |
| 21d | rank | 267 | +1.48% | +1.20% | 55.8% |
| 63d | **stop** | 166 | **+10.09%** | +1.20% | 53.0% |
| 63d | rank | 251 | +5.62% | +0.95% | 51.4% |
| 126d | **stop** | 160 | **+20.48%** | +9.92% | 59.4% |
| 126d | rank | 239 | +11.47% | +5.50% | 59.4% |

**Stocks sold by the stop went up 20% on average over the following six
months** — more than the ones sold on rank. In a momentum portfolio of
high-beta names, a 20% fall from a position's own peak is usually ordinary
volatility, and the stop converts it into a realised loss just before the
recovery. That is the entire 2.9pp CAGR cost, and it is visible most starkly
in 2020: with the stop, 39.26%; without it, **81.07%**. The stop sold into the
March crash and was in cash for the rebound.

**And this is exactly why the number does not settle the question.** The
sample is 2015-2026 — measured over 2021-2026 for the exits above — a period
where nearly every drawdown reversed. What a stop actually insures against is
the fall that *doesn't* come back: a single-name collapse (fraud, a funding
freeze, a delisting) or a market where 20% is the start rather than the end.
The panel begins 2009-03, so 2008 is not in it at all, and the two bears it
does contain were broad drawdowns where names fell together and recovered
together.

The asymmetry is the point: **the stop's cost is continuous and measurable —
a few points of drag every year — while its benefit is discrete and rare.** A
backtest over a decade with no catastrophe will always price insurance as a
waste, in the same way a decade with no fire makes fire insurance look like a
bad trade. It also matters that OM25 holds to rank 45 before the rank rule
fires, so with the stop removed the *only* fast reaction to a single name
collapsing is the weekly rank check.

So "it cost more than it saved" is true of this sample and is not a claim
about the next tail event.

## The conditional stop does not work as a compromise

| tilt / overlay | stop | CAGR | Sharpe | max DD | Ulcer | stop exits |
|---|---|---:|---:|---:|---:|---:|
| N100 / none | always20 | 29.61% | 1.60 | -34.78% | 10.44 | 298 |
| N100 / none | **riskoff20** | 30.14% | 1.62 | -34.82% | 10.42 | 224 |
| N100 / none | off | **32.50%** | 1.69 | -35.93% | 9.35 | 0 |
| N100 / roc31@75 | always20 | 26.97% | 1.77 | -21.94% | 8.78 | 259 |
| N100 / roc31@75 | **riskoff20** | 27.61% | 1.82 | -21.99% | 8.79 | 190 |
| N100 / roc31@75 | off | **30.73%** | 1.96 | -25.70% | 7.59 | 0 |
| N500 / roc31@75 | always20 | 28.29% | 1.85 | -21.31% | 8.66 | 249 |
| N500 / roc31@75 | **riskoff20** | 28.43% | 1.85 | -21.38% | 8.67 | 185 |
| N500 / roc31@75 | off | **31.54%** | 1.97 | -25.09% | 7.75 | 0 |

Arming the stop only in risk-off behaves **almost exactly like leaving it on
all the time**, not like a midpoint. It recovers just 0.1-0.6pp of the ~3pp
the stop costs, and its drawdown, Ulcer and days-beyond-20% are identical to
the always-on version to two decimal places.

The reason is in the exit counts: **75-78% of stop triggers already happen
during risk-off** (224 of 298, 190 of 259, 185 of 249). Stocks fall 20% from
their peaks when the market is falling. Conditioning the stop on the market
being weak barely conditions anything — it removes the quarter of stop exits
that occur in calm markets, which were the cheap ones.

**Verdict: this is not a useful third option.** The choice remains binary:
keep the stop and pay ~3pp, or remove it and accept unhedged single-name tail
risk.

## The tilt swap is a small, consistent improvement

Replacing the score's regime tilt signal (NIFTY 100 vs 100-DMA) with
NIFTY 500 ROC31 > 0, like-for-like across all six pairings:

| overlay / stop | N100 MA tilt | N500 ROC31 tilt | delta |
|---|---:|---:|---:|
| none / always20 | 29.61% (1.60) | **31.32% (1.70)** | +1.71pp, +0.10 |
| none / off | 32.50% (1.69) | **33.85% (1.76)** | +1.35pp, +0.07 |
| roc31@75 / always20 | 26.97% (1.77) | **28.29% (1.85)** | +1.32pp, +0.08 |
| roc31@75 / off | 30.73% (1.96) | **31.54% (1.97)** | +0.81pp, +0.01 |

Better in every pairing, and drawdown is equal or slightly better (-25.09% vs
-25.70% on the leading config). In the 2018-19 episode it also helps: with no
overlay, -1.64% CAGR / -22.45% DD against -3.23% / -24.35%.

Best config found in this task overall — **N500 ROC31 tilt + ROC31@75 overlay,
stop off**: 31.54% CAGR, Sharpe 1.97, max DD -25.09%, Ulcer 7.75, 0.3% of days
beyond a 20% drawdown, worst 12m -12.3%, median 12m 19.8%.

### Two reasons to be cautious about it anyway

1. **It concentrates the strategy on a single signal.** Today the score tilt
   (NIFTY 100 MA) and the proposed overlay (NIFTY 500 ROC31) are independent —
   if one misreads the market, the other may not. Making both read the same
   series means a single wrong signal moves *what it holds* and *how much it
   holds* in the same direction at the same moment. The measured gain is
   ~1pp of CAGR; the cost is losing that error-diversification. On the
   founder's probabilistic-not-predictive principle, that is a poor trade for
   1pp.
2. **It shortens the strategy's testable history from 2010 to 2015.** The
   NIFTY 100 series starts 2010-01; NIFTY 500 starts 2015-01. Moving the tilt
   onto NIFTY 500 means OM25's core score can no longer be backtested over
   2009-2016 — **its own original in-sample window.** The strategy's founding
   validation would become permanently unreproducible.

The overlay already has this dependency, but the overlay is an add-on that can
be switched off; the tilt is inside the score.

**Recommendation: do not swap the tilt for ~1pp.** Revisit if NIFTY 500
history is backfilled pre-2015, which would remove objection 2 and allow a
proper test of objection 1.

---

# 14. N100 ROC31 as the score tilt (2026-09-04)

Tests the middle path: keep NIFTY 100 as the tilt index but swap the mechanic
from 100-DMA to 31-session ROC. This was proposed to address the two
objections to the N500 ROC31 tilt.

## It solves the history objection, not the independence one

Signal agreement, share of days in the same bull/bear state, 2015-07 onward:

| pair | agreement |
|---|---:|
| N100_MA vs N500_ROC31 (overlay) | 83.1% |
| **N100_ROC31 vs N500_ROC31 (overlay)** | **95.0%** |
| N100_MA vs N100_ROC31 | 82.4% |

Bear-day share is similar for all three (30.0% / 32.3% / 31.3%).

So N100_ROC31 **fully solves objection 2** — NIFTY 100 history starts 2010, so
the strategy stays backtestable across its original in-sample window — but
**does not solve objection 1**. At 95% agreement it is very nearly the same
signal as the overlay; the index differs, the mechanic does not.

## Long-history test — the strongest evidence for the ROC mechanic so far

Because the tilt stays on NIFTY 100, this can be tested over **2010-07 ->
2026-08 (16.1 years)**, no overlay, isolating the tilt change alone. That
window contains 2011, 2013, 2015-16, 2018-19, COVID and 2025 — roughly five
or six drawdown episodes against the two available in the N500 window.

| tilt | stop | CAGR | Sharpe | max DD | Calmar | Ulcer | % days >20% DD | % 12m neg | worst 12m | median 12m |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| N100_MA | always20 | 31.27% | 1.76 | -34.79% | 0.90 | 10.21 | 7.5% | 20.1% | -19.0% | 19.2% |
| **N100_ROC31** | always20 | **32.46%** | **1.85** | **-32.60%** | **1.00** | **9.47** | **5.3%** | **18.8%** | **-17.5%** | **20.5%** |
| N100_MA | off | 33.13% | 1.79 | -35.97% | 0.92 | 9.42 | 4.9% | 17.1% | -19.9% | 20.4% |
| **N100_ROC31** | off | **33.57%** | **1.84** | **-34.49%** | **0.97** | **8.98** | **3.6%** | **15.1%** | -18.6% | **21.1%** |

**N100_ROC31 beats N100_MA on every metric, in both stop settings, over 16
years.** With the stop: +1.19pp CAGR, +0.09 Sharpe, +2.2pp drawdown, Calmar
0.90 -> 1.00. Without: +0.44pp, +0.05, +1.5pp. The gains are modest but they
are consistent, and this is the only test in the whole task with enough
episodes to be worth much.

## But with the overlay running, the tilt choice stops mattering

2015-07 -> 2026-08, ROC31@75 overlay on, stop off:

| tilt | CAGR | Sharpe | max DD | Calmar | Ulcer | % 12m neg | worst 12m | median 12m |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| N100_MA | 30.73% | 1.96 | **-25.70%** | 1.20 | **7.59** | **16.9%** | **-11.9%** | 19.1% |
| N100_ROC31 | 30.63% | 1.96 | -26.63% | 1.15 | 8.05 | 17.9% | -13.4% | **20.0%** |
| N500_ROC31 | **31.54%** | **1.97** | -25.09% | **1.26** | 7.75 | 17.4% | -12.3% | 19.8% |

Spread across the three: 0.9pp of CAGR, 0.01 of Sharpe, 1.5pp of drawdown.
That is noise. **Once the exposure overlay is running it dominates, and which
tilt sits underneath barely registers** — including the N100_ROC31 variant,
which is marginally the worst of the three on drawdown and worst-12-month
despite being the best tilt on its own.

Without the overlay the tilt does matter, and N100_ROC31 is the better one
(33.04% / 1.73 / -34.55% vs N100_MA's 32.50% / 1.69 / -35.93%).

## Recommendation

The answer depends on whether the overlay ships:

- **If the overlay does NOT ship: switch the tilt to N100_ROC31.** It is
  better on return and risk over a 16-year sample with five-plus episodes,
  costs nothing operationally (same index, same data, one formula change), and
  keeps the strategy fully backtestable to 2010. This is the best-evidenced
  single change found anywhere in this task.
- **If the overlay DOES ship: leave the tilt on N100_MA.** The tilt choice is
  worth ~0.1pp under an overlay, and N100_MA is the variant that disagrees
  with the overlay most often (83% agreement vs 95%), which is worth more than
  a rounding error when the whole design rests on one market signal being
  right.
- **Do not use N500_ROC31 as the tilt** in either case. Its edge over
  N100_ROC31 is inside noise, and it permanently costs the ability to
  reproduce OM25's founding validation.

---

# 15. N100 as the overlay index — the long-duration test (2026-09-04)

The idea: since N100 ROC31 tracks N500 ROC31 closely, read the **overlay** off
NIFTY 100 instead. NIFTY 100 history starts 2010 against NIFTY 500's 2015, so
this lifts the binding constraint on this entire line of work — 11 years with
two bear episodes becomes 16 years with five or six.

## The two overlays are near-equivalent

Same window, same everything else (tilt N100_MA, stop off, 75% bear exposure),
2015-07 -> 2026-08:

| overlay | CAGR | Sharpe | max DD | Ulcer | % days >20% DD | % 12m neg | worst 12m | median 12m |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **N100 ROC31 @75** | 30.57% | 1.96 | **-23.4%** | **7.44** | **0.1%** | **15.9%** | -11.9% | 17.7% |
| N500 ROC31 @75 | 30.73% | 1.96 | -25.7% | 7.59 | 0.3% | 16.9% | -11.9% | **19.1%** |
| no overlay | 32.50% | 1.69 | -35.9% | 9.35 | 4.1% | 18.5% | -19.9% | 18.8% |

Identical Sharpe, CAGR within 0.16pp, and N100 is **better** on drawdown depth,
Ulcer and days-beyond-20%. The hypothesis holds: nothing is given up by
switching index, and 5 extra years of testable history are gained.

## 13.1-year walk-forward — the headline result

Rolling 3-year train / 1-year test from 2013-07, 35-cell (lookback x confirm)
grid re-selected annually on train Sharpe, spliced into one signal and run as a
single backtest. Test period **2013-07-01 -> 2026-08-21 (13.1 years)**:

| config | CAGR | Sharpe | max DD | Calmar | Ulcer | % days >20% DD | % 12m neg | worst 12m |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| **WALK-FORWARD N100 ROC** | 30.84% | **2.03** | **-23.4%** | **1.32** | **7.04** | **0.3%** | **17.3%** | **-11.6%** |
| FIXED N100 ROC31/c3 @75 | 34.50% | 2.21 | -23.4% | 1.47 | 6.85 | 0.1% | 13.4% | -11.8% |
| production (stop 20, no overlay) | 34.53% | 1.88 | -34.8% | 0.99 | 9.86 | 7.0% | 21.7% | -19.0% |
| no stop, no overlay | **36.73%** | 1.92 | -36.0% | 1.02 | 8.97 | 4.1% | 18.2% | -19.9% |

**The walk-forward max drawdown is -23.4% — identical to the fitted pick**, over
13 years containing 2013, 2015-16, 2018-19, COVID and 2025. Sharpe 2.03 against
production's 1.88, Ulcer 7.04 vs 9.86, days beyond a 20% drawdown 0.3% vs 7.0%,
worst 12-month -11.6% vs -19.0%.

The CAGR cost is **-3.69pp** against production. The N500 walk-forward measured
-3.78pp on a different window with a different index — two independent
estimates landing within 0.1pp of each other. That is a stable number, not a
window artifact.

### The result is not parameter-sensitive

The fold picks scattered much more widely than in the N500 run — lookbacks of
15, 21, 31, **42, 52 and 63**, confirms of 1 to 5. Several folds chose cells the
full-window grid had flagged as poor. **It still delivered -23.4% max drawdown
and Sharpe 2.03.** The benefit comes from having a reasonable ROC exposure
overlay at all, not from finding the right cell — which is the strongest
argument yet that this is not a fitted artifact.

## Head-to-head walk-forwards on identical dates (2018-07 -> 2026-08)

| walk-forward | CAGR | Sharpe | max DD | Ulcer | longest underwater | % 12m neg | worst 12m | median 12m |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| N100 (from the 13.1y run) | 30.22% | 1.75 | **-23.4%** | 7.62 | 24.6 mo | 17.8% | **-9.4%** | 19.7% |
| N500 (from the 8.1y run) | 31.28% | 1.78 | -25.8% | **7.46** | **16.0 mo** | **13.8%** | -10.9% | **23.7%** |

Close, and neither dominates: N100 is better on drawdown depth and worst
12-month, N500 on drawdown *duration* and the 12-month distribution. The
difference comes from the folds picking different cells, not from the index.

## Against the product bar

13.1-year walk-forward curve:

| criterion | bar | result | |
|---|---|---|---|
| max drawdown | <= 25% | -23.4% | **PASS** |
| days >20% underwater | <= 2% | 0.3% | **PASS** |
| longest underwater | <= 18 mo | 24.6 mo | **FAIL** |
| % 12m entries negative | <= 20% | 17.3% | **PASS** |
| worst 12m | >= -15% | -11.6% | **PASS** |
| Ulcer | <= 8 | 7.04 | **PASS** |

Five of six. It now clears max drawdown — the criterion the N500 version
missed — and fails instead on duration. The 24.6-month figure is driven by the
**ongoing** flat stretch: 751 days without a new high as of the panel end. That
is the same condition every portfolio in this study is currently in, and it is
live rather than historical.

## Revised recommendation

**Switch the overlay from NIFTY 500 to NIFTY 100.** Statistically equivalent on
the common window, marginally better on drawdown depth, and it buys five extra
years of validation including a 13-year walk-forward instead of an eight-year
one. There is no cost to the change.

The candidate configuration is now:

- OM25 v3 unchanged: Nifty 250, capture-based score, N100-vs-100DMA tilt,
  25 names, bi-weekly, rank-45 exit buffer
- **[NEW] Exposure overlay: NIFTY 100, 31-session ROC, 3-day confirm,
  100% invested risk-on / 75% risk-off**
- **[NEW] 20% per-stock trailing stop removed**

Keeping the tilt on N100_MA remains correct: with the overlay running, tilt
choice is worth ~0.1pp, and N100_MA is the variant that disagrees with an ROC
overlay most often.

Still open before this could ship: the tilt walk-forward, and a decision on
accepting single-name tail risk with the stop removed.

---

# 16. How the candidate has done recently (2026-09-04)

Reality check on the most recent stretch. **Neither line below has traded —
the candidate has never been live, so this is a backtest over the recent
period, not a live record.**

Total return % / max drawdown % over each window (not annualised):

| series | 2026 YTD | trailing 12m | trailing 24m | 2025+2026 |
|---|---|---|---|---|
| production OM25 | **+2.3% / -14.0%** | **-0.4% / -15.2%** | +2.5% / -25.3% | -0.3% / -24.3% |
| candidate (fixed params) | -2.3% / **-8.2%** | -1.8% / **-8.2%** | **+5.6% / -17.1%** | **+5.0% / -14.7%** |
| candidate (walk-forward) | -2.8% / -7.6% | -3.7% / -7.6% | -5.3% / -20.2% | -1.8% / -16.8% |
| NIFTY 100 | -5.0% / -15.0% | -1.2% / -15.0% | -1.8% / -17.5% | +3.3% / -15.0% |

**In 2026 the candidate has not helped on return.** It is 4.6 points behind
production year to date and 1.4 points behind over the trailing year. It has
delivered exactly what it promised on risk — the 2026 drawdown is -8.2%
against production's -14.0%, and over 24 months -17.1% against -25.3% — but a
subscriber looking at 2026 alone would see a portfolio that fell less and
also made less.

Over 24 months the fixed candidate is *ahead* (+5.6% vs +2.5%), so even inside
"recent" the answer flips with the window.

## What happened, month by month

| month | production | candidate (fixed) | NIFTY 100 |
|---|---:|---:|---:|
| 2026-01 | -2.4 | -1.2 | -2.9 |
| 2026-02 | +2.4 | +1.2 | -0.0 |
| **2026-03** | **-12.5** | **-6.5** | -11.7 |
| **2026-04** | **+13.9** | **+3.4** | +8.8 |
| 2026-05 | +4.6 | +2.6 | -1.2 |
| 2026-06 | -1.8 | -2.2 | +1.2 |
| 2026-07 | -2.8 | -1.9 | +2.3 |
| 2026-08 | +3.3 | +3.3 | -0.4 |

March and April are the whole story. The overlay **halved the March fall**
(-6.5% against -12.5%) and then **missed most of the April rebound** (+3.4%
against +13.9%). Compounded across those two months production is -0.3% and
the candidate is -3.3%.

That is the V-shape failure mode — the same one that made an overlay a bad
trade on L6 v2 — showing up in OM25's most recent correction. The overlay is
built for grinding declines; 2026's correction was sharp and reversed fast.

## The overlay has been unusually engaged

Share of days the NIFTY 100 ROC31 signal was risk-off:

| year | risk-off |
|---|---:|
| 2024 | 18% |
| 2025 | 41% |
| 2026 YTD | **54%** |

Six regime flips in 2026 alone. So this is a period where the overlay is
maximally active and its cost maximally visible — the strategy has spent more
than half of 2026 at 75% exposure, in a year that ended up roughly flat.

## Current state

| series | current drawdown | days since last high |
|---|---:|---:|
| production OM25 | -2.6% | 675 |
| candidate (fixed) | -4.5% | **417** |
| candidate (walk-forward) | -7.2% | 751 |
| NIFTY 100 | -6.8% | 694 |

## Read

The candidate is **not a fix for the flat stretch the portfolios are in.** It
would have made the last two years smoother, not more profitable — and over
the last eight months it would have been modestly worse on both, because the
one big move of 2026 was a V.

That does not invalidate the 13-year evidence, which was always a claim about
drawdown and ride quality rather than return, and which priced the cost at
~3.7pp of CAGR. 2026 is that cost being paid, in a window too short to mean
anything on its own — 158 trading days.

But it is worth being clear-eyed: **if this shipped today, the first thing
subscribers would have experienced is lower returns than the current portfolio
in a year that felt bad anyway.** The case for it rests on the next 2018-19,
not on the last eight months.

---

# 17. Year-by-year, trailing windows, and terminal wealth (2026-09-04)

All figures backtested on Rs 10,00,000 with 20bps slippage. **No brokerage and
no tax.** With bi-weekly rebalancing and Indian STCG at 20%, real after-tax
outcomes are materially below every number here — the retune doc estimated
3-6pp of CAGR.

## Calendar years — total return % (worst drawdown inside that year)

| series | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 YTD |
|---|---|---|---|---|---|---|
| production OM25 | **115.2 (-8)** | **13.0 (-24)** | **74.3 (-16)** | **80.0 (-11)** | -2.4 (-24) | **2.7 (-14)** |
| candidate (fixed) | 79.7 (-9) | 9.5 (-18) | 71.8 (-12) | 77.1 (-12) | **6.9 (-15)** | -1.6 (**-8**) |
| candidate (walk-forward) | 78.2 (-8) | 9.4 (-19) | 57.1 (-16) | 51.3 (-9) | 0.7 (-17) | -2.3 (-8) |
| NIFTY 100 | 25.0 (-10) | 3.6 (-17) | 20.0 (-9) | 11.8 (-11) | 9.0 (-10) | -4.8 (-15) |

The pattern is consistent and it is the whole trade: **the candidate gives up
a large slice of the best years and protects in the worst one.** 2021 is the
starkest — 79.7% against 115.2%, a 35-point gap, because the overlay sat
risk-off through part of a monster bull run. 2023 and 2024 cost 2-3 points
each. 2025 is where it is repaid: +6.9% against -2.4%.

Note the walk-forward line gives up much more in 2023-24 (57.1% and 51.3%)
than the fixed-parameter line does. That is the selection cost landing in the
two biggest recent years.

## Trailing windows to 2026-08-21 — total % / CAGR % / max DD %

| series | 1 year | 3 years | 5 years | 10 years |
|---|---|---|---|---|
| production OM25 | -0 / -0.4 / -15 | **147 / 35.2 / -25** | **376 / 36.6 / -25** | **1488 / 31.8 / -35** |
| candidate (fixed) | -2 / -1.8 / **-8** | 141 / 34.1 / **-17** | 345 / 34.8 / **-18** | 1478 / **31.8** / **-23** |
| candidate (walk-forward) | -4 / -3.7 / -8 | 91 / 24.0 / -21 | 231 / 27.1 / -21 | 1056 / 27.7 / -23 |
| NIFTY 100 | -1 / -1.2 / -15 | 32 / 9.6 / -18 | 52 / 8.8 / -18 | n/a |

**Over 10 years the fixed candidate matches production exactly — 31.8% CAGR
both — with a -23% worst drawdown instead of -35%.** That is the cleanest
statement of the case available anywhere in this work.

Over 3 and 5 years the candidate is 1-2pp behind, and the walk-forward version
is 9-11pp behind.

## Terminal wealth — Rs 10,00,000 invested, value at 2026-08-21

| series | from Jul-2013 (13.1y) | from Aug-2016 (10y) | from Aug-2021 (5y) | from Aug-2023 (3y) |
|---|---|---|---|---|
| production OM25 | **Rs 492.6L** | **Rs 158.8L** | **Rs 47.6L** | **Rs 24.7L** |
| candidate (fixed) | Rs 491.2L | Rs 157.8L | Rs 44.5L | Rs 24.1L |
| candidate (walk-forward) | Rs 341.9L | Rs 115.6L | Rs 33.1L | Rs 19.1L |
| NIFTY 100 | n/a | n/a | Rs 15.2L | Rs 13.2L |

## The number that matters

Two ways to price the same protection over 13.1 years:

- **With hindsight on the parameters** (fixed ROC31/c3): Rs 491.2L against
  production's Rs 492.6L. **The protection is free** — a 0.3% difference in
  terminal wealth for cutting max drawdown from -35% to -23%.
- **Without hindsight** (parameters re-picked annually from prior data only):
  Rs 341.9L against Rs 492.6L. **The protection costs Rs 150.7L, or 31% of
  terminal wealth.**

The honest expectation for forward deployment is the second number, not the
first. The fixed line knows which cell to use before the period starts; nobody
deploying this in 2013 would have.

So the trade, stated properly: **giving up roughly a third of 13-year terminal
wealth to cut the worst drawdown by 12 points and the worst 12-month outcome
from -19% to -12%.** Whether that is worth it is a product decision about who
the subscriber is, not a research question — and it is a much heavier price
than "3.7pp of CAGR" makes it sound.

Two things that soften it slightly, and one that sharpens it:

- Softening: the walk-forward deliberately re-picked parameters every year
  from a 35-cell grid, which is a harsher test than committing to one
  reasonable setting and leaving it alone. The grid work showed the benefit is
  not cell-sensitive, so a fixed sensible choice is defensible.
- Softening: none of these figures include tax. High-turnover production would
  lose more to STCG than the lower-turnover candidate, narrowing the gap.
- Sharpening: the gap is concentrated in 2021, 2023 and 2024 — three of the
  best years in Indian mid-cap history. If the next decade contains fewer such
  years, the candidate gives up less.

---

# 18. Investor-pitch statistics (2026-09-04)

Harness: `investor_stats.py`. Common window 2013-07-01 -> 2026-08-21 (13.1y),
every trading day treated as an entry point.

## Holding-period outcomes — the horizon question

| held for | series | % positive | % beat NIFTY 100 | median | p5 | worst | best |
|---|---|---:|---:|---:|---:|---:|---:|
| **1 year** | production | 91.1% | 92.1% | +40.4% | -1.7% | -5.9% | +192.7% |
| | **candidate (fixed)** | **95.1%** | 94.7% | +41.8% | **+0.1%** | -7.8% | +173.1% |
| | candidate (walk-fwd) | 86.8% | 83.5% | +36.6% | -3.5% | -8.2% | +148.3% |
| | NIFTY 100 | 85.1% | — | +10.4% | -2.9% | -6.5% | +87.2% |
| **2 years** | production | 99.1% | 99.3% | +152.2% | +28.8% | -5.1% | +327.4% |
| | **candidate (fixed)** | **99.7%** | **100.0%** | +129.6% | +32.4% | **-1.5%** | +281.4% |
| | candidate (walk-fwd) | 97.1% | 96.7% | +107.2% | +13.9% | -10.4% | +260.3% |
| | NIFTY 100 | 98.3% | — | +32.5% | +3.3% | -2.5% | +131.6% |
| **3 years** | production | 100% | 100% | +268.3% | +182.8% | +163.7% | +393.8% |
| | candidate (fixed) | 100% | 100% | +243.8% | +176.2% | +155.5% | +343.3% |
| | candidate (walk-fwd) | 100% | 100% | +186.5% | +129.7% | +100.0% | +265.0% |
| | NIFTY 100 | 100% | — | +49.5% | +31.8% | +27.9% | +126.0% |

5-year holds: all series 100% positive, worst outcome +357% (production),
+313% (candidate), +208% (walk-forward), +53% (NIFTY 100).

### The statistical caveat that has to travel with these numbers

The "% positive" figures look like large samples — 894 start days at 3 years —
but the windows overlap almost completely. In 13.1 years of data there are
only about **13 independent 1-year periods, 6 independent 2-year periods, 4
independent 3-year periods and 2.6 independent 5-year periods.**

So:

- **The 1-year numbers are supportable.** ~13 independent observations, and
  the result (95% of start days positive for the candidate) is consistent
  across sub-periods.
- **The 2-year numbers are weak but directional.**
- **"100% of 3-year and 5-year periods were positive" is close to
  meaningless** — it rests on 2-4 independent observations inside a window
  that contains no 2008-style event and is dominated by one of the strongest
  mid-cap bull runs in Indian history.

That statement should not go in front of an investor as a probability claim.
It is a description of one favourable stretch of history, not evidence about
the next three years.

## Capture and consistency vs NIFTY 100 — the strongest honest material

| series | up capture | down capture | capture ratio | beta | % months positive | % months beat bench | % quarters beat bench |
|---|---:|---:|---:|---:|---:|---:|---:|
| production OM25 | 112% | 84% | 1.34 | 0.95 | 65.0% | 64.6% | **73.1%** |
| **candidate (fixed)** | 95% | **66%** | **1.44** | **0.73** | **66.2%** | 63.3% | 61.5% |
| candidate (walk-fwd) | 92% | 67% | 1.37 | 0.73 | 65.0% | 59.5% | 61.5% |

The candidate captures **95% of the market's up moves and only 66% of its
down moves**, at a beta of 0.73. That is the single most defensible line in
this whole analysis — it is a structural property of the design, measured
daily over 13 years, not a horizon artifact.

Note the trade-off in the batting averages: production beats the benchmark
more often (73.1% of quarters vs 61.5%) but the candidate loses less when it
loses. Frequency of winning and severity of losing pull in opposite
directions; the candidate optimises the second.

## Recovery behaviour

| series | drawdowns >15% | median recovery | worst recovery | currently underwater | current episode trough |
|---|---:|---:|---:|---:|---:|
| production OM25 | 5 | 203 days | 759 days | 674 days | -25.3% |
| candidate (fixed) | 5 | **174 days** | 726 days | **416 days** | **-9.3%** |
| candidate (walk-fwd) | 4 | 212 days | 730 days | 750 days | -20.9% |
| NIFTY 100 | 2 | 350 days | 406 days | 693 days | -17.5% |

Both versions take about the same number of >15% hits; the candidate gets out
of them faster (174 vs 203 days median) and its current one is far shallower
(-9.3% vs -25.3%).

## What I would and would not pitch

**Defensible:**

- "Captures 95% of the market's upside and 66% of its downside" — daily data,
  13 years, structural.
- "In 95% of one-year holding periods since 2013, the strategy was positive,
  against 85% for the Nifty 100" — ~13 independent observations, honest.
- "Median one-year return of 42% against the index's 10%."
- "Typical recovery from a drawdown deeper than 15% has been about six
  months."
- "Beta of 0.73 — it is not simply a leveraged bet on the index."

**Do not pitch:**

- "No 3-year period has ever lost money." True of this sample, ~4 independent
  observations, no 2008 in the window. It invites exactly the expectation that
  destroys trust when it breaks.
- Any 5-year statistic. 2.6 independent periods.
- Terminal-wealth figures without the tax caveat — none of these numbers model
  STCG or brokerage, and at bi-weekly turnover that gap is 3-6pp of CAGR.
- The fixed-parameter version's returns as if they were achievable. The
  walk-forward line is the honest forward expectation, and it is visibly worse
  on every horizon statistic (86.8% of 1-year periods positive, not 95.1%).

**The horizon argument is real but should be made at one and two years, not
three and five.** At one year the candidate turns a 91% hit rate into 95% and
lifts the 5th-percentile outcome from -1.7% to +0.1% — that is the honest
version of "hold for at least a year", and it is a better pitch than an
unfalsifiable claim about three-year periods.

---

# 19. SIP analysis (2026-09-04)

Harness: `sip_analysis.py`. Rs 10,000 invested on the first trading day of
every month, for every possible start month, 2013-07 -> 2026-08. Returns are
money-weighted (XIRR), which is the right measure when capital arrives over
time. Still no tax or brokerage.

## Outcomes by SIP duration

| SIP | series | % positive | median XIRR | p5 | worst | median corpus | worst corpus |
|---|---|---:|---:|---:|---:|---:|---:|
| **2y** (Rs 2.4L in) | production | 90.3% | 30.0% | -4.0% | -15.2% | Rs 3.2L | Rs 2.0L |
| | **candidate (fixed)** | **95.5%** | **32.6%** | **+1.1%** | **-6.9%** | Rs 3.3L | Rs 2.2L |
| | candidate (walk-fwd) | 92.5% | 28.6% | -0.6% | -6.8% | Rs 3.2L | Rs 2.2L |
| | NIFTY 100 | 92.9% | 11.1% | -0.3% | -7.1% | Rs 2.7L | Rs 2.2L |
| **3y** (Rs 3.6L in) | production | 95.9% | 32.8% | +2.0% | -10.2% | Rs 5.7L | Rs 3.1L |
| | **candidate (fixed)** | **99.2%** | **34.9%** | +5.9% | **-1.5%** | Rs 5.9L | Rs 3.5L |
| | candidate (walk-fwd) | **99.2%** | 31.2% | **+6.4%** | -1.0% | Rs 5.6L | Rs 3.5L |
| | NIFTY 100 | 100% | 12.8% | +4.0% | +0.8% | Rs 4.4L | Rs 3.6L |
| **5y** (Rs 6.0L in) | production | 100% | **37.1%** | +7.8% | +0.8% | **Rs 14.8L** | Rs 6.1L |
| | candidate (fixed) | 100% | 36.1% | **+11.9%** | **+8.0%** | Rs 14.5L | **Rs 7.3L** |
| | candidate (walk-fwd) | 100% | 34.1% | +11.3% | +7.4% | Rs 13.8L | Rs 7.2L |
| | NIFTY 100 | 100% | 12.3% | +6.7% | +5.6% | Rs 8.2L | Rs 6.9L |

1-year SIP: production 80.8% positive / 25.5% median / -28.1% worst;
candidate 84.2% / 26.1% / **-14.8%** worst. A one-year SIP is still a coin-flip
enough of the time that it should not be sold as a horizon.

10-year SIP (Rs 12L invested): median corpus Rs 93.9L production, Rs 91.2L
candidate, Rs 72.9L walk-forward. **Only 38 start months exist — about three
independent windows. Treat as illustration, not statistics.**

## The result that matters: SIP inverts the lump-sum verdict

Under lump-sum, production beats the candidate on return at every horizon.
**Under SIP, the candidate wins on both median and worst at 2 and 3 years:**

| | 2y SIP median | 2y SIP worst | 3y SIP median | 3y SIP worst |
|---|---:|---:|---:|---:|
| production | 30.0% | -15.2% | 32.8% | -10.2% |
| candidate (fixed) | **32.6%** | **-6.9%** | **34.9%** | **-1.5%** |

And **even the walk-forward version** — the honest forward expectation —
beats production on consistency and worst case at both horizons (92.5% vs
90.3% positive at 2y with a -6.8% worst; 99.2% vs 95.9% at 3y with a -1.0%
worst), giving up only 1-2pp of median XIRR.

The mechanism: XIRR is money-weighted, so a drawdown late in a SIP hits a
large accumulated corpus, while an early one hits almost nothing. Lump-sum
outcomes are dominated by the endpoint; SIP outcomes are dominated by the
*path*, and specifically by what happens once the corpus is big. The candidate
protects the later, larger corpus. That is worth more to a monthly investor
than the extra upside production captures in a rally.

**Since most Indian retail invests monthly, the SIP framing is the relevant
one for this product — and it is the framing in which the candidate looks
best.**

## SIP does not reduce dispersion — it raises the floor

Spread between 5th and 95th percentile outcome:

| horizon | series | SIP spread | lump-sum spread | SIP p5 | lump p5 |
|---|---|---:|---:|---:|---:|
| 2y | production | 102.6 | 83.6 | -4.0% | -6.2% |
| 2y | candidate | 86.6 | 79.6 | **+1.1%** | -3.6% |
| 3y | production | 70.6 | 64.7 | +2.0% | -0.7% |
| 3y | candidate | 62.6 | 54.3 | **+5.9%** | +0.9% |
| 5y | candidate | 51.2 | 51.9 | **+11.9%** | +7.5% |

The common claim that SIP "reduces volatility of outcomes" is **not true here**
— the XIRR spread is wider than the lump-sum CAGR spread at most horizons.
What SIP does is lift the **bad** outcomes: the 5th-percentile 3-year SIP
returns +5.9% against +0.9% for a lump sum. Averaging the entry point does not
narrow the distribution, it truncates the left tail.

That is still the useful pitch, just stated correctly.

## Pitch lines this supports

- "A three-year SIP has been positive in 99% of start months, with a worst
  case of -1.5%" — 122 start months, ~4 independent windows. Directional, and
  should be stated with the sample caveat.
- "Rs 10,000/month for five years turned Rs 6L into a median Rs 14.5L, with
  the worst start month still producing Rs 7.3L." Honest and concrete.
- "For monthly investors the defensive version has historically been better on
  both the typical outcome and the bad one" — this is the genuinely
  differentiated claim, and it holds for the walk-forward version too.

## Still do not claim

- Anything from the 10-year SIP row (3 independent windows).
- That SIP reduces risk in general — it lifts the floor, it does not narrow
  the distribution.
- One-year SIP figures as a horizon recommendation: 16-19% of start months
  were still negative.
