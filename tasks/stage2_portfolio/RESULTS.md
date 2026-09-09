# S2 (Stage 2) portfolio - results

Run 2026-09-09. Research only; nothing is wired to production.

## What S2 is

**Gate (hard pass/fail, all seven must hold on the signal date):**

| # | Condition |
|---|---|
| 1 | Close > 150 DMA and Close > 200 DMA |
| 2 | 150 DMA > 200 DMA |
| 3 | 200 DMA rising over the last 20 trading days |
| 4 | 50 DMA > 150 DMA (full stack) |
| 5 | Close > 50 DMA |
| 6 | Close >= 1.30 x 52-week low |
| 7 | Close >= 0.75 x 52-week high |

plus RS >= 70th percentile (126-day return, ranked across the point-in-time
universe) and stage age >= 21 days, so a name has to have held the structure
for a month before it is buyable.

**Rank (among gate-passers only)** - four pre-registered variants, each leg
percentile-ranked within the day's eligible set:

| Variant | Freshness | Un-extended | Vol contraction | Accumulation | RS |
|---|---|---|---|---|---|
| `A_rs` | - | - | - | - | 1.00 |
| `B_quality` | 0.25 | 0.25 | 0.25 | 0.25 | - |
| `C_nofresh` | - | 0.33 | 0.33 | 0.33 | - |
| `D_blend` | 0.125 | 0.125 | 0.125 | 0.125 | 0.50 |

Freshness prefers a younger advance, un-extended prefers a smaller gap to the
50 DMA, contraction prefers 21-day vol below its own 126-day vol, accumulation
is 50-day up-volume over down-volume.

**Mechanics:** NSE 500, weekly Friday signal to next-day OHLC/4, 22 names,
equal 1/N capped at 7.5%, max 4 names per sector, 20 bps slippage. Exit when
the name leaves the top (22 + buffer) of the ranking - which includes leaving
the gate, since a gate failure removes it from scoring entirely.

## Headline

OOS 2017-01-01 to 2026-08-21, every signal re-run on identical data
(`data/final_table.csv`):

**Snapshot basis** - the same universe basis the published figures use:

| Signal | CAGR | Max DD | Sharpe | Calmar |
|---|---|---|---|---|
| L6-like | 40.01% | -40.31% | 1.60 | 0.99 |
| TL25 v3 | 37.64% | -40.77% | 1.67 | 0.92 |
| **S2 `D_blend`** | **35.29%** | **-27.51%** | **1.67** | **1.28** |
| S2 `A_rs` | 34.47% | -28.08% | 1.64 | 1.23 |
| S2 `B_quality` | 24.85% | -30.25% | 1.29 | 0.82 |
| S2 `C_nofresh` | 24.15% | -27.79% | 1.27 | 0.87 |

**Survivorship-free basis** - reconstructed membership, 854 symbols:

| Signal | CAGR | Max DD | Sharpe | Calmar |
|---|---|---|---|---|
| TL25 v3 | 22.66% | -40.50% | 1.03 | 0.56 |
| **S2 `D_blend`** | **20.05%** | **-30.69%** | **1.00** | **0.65** |
| L6-like | 19.47% | -47.77% | 0.81 | 0.41 |
| S2 `A_rs` | 19.13% | -32.46% | 0.96 | 0.59 |
| S2 `C_nofresh` | 16.86% | -30.17% | 0.94 | 0.56 |
| S2 `B_quality` | 15.94% | -32.83% | 0.87 | 0.49 |

**The signature is drawdown.** On both bases, in both windows, every S2 variant
draws down less than TL25 and L6 - typically 10 to 13 percentage points less -
for 2 to 5 points less CAGR. S2 has the best Calmar in the set on both bases.
It is not a higher-return book; it is a shallower-drawdown one.

## It is a genuinely different book

OOS, in matched mechanics (`data/oos_holdings_overlap.csv`,
`data/oos_return_correlation.csv`):

