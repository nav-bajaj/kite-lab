import type { LearnExplainer } from "./_types";

export const stressScore: LearnExplainer = {
  slug: "stress-score",
  title: "Stress score",
  category: "indicator",
  summary:
    "A 0-100 reading of how stressed the Indian equity market is right now, blending volatility, drawdown, breadth, and dispersion.",
  related: ["vix", "drawdown", "pct-above-200dma", "dispersion"],
  lastUpdated: "2026-05-28",
  sections: [
    {
      heading: "What it is",
      body: `The stress score is a single number from **0 (very calm)** to **100 (panic / capitulation)** that combines four pieces of evidence about market conditions in India:

- **VIX percentile (35%)** — where today's India VIX sits relative to its trailing 252-day distribution
- **Nifty drawdown depth (25%)** — how far Nifty is below its recent peak
- **% NSE 500 below 200-DMA (20%)** — share of broad-market stocks below their long-term trend
- **Cross-sectional dispersion (20%)** — how unevenly stocks are moving versus their own history

Each component is scaled to 0-100 and then weighted as above. The output is a single, comparable reading across regimes.`,
    },
    {
      heading: "Why it matters",
      body: `Markets rarely give one clean signal. Volatility can be high while breadth still holds; drawdowns can deepen while dispersion stays calm. The composite forces those threads into one number that's hard to argue with — when stress reads 85, multiple things are wrong at once.

The score is also useful for **conditional thinking**: how have markets historically behaved when stress was last in this range? Our [conditional distribution engine](/insights/learn/concept/conditional-distribution) uses this exact bucketing — over 16 years of Indian data, the highest-stress quintile has shown materially higher forward returns at the 20-day horizon than calm quintiles. That's the empirical basis for "buy panic" thinking, with the caveat that any individual instance can still feel terrible.`,
    },
    {
      heading: "How to read it",
      body: `- **Below 30 — Calm.** Trend-following conditions; breadth typically healthy.
- **30-60 — Normal.** Most trading days live here. No clear edge.
- **60-80 — Elevated.** Volatility unusually high, breadth weakening, drawdown notable. Pay closer attention; reduce sizing if you're discretionary.
- **80+ — Panic / capitulation.** Historically the strongest forward-return zone in our data — but also the most uncomfortable to act in. Past stress > 80 days include March 2020 (COVID), October 2008 (GFC), Sep-Oct 2018 (NBFC crisis).

Single-day jumps of 15+ points in the score are themselves informative — they usually mark either a crystallising breakdown or the early phase of an event that will need several days to resolve.`,
    },
  ],
};
