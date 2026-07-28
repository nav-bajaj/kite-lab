# Module 1 lesson — What exactly is "the market"?

Time: about 60 minutes, including the walkthrough, worksheet, and quiz.

## Start with a question you can't answer yet

How many stocks are in the Indian stock market?

Take a guess before reading on. Seriously — pick a number.

If you said 50, that's a reasonable guess. The Nifty 50 is the number that
shows up in the news every evening. If you said 500, also reasonable —
Marketworks talks about 500 stocks all the time. And if you've ever typed a
random letter into your broker app and scrolled, you might say "thousands,
surely."

Here's the strange part: every one of those answers is correct about
*something*. None of them is "the market."

Think of it like an election. If someone tells you "the people have voted
yes," your first question should be: *which people?* Everyone in the country?
One state? One housing society? The result means nothing until you know who
was on the voter list.

Markets work the same way. Before anyone can say the market is strong, weak,
or expensive, they have to say **which stocks they measured**. That chosen
list has a name: your **universe**. Choosing it well is the first real skill
in this course.

## What you'll be able to do after this module

By the end, you'll be able to tell apart five things that sound
interchangeable — a company, a share, an exchange, an index, and a research
universe. You'll know how India's thousands of listings get narrowed down to
the 500 stocks Marketworks studies, why we start there, and — just as
important — what that list of 500 *cannot* tell you.

# Part 1 — Five words that sound the same but aren't

People say "I bought Tata Motors on the NSE, it's in the Nifty" in one
breath. That sentence quietly mixes four different things. Let's pull them
apart, because the rest of the course leans on these distinctions.

## The company

A company is the actual business: the factories, the employees, the brands,
the software, the debts, the cash coming in and going out. It exists whether
or not anyone trades it.

## The share (and its cousins)

When you buy one share, you're buying a small slice of ownership in that
business — a claim on a piece of what it earns and owns. The market's
general word for any tradable claim like this is a **security**.

An ordinary share is one kind of security. But exchanges also trade other
kinds: funds you can buy like a stock (ETFs), slices of rental property
income (REITs), slices of infrastructure income (InvITs), bonds, and more.
This matters because your broker app shows *all* of them mixed together.

## The exchange

An exchange is the regulated marketplace where these securities trade — the
venue, not the merchandise. India has more than one. NSE and BSE are the two
big ones, and here's the trap: **most large companies are listed on both.**

So you can't count "companies on NSE" plus "companies on BSE" and call the
total "Indian companies." You'd be counting Reliance twice. The two lists
overlap heavily.

