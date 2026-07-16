import type { LearnExplainer } from "./_types";

export const pctAbove200dma: LearnExplainer = {
  slug: "pct-above-200dma",
  title: "% above 200-DMA",
  category: "indicator",
  summary:
    "The share of stocks in a long-term uptrend — the simplest way to see how many stocks are healthy, not just the index.",
  related: ["sector-breadth", "mcclellan-oscillator", "regime"],
  lastUpdated: "2026-05-28",
  sections: [
    {
      heading: "What it is",
      body: `For every NSE 500 stock, compute its 200-day moving average. A stock is "above its trend" if its closing price is above its 200-DMA. The breadth metric is the **percentage of NSE 500 stocks** in that state on a given day.

If 320 of 500 stocks are above their 200-DMA today, the reading is 64%. We track this daily over the full 16-year history.

It's also one of the four ingredients of the [stress score](/insights/learn/stress-score) — specifically, the 20% weight on "% below 200-DMA" (inverse of this reading).`,
    },
    {
      heading: "Why it matters",
      body: `The 200-day moving average is widely watched as the long-term trend filter. Whether or not it's "right", price reacts at this level often enough that the level itself becomes meaningful via reflexivity.

Knowing that, say, 65% of stocks are above their 200-DMA tells you:

- The trend is broadly intact (not just a few mega-caps holding up the index)
- Where in the cycle we likely are — readings near 80-90% are late-cycle stretching, readings below 25% are stress / capitulation
- Whether to trust breakouts — they have much higher follow-through when broad breadth supports them`,
    },
    {
      heading: "How to read it",
      body: `- **> 75%** — Late-cycle stretching. Breadth this broad is hard to sustain; reversion risk elevated.
- **55-75%** — Healthy trend. Most rallies live here.
- **40-55%** — Mixed / churning. Often DRIFT regime.
- **25-40%** — Weakening. Trend repair needed.
- **< 25%** — Stress / washout. Historically the zone where bottoms form, but takes time.

**Divergence** is the most useful read: when index is making new highs but % above 200-DMA is dropping, leadership is narrowing — a yellow flag. When index is making new lows but % above 200-DMA is rising, more stocks are healing internally — an early green shoot.`,
    },
    {
      heading: "Historical context",
      body: `- **March 2020 (COVID).** Breadth collapsed below 10% — the deepest washout in our panel. Recovery began before the index made new highs (a classic bullish divergence).
- **Oct 2018 (NBFC crisis).** Breadth slid from ~70% to ~20% over a few months even as Nifty held up better than the broad market — narrowing leadership warned earlier than the index price did.
- **All of 2017.** Breadth above 75% for most of the year — a textbook broad TREND_BULL.
- **2022 sideways year.** Breadth oscillated between 40-60% while the index churned — a DRIFT regime characteristic.

The breadth panel feeds into our [stress score](/insights/learn/stress-score) (20% weight on the "below 200-DMA" component) and the [regime classifier](/insights/learn/regime).`,
    },
    {
      heading: "Common misreadings",
      body: `- **"Breadth is 60% — that's good, right?"** It depends on direction. 60% trending up from 40% is great; 60% trending down from 80% is a warning. Look at the trajectory, not just the level.
- **"Breadth is below 25% — bottom is in."** Often, but the path to the actual low can be choppy. Breadth below 25% identifies the *zone* where bottoms form historically — it doesn't time the exact day.
- **"Index up, breadth flat — fine."** Index-only confirmation hides narrowing leadership. The divergence is the leading indicator; the index lags it.`,
    },
  ],
};
