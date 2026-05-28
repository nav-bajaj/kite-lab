import type { LearnExplainer } from "./_types";

export const drawdown: LearnExplainer = {
  slug: "drawdown",
  title: "Drawdown",
  category: "concept",
  summary:
    "How far an index or stock is below its most recent peak. The most-used measure of pain in markets.",
  related: ["stress-score", "regime"],
  lastUpdated: "2026-05-28",
  sections: [
    {
      heading: "What it is",
      body: `Drawdown is the percentage decline from a series' all-time-high (or rolling peak) to the current value. If Nifty made an all-time high at 25,000 and is now at 22,500, the current drawdown is -10%.

We track drawdowns at two scopes:

- **Index drawdown** — Nifty 50 from its peak. Used as one input to the [stress score](/insights/learn/stress-score) (25% weight).
- **Maximum drawdown** — the worst drawdown experienced over a chosen window. Used to characterise how painful past episodes were.

Drawdowns are **always negative or zero** (a series at its peak has zero drawdown; a series below its peak has negative drawdown).`,
    },
    {
      heading: "Why it matters",
      body: `Average return tells you what to expect long-term. Drawdown tells you what the journey feels like — and what you can survive. Backtested strategies with the same CAGR can have very different drawdown profiles, and the one with the deeper drawdowns is the one investors actually sell at the bottom of.

For the broad Indian market, drawdowns have a relatively stable structure: most years see a 5-12% intra-year drawdown; about every 4-7 years there's a 20-30% drawdown; once-a-decade events go to 40%+. Knowing this lets you size positions for the conditions you can tolerate.`,
    },
    {
      heading: "How to read it",
      body: `- **-5% or less** — Routine. Most years see at least one of these.
- **-5% to -10%** — Notable. Often coincides with regime shifting from TREND_BULL to DRIFT.
- **-10% to -20%** — Painful. Historically the zone where the [stress score](/insights/learn/stress-score) becomes elevated.
- **-20% to -30%** — Crisis-zone. 2008, 2015-16, 2018-19, 2020 all qualified. Forward returns from these levels have historically been strong, but the **path** to get there can take months.
- **> -30%** — Once-a-decade. COVID's flash to -35% in March 2020 is the most recent example.

Drawdown depth itself isn't a tradeable signal — it's a context input. The combination of "deep drawdown + breadth healing + volatility cooling" is what often marks the bottom, not drawdown alone.`,
    },
  ],
};