| Pair | Holdings overlap (mean month-end Jaccard) | Weekly return corr |
|---|---|---|
| TL25 v3 vs L6 | 0.30 | 0.905 |
| S2 `D_blend` vs TL25 v3 | 0.31 | 0.876 |
| S2 `D_blend` vs L6 | 0.31 | 0.878 |
| S2 `B_quality` vs L6 | 0.16 | 0.829 |
| *(same signal, different plumbing)* TL25 native vs TL25 in S2 mechanics | 0.63 | 0.969 |

S2 shares about 30% of its names with the momentum books - the same overlap
TL25 and L6 already have with each other - and is slightly less correlated to
either of them than they are to one another. The 0.63 / 0.969 row is the
control: that is what "same signal, different mechanics" looks like, and S2
does not look like that.

The gate also produces an automatic cash buffer. Stage-2 breadth across the
universe runs from 0 to 178 names (median 42), collapsing in stress - 15 names
in June 2013, 10 in June 2022. The book is fully invested 61% of days, holds
18.2 names on average, and sits under 50% invested on 8.5% of days without any
regime overlay. That de-risking is a property of the gate, not a bolt-on.

## What moves the result and what does not

| Dimension | Tested | Verdict |
|---|---|---|
| **Sector cap** | 0 / 3 / 4 / 6 | **The one real lever.** Cap 4 vs none: OOS Calmar 0.47 to 0.56, max DD -33.7% to -30.2%, and CAGR *rises*. Peak sector weight falls from 51% to 31%. |
| Ranking variant | 4 variants | Second-order but regime-dependent - see the caveat below. |
| Per-position stop | none / 20% / 25% | **Complete non-lever** - identical to two decimals. The gate exits first: a name down 20% from its peak has almost always already broken the structure and been sold at the weekly check. |
| Weight discipline | drift / trim / equal | Non-lever. Peak single-name weight only reaches 9-11% under drift, so there is nothing for a trim to catch. |
| Book size | 20 / 22 / 25 | Non-lever. Anywhere in the founder's range is fine. |
| Exit buffer | 10 / 20 / 40 / 100 / 400 | Buffer >= 40 is already a gate-only exit; 40, 100 and 400 are identical. |
| Min hold | 0 / 30 days | IS Calmar 0.82 to 0.98, OOS 0.56 to 0.43. Opposite signs - do not adopt. |

## The two findings worth more than the portfolio

### 1. Survivorship is worth about 15 percentage points of CAGR

Same strategy, same engine, same window, only the universe basis changes
(`data/survivorship_effect.csv`):

| Signal | Snapshot | Survivorship-free | Gap |
|---|---|---|---|
| TL25 v3 | 37.64% | 22.66% | -14.98pp |
| S2 `D_blend` | 35.29% | 20.05% | -15.24pp |

The production membership file carries real effective dates for only 34 of 535
rows; the rest are open-ended from 1900-01-01, so a backtest on it is close to
"the stocks that are in the NSE 500 today, run backwards". The reconstructed
membership has 1,319 dated spells over 1,020 symbols, 819 of them closed.

The gap is nearly identical for both strategies, so **every relative
conclusion in this document survives** - but the absolute published figures do
not carry to a survivorship-free universe. Note this is not yet a restatement:
this task's engine, panel build and benchmark all differ from the production
runners. Attributing the gap properly means running
`scripts/run_tl25_v3_portfolio.py --membership <reconstructed>` and diffing
against its own baseline. That is queued in TASKS.md and should happen before
anything is said publicly, especially given the open
`om25_published_numbers_drift` thread.

### 2. The tight gate IS the drawdown control - you cannot also have long holds

Median hold on the baseline is 21 days, which is not a stage-2 holding period;
Weinstein advances run months. The cause is not rank churn - widening the exit
buffer to 400 (pure gate-only exit) leaves median hold at 21 days. It is that
the seven-condition gate is ANDed, so one dip below the 50 DMA drops the name.

Splitting entry from hold (strict trend template to enter, Weinstein's actual
sell rule - lost the 150 DMA, MA no longer above the 200 - to exit) does
exactly what it should mechanically, and then hands back the whole reason to
run S2 (`data/asymmetric_gate.csv`):

