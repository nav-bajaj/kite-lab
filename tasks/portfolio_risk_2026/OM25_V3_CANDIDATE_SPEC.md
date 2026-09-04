# OM25 v3 + ROC overlay, stop removed — what it actually does

Plain-language spec of the candidate configuration. Everything marked
**[NEW]** differs from what runs in production today.

## What it buys

- **Universe: the Nifty 250** — India's 250 largest listed companies (Nifty
  100 plus the next 150). Nothing outside that list is ever bought.
- **Point-in-time membership.** A stock is only eligible to buy if it was
  actually in the index on that date. If a stock later drops out of the index,
  it is not force-sold — it leaves on the normal exit rules.

## How it ranks stocks

Every stock is scored on how it behaved over the **last 252 trading days
(~1 year)**, against the equal-weighted average of the eligible universe:

- **Upside capture (UC)** — on days the market rose, how much of that rise did
  the stock capture?
- **Downside capture (DC)** — on days the market fell, how much of that fall
  did it take?
- **Capture ratio (CR) = UC / DC** — reward per unit of pain.

Both UC and CR are converted to percentile ranks across all eligible stocks,
so the score is always relative to peers, never an absolute threshold.

To be scored at all, a stock must have: at least 220 days of price history in
the window, a **positive total return** over the 252 days, and at least 50 up
days and 50 down days to measure against.

## How the ranking shifts with the market

A separate market-condition signal decides how the two components are weighted:

- **Signal:** NIFTY 100 versus its 100-day moving average, with a 3-day
  confirmation before it changes state.
- **Bull:** score = 50% upside-capture rank + 50% capture-ratio rank — reward
  stocks that participate in rallies.
- **Bear:** score = 100% capture-ratio rank — stop rewarding upside entirely
  and rank purely on resilience.

This changes *what it buys*, not how much.

## **[NEW]** How much it stays invested

A second, independent signal decides exposure:

- **Signal:** the **NIFTY 100 index level today versus 31 trading sessions ago**
  (roughly six weeks). Higher = risk-on, lower = risk-off. Confirmed over
  3 consecutive days before it flips, and always acts on the prior day's
  close, so there is no hindsight. (NIFTY 100 rather than NIFTY 500: the two
  give near-identical results, but NIFTY 100 history reaches back to 2010 and
  so allows five more years of testing.)
- **Risk-on: 100% invested.**
- **Risk-off: 75% invested** — the portfolio sells 25% pro-rata across every
  holding and holds the rest in cash. It also stops making new purchases while
  risk-off.
- **Returning to risk-on:** the cash is redeployed at the next scheduled
  rebalance, not immediately.

This changes *how much* it holds, never *what* it holds. Historically it sits
risk-off roughly 30% of the time, and flips about five times a year.

## The portfolio

- **25 stocks**, equal weighted — 4% target each, hard cap 7.5%.
- **Weights are allowed to drift** after purchase. Winners are not trimmed
  back to 4%.

## When it trades

- **Ranking is computed every second Friday** (bi-weekly).
- **Orders execute the next trading day** at the average of that day's open,
  high, low and close — a realistic fill assumption, not the closing price.
- **A rank check also runs every Friday** to catch exits between rebalances.

## When it sells a stock

- **When its rank falls below 45.** The portfolio holds 25 names but tolerates
  a stock slipping to rank 45 before selling — a deliberate buffer so ordinary
  wobble does not trigger a trade. A stock ranked 30 is held, not sold.
- **[NEW] The 20% per-stock trailing stop-loss is removed.** Previously any
  holding that fell 20% from its own peak was sold automatically; that
  accounted for **39% of all exits** in production. Under this configuration
  the only stock-level exit is the rank rule, and downside protection comes
  from the portfolio-level exposure cut instead.
- A stock is otherwise held indefinitely, however long it stays highly ranked.

## Costs assumed

- **0.2% slippage per side** on every trade.
- **Brokerage and tax are not modelled.** With bi-weekly rebalancing, real
  after-tax returns will be materially lower than the figures above.

## What changes versus production, in one line each

1. Add a NIFTY-100 6-week-momentum exposure switch: 100% invested in risk-on,
   75% in risk-off.
2. Remove the 20% per-stock trailing stop.
3. Everything else — universe, score, regime tilt, 25 names, bi-weekly
   cadence, rank-45 exit buffer, sizing, slippage — is unchanged.

## What it delivered in walk-forward testing

2013-07 to 2026-08 (**13.1 years**), with the exposure-signal settings
re-chosen every year using only data available at the time:

| | production today | this candidate |
|---|---:|---:|
| Annualised return | 34.5% | 30.8% |
| Sharpe | 1.88 | **2.03** |
| Worst drawdown | -34.8% | **-23.4%** |
| Worst 12-month outcome | -19.0% | **-11.6%** |
| Share of start dates losing money over 12 months | 21.7% | **17.3%** |
| Share of days more than 20% down | 7.0% | **0.3%** |

**The trade: roughly 4 points of annual return, in exchange for a materially
gentler ride.**

## Honest limitations

- The exposure signal is tested from 2010, the start of NIFTY 100 history —
  **16 years containing roughly five drawdown episodes.** Longer than the rest
  of this work, still not a full market cycle history.
- The 2018-19 mid-cap bear was the episode that motivated the work, so it is
  not an independent test of it.
- Removing the stop is removing tail insurance. On 2015-2026 it cost more
  return than it saved in drawdown — that is not evidence about a 2008-style
  event, which this sample does not contain.
- Nothing here is live-tested. It is a backtest.
