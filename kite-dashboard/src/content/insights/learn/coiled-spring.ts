import type { LearnExplainer } from "./_types";

export const coiledSpring: LearnExplainer = {
  slug: "coiled-spring",
  title: "Coiled spring",
  category: "pattern",
  summary:
    "A stock that's gone quiet in a tight price range while still in an uptrend — often a pause before a bigger move, in either direction.",
  related: ["breakout", "rs-leader"],
  lastUpdated: "2026-05-28",
  sections: [
    {
      heading: "What it is",
      body: `A "coiled spring" is a stock where:

- **Realised volatility** (20-day rolling) sits in its own **bottom 25%** versus the trailing 252 days — meaning the stock is unusually quiet for itself
- The stock is **above its 50-DMA AND above its 200-DMA** — basic trend support is intact
- Recent price action has stayed in a **tight band** (typically a 5-8% range) for several weeks

The setup is named for what often follows: a pent-up move that releases as either a clear breakout (up out of the range) or a fast failure (down through 50-DMA support).`,
    },
    {
      heading: "Why it matters",
      body: `Tight ranges in trending stocks are uncommon — most names either keep trending or pull back significantly. When a stock instead **pauses without giving back trend**, it usually means buyers are absorbing supply without forcing the issue. The setup compresses energy that has to release in some direction.

The pattern itself is **direction-agnostic** until resolution — it tells you the move is coming, not which way it goes. The broader regime is the best tiebreaker: in TREND_BULL conditions, coiled springs tend to resolve up; in STRESS or STRETCHED, they tend to resolve down.

We list 10-15 of the tightest coiled springs each day on the [Watchlists](/insights/watchlists) page.`,
    },
    {
      heading: "How to read it",
      body: `- **The breakout level** is usually the upper edge of the recent tight range, often coincident with a recent swing high
- **The failure level** is usually the 50-DMA. Below that, the setup is invalidated
- **Volume on the resolution day** matters more than usual — quiet break-outs have higher fade rates than thrust break-outs
- **Time in range** matters — the longer a stock has been tight, the larger the eventual move tends to be

This is one of the rare patterns where you can have a clear plan in both directions: long on confirmed breakout, short / exit on close below 50-DMA. Always size for the regime — coiled springs in STRESS have lower win rates than the average.`,
    },
    {
      heading: "How we detect it on the Watchlists page",
      body: `The transparent detection rule (\`watchlists.get_coiled_springs\`):

- Close today is **above both 50-DMA and 200-DMA**
- 20-day **realised volatility** of the stock's daily returns is **in the bottom quartile** of that stock's own 252-day distribution
- Sorted ascending by recent volatility — tighter (more coiled) names first

The "stock's own bottom quartile" framing matters — what counts as "tight" varies enormously by stock. A 1% daily volatility might be tight for HDFCBANK and loose for a small-cap. By using each stock as its own benchmark, the list captures genuine compression rather than just selecting low-vol stocks.`,
    },
    {
      heading: "When the setup fails",
      body: `- **Range break on low volume.** Quiet exits from the range are typically faded. The setup works best when the breakout day has visible volume thrust.
- **Below 50-DMA close.** Once the stock closes below the 50-DMA, the "coiled" condition is invalidated — the spring released down. Re-evaluation needed.
- **STRESS regime.** Coiled springs in STRESS resolve down more often than they resolve up — pattern + regime mismatch.
- **Long time at the same level.** Setups that have been coiled for 6+ months sometimes "die" — the energy drains rather than releases. Newer coiled patterns (1-3 months tight) have historically resolved more cleanly.`,
    },
  ],
};