| Config | Median hold | Trades > +100% | OOS CAGR | OOS Max DD | OOS Calmar |
|---|---|---|---|---|---|
| `A_rs` symmetric, buffer 40 | 35d | 0.87% | 20.44% | -32.86% | 0.62 |
| `A_rs` asymmetric, buffer 40 | 77d | 2.36% | 19.85% | -40.05% | 0.50 |
| `D_blend` symmetric, buffer 40 | 35d | 0.62% | 18.84% | -33.41% | 0.56 |
| `D_blend` asymmetric, buffer 40 | 56d | 1.78% | 19.52% | -39.59% | 0.49 |

Holds get 2-3x longer and tail trades 3-4x more common, for no return, and the
drawdown goes straight back to TL25/L6 territory. This is the opposite of the
VCP relook's finding, and for a clear reason: there the exit ladder was the
*only* exit, so loosening it released a power-law tail. S2 is not a tail book
(0.04-0.6% of trades exceed +100%; win rate 42.3%, average win +10.7% against
average loss -5.6%). Its edge is a high hit rate on short advances, and the
constant exiting is what produces that.

## Caveats

- **No fundamentals anywhere in this.** There is no earnings or financials
  feed in the repo, so "growth" here means price and volume behaviour only -
  RS percentile, the 52-week-range position, and up/down volume. No claim in
  this document is a fundamentals claim. A real growth leg needs the
  point-in-time feed that is still the open thread from the breakout-call
  research.
- **The ranking leg is not settled.** IS ranks `C_nofresh` best and `D_blend`
  worst; OOS reverses it, on *both* data bases. Consistent across bases means
  it is probably a regime difference (2009-2016 rewarded quality, 2017-2026
  rewarded relative strength) rather than noise - but an IS-only selection
  rule would have picked the wrong variant here, so `D_blend`'s numbers are
  OOS-selected and should be read as an upper bound. The gate is the robust
  part; the rank is not.
- **The sector cap misses promoter groups.** The two worst days in the study
  are Adani events (2023-01-27, -14.7%; 2024-11-21, -8.2%), and the Adani
  complex spans five Zerodha sectors, so a sector cap does not touch it. The
  Jun-2024 election crash (-12.6%) was a PSU/power event that the cap does
  partly catch. Those are all real market events, not data errors.
- **Sector map is anachronistic and partial** - 484 of 854 panel symbols
  (57%), current snapshot applied to all history. Unmapped symbols are each
  treated as their own group, so they are never capped. This makes the
  reported cap effect a lower bound.
- **Panel ends 2026-08-21**, the merged panel's last bar, not 2026-09-08.
- Prices are split/bonus back-adjusted, and the stage-2 gate is built entirely
  from ratios (price vs MA, price vs 52-week range), so the price-level bias
  documented in `reference_price_panel_split_adjusted` does not apply here.

## Verdict

S2 does what it was asked to do: it is a trend-following book built on a
different primitive, it holds a genuinely different set of names, and its
drawdown profile is materially better than the momentum books on every basis
tested. It does not beat them on return.

Whether that earns a production slot is a founder call. The case for it is as
a defensive or diversifying sleeve - it is the best-Calmar book in the set and
it de-risks itself in stress without a regime overlay. The case against is
that COMBO Defensive already occupies that slot, S2 turns over 150-250 buys a
year against TL25's 110, and the ranking leg is unsettled.

The survivorship finding is the more urgent item and is independent of any of
this.

---

# Addendum 2026-09-09 - founder spec (variant E)

Requested changes from `D_blend`: score = relative strength + un-extension
only (0.5/0.5); stage-age minimum removed; 20 names; no sector cap; no trim
back to 7.5% (drift); exit on gate failure or leaving the top (20 + 10); no
stop.

## Result

| Basis | Window | CAGR | Max DD | Sharpe | Calmar | Alpha |
|---|---|---|---|---|---|---|
| Snapshot | IS | 25.46% | -37.40% | 1.34 | 0.68 | - |
| Snapshot | OOS | 26.50% | -43.14% | 1.23 | 0.61 | +12.54pp |
| Survivorship-free | IS | 15.41% | -45.32% | 0.81 | 0.34 | - |
| Survivorship-free | OOS | 13.83% | -42.47% | 0.66 | 0.33 | **-0.12pp** |

