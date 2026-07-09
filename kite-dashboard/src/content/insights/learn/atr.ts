import type { LearnExplainer } from "./_types";

export const atr: LearnExplainer = {
  slug: "atr",
  title: "ATR (Average True Range)",
  category: "concept",
  summary:
    "A measure of a stock's typical daily trading range. We show it as a % of price so names of any price can be compared.",
  related: ["extension-risk", "beta", "drawdown"],
  lastUpdated: "2026-07-09",
  sections: [
    {
      heading: "What it measures",
      body: `ATR captures how much a stock typically moves in a day — its normal "wiggle". A stock with a 4% ATR routinely swings twice as much intraday as one with a 2% ATR. We report **ATR %** (ATR ÷ price) so a ₹80 stock and a ₹4,000 stock are directly comparable.`,
    },
    {
      heading: "Exactly how we compute it",
      body: `For each day we compute the **true range** — the largest of: today's high minus low, today's high minus yesterday's close, and yesterday's close minus today's low (the last two capture overnight gaps). **ATR(14)** is the simple average of the true range over the last 14 days. **ATR %** divides that by the latest close.

We use the simple-mean variant of ATR (not Wilder's smoothing) — a transparent, standard choice.`,
    },
    {
      heading: "How to read it",
      body: `- **Higher ATR %** = a more volatile name; day-to-day noise is larger, so a 3% move may be unremarkable.
- **Lower ATR %** = a steadier name; the same 3% move is a bigger event.
- ATR is the natural unit for [Extension](/insights/learn/extension-risk): "8 ATRs above the 20-DMA" means the same thing for a calm stock and a jumpy one.`,
    },
    {
      heading: "Common misreadings",
      body: `- **ATR has no direction.** It measures the *size* of moves, not whether they're up or down.
- **It is not a stop-loss recommendation.** ATR is sometimes used that way in trading systems; here it is descriptive context only.`,
    },
  ],
};
