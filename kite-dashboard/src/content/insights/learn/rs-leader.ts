import type { LearnExplainer } from "./_types";

export const rsLeader: LearnExplainer = {
  slug: "rs-leader",
  title: "RS leader (stock-level)",
  category: "pattern",
  summary:
    "Stocks that have outperformed Nifty by the largest margin over the last 6 months. The persistent winners list.",
  related: ["sector-rs", "breakout"],
  lastUpdated: "2026-05-28",
  sections: [
    {
      heading: "What it is",
      body: `For every stock in NSE 500, compute its 126-day (~6-month) return minus Nifty 50's return over the same window. Rank stocks by that **relative strength** number. The top 25 form the RS Leaders watchlist.

This is the stock-level cousin of [sector RS](/insights/learn/sector-rs). The same logic applies: positive RS means a stock beat Nifty; negative means it lagged.

Refreshed daily on the [Watchlists](/insights/watchlists) page.`,
    },
    {
      heading: "Why it matters",
      body: `Indian equity markets show meaningful momentum at 3-12 month horizons. Our production portfolios (Quality Momentum, Trend Leaders, Core Momentum) are built on exactly this finding. Stocks that have outperformed the index over the trailing 6 months tend to continue outperforming over the next 1-3 months — not always, but often enough to be statistically meaningful.

The RS Leaders list is a transparent, public version of what those portfolios screen for. It's not a recommendation; it's a screen. **Persistent leaders** (names that stay near the top for many months) have historically been the highest-quality compounders.`,
    },
    {
      heading: "How to read it",
      body: `- **Watch tenure** — stocks that have been in the top-25 for 3+ months are more interesting than recent entrants
- **Sector concentration** — when the leaderboard is dominated by one sector, leadership is narrow. When it's spread across 6-8 sectors, leadership is broad
- **New entrants** — fresh names jumping into the top-25 from outside are often early-stage trends worth a closer look
- **Departures** — leaders falling out of the list often signal the end of a momentum run for that name

This is observation, not prediction. We deliberately don't claim "RS leaders will return X% next month" — instead, we surface the list and let you draw your own conclusions about which names align with your process.`,
    },
    {
      heading: "How we detect it on the Watchlists page",
      body: `The transparent detection rule (\`watchlists.get_rs_leaders\`):

- For each NSE 500 stock, compute its return over the last **126 trading days** (~6 months)
- Subtract Nifty 50's return over the same window
- Top 25 by this **RS spread** are the published list

Worth noting:

- 126 days is a long-enough window that single-day noise washes out, short-enough that current themes still drive the result
- We don't filter on price or market cap — small / mid / large all compete on the same RS metric
- The 50 / 100 / 200-day windows give earlier signals but are noisier; the 252-day (1-year) window captures durable themes but lags
- This list is the conceptual cousin of what our Quality Momentum and Trend Leaders portfolios screen for, but with a different ranking layer`,
    },
    {
      heading: "When the screen misleads",
      body: `- **Regime transitions.** A stock that led for 6 months and is now sliding could still be in the top-25 because of its earlier outperformance — it lags the actual leadership change by weeks.
- **Mega-cap dominance.** When a few mega-caps lead, they crowd out the rest of the index, suppressing other names' RS. Cross-check against [concentration](/insights/learn/concentration).
- **One-shot events.** A stock that gapped up 30% on a single corporate action and then went flat still shows high RS — but it isn't really "in a trend". Quick eyeball check on the chart guards against this.
- **Sector concentration in the list.** If 12 of the 25 RS leaders are from one sector, the "leadership" might really be a single sector call. Check the sector distribution on the watchlist page.`,
    },
  ],
};