On the survivorship-free basis this does not beat the NIFTY 500. Turnover
rises to 322 buys/year and median hold falls to 14 days.

## Attribution - four of the five changes are cheap, one is not

One-at-a-time from the `D_blend` baseline, survivorship-free OOS
(`data/ablation_e.csv`):

| Change | OOS Calmar | OOS Max DD | vs baseline |
|---|---|---|---|
| baseline `D_blend` | 0.65 | -30.69% | - |
| score -> RS + un-extension only | 0.53 | -32.87% | -0.12 |
| **stage-age minimum removed** | **0.35** | **-47.80%** | **-0.30** |
| top_n 22 -> 20 | 0.59 | -34.25% | -0.06 |
| sector cap removed | 0.52 | -35.76% | -0.13 |
| trim removed (drift) | 0.61 | -32.51% | -0.04 |
| all five together | 0.33 | -42.47% | -0.32 |

Removing the stage-age minimum costs more than the other four combined, and it
is the only change that hurts in **both** windows on **both** data bases - IS
Calmar 0.70 to 0.37 survivorship-free, 1.19 to 0.62 on snapshot. Everything
else the founder asked for is close to free.

## Restoring the guards, keeping the rest of the spec

`data/variant_e_guards.csv`:

| Config | IS Calmar | OOS CAGR | OOS Max DD | OOS Calmar | Trades/y | Peak sector |
|---|---|---|---|---|---|---|
| *Survivorship-free* | | | | | | |
| E as specified | 0.34 | 13.83% | -42.47% | 0.33 | 322 | 52.2% |
| E + stage-age 21 | 1.05 | 16.33% | -38.17% | 0.43 | 212 | 53.7% |
| E + stage-age 21 + cap 4 | 1.01 | 16.72% | -34.23% | 0.49 | 212 | 31.4% |
| `D_blend` reference | 0.70 | 20.05% | -30.69% | 0.65 | 183 | 30.3% |
| *Snapshot* | | | | | | |
| E as specified | 0.68 | 26.50% | -43.14% | 0.61 | 332 | 51.4% |
| E + stage-age 21 | 1.40 | 28.06% | -32.87% | 0.85 | 220 | 48.0% |
| E + stage-age 21 + cap 4 | 1.42 | 26.37% | -31.28% | 0.84 | 219 | 30.8% |
| `D_blend` reference | 1.19 | 35.29% | -27.51% | 1.28 | 177 | 30.6% |

**`E + stage-age 21` is the best IS configuration in the whole study** - IS
Calmar 1.05 survivorship-free and 1.40 on snapshot, against `D_blend`'s 0.70
and 1.19. It loses to `D_blend` OOS. That is the same split the study has hit
throughout: the 2009-2016 window rewards the simpler, quality-led rank and
2017-2026 rewards the RS-led one, so neither score choice is settled and
`D_blend`'s OOS lead remains partly a selection artefact.

The stage-age minimum is not in that category. It helps everywhere.

## What the stage-age filter actually does

It is **not** better stock selection. In the no-filter run, 61% of entries
(1,866 of 3,036) go in with under 21 days of confirmed structure, and their
per-trade record is indistinguishable from the confirmed ones:

| Entry | n | Win rate | Mean P&L | Median hold |
|---|---|---|---|---|
| stage age < 21d | 1,866 | 40.6% | +1.09% | 14d |
| stage age >= 21d | 1,170 | 40.5% | +0.95% | 14d |

(Both drawn from the same no-filter run, so the mature group is the residual
after young names took slots - this compares entries within one book, not the
two configurations against each other.)

The benefit shows up at portfolio level, not trade level: without the filter a
name qualifies on the first day all seven conditions align, so twenty slots
fill with day-one breakouts at the same moment in whatever theme is popping.
Peak sector weight goes to 52%, turnover rises 50%, and the drawdown widens -
on identical per-trade economics.

## Recommendation

