import type { LearnExplainer } from "./_types";

export const dispersion: LearnExplainer = {
  slug: "dispersion",
  title: "Cross-sectional dispersion",
  category: "indicator",
  summary:
    "How spread out daily returns are across NSE 500 stocks. High dispersion = stock-picker's market; low dispersion = everything moving together.",
  related: ["stress-score", "vix"],
  lastUpdated: "2026-05-28",
  sections: [
    {
      heading: "What it is",
      body: `Take each NSE 500 stock's daily return on a given day. The **cross-sectional standard deviation** of those returns is dispersion. High dispersion means stocks are scattered — some up sharply, others down sharply. Low dispersion means most stocks moved in roughly the same direction by roughly the same amount.

We report dispersion as a **z-score** relative to its trailing 252-day distribution. A reading of +2 means today's dispersion is unusually high; -1.5 means unusually low.

It's one of the four components of the [stress score](/insights/learn/stress-score) — specifically the 20% dispersion-z weight.`,
    },
    {
      heading: "Why it matters",
      body: `Dispersion is the **mirror image of correlation**. When everything is moving together (low dispersion), passive index exposure dominates and stock selection adds little value. When dispersion is high, individual stock stories matter more than the market move.

In Indian markets, **rising dispersion alongside falling indices** is a warning sign — it suggests the market is identifying differences between stocks (often around solvency, earnings, sector-specific risks). This pattern preceded the worst phases of 2018-19 and 2020.

Falling dispersion in a rising market, by contrast, is often associated with breadth thrust events — many stocks moving up together, which historically signals durable bottoms.`,
    },
    {
      heading: "How to read it",
      body: `- **z > +2** — Highly unusual day. Wide split between winners and losers. Often a single event (a specific sector blowing up while others hold) or a regime-change point.
- **z between -1 and +1** — Typical. Don't read much into it.
- **z < -1.5** — Compressed dispersion. Index-like behaviour dominant. Sometimes precedes range breaks (the calm before an event).

**Sustained elevated dispersion** (z > +1 for many days) is the more meaningful signal — it means market regime has shifted to one where stock selection matters again.`,
    },
  ],
};
