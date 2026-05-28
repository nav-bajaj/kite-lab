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
  ],
};