Keep the founder's score, 20 names, drift and buffer 10. Restore the stage-age
minimum; it is the cheapest risk control in the study and the only parameter
that tested positive in every window on every basis. The sector cap is worth
another 0.06 Calmar and 4pp of drawdown survivorship-free, and is roughly free
on snapshot - take it if the 52% single-sector concentration is unacceptable,
which given the Adani and PSU episodes in this sample it probably is.

---

# Addendum 2 - fixing hold time (S2-v2)

## The diagnosis was correct

Hold time on the same survivorship-free data, OOS:

| Book | Median hold | Mean | p90 | Turnover |
|---|---|---|---|---|
| TL25 v3 | 56d | 67d | 126d | 5.8x/yr |
| Variant E as specified | 14d | 22d | 49d | 16.1x/yr |
| L6-like | 14d | 34d | 91d | 11.1x/yr |

S2 was turning the book over 16 times a year against TL25's 5.8.

## What did not work

Loosening the hold gate alone. Tested earlier: it buys hold time by tolerating
deterioration, so drawdown widens roughly in step (-30% to -40%). Also
`min_hold_days`, which helps IS and hurts OOS.

## What worked: exit confirmation

A name is sold only after it fails the keep test on **N consecutive weekly
checks**, rather than the first time. This is the exact mirror of the entry
stage-age rule - one bad week is noise on the way out as much as on the way in.
It lengthens holds by removing whipsaw rather than by tolerating damage, which
is why it improves drawdown instead of costing it.

`exit_confirm_weeks = 3` vs 1 improves OOS Calmar in **16 of 16** comparisons
across both data bases, every hold mode and both stage-age settings
(`data/hold_time_*.csv`). Nothing else in this study has been that consistent.

Pushing confirmation deeper keeps raising CAGR and hold time, but drawdown
stops improving past 3-4 weeks - beyond that the extra return is bought with
risk (`data/confirm_depth.csv`).

## S2-v2

Your spec, unchanged: RS + un-extension score (0.5/0.5), 20 names, no sector
cap, drift, no stop, no stage-age minimum. Three changes to the exit only:

- **Hold gate tiered.** Entry still needs all seven conditions plus RS >= 70.
  Holding needs only the structure: above the 150 and 200 DMA, 50 > 150 > 200,
  200 DMA rising. Slipping under the 50 DMA or out of the top quartile of the
  52-week range no longer forces a sale.
- **Exit confirmation 3 weeks.**
- **Exit buffer 40** (keep set = top 60 rather than top 30).

| Basis | Window | CAGR | Max DD | Sharpe | Calmar | Median hold | Turnover | Trades >+50% |
|---|---|---|---|---|---|---|---|---|
| Survivorship-free | IS | 16.53% | -28.07% | 0.91 | 0.59 | 91d | 3.2x | 5.69% |
| Survivorship-free | OOS | 25.57% | -34.56% | 1.28 | 0.74 | 84d | 3.5x | 3.83% |
| Snapshot | IS | 27.56% | -23.37% | 1.54 | 1.18 | 92d | 3.1x | 6.42% |
| Snapshot | OOS | 32.04% | -35.50% | 1.56 | 0.90 | 77d | 3.6x | 5.04% |

Against variant E as originally specified, survivorship-free OOS:

| Metric | E | S2-v2 |
|---|---|---|
| CAGR | 13.83% | **25.57%** |
| Max DD | -42.47% | **-34.56%** |
| Sharpe | 0.66 | **1.28** |
| Calmar | 0.33 | **0.74** |
| Median hold | 14d | **84d** |
| Turnover | 16.1x | **3.5x** |
| Alpha vs NIFTY 500 | -0.12pp | **+11.4pp** |

Against TL25 v3 native on the same data (22.66% / -40.50% / Sharpe 1.03 /
Calmar 0.56 / 56d / 5.8x), S2-v2 is ahead on every axis: return, drawdown,
Sharpe, Calmar, hold time and turnover. On the snapshot basis TL25 still leads
on CAGR (37.64% vs 32.04%) and ties on Calmar.

## Two earlier conclusions now change