SEBI, the market regulator, maintains the official list of recognized
exchanges: [SEBI — details of stock exchanges](https://www.sebi.gov.in/stock-exchanges.html).

## The index

An index is not a place and not a product you own. It's a **measuring
stick**: a basket of stocks picked by written rules, whose combined value is
tracked as one number so we can talk about "how that basket did."

A useful comparison: an index is picked like a cricket team. There are
written selection rules, a selection review on a schedule, and players get
dropped and added. Being on the team says you met the selection criteria on
selection day. It is not a lifetime guarantee, and it doesn't make you the
best at everything.

## The research universe

Finally, the one this module is really about. A research universe is simply
**the list of stocks you've decided to ask your question about**.

Different questions need different lists. "How are India's biggest companies
doing?" — the Nifty 50 works fine. "Are mid-sized and smaller companies
rising too, or just the giants?" — 50 stocks can't answer that; you need a
wider list. "Which tiny companies are quietly gaining?" — that needs a
different list again, plus a much more careful conversation about risk.

There is no single correct universe. There's only a universe that fits your
question, or doesn't.

And note what a universe is *not*: "whatever my broker app shows me." That's
like planning a wedding by inviting your entire phone contacts list —
technically complete, useless for the actual decision.

# Part 2 — From thousands of listings to a workable 500

Here's the whole journey on one page. We'll walk down it step by step.

```text
EVERYTHING LISTED ON INDIAN EXCHANGES
        │  several exchanges, overlapping lists,
        │  shares mixed with ETFs, REITs, bonds, and more
        ▼
COMPANIES LISTED ON NSE
        │  the main board, plus a separate platform
        │  for very small companies (SME / Emerge)
        ▼
ORDINARY SHARES THAT ACTUALLY TRADE
        │  filters: trades regularly? enough shares
        │  publicly available? cheap enough to trade in
        │  and out of? not suspended?
        ▼
NIFTY 500  ← the official index
        │  100 large companies
        │  150 mid-sized companies
        │  250 smaller companies
        ▼
MARKETWORKS DATED UNIVERSE
        the Nifty 500 list as it stood on a specific date,
        plus a record of which stocks we have usable data for
```

## How big is the starting pool, really?

NSE's own year-end summary reported that as of 31 December 2025 there were
**2,898 companies listed on NSE**, of which 2,358 were on the main board.
(NSE noted this count excludes mutual funds, ETFs, and bonds.)

Notice we attached a date to that number. That's deliberate, and it's a
habit you'll see through the whole course. Companies list, delist, and merge
all the time — a count without a date goes stale without telling you.

Source: [NSE Annual Highlights — Calendar Year 2025](https://nsearchives.nseindia.com/web/pressrelease/2026-01/PR_cc_01012026_20260101194417.pdf).

## Why not just study all ~2,900?

"Everything" sounds thorough. In practice it mixes companies that are
nothing alike as *data*.

Some stocks trade crores of rupees every day; others barely trade at all. A
stock that hardly trades can show a dramatic 15% jump on a day when only a
handful of shares changed hands — the move looks like information, but it's
mostly noise. And a beginner can look at a ₹5 share and think "cheap!", when
the price of one share tells you nothing about what the whole company is
worth or whether it's good value.

Narrowing the list isn't a judgment that the excluded companies are bad.
It's about building a clean first laboratory — a set of stocks similar
enough that comparing them actually means something.

# Part 3 — Meet the Nifty 500

The official index we start from is called the **Nifty 500**.

One naming note before anything else: inside Marketworks you'll sometimes
see the shorthand "NSE 500". In this course we'll be precise. **Nifty 500**
means the official index. **Marketworks Nifty 500-derived universe** means
our dated copy of its member list, with our data attached. Keeping those
names separate stops you from ever confusing an exchange (NSE) with an
index (Nifty 500).

## How a stock gets in — the selection rules, in plain words

Remember the cricket-team idea? Here are the actual selection rules, as
written by NSE Indices, translated into everyday language. To be eligible, a
stock must:

- be an ordinary share of an Indian company trading on NSE (no bonds,
  warrants, suspended shares, or similar instruments);
- have actually traded on at least 90% of days over the past six months —
  no ghost stocks;
- have enough shares genuinely available for the public to buy and sell
  (this publicly tradable portion is called the **free float** — it excludes
  what promoters and strategic holders keep locked away);
- be cheap to get in and out of — when you trade, the price shouldn't move
  against you by more than about 1% just because you traded (the market
  calls this slippage the **impact cost**);
- have some listing history, and rank among the top 800 stocks on both
  trading activity and total company value.

From everything that qualifies, the index takes the **500 biggest
companies**, measured by average total value over six months. Total company
value here means **market capitalization**: share price × number of shares —
roughly, what it would cost to buy the entire company.

These are the current rules and they do change. The authoritative version
lives with NSE Indices:
[Nifty equity-index methodology, March 2026](https://www.niftyindices.com/Methodology/Method_NIFTY_Equity_Indices.pdf).

## What the 500 contains

NSE Indices describes India's listed companies as a ladder by size. The
biggest 100 companies are "large cap." The next 150 are "mid cap." The 250
after that are "small cap." Everything beyond is "microcap" and smaller
still. ("Cap" is just short for market capitalization — company size.)

The Nifty 500 is the top three rungs together: 100 large + 150 mid + 250
small. That's the point of it — you see the giants *and* the middle *and*
the smaller players, without yet wading into the thinnest, hardest-to-trade
end of the market.

Source: [Nifty 500 white paper, October 2025](https://www.niftyindices.com/docs/default-source/indices/nifty-500/nifty-500-whitepaper_2025.pdf?sfvrsn=7b2c6635_4).

## One index number, unequal votes

When the news says "the Nifty 500 rose 1%," how is that one number made
from 500 stocks?

Not by equal votes. Each company counts in proportion to the market value of
its publicly tradable shares — its free float. A giant like a top bank moves
the index far more than the 400th company on the list. The official term for
this is **free-float market-cap weighted**; the plain version is: *big
companies' moves count for more*.

Hold onto that. It becomes the key to Part 5.

## The list is not permanent

The Nifty 500 is refreshed twice a year — under the current schedule,
changes take effect on the last working day of March and September. Stocks
join; stocks drop out.

Source: [Nifty Indices reconstitution calendar](https://niftyindices.com/resources/index-rebalancing-schedule).

So "the Nifty 500" is really a series of dated lists. Any serious analysis
has to say *which* list: the members as of which date. You'll see
Marketworks stamp that date on its data everywhere.

# Part 4 — Why Marketworks starts here

Out of every possible universe, why this one? Five reasons.

**It covers most of the market that matters economically.** As of 30 March
2026, NSE Indices reported the Nifty 500 covered about 92% of the market
value of all NSE-listed stocks (measured on free float) and about 84% of
everything traded over the prior six months. Those percentages drift over
time — hence the date — but the picture is stable: this list captures the
overwhelming bulk of where India's listed money sits and trades.
Source: [Nifty 500 official index page](https://www.niftyindices.com/indices/equity/broad-based-indices/nifty-500).

**It includes large, mid, and small companies.** The Nifty 50 can tell you
about giants. It can't tell you whether hundreds of mid and small companies
are joining a rally or sitting it out — and that difference is exactly what
this course teaches you to see.

**It's pre-filtered for tradability.** Every member already passed the
trading-regularity, free-float, and cost-to-trade checks. That clears out
the noisiest data problems before we start. It does *not* mean the stocks
are safe — filtered is not the same as recommended.

**Five hundred stocks is enough to compare.** Marketworks constantly asks
questions like "how many stocks are above their long-term trend?" and
"which sectors are moving together?" Those questions need a crowd. Five
hundred is a real crowd that's still small enough to understand.

**Everyone measures the same thing.** If every learner picked their own
stock list, no two readings could be compared. A shared, dated universe
means your number and my number can disagree for interesting reasons, not
because we counted different stocks.

# Part 5 — The index went up. Did most stocks?

Here's the payoff for everything so far — the single most useful idea in
this module.

Think of a school exam. The class *average* can go up because two toppers
scored 98, even while most of the class scored worse than last time. "The
average rose" and "most students did worse" can both be true. They answer
different questions.

Indexes work exactly like that average — and remember from Part 3, the
"toppers" (biggest companies) carry extra weight.

Try it with a toy index of ten stocks, where the two biggest carry half the
total weight between them. One day, those two rise and the other eight all
fall. Run the numbers (you will, in the worksheet) and the weighted index
finishes *up* about +0.3% — even though **eight out of ten stocks fell**.

Two honest headlines for the same day:

1. "The index rose."
2. "Only 20% of stocks rose."

The first tells you what happened to the weighted basket. The second tells
you how many stocks actually joined the move — the market's word for this is
**breadth**, and it's simply a head-count: each stock gets one equal vote,
big or small.

Marketworks shows you both views on purpose. The index without breadth can
hide a rally carried by three giants. Breadth without the index can hide
where the actual money is. Neither one is "the real market." Read them
together.

# Part 6 — What the Nifty 500 can't tell you

Every universe leaves things out. Naming your blind spots isn't pessimism —
it's the difference between a measurement and a guess. Starting with the
Nifty 500 does **not** mean:

- these are 500 *good* companies (the filters check tradability, not
  quality or price);
- they're all equally easy to trade (a small-cap member is far thinner than
  a large bank);
- the smallest companies in India are represented (the microcap tail sits
  entirely outside);
- being in the index is a recommendation (it never is);
- today's list was always the list (members come and go every six months).

## The time-travel trap

That last point deserves its own warning, because it produces one of the
most common mistakes in market analysis.

Today's Nifty 500 list is a photograph of today. If you take today's list
and study "how these 500 stocks performed over the last ten years," you've
quietly cheated: you're studying only the companies that *survived and
succeeded enough to be in the index today*. The ones that shrank, failed, or
got delisted along the way have vanished from your study.

This is called **survivorship bias** — judging a journey by interviewing
only the people who finished it. Module 3 tackles it properly. For now, keep
one sentence: *a universe list is data, and it has a date.*

## "500 members" doesn't mean "500 measured"

One more honest wrinkle. A metric like "% of stocks above their 200-day
average" needs 200 days of price history per stock. A company that joined
the market recently doesn't have that yet. So on a given day, Marketworks
might compute that metric on, say, 480 of the 500 — and the display should
tell you so.

(The reverse also happens: around a merger or an index maintenance event,
even the *official* dated member file can briefly hold slightly more or
fewer than 500 securities. When that occurs, we report the official count
as published — we never quietly round it to 500 or invent a reason.)

So any statistic you trust should answer: counted **how many**, out of
**what list**, as of **when**, and **what was left out**. A percentage
without those answers is a number wearing a costume.

# The habit this module leaves you with

Whenever anyone — including Marketworks, including this course — shows you a
market statistic, run this checklist:

```text
Which stocks were measured, exactly?
Why is that the right list for this question?
How did stocks get onto the list?
Does every stock count equally, or do big ones count more?
Which date's list is this?
How many stocks were actually counted?
What's outside the list that I should remember exists?
```

If those questions have no answers, the statistic isn't wrong — it's just
not ready to be believed yet.

# Closing thought

The Nifty 500 is a good starting point precisely because it's neither
extreme: not the 50-stock headline view that misses most of the market, and
not the everything-in-the-broker-app view that drowns you in noise. It's a
wide, rules-based, dated list — a laboratory built for learning how India's
large, mid, and small companies move together and apart.

In Module 2, we put the laboratory to work on its first real question:

> When the index rises, is the whole market really rising — or is the index
> hiding what most stocks are doing?
