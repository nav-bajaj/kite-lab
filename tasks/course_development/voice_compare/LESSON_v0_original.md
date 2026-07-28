# Module 1 lesson — Define the market before you read it

Estimated learner time: 60 minutes including walkthrough, worksheet, and quiz.

## Opening question

How many stocks are in “the Indian stock market”?

You might answer 50 because the Nifty 50 appears in the news. You might answer
500 because Marketworks frequently discusses the NSE 500. You might open a
broker app, search broadly, and conclude there are several thousand.

Each answer points to something real. None defines “the market” by itself.

Before we ask whether the market is strong, weak, broad, narrow, expensive, or
stressed, we need to say **which securities we are measuring**.

That chosen set is our **universe**.

## What you will be able to do

At the end of this module, you can:

1. distinguish a company, security, exchange listing, index, and research
   universe;
2. sketch the main layers of India's exchange-listed equity landscape;
3. explain how the official Nifty 500 narrows the wider market;
4. explain why Marketworks uses a Nifty 500-derived universe;
5. distinguish free-float index weighting from equal-stock breadth; and
6. state what the Nifty 500 leaves out.

# Part 1 — “The market” is not one list

## Company

A company is the business: its factories, employees, software, brands,
contracts, debts, cash flows, and legal obligations.

## Security

A security is a financial claim. A company's common equity share is one kind
of security. The market also contains ETFs, debt securities, preference
shares, REITs, InvITs, and other instruments.

Buying one ordinary equity share means owning a small residual claim on a
company. It does not mean owning every security associated with that company.

## Exchange

An exchange is a regulated venue where eligible securities are admitted and
traded. India has more than one recognized stock exchange. NSE and BSE both
operate equity segments, and many large companies trade on both.

This creates an immediate counting trap:

> You cannot add the number of NSE-listed companies to the number of BSE-listed
> companies and call the result “Indian companies.”

The two sets overlap.