**The stage-age minimum is no longer needed - and now costs.** Adding it back
on top of S2-v2 drops survivorship-free OOS Calmar 0.74 to 0.61 and CAGR
25.57% to 18.30%, and leaves the book only 75% invested. Entry confirmation
and exit confirmation were doing the same job (filtering whipsaw); the exit
side does it better and cheaper. The founder's instinct to remove the entry
filter was right - it just needed the compensating control on the exit, which
the earlier addendum's recommendation did not have. That recommendation is
superseded.

**The sector cap now costs too.** With 84-day holds it forces selling of
winners in a leading sector: survivorship-free OOS Calmar 0.74 to 0.61, DD
-34.56% to -38.04% (roughly neutral on snapshot). It still does its job on
concentration - peak sector weight 54% to 25% - so it is now a genuine risk
preference rather than a free control.

**The stop remains a non-lever**, as before: 25% costs a little, 30% is inside
the noise, even with holds five times longer.

## What is unchanged and still open

- Peak sector weight reaches 54% survivorship-free without the cap. Given the
  Adani and PSU episodes in this sample that is the main residual risk, and
  the cap is the only tested control for it.
- Tail participation is better but still thin: 3.8% of trades exceed +50% and
  0.9% exceed +100%, against 2.4% / 0.6% for the short-hold version.
- IS and OOS still disagree on level (survivorship-free IS Calmar 0.59 vs OOS
  0.74). The exit-confirmation *direction* is consistent across both; the
  absolute numbers are not.

---

# Addendum 3 - does S2-v2 hold up as a separate offering?

All five books run on identical panel, calendar, membership, benchmark and
costs. TL25 v3, L6 v2, OM25 v3 and COMBO Defensive each run at their locked
production config through `scripts/_clean_engine.run_strategy` - the same
engine production uses. Window starts 2010-01-04, where the NIFTY 100 history
that OM25 and COMBO need for their regime panel begins.

Harness check: TL25 v3 native measures 33.33% OOS CAGR on the snapshot basis
against its published 34.86%, so the replication is faithful to ~1.5pp.

## The two data bases disagree, and not by a little

**Survivorship-free** (reconstructed membership, 854 symbols):

| Book | IS Calmar | OOS CAGR | OOS DD | OOS Sharpe | OOS Calmar | Hold | Turnover |
|---|---|---|---|---|---|---|---|
| **S2-v2** | 0.49 | **25.57%** | **-34.56%** | **1.28** | **0.74** | 84d | 3.5x |
| L6 v2 | 0.44 | 23.50% | -46.00% | 0.97 | 0.51 | 21d | 8.8x |
| OM25 v3 | 0.56 | 21.41% | -36.14% | 1.05 | 0.59 | 77d | 3.4x |
| TL25 v3 | 0.72 | 18.50% | -43.56% | 0.88 | 0.42 | 42d | 6.4x |
| COMBO Defensive | 0.58 | 14.47% | -37.97% | 0.79 | 0.38 | 28d | 3.3x |

**Snapshot** (production membership):

| Book | IS Calmar | OOS CAGR | OOS DD | OOS Sharpe | OOS Calmar | Hold | Turnover |
|---|---|---|---|---|---|---|---|
| L6 v2 | 0.87 | 45.45% | -37.16% | 1.81 | 1.22 | 21d | 7.9x |
| OM25 v3 | 0.99 | 35.44% | -35.01% | 1.71 | 1.01 | 84d | 3.0x |
| TL25 v3 | 1.16 | 33.33% | -40.55% | 1.54 | 0.82 | 42d | 6.1x |
| COMBO Defensive | 1.25 | 33.19% | **-31.26%** | 1.78 | 1.06 | 28d | 5.2x |
| **S2-v2** | 1.10 | 32.04% | -35.50% | 1.56 | 0.90 | 77d | 3.6x |

Survivorship-free, S2-v2 is the best book in the lineup on CAGR, drawdown,
Sharpe and Calmar simultaneously. On snapshot it is last on CAGR and Sharpe
and second-last on Calmar. Same strategy, same window, same engine.

