# Module 1 walkthrough — From “the market” to the Marketworks universe

Target time: 12-15 minutes.

## Walkthrough outcome

The learner should leave able to point to four different objects:

1. the official Nifty 500 index;
2. a dated constituent universe;
3. the subset with usable data for a calculation; and
4. the Nifty 500 index series used as a weighted benchmark.

The instructor should not use “NSE,” “Nifty,” “index,” and “universe”
interchangeably.

## Before recording or teaching

Verify on the delivery date:

- current official Nifty 500 page and methodology links;
- official coverage and traded-value statistics;
- current reconstitution schedule;
- course universe-manifest version and row count;
- Marketworks latest completed data date;
- current active denominator for `% above 200-DMA`;
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

> “This page says something about the market. Before we read whether it is
> strong or weak, we need to know what the page means by market.”

Ask the learner:

- Is the headline describing an index or a collection of stocks?
- If an index is green, do we know how many stocks are green?
- Where would we look for the universe and date?

Do not answer yet.

## 1:30-4:00 — Open the official Nifty 500 definition

Open the [official Nifty 500 page](https://www.niftyindices.com/indices/equity/broad-based-indices/nifty-500).

Point out:

- official name: Nifty 500;
- top-500 selection from an eligible NSE universe;
- dated free-float market-cap coverage;
- dated traded-value coverage;
- factsheet, constituent, and methodology downloads; and
- sector distribution.

Say:

> “This page defines an index. It does not say that every listed Indian company
> is in the basket, and it does not say every company has equal weight.”

Ask:

> “Which number on this page tells us how wide the coverage is? Which phrase
> tells us how the index is weighted?”

## 4:00-6:30 — Show the eligibility funnel

Open the official broad-market methodology and show, without reading every
legal line:

- eligible security types;
- minimum trading frequency;
- impact-cost/liquidity condition;
- free-float condition;
- top-800 turnover and market-cap rank condition; and
- top-500 size selection.

Say:

> “The index is not simply the 500 highest share prices. It begins with an
> investability screen and then uses company size.”

Check:

- Share price is not market capitalization.
- Index membership is not a quality certification.

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

> “This is why 500 is materially different from 50. We are not merely adding
> more large companies; we are adding the mid- and small-cap layers.”

Clarify that the ranks and membership are reviewed and can change.

## 8:30-11:00 — Return to Marketworks breadth

Open:

- `/insights/learn/pct-above-200dma`; then
- the Pulse breadth panel or current equivalent.

Point to:

- “NSE 500” product shorthand;
- latest completed date;
- breadth value;
- denominator/coverage if visible; and
- link to methodology or Learn explanation.

Say:

> “The official index return gives larger free-float companies more influence.
> This breadth metric asks a different question: of the covered universe, how
> many stocks are above their own 200-day average?”

Use the prepared ten-stock example:

- weighted index return: `+0.30%`;
- advancing stocks: `2 of 10`;
- declining stocks: `8 of 10`; and
- advance breadth: `20%`.

Ask:

> “Can the index be positive while participation is weak?”

Expected answer: yes, because the index is weighted and breadth counts stock
participation.

## 11:00-13:30 — Open the screener

Open `/insights/screener`.

Point out:

- the number of rows returned;
- any current filters;
- the data date;
- an individual stock's sector; and
- whether the product shows missing or partial coverage.

Say:

> “The screener is a view over a dated data universe. If it displays fewer than
> 500 usable rows, that is a coverage fact to explain—not a number to hide.”

Do not open a stock and discuss whether it should be bought. This walkthrough
is about the set, not a selection from the set.

## 13:30-15:00 — Close with the universe contract

Return to the Pulse page and fill:

```text
Official index:
Product universe:
Membership/snapshot date:
Metric:
Index weighting:
Breadth counting method:
Active denominator:
Known exclusions:
```

Close with:

> “From now on, ‘the market’ is not enough. We will name the universe, date,
> denominator, and weighting before interpreting the result.”

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

- “NSE 500 is the 500 stocks on NSE.”
- “These are the 500 safest Indian companies.”
- “Nifty 500 covers the entire Indian market.”
- “There are exactly 500 usable stocks on every date.”
- “The index rose, so most constituents rose.”
- “Index inclusion makes the stock a good investment.”

# Product follow-ups

The current Learn copy may use a simplified denominator such as “320 of 500.”
Before course publication, align it with the production breadth calculation,
which uses the count of members with sufficient history for that date. The
course should show both intended membership and metric-eligible denominator.
