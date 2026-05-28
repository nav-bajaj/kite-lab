import type { LearnExplainer } from "./_types";

export const regime: LearnExplainer = {
  slug: "regime",
  title: "Market regime",
  category: "indicator",
  summary:
    "A 4-state classification — Trend Bull, Drift, Stretched, Stress — that captures where markets are in the cycle.",
  related: ["stress-score", "pct-above-200dma", "vix"],
  lastUpdated: "2026-05-28",
  sections: [
    {
      heading: "What it is",
      body: `Every trading day, the engine classifies the Indian market into one of four regimes based on Nifty 100's position vs its 100-DMA, broad NSE 500 breadth, India VIX percentile, and Nifty drawdown depth:

- **TREND_BULL** — Nifty 100 above 100-DMA, breadth healthy, volatility moderate. Trend-following conditions.
- **DRIFT** — Mixed signals. Index near trend but breadth or volatility lukewarm. Choppy, range-bound conditions.
- **STRETCHED** — Index well above trend with deteriorating internals (narrow leadership or stretched extension). Reversion risk elevated.
- **STRESS** — Index below trend, broad breakdown, volatility elevated. Panic / capitulation conditions.

A 3-day confirmation smoothing prevents whipsaws — single-day border crossings don't flip the regime; the underlying conditions must persist.`,
    },
    {
      heading: "Why it matters",
      body: `The same indicator means different things in different regimes. A breakout signal that fires in TREND_BULL has very different follow-through statistics than the same signal in STRESS. Volatility "running hot" in DRIFT is unremarkable; the same VIX level in STRETCHED is a serious warning.

Conditioning on regime is the single biggest improvement you can make to interpreting any other indicator we publish. **Regime first, indicator second.**`,
    },
    {
      heading: "How to read it",
      body: `Watch the regime label AND its **persistence days**. A 60-day-old TREND_BULL is fundamentally different from a 5-day-old one — late-cycle bulls often show fading breadth even while the headline holds up, while early bulls usually have full breadth participation.

Regime **transitions** are often more informative than the steady state. STRETCHED → STRESS transitions in past data: Sep 2018, Feb-Mar 2020, May-Jun 2022. STRESS → DRIFT or DRIFT → TREND_BULL transitions, by contrast, tend to mark the early phase of new uptrends.

Validated on historical episodes: COVID crash (Mar 2020) reads STRESS; calm 2017 melt-up reads TREND_BULL with high persistence; 2018 NBFC crisis reads STRETCHED → STRESS sequence.`,
    },
  ],
};
