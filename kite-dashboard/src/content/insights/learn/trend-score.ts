import type { LearnExplainer } from "./_types";

export const trendScore: LearnExplainer = {
  slug: "trend-score",
  title: "Trend Score",
  category: "indicator",
  summary:
    "A transparent 0–100 score of how cleanly a stock is trending — DMA positioning, alignment, slope, proximity to its high, and drawdown control.",
  related: ["rs-rank", "momentum-consistency", "pct-above-200dma"],
  lastUpdated: "2026-07-09",
  sections: [
    {
      heading: "What it measures",
      body: `Trend Score condenses "is this stock in a healthy uptrend?" into one 0–100 number. High scores describe a stock trading above its moving averages, with the averages stacked in the right order and sloping up, near its 52-week high, and without deep recent drawdowns. It is a **description of trend structure**, not a signal to act.`,
    },
    {
      heading: "Exactly how we compute it",
      body: `A weighted checklist, each component scored 0–1 then blended. Weights are fixed and disclosed:

- **DMA position (0.40)** — the share of the 20 / 50 / 100 / 200-DMAs the price is currently above.
- **Alignment (0.20)** — 1 if the 50-DMA is above the 200-DMA (the classic "golden" stack), else 0.
- **Slope (0.15)** — the share of the 50- and 200-DMA that are rising over the last 20 days.
- **Proximity to 52w high (0.15)** — scales from 1 at the high down to 0 once the stock is 25% or more below it.
- **Drawdown control (0.10)** — scales from 1 at no drawdown down to 0 at a 50% max drawdown over the last year.

If some inputs are missing (short history), the score renormalizes over what's available, so it stays comparable.`,
    },
    {
      heading: "How to read it",
      body: `- **80+** — a textbook uptrend: above all DMAs, aligned, rising, near highs.
- **40–70** — mixed structure: maybe above the 200-DMA but below the 50-DMA, or well off its high.
- **Below 30** — a downtrend or a base; the structure isn't there.

Pair it with [Momentum Consistency](/insights/learn/momentum-consistency): a high Trend Score with low Consistency often means one sharp move rather than a durable grind.`,
    },
    {
      heading: "Common misreadings",
      body: `- **A high score is not a buy.** It says the trend is intact *today*; trends end. This is decision-support data, not advice.
- **The score is backward-looking** by construction — every input is computed from price history.
- **Round thresholds are design choices.** The 25%-from-high and 50%-drawdown cutoffs are transparent, round numbers we picked for interpretability, not values optimized on returns.`,
    },
  ],
};