SEBI maintains the current list of recognized exchanges and their permitted
segments: [SEBI — details of stock exchanges](https://www.sebi.gov.in/stock-exchanges.html).

## Listing

A listing connects a security with an exchange and a trading segment. One
company may have securities admitted on multiple exchanges. A broker search
can also show products that are not ordinary main-board equity shares.

“Available in my broker app” is therefore not a useful research-universe
definition.

## Index

An index is a rules-based measurement of a selected basket. It has:

- an eligibility universe;
- selection rules;
- a weighting method;
- a calculation method; and
- a review schedule.

An index is not the exchange, and it is not a complete list of everything an
investor could buy.

## Research universe

A research universe is the set of securities to which we apply a question or
calculation.

Examples:

- “How are India's largest companies performing?” may use the Nifty 50.
- “How broad is the trend across large, mid, and small companies?” needs a
  broader universe.
- “Which microcaps have adequate liquidity?” needs a different universe and a
  much stricter risk discussion.

There is no universally correct universe. There is a universe that is more or
less appropriate for a stated question.

# Part 2 — A practical map of India's listed equity landscape

Use this funnel:

```text
INDIA'S EXCHANGE-LISTED LANDSCAPE
        │
        ├── multiple recognized exchanges and overlapping listings
        │
        ├── multiple security/product types
        │     common equity, SME equity, ETFs, REITs, InvITs, debt, others
        │
        ▼
NSE-LISTED COMPANIES
        │
        ├── main board
        └── SME / Emerge and other eligible listings
        ▼
ELIGIBLE, TRADED COMMON EQUITY
        │
        ├── Indian domicile / permitted eligibility
        ├── trading-frequency and liquidity checks
        ├── free-float requirement
        └── security-type and suspension exclusions
        ▼
NIFTY 500
        │
        ├── 100 large-cap companies
        ├── 150 mid-cap companies
        └── 250 small-cap companies
        ▼
MARKETWORKS DATED UNIVERSE
        ├── constituent snapshot/version
        ├── available price histories
        └── displayed active denominator and missing coverage
```

## How large is the wider NSE company set?

NSE's calendar-year 2025 annual highlights reported, as of 31 December 2025:

- 2,898 companies listed on NSE;
- 2,358 companies on the main board; and
- the total-company count excluded mutual funds, ETFs, and debt securities.

These are dated exchange statistics, not timeless constants. Listings,
delistings, migrations, mergers, and corporate actions change the count.

Source: [NSE Annual Highlights — Calendar Year 2025](https://nsearchives.nseindia.com/web/pressrelease/2026-01/PR_cc_01012026_20260101194417.pdf).

## Why not begin with every listed company?

“Everything listed” sounds comprehensive, but it mixes together securities
with very different:

- liquidity;
- trading frequency;
- listing histories;
- market capitalization;
- information availability;
- operational/data quality; and
- product structures.

A beginner can mistake a very low price for cheap valuation, or a large
one-day percentage move for meaningful information, without noticing that few
shares traded.

The goal of narrowing is not to declare the excluded companies bad. It is to
create a more coherent first laboratory.

# Part 3 — What the Nifty 500 actually is

The official name is **Nifty 500**.

Marketworks and some internal product surfaces may say **NSE 500** as shorthand
for the NSE-based stock universe. In course material:

- use **Nifty 500** when referring to the official index; and
- use **Marketworks Nifty 500-derived universe** when referring to the dated
  constituent and data snapshot used by a calculation.

This wording prevents the learner from confusing an exchange with an index.

## Selection in plain language

The official methodology first creates an eligible NSE universe. Its current
criteria include:

- Indian domicile and NSE trading/permitted-to-trade status;
- exclusion of instruments such as convertible stock, bonds, warrants, rights,
  fixed-return preferred stock, suspended stocks, and BZ-series stocks;
- minimum free-float or free-float market-cap requirement;
- trading on at least 90% of days in the previous six months;
- average impact cost not greater than 1%;
- a minimum listing-history rule for new securities; and
- a rank within the top 800 on both average daily turnover and average full
  market capitalization.

From that eligible set, the index selects the top 500 using six-month average
full market capitalization.

The complete rules belong to the official methodology, which can change:
[Nifty equity-index methodology, March 2026](https://www.niftyindices.com/Methodology/Method_NIFTY_Equity_Indices.pdf).

## What sits inside the 500?

NSE Indices' 2025 Nifty 500 white paper describes the Indian market-cap ladder
as:

- top 100 companies: large cap;
- next 150: mid cap;
- subsequent 250: small cap; and
- remaining eligible companies: microcap and beyond.

The Nifty 500 brings the first three groups together. That gives the learner
exposure to different company sizes without immediately moving into the
longer, less liquid tail.

Source: [Nifty 500 white paper, October 2025](https://www.niftyindices.com/docs/default-source/indices/nifty-500/nifty-500-whitepaper_2025.pdf?sfvrsn=7b2c6635_4).

## How is the index weighted?

The Nifty 500 index level is **free-float market-capitalization weighted**.

Break that phrase into two ideas:

1. **Market capitalization:** share price multiplied by shares outstanding.
2. **Free float:** the portion considered available for public trading, rather
   than tightly held strategic/promoter ownership.

Larger free-float companies therefore have more influence on the index return.
The index is not an equal vote among 500 companies.

## How often does membership change?

The Nifty 500 is reconstituted semi-annually, with changes effective on the
last working day of March and September under the current schedule.

Source: [Nifty Indices reconstitution calendar](https://niftyindices.com/resources/index-rebalancing-schedule).

An analysis must therefore answer:

> “Which version of the universe, as of which date?”

# Part 4 — Why Marketworks begins here

The Nifty 500 is not the whole Indian stock market. It is a useful starting
research universe because it balances five needs.

## 1. It captures most of the economically relevant listed market

As of 30 March 2026, NSE Indices reported that the Nifty 500 represented:

- about 92.04% of NSE-listed stocks' free-float market capitalization; and
- about 84.07% of the six-month traded value of all NSE stocks.

Those figures move over time and must carry their date.

Source: [Nifty 500 official index page](https://www.niftyindices.com/indices/equity/broad-based-indices/nifty-500).

This is broad enough to study the market without pretending the unmeasured tail
does not exist.

## 2. It includes large, mid, and small companies

The Nifty 50 can tell us a great deal about India's largest companies. It
cannot, by itself, tell us whether hundreds of mid- and small-cap stocks share
the move.

The broader universe makes questions about participation and leadership much
more meaningful.

## 3. It applies investability screens before size selection

The official eligible universe incorporates trading frequency, impact cost,
free float, security type, and other filters. That is a stronger starting point
than an unfiltered broker search.

It reduces obvious noise. It does not remove investment risk.

## 4. It is broad enough for cross-sectional comparison

Marketworks asks:

- How many stocks are above their long-term trend?
- Which sectors have broad participation?
- Which stocks are stronger than the benchmark?
- How unusual is a price or volatility condition across peers?

Five hundred intended constituents provide a useful cross-section for those
questions while remaining understandable and computationally manageable.

## 5. It creates a shared language

If every learner chooses a different stock list, two breadth readings cannot be
compared. A versioned common universe lets us reproduce, challenge, and discuss
the same calculation.

# Part 5 — Index return and breadth are different views

Suppose a ten-stock index has the following weights:

```text
Two largest stocks: 50% combined weight
Other eight stocks: 50% combined weight
```

On one day:

- both large stocks rise;
- the other eight stocks fall; and
- the weighted index finishes positive.

Two statements can now be true:

1. **The index rose.**
2. **Only 20% of stocks rose.**

The index asks:

> What happened to this weighted basket?

Breadth asks:

> How many covered stocks participated?

Marketworks often counts each eligible covered stock once for breadth, even
though the official Nifty 500 index return gives larger free-float companies
more weight.

Neither view is “the real market.” Together they reveal more than either alone.

# Part 6 — What the Nifty 500 does not solve

Starting here does not mean:

- every constituent is high quality;
- every constituent is liquid enough for every investor or order size;
- small-cap constituents carry the same risks as large caps;
- the universe includes the full microcap tail;
- an index member is attractively valued;
- the current constituent list existed unchanged in the past;
- a stock remains in the index forever; or
- index inclusion is a recommendation.

## Current-snapshot versus historical-universe risk

A current Nifty 500 list used to calculate today's breadth is a current
cross-section.

The same current list projected backward for ten years is not a historical
point-in-time universe. It omits companies that disappeared and includes
current members before they joined. That can create survivorship and membership
bias.

Module 3 will formalize this problem. For now, remember:

> Universe membership is data, and it has a date.

## Coverage can be less than membership

An official index may intend 500 constituent companies, while a dashboard has
usable history for fewer on a specific date.

The reverse can also appear in a dated official factsheet: the index's design
target may be 500 companies while the published security count temporarily
differs during index maintenance or a corporate action. Use the dated official
constituent file as published. Do not silently force the count to 500, and do
not invent an explanation that is absent from an official maintenance notice.

The calculation must show:

- intended universe count;
- eligible count for the metric;
- missing/excluded count; and
- as-of date.

A breadth value without a denominator is incomplete.

# The Module 1 operating rule

Before interpreting any market statistic, ask:

```text
What is the universe?
Why does this universe fit the question?
How are members selected?
Is the result weighted or equal-count?
What is the membership date?
How many members have usable data?
What sits outside the universe?
```

If those questions have no answer, the market statistic is not ready to
interpret.

# Closing thought

The Nifty 500 is useful because it is neither a headline-only view of the
largest companies nor an unfiltered list of every security that happens to
trade.

It is a wide, rules-based starting laboratory for learning how India's large,
mid, and small companies move together and apart.

In Module 2, we will use that laboratory to answer the next question:

> Is the market's movement broad, or is the index hiding what most stocks are
> doing?
