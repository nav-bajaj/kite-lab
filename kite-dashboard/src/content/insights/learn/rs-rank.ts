import type { LearnExplainer } from "./_types";

export const rsRank: LearnExplainer = {
  slug: "rs-rank",
  title: "Relative Strength (RS) rank",
  category: "indicator",
  summary:
    "Where every stock sits in the market's momentum pecking order, from rank 1 (strongest) to 500 (weakest).",
  related: ["rs-leader", "trend-score", "momentum-consistency"],
  lastUpdated: "2026-07-09",
  sections: [
    {
      heading: "What it measures",
      body: `RS rank orders all NSE 500 stocks by momentum strength on a single scale: **rank 1 = strongest, rank 500 = weakest**. It answers "where does this stock sit in the pecking order of momentum, right now?"

The **RS percentile** is the same information as a 0–100 number (higher = stronger) — the 90th percentile means the stock is in the top 10% of the universe. The **sector rank** repeats the exercise inside the stock's own index basket ("#4 of 38 in the sector").`,
    },
    {
      heading: "Exactly how we compute it",
      body: `We use a **percentile-then-blend** composite — the same shape our production momentum portfolios use, so the public screen is consistent with the firm's own definition of momentum.

For each stock we take four horizon returns and rank each one cross-sectionally across the universe into a 0–1 percentile. We then blend those percentiles with fixed weights:

- 1-month return → weight **0.10**
- 3-month return → weight **0.20**
- 6-month return → weight **0.30**
- 12-month return → weight **0.40**

The longer horizons carry more weight because durable, multi-quarter trends are what momentum research rewards; the 1-month term keeps the score responsive to fresh leadership. The blended score is then ranked 1..500. A stock needs a full 12 months of history to be ranked.`,
    },
    {
      heading: "How to read it",
      body: `- **Top decile (rank ≤ ~50, percentile ≥ 90)** carries the "Momentum leader" tag. In our 16-year study, RS-top-decile names beat a matched NSE 500 baseline by **+1.19pp over the next 20 trading days** (56% positive vs 54% baseline) and **+3.9pp at 60 days** — a validated, disclosed tendency, not a forecast for any single stock.
- **Sector rank** separates "strong stock in a strong sector" from "the one strong name in a weak sector". Cross-check with the [Sectors](/insights/sectors) page.
- **Δ 21d** (21-day rank change) shows whether a stock is climbing or sliding the ladder. A stock jumping from 312 to 88 is a rank *improver* — see the "New momentum" tag.`,
    },
    {
      heading: "Common misreadings",
      body: `- **RS is relative, not absolute.** In a falling market the rank-1 stock can still be down — it's just falling less than the rest.
- **A high rank built on one horizon is fragile.** A stock riding a single 12-month move can rank well even as its 1- and 3-month momentum fades. The multi-horizon blend softens this but doesn't eliminate it — glance at the return ladder.
- **Rank *improvement* is not a return prediction.** The biggest 21-day improvers ("New momentum") are an observation: the rank changed. In our validity study that cohort did **not** beat the baseline forward, so we surface the names without any performance claim.`,
    },
  ],
};