This is not noise, and the direction is explainable: **S2 benefits least from
survivorship because its gate is structural rather than return-chasing.** The
momentum books rank on trailing return, so a universe restricted to today's
survivors hands them exactly the names they would have wanted; L6 gains 22
points of CAGR moving from the honest basis to the biased one, S2-v2 gains 6.

## Differentiation - passes cleanly, on both bases

OOS holdings overlap (mean Jaccard) and weekly return correlation:

| Pair | Overlap (SF / snapshot) | Correlation (SF / snapshot) |
|---|---|---|
| S2-v2 vs COMBO | 0.105 / 0.139 | **0.590 / 0.688** |
| S2-v2 vs TL25 v3 | 0.116 / 0.099 | 0.802 / 0.807 |
| S2-v2 vs OM25 v3 | 0.123 / 0.123 | 0.792 / 0.816 |
| S2-v2 vs L6 v2 | 0.204 / 0.186 | 0.853 / 0.834 |
| *(reference)* TL25 vs L6 | 0.295 / 0.292 | 0.902 / 0.902 |
| *(reference)* OM25 vs COMBO | 0.172 / 0.354 | 0.721 / 0.793 |

S2-v2 shares 10-20% of its names with any existing book - lower than the
production books share with each other - and is the least correlated pair with
COMBO on both bases. As a *distinct* product it is not in question.

It also has one property no other book has, on either basis: 77-84 day median
holds at 3.5x turnover, against 21-42 days and 5-9x for TL25 and L6. That
matters for STCG churn and for capacity.

## Marginal value to the lineup

Equal-weight blend of the four production books, with and without S2-v2, OOS:

| Basis | Blend | CAGR | DD | Sharpe | Calmar |
|---|---|---|---|---|---|
| Survivorship-free | 4 books | 19.77% | -36.08% | 1.02 | 0.55 |
| Survivorship-free | + S2-v2 | **21.00%** | **-32.47%** | **1.11** | **0.65** |
| Snapshot | 4 books | 37.14% | -29.69% | 1.79 | 1.25 |
| Snapshot | + S2-v2 | 36.25% | -29.41% | 1.80 | 1.23 |

Survivorship-free, adding S2-v2 improves the blend on every axis. On snapshot
it is a wash. Correlation to the 4-book blend is 0.83-0.84 either way.

## Verdict

**Not yet.** The differentiation case is settled - S2-v2 is genuinely a
different book with a materially different turnover and holding profile. The
performance case is not, and it rests entirely on a question this task did not
set out to answer: which universe basis is right.

- If the survivorship-free basis is correct, S2-v2 is the best risk-adjusted
  book in the lineup, it dominates COMBO Defensive on both return and
  drawdown, and it improves the blend. It ships.
- If the snapshot basis is correct, it is the weakest book in the lineup, adds
  nothing to the blend, and COMBO already occupies its slot better. It does
  not ship.

Two further cautions that apply on both bases:

- **S2-v2 never leads the IS window** - 4th of 5 survivorship-free (Calmar
  0.49), 3rd of 5 on snapshot. Every favourable number it has comes from the
  2017-2026 OOS window alone. One window is one observation.
- **The survivorship-free basis is itself young.** The reconstructed
  membership and ex-member backfill were built on the `index_reconstruction`
  branch in the last week; 166 of 1,020 symbols still have no prices. It is
  the more honest basis in principle, not yet a validated one.

**The blocking item is not S2.** It is the survivorship question already
queued in TASKS.md, which decides this verdict and independently decides
whether the published track record for all four production books needs
restating. That should be settled first; S2-v2 can wait behind it.

---

# Addendum 4 - the 2020+ window

`docs/portfolios.md` quotes L6 v2 at CAGR 59.4% / Sharpe 1.92 / MaxDD -30.0% /
hit rate 49.3% for 2020-07-10 to 2026-02-02. Both that window and the one the
daily pipeline actually runs (`--start 2020-01-01`) re-measured here
(`data/from2020.csv`):

## L6 v2

