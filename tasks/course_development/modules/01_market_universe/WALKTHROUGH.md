# Module 1 walkthrough — Watching "the market" become a named list

Target time: 12-15 minutes.

## Walkthrough outcome

By the end, the learner can point at four different things on screen and
name each one:

1. the official Nifty 500 index;
2. the member list as it stood on a specific date — the dated universe;
3. the smaller set of stocks with usable data for a given calculation; and
4. the Nifty 500 index series itself, used as the weighted yardstick.

Instructor discipline: never use "NSE," "Nifty," "index," and "universe" as
if they were the same word. Keeping them apart is the whole point of this
walkthrough.

## Before recording or teaching

Verify on the delivery date:

- current official Nifty 500 page and methodology links;
- official coverage and traded-value statistics, with their as-of dates;
- the current refresh schedule for index membership (the reconstitution
  calendar);
- course universe-manifest version and row count;
- Marketworks latest completed data date;
- the count of stocks actually measured today (the denominator) for
  `% above 200-DMA`;
- any missing symbols or price histories; and
- the product's exact universe label.

Record the values in:

```text
Walkthrough recorded:
Official index facts as of:
Course universe snapshot:
Marketworks data as of:
Intended members:
Metric-eligible members:
Missing/excluded:
```

Never narrate a changing number without its date.

# Live sequence

## 0:00-1:30 — Start with the ambiguity

Open the Marketworks Pulse page at `/insights`.

Say:

> "This page is telling us something about the market. Most of what you see
> here is built from an index — a measuring stick: a basket of stocks picked
> by written rules and tracked as one number. Before we read whether the
> news is good or bad, let's ask a more basic question: when this page says
> 'the market', which stocks does it actually mean?"

Ask the learner:

- "Is this headline describing one index number, or lots of individual
  stocks?"
- "If the index is green today, do we know how many stocks are actually
  green?"
- "Where on this page would you look to find which stocks were counted, and
  on what date?"

Do not answer yet.

## 1:30-4:00 — Open the official Nifty 500 definition

Open the [official Nifty 500 page](https://www.niftyindices.com/indices/equity/broad-based-indices/nifty-500).

Point out:

- the official name: Nifty 500;
- the top-500 selection from the pool of eligible NSE stocks;
- the coverage figure — how much of the market's value this index captures,
  measured on the publicly tradable portion of shares (the free float) —
  with its date;
- the traded-value coverage figure, with its date;
- the factsheet, member-list, and methodology downloads; and
- the sector distribution.

Say:

> "This page is a definition. Notice two things it does not say. It never
> says every listed Indian company is in this basket. And it never says every
> company gets an equal vote."

Ask:

> "Two treasure hunts on this page. First: which number tells us how much of
> the market this index covers? Second: which phrase tells us whether big
> companies count for more than small ones?"

## 4:00-6:30 — Show the eligibility funnel

Open the official broad-market methodology and show, without reading every
legal line:

- which kinds of securities are allowed in;
- the minimum trading-regularity requirement;
- the cost-to-trade check — the price shouldn't move against you much just
  because you traded (the impact cost);
- the requirement for enough publicly tradable shares (the free float);
- the top-800 rank condition on trading activity and company value; and
- the final top-500 selection by size.

Say:

> "The index is not simply the 500 highest share prices. First comes a screen
> that asks: does this stock actually trade, and can you get in and out
> without moving the price against yourself? Only after that screen does
> company size decide who makes the cut."

Check:

- Share price is not company size (market capitalization).
- Being in the index is not a quality certificate.

## 6:30-8:30 — Show the size ladder

Display the prepared large/mid/small ladder:

```text
1-100       large cap
101-250     mid cap
251-500     small cap
501-750     microcap layer represented by Nifty Microcap 250
beyond      remaining eligible/listed tail
```

Say:

> "This is why 500 is a genuinely different view from 50. We're not just
> adding more giants. We're adding the middle of the market and the smaller
> players — the layers the Nifty 50 can't see."

Clarify that membership is reviewed on a schedule, and stocks join and drop
out.

## 8:30-11:00 — Return to Marketworks breadth

Open:

- `/insights/learn/pct-above-200dma`; then
- the Pulse breadth panel or current equivalent.

Point to:

- the "NSE 500" product shorthand;
- the latest completed date;
- the breadth value;
- the denominator and coverage, if visible; and
- the link to the methodology or Learn explanation.

Say:

> "The official index return gives bigger companies a bigger vote — the more
> of a company's shares the public can actually trade, the more its move
> counts. This breadth number asks a different question: out of the stocks we
> could measure today, how many are above their own 200-day average — that's
> each stock's average closing price over its last 200 trading days, a
> slow-moving line that shows its long-term trend. Here, every stock gets
> one equal vote."

Use the prepared ten-stock example:

- weighted index return: `+0.30%`;
- rising stocks: `2 of 10`;
- falling stocks: `8 of 10`; and
- share of stocks rising (advance breadth): `20%`.

Ask:

> "Here's the puzzle: can the index finish the day up while most stocks
> finish down?"

Expected answer: yes. The index is a weighted average, so two heavyweights
can lift it while eight stocks fall. Breadth counts heads — one equal vote
each — so it shows the weakness the index hides.

## 11:00-13:30 — Open the screener

Open `/insights/screener`.

Point out:

- the number of rows returned;
- any filters currently applied;
- the data date;
- one stock's sector; and
- whether the product shows missing or partial coverage.

Say:

> "The screener is a window onto a dated list. If it shows fewer than 500
> usable rows, that is not a problem to hide — it's a fact to say out loud:
> this many stocks had usable data today."

Do not open a stock and discuss whether it should be bought. This walkthrough
is about the list, not about picking from the list.

## 13:30-15:00 — Close with the universe contract

Return to the Pulse page and fill:

```text
Official index:
Product universe:
Membership/snapshot date:
Metric:
Index weighting:
Breadth counting method:
Stocks actually counted (denominator):
Known exclusions:
```

Close with:

> "From today, 'the market went up' is an unfinished sentence. Before we read
> any result, we'll name four things: which list, as of which date, how many
> stocks were actually counted, and whether every stock got an equal vote."

# Screenshot fallback

If live data is unavailable, use dated screenshots in this order:

1. official Nifty 500 definition and coverage;
2. methodology eligibility funnel;
3. large/mid/small ladder;
4. Marketworks `% above 200-DMA` explainer;
5. Pulse breadth panel;
6. screener row count and data date; and
7. completed universe-contract card.

Every screenshot footer must include:

```text
Captured on:
Data as of:
Source:
Methodology/version:
```

# Walkthrough red flags

Stop and correct the narration if the instructor says:

- "NSE 500 is the 500 stocks on NSE."
- "These are the 500 safest Indian companies."
- "Nifty 500 covers the entire Indian market."
- "There are exactly 500 usable stocks on every date."
- "The index rose, so most constituents rose."
- "Index inclusion makes the stock a good investment."

# Product follow-ups

The current Learn copy may use a simplified denominator such as "320 of 500."
Before course publication, align it with the production breadth calculation,
which uses the count of members with sufficient history for that date. The
course should show both the intended membership and the count of stocks
actually measured (the metric-eligible denominator).
