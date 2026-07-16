import type { LearnExplainer } from "./_types";

export const sustainedUptrend: LearnExplainer = {
  slug: "sustained-uptrend",
  title: "Sustained uptrend (clean trend)",
  category: "pattern",
  summary:
    "Stocks that have climbed strongly over the past year without any nasty falls along the way — the mark of a smooth, orderly trend.",
  related: ["rs-leader", "breakout"],
  lastUpdated: "2026-05-28",
  sections: [
    {
      heading: "What it is",
      body: `A stock that, as of today:

- Has returned at least **+20% over the trailing 252 trading days** (~1 year)
- Has had a **maximum drawdown of no more than 8%** over the last 60 trading days
- Is **above its 200-DMA**

Three filters that together require both strength (the 1-year return) and durability (the recent shallow-drawdown filter). A stock with a 50% gain over a year but a recent 20% pullback doesn't qualify; the 'clean' part of clean trend is what the filters select for.`,
    },
    {
      heading: "Why it matters",
      body: `Persistent trends with mild corrections are the quietest, highest-quality compounders. They don't make headlines because they don't have dramatic moves — they just keep going. Many investors miss them because they're never "interesting" on any single day.

The pattern is conceptually similar to [RS leader](/insights/learn/rs-leader), but with a key difference: RS Leader screens for outperformance vs Nifty (relative), while sustained-uptrend screens for low-drawdown strength (absolute). A stock can be an RS Leader because it fell less than Nifty during a bear move — that wouldn't pass the sustained-uptrend filter.`,
    },
    {
      heading: "How we detect it on the Watchlists page",
      body: `The transparent detection rule (\`watchlists.get_sustained_uptrend\`):

\`\`\`
ret_252 >= 0.20                     # 1-year return >= 20%
max_drawdown_60d >= -0.08            # 60-day max drawdown <= 8%
close > 200_day_moving_average       # above long-term trend
\`\`\`

Sorted by "cleanliness" — return ÷ drawdown — so the cleanest trends rank first.`,
    },
    {
      heading: "Validity findings",
      body: `Tested on 165 sample dates from 2012 to 2025 (every 21st trading day), with the top 25 firings per date entering the sample:

- 20d forward: pattern names +2.48% mean vs NSE 500 baseline +1.73% → excess **+0.75pp**, direction lift **+4.9pp**
- 60d forward: pattern +7.40% vs baseline +5.64% → excess **+1.76pp**, direction lift **+6.1pp**
- 120d forward: pattern +13.75% vs baseline +11.63% → excess **+2.12pp**, direction lift **+6.3pp**

At the 20d horizon, the excess (+0.75pp) falls just under the +1.0pp threshold we use for confident forward-return narrative. Direction lift is healthy across all horizons. **Publishing decision: names list, no forward-return claims.** The pattern surfaces interesting stocks but we're being conservative about how we frame the historical statistics.`,
    },
    {
      heading: "When it fails",
      body: `- **Mean-reversion regimes.** Sustained trends can be late-cycle. A clean uptrend that's been clean for 12 months may be closer to its end than its middle.
- **Single-event movers.** Stocks that gapped up on M&A or earnings surprises can satisfy the filter without "trending" in the technical sense. Eyeball-check the chart.
- **Sector beta dressed as alpha.** If sector RS is strongly positive, every stock in the sector might pass the filter. The list value comes from cross-sector names, not multiple names from one sector all riding the same wave.`,
    },
  ],
};
