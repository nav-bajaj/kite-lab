# Results — suggested capital and SIP

Phase 1. Run 2026-09-06, live prices as of 2026-08-21.
Reproduce: `python tasks/minimum_capital_2026/capital_sizing.py`
(writes `runs/capital_sizing.json`).

Phase 2 (the price-cap study) is in `RESULTS_PRICE_CAP.md` and **changes
the recommendation below** — read both before acting.

---

## Recommendation

| | uncapped books (today) | with a Rs 4,000 price cap |
|---|---|---|
| practical minimum | **Rs 5L** | Rs 1-2L |
| recommended ticket | **Rs 10L** | Rs 2-3L |
| SIP floor | Rs 10,000/month | Rs 10,000/month |
| SIP recommended | Rs 25,000/month on a Rs 10L base | scales with the ticket |

Answering the original question directly: **Rs 5-10L, not Rs 1-5L.** The
bottom of the Rs 1-5L band is structurally broken and the top of it
barely works.

## Why Rs 1-5L is the wrong band

Position size is `capital / 25`. At Rs 1L that is Rs 4,000, and the
production books hold names far above it — POWERINDIA Rs 34,190,
NEULANDLAB Rs 23,301, APARINDS Rs 16,856. Those positions cannot be
opened at all.

Current books, whole-share feasibility:

| capital | position | unbuyable names | cash stranded | RMS weight error |
|---|---|---|---|---|
| Rs 1L | Rs 4,000 | 1-6 per portfolio | 18-38% | 29-53% |
| Rs 3L | Rs 12,000 | 0-2 | 10-17% | 21-31% |
| Rs 5L | Rs 20,000 | 0-1 | 4-11% | 6-24% |
| Rs 10L | Rs 40,000 | 0 | 2-6% | 3-7% |

At Rs 1L a client owns 19 of 25 names. That is not the strategy, it is a
distorted subset of it.

## Fixed costs settle it

DP charge is ~Rs 15.93 per scrip per sale regardless of size, and these
books sell a lot — median full-year sale events: 69 (OM25), 162 (TL25),
185 (L6), 202 (COMBO).

| all-in explicit cost drag | Rs 1L | Rs 3L | Rs 5L | Rs 10L | Rs 20L |
|---|---|---|---|---|---|
| Quality Momentum | 1.38% | 0.65% | 0.50% | 0.39% | 0.34% |
| Trend Leaders | 3.31% | 1.59% | 1.25% | 0.99% | 0.86% |
| Core Momentum | 3.78% | 1.82% | 1.43% | 1.13% | 0.98% |
| Defensive Blend | 3.80% | 1.65% | 1.22% | 0.90% | 0.74% |

DP + STT + stamp + txn/GST. The 0.2% slippage is already inside the
published CAGRs. At Rs 1L a follower loses 3-4%/yr to friction on the
higher-turnover books; at Rs 10L it is under 1.2% and mostly the
turnover component that no amount of capital fixes.

## Why Rs 10L specifically

Position becomes Rs 40,000, which covers **99.6%** of the NSE 500 at
1+ share, **94.9%** at 5+ shares, **88.8%** at 10+ shares (rounding
error under 5%).

Independently: every production backtest runs at
`initial_capital: 1000000`. Suggesting Rs 10L means the client's
experience and our published evidence are the same object.

Capacity is not a constraint anywhere near here — at Rs 5 cr a position
is still only ~1.9% of a p10-liquidity name's daily traded value.

## SIP

The lumpsum is not optional and a SIP cannot substitute for it. Starting
at Rs 25,000/month means holding 1-2 names for the first year. Cross the
minimum first, then SIP.

Deploy each month's SIP into the 1-3 most underweight names at the next
rebalance — never spread across all 25, because Rs 25,000/25 = Rs 1,000,
below the price of ~30% of the universe.

| monthly SIP | buys >=1 share in | >=3 shares | verdict |
|---|---|---|---|
| Rs 5,000 | 91.6% of names | 71.5% | too granular |
| **Rs 10,000** | 96.1% | 86.3% | floor |
| **Rs 25,000** | 98.7% | 95.5% | recommended on a Rs 10L base |
| Rs 50,000 | 99.8% | 97.6% | funds a full new position monthly |

Tiers: **Rs 5L + Rs 10k/month** (entry), **Rs 10L + Rs 25k/month**
(recommended), 10% annual step-up. Rs 25k/month is 30% of a Rs 10L
corpus per year.

SIP buys are nearly free — no DP charge on buys, zero delivery brokerage
at Zerodha, ~0.02% stamp/txn plus slippage. There is no cost argument for
quarterly instead of monthly. Time it to the portfolio's own rebalance
date (bi-weekly Friday for Quality Momentum / Trend Leaders / Defensive
Blend, weekly Thu-signal/Fri-execute for Core Momentum).

## Cross-reference: SIP outcomes are already measured elsewhere

`tasks/portfolio_risk_2026/` §19 (`sip_analysis.py`, `runs/sip_analysis.csv`)
measures the *outcome distribution* of a SIP — money-weighted XIRR by
holding period, every start month 2013-07 to 2026-08. That is the
complement of this file: it asks what a SIP returns, this one asks what
amount is mechanically deployable. It happens to run at exactly
Rs 10,000/month, the floor recommended above.

Two of its findings should travel with any SIP guidance we publish:

- **Duration matters more than amount.** A 1-year SIP into production
  OM25 was positive only 80.8% of the time with a worst case of -28.1%
  XIRR; 2-year 90.3%, 3-year 95.9%, 5-year 100%. Pair the suggested SIP
  amount with a stated minimum horizon — on that evidence, 3 years.
- **Do not claim SIP reduces volatility of outcomes.** It does not here —
  the XIRR spread is *wider* than the lump-sum CAGR spread at most
  horizons. What it does is lift the bad outcomes (5th-percentile 3-year
  SIP +5.9% vs +0.9% lump sum). It truncates the left tail rather than
  narrowing the distribution.

## Flags

**No projection figures are published here.** A 5-year lumpsum+SIP
projection was run during the session at 12% / 18% / 25%; **those rates
were assumed, not derived from anything in this repo**, so they are
deliberately excluded. If a SIP calculator ships, the assumption must be
chosen deliberately — do not let the 35-59% backtest CAGRs become the
implied forward number.

**Framing.** "Suggested capital" and "suggested SIP" read closer to
investment advice than the portfolio pages do, and the site is gated
pending SEBI. This is the same gate as `tasks/client_portal/TASKS.md`
row P-1 (publishing buy/sell model portfolios can trigger SEBI Research
Analyst / Investment Adviser registration) — suggesting a ticket size
and a monthly contribution sits closer to that line, not further from
it. Prefer the operational framing — "below Rs 5L the portfolio
cannot be replicated accurately, here is the arithmetic" — over a
recommendation about how much someone should invest. The whole-share and
cost tables support the first framing on their own.
