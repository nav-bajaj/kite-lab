import type { LearnExplainer } from "./_types";

export const beta: LearnExplainer = {
  slug: "beta",
  title: "Beta",
  category: "concept",
  summary:
    "How much a stock tends to move when the market moves — measured against Nifty 50 over the last 60 days.",
  related: ["atr", "drawdown"],
  lastUpdated: "2026-07-09",
  sections: [
    {
      heading: "What it measures",
      body: `Beta describes a stock's sensitivity to the overall market. A beta of **1.0** means the stock tends to move in line with Nifty 50; **1.5** means it tends to move about 1.5x as much (amplifying both up and down days); **0.6** means it tends to move less than the index. A negative beta (rare) means it tends to move opposite the market.`,
    },
    {
      heading: "Exactly how we compute it",
      body: `We regress the stock's **daily returns** against Nifty 50's daily returns over the trailing **60 trading days** — beta is the slope of that relationship (covariance of the two ÷ variance of the index). Sixty days keeps it current; a longer window would be smoother but slower to reflect a changed character.`,
    },
    {
      heading: "How to read it",
      body: `- **High beta (>1.3)** — an amplifier. In a strong tape it can lead; in a sell-off it typically falls harder.
- **Low beta (<0.8)** — a dampener; tends to move less than the index either way.
- Read beta *with* [ATR %](/insights/learn/atr): beta is about co-movement with the market, ATR is about absolute daily range. A stock can be high-ATR but low-beta if its moves are idiosyncratic.`,
    },
    {
      heading: "Common misreadings",
      body: `- **Beta is not risk in general** — it only captures market-linked movement, not company-specific risk.
- **It drifts.** A 60-day beta reflects the recent past and can shift as the stock's character or the market regime changes.
- **High beta isn't "better".** It cuts both ways, harder.`,
    },
  ],
};
