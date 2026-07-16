import type { LearnExplainer } from "./_types";

export const momentumConsistency: LearnExplainer = {
  slug: "momentum-consistency",
  title: "Momentum Consistency",
  category: "indicator",
  summary:
    "A 0–100 score of how steady a stock's climb has been — a smooth, reliable riser scores high; one that owes it all to a single jump scores low.",
  related: ["trend-score", "rs-rank", "drawdown"],
  lastUpdated: "2026-07-09",
  sections: [
    {
      heading: "What it measures",
      body: `Two stocks can post the same 6-month return in very different ways: one grinding higher week after week, the other flat then gapping up 40% on a single event. Momentum Consistency scores the **quality** of the move — high means smooth and broadly-participated, low means lumpy or reliant on one spike.`,
    },
    {
      heading: "Exactly how we compute it",
      body: `A weighted checklist over the trailing 6 months, each part 0–1 then blended:

- **Share of positive weeks (0.45)** — what fraction of the last ~26 weeks closed up. Steady trends print green most weeks.
- **Drawdown control (0.30)** — scales from 1 at no 6-month drawdown down to 0 at a 30% max drawdown. Rewards trends that didn't give a lot back.
- **Volatility-adjusted return (0.25)** — 6-month return ÷ 60-day annualized volatility, scaled to full at a ratio of 2. Rewards return earned per unit of risk.

Missing inputs renormalize over what's available.`,
    },
    {
      heading: "How to read it",
      body: `- **High Consistency + high Trend Score** — a durable, orderly uptrend (the "Quiet compounder" pattern when volatility is also low).
- **Low Consistency + high recent return** — the move likely came from one or two sessions; more event-driven than trend-driven. Eyeball the chart.
- It is a lens on *how* a stock got here, not a forecast of where it goes next.`,
    },
    {
      heading: "Common misreadings",
      body: `- **Smooth past ≠ smooth future.** A high score describes the trailing 6 months; regimes change.
- **Low Consistency isn't "bad".** A stock basing quietly then breaking out will score low on positive-weeks — context matters.
- **The 30% drawdown and 6-month window are round, transparent choices**, not values tuned on returns.`,
    },
  ],
};
