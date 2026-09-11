# Trend screen — a browsable list of what to hold and what to avoid

## The product

Subscribers open a screen and see which stocks are trending, read a 15-second
summary of each one's trend structure off the chart, and see a separate list of
names to avoid. Once the trend classification is accepted, the same engine
recommends where in the trend to act — near the 50-day, inside the 50/100
band, on a triangle breakout.

Founder's direction, 2026-09-11. This supersedes the breakout-calls product
idea, not the research: `breakout_calls_2026` measured the pattern honestly,
failed 5 of 7 portfolio gates, and its per-trade and exit machinery is reused
here wholesale.

## Universe — settled (👤 2026-09-11)

**Top 500 by trailing turnover AND above the turnover-scaled floor, point in
time, survivorship-free.** 1,716 names, of which **1,134 stop trading before
2026** — delisted companies are carried at last traded price, so the screen
never sees only the survivors.

**Rank alone is not enough, and the first run of this task got that wrong.**
The screen was originally built on a pure top-750 rank over the whole store. A
rank is not a liquidity test: the 750th name by turnover traded **₹0.03cr a
day in 2006** and the 500th traded ₹0.24cr. Those are not investable at any
size, and their presence flattered the early-era results and made the first
capacity test look like a collapse. The floor (₹10cr in 2026 money, deflated
by aggregate market turnover) is what removes them — it cuts 132 names from
the 2006 universe and nothing at all from 2022 onward.

**Not Nifty 500 index membership.** PIT membership scores worse (14.3% CAGR,
Sharpe 0.56, 2013-2019 at 0.29) because membership lags price — a stock joins
the index after it has already run. Turnover rank plus a floor is a better
definition of "our market" than the index is.

Everything in this task was re-run on the clean universe. Nothing broke, and
the portfolio got *better* (22.4% CAGR / 0.83 Sharpe, against 19.4% / 0.78 on
the dirty one) — removing the illiquid tail removed noise, not signal.

## The core claim is a forward-return claim, so it was tested first

Per CLAUDE.md's TDD policy. Every name classified at every month-end,
2006-2026 on the clean universe: **99,322 observations, 1,716 names.** Forward
returns measured as **excess over the same month's cross-sectional mean**, so
market direction is netted out.

Raw returns would have been actively misleading here: DOWNTREND names show a
higher raw 12-month return (+25.9%) than LEADING names (+20.5%), purely
because downtrends cluster near bear-market lows where everything subsequently
rises. On an excess basis DOWNTREND is the worst bucket. Any published figure
uses excess.

| state | share | 3m | 6m | 12m | hit 6m | per-era 6m |
|---|---|---|---|---|---|---|
| EXTENDED | 3% | +4.0% | +6.4% | +10.6% | 46% | +6.7 / +7.1 / +5.6 |
| LEADING | 25% | +1.6% | +2.8% | +4.4% | 48% | +3.6 / +3.7 / +1.5 |
| ADVANCING | 27% | −0.1% | +0.4% | +0.5% | 43% | +0.3 / +0.5 / +0.4 |
| BASING | 6% | −0.6% | −1.5% | −1.8% | 40% | −1.5 / −1.3 / −1.7 |
| WEAKENING | 11% | −1.0% | −2.3% | −3.9% | 40% | −2.2 / −3.0 / −1.6 |
| DOWNTREND | 28% | −1.3% | −2.5% | −4.0% | 38% | −2.5 / −3.0 / −2.0 |

**The ordering holds in all three eras.** Buy list (LEADING+EXTENDED) versus
avoid list (WEAKENING+DOWNTREND): **+3.1% at 3m, +5.7% at 6m, +9.1% at 12m.**

LEADING decays in the recent era (+3.6 / +3.7 / +1.5) and EXTENDED does not
(+6.7 / +7.1 / +5.6). Worth watching and worth stating; not a reason to stop.

## Two findings that change the design

### 1. It is a basket, not a stock picker

**Every bucket has a hit rate below 50% against the index**, LEADING included
(48% at 6m). Forward returns are right-skewed, so the mean is carried by a
minority while the median name in even the best bucket lags the market.

Important qualifier added 2026-09-11 (👤): *excess* hit rate is the wrong lens
for a subscriber. On **raw** returns the buy list wins 59% of the time at six
months with a 1.92:1 payoff, and with the 150-day trail attached the trade
expectancy is **+11.4% per trade on the whole list, +15.6% on the top 20**.
Expectancy, not hit rate, is the number to build on. The basket framing still
holds — one name is still a coin flip against the index — but "most of these
lose" was an overstatement and is corrected here.

A subscriber who picks one or two names off the leading list has a
worse-than-coinflip chance of beating the index, while the list as a whole
reliably beats it. The product must be framed and priced as a basket — hold
many, or hold the list — because the alternative is a subscriber who takes two
names, underperforms, and churns, having been told something true about a
population and heard it as a promise about a stock.

### 2. "Buy near the 50-day" looks backwards

EXTENDED — Stage-2 names trading more than 20% above their 50-day — is the
**best** bucket, not the worst: +6.4% excess at 6m against LEADING's +2.8%,
and it beats LEADING under **all 135 threshold configurations tried**. Not a
small sample, not one era, not one parameter set.

So waiting for a pullback toward the 50-day would select the weaker half of
the Stage-2 population. This contradicts the entry idea in the brief and it is
the first thing to settle before any buy-point feature is built.

**The honest caveat:** this is measured on buy-and-hold forward return from a
month-end snapshot. A pullback entry buys a tighter stop, so it can still win
on R-multiple while losing on raw return — and `breakout_calls_2026` §4 showed
R-multiple is what the exit ladder optimises. Entry location has to be
measured on both, which is phase 3 below.

## Phases

1. **Classifier hardening.** Thresholds are currently first-draft (20% above
   the 50 for EXTENDED, Minervini's Stage-2 template for LEADING). Sweep them,
   check the ordering survives, and check the buckets are stable month to month
   — a state that flickers is unusable in a subscriber-facing list.
2. **The 15-second read.** What the card says: state, how long in it, distance
   from the 50 and the 200, base structure and depth, distance to the pivot,
   relative strength. Every line must be something the classifier already
   knows to be true, not prose.
3. **Entry location.** Settle finding 2 properly: conditional on LEADING,
   measure forward return *and* R-multiple for entry near the 50, inside the
   50/100 band, and on a pivot breakout. Reuse the `breakout_calls_2026` exit
   ladder so the R comparison is like-for-like.
4. **The avoid list.** Cheapest defensible claim in the product and worth
   shipping first — DOWNTREND underperforms by 2.9% over 6 months, in every
   era, on 59,540 observations.
5. **Delivery.** How often the list refreshes, how churn is handled, and what a
   subscriber sees when a name leaves the list.

## Scope boundary

- No change to production portfolios.
- No published figure until phase 1 fixes the thresholds; today's numbers are
  a first draft of a taxonomy, not a validated product.
- Backtest-to-product gap: none of this yet accounts for what a subscriber
  actually does with the list. Phase 5.

## Carried over from `breakout_calls_2026`

| What | Where |
|---|---|
| PIT universe + turnover-scaled floor | `lib/universe.py` |
| Trend classifier and the forward-return test | `lib/trend_state.py` |
| Month-end features, 99k rows, clean universe | `data/features_t500*.parquet` (regenerated, not committed) |
| Base/pivot detector, exit ladder, book simulator | `tasks/breakout_calls_2026/lib/` |
| Adjusted panels, 2,519 names incl. 560 delisted | `data/master/prices/adjusted_pr/` |