| Basis | Window | CAGR | Max DD | Sharpe | Sortino | Calmar | Win rate |
|---|---|---|---|---|---|---|---|
| Snapshot | published (2020-07-10..2026-02-02) | 54.06% | -29.89% | 2.07 | 2.46 | 1.81 | 49.9% |
| Snapshot | prod (2020-01-01+) | 47.76% | -37.84% | 1.79 | 2.07 | 1.26 | 49.0% |
| Survivorship-free | published | 31.20% | -37.17% | 1.22 | 1.42 | 0.84 | 44.8% |
| Survivorship-free | prod | 29.40% | -40.67% | 1.12 | 1.27 | 0.72 | 45.3% |

**The published figure replicates on drawdown and hit rate almost exactly**
(-29.89% vs -30.0%, 49.9% vs 49.3%) and comes in 5.3pp light on CAGR (54.06%
vs 59.4%) - panel build, benchmark and membership vintage differ. Treat the
harness as aligned and the residual as basis noise.

Decomposition of the published 59.4%: about 5pp is replication difference,
about 23pp is survivorship. On an honest universe the same window gives 31.20%.

Note the window choice alone is worth 6pp of CAGR and 8pp of drawdown. The
published window starts 2020-07-10, after the COVID bottom; the production
window starts 2020-01-01 and includes the crash.

## Full lineup, 2020-01-01 onward

| Basis | Book | CAGR | Max DD | Sharpe | Calmar | Hold | Turnover | Win rate |
|---|---|---|---|---|---|---|---|---|
| Snapshot | L6 v2 | **47.76%** | -37.84% | 1.79 | 1.26 | 21d | 8.0x | 49.0% |
| Snapshot | OM25 v3 | 43.33% | -34.24% | 1.91 | 1.27 | 77d | 3.2x | 47.9% |
| Snapshot | COMBO | 37.62% | **-16.45%** | **1.95** | **2.29** | 28d | 4.9x | 33.6% |
| Snapshot | TL25 v3 | 37.12% | -34.14% | 1.59 | 1.09 | 42d | 6.4x | 47.9% |
| Snapshot | S2-v2 | 34.01% | -35.71% | 1.57 | 0.95 | 77d | 3.8x | **58.1%** |
| SF | L6 v2 | **29.40%** | -40.67% | 1.12 | 0.72 | 21d | 8.8x | 45.3% |
| SF | OM25 v3 | 25.75% | -35.88% | 1.15 | 0.72 | 70d | 3.6x | 47.5% |
| SF | S2-v2 | 24.27% | -34.15% | 1.15 | 0.71 | 77d | 3.7x | **55.0%** |
| SF | TL25 v3 | 23.27% | -35.38% | 1.02 | 0.66 | 42d | 6.6x | 44.7% |
| SF | COMBO | 21.93% | **-19.71%** | 1.13 | **1.11** | 28d | 2.9x | 30.6% |

L6 v2 has the highest CAGR in every cell, and pays for it with the highest
turnover (8-8.8x), the shortest holds (21d) and the worst drawdown.

## This changes the S2 vs COMBO read

Every book's worst 2020+ drawdown is the same event - 23-24 March 2020:

| Book | Worst DD | Date | Cash on 2020-03-31 |
|---|---|---|---|
| L6 v2 | -37.84% | 2020-03-24 | 0.5% |
| S2-v2 | -35.71% | 2020-03-24 | 35.4% |
| COMBO | -16.45% | 2020-03-23 | **84.3%** |

Addendum 3 found S2-v2 had the lowest drawdown of the lineup over 2017-2026
survivorship-free. That holds, but it is not the whole picture: in a fast
market-wide crash COMBO's regime overlay is far better than S2's gate. The
overlay reads one index against its 100-DMA and cuts gross exposure within
days; S2's gate has to wait for individual names to break structure, and got
only 35% to cash while COMBO got 84%.

S2-v2's drawdown advantage is against slow, rotational drawdowns. It is not a
crash hedge, and it does not displace COMBO Defensive on the axis COMBO
exists for. That weakens the case in Addendum 3 further: on the 2020+ window
S2-v2 is last on Calmar on the snapshot basis and third of five
survivorship-free.

Its one distinctive edge across every cell is win rate - 55-58% against
30-50% for the rest - alongside the longest holds and near-lowest turnover.
