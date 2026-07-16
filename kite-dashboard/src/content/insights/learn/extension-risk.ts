import type { LearnExplainer } from "./_types";

export const extensionRisk: LearnExplainer = {
  slug: "extension-risk",
  title: "Extension",
  category: "indicator",
  summary:
    "A 0–100 gauge of how far a stock has run above its usual trend. A high reading just means 'stretched' — it's a description, not a signal to sell.",
  related: ["atr", "trend-score"],
  lastUpdated: "2026-07-09",
  sections: [
    {
      heading: "What it measures",
      body: `Extension answers "how far has this stock run above its own recent averages, relative to its normal daily range?" A stock 8 ATRs above its 20-DMA is *extended vs its own history* — it has travelled a long way without pausing. The label bands are **Low / Moderate / High / Very high**.

Read it as a **descriptive state**, exactly like "trading 20% above the 200-DMA". It is not a prediction and not a signal to sell.`,
    },
    {
      heading: "Exactly how we compute it",
      body: `A weighted checklist, each part scored 0–1 then blended:

- **Distance above the 20-DMA in ATR units (0.35)** — capped at 6 ATRs = full score.
- **Distance above the 50-DMA in ATR units (0.25)** — capped at 10 ATRs.
- **5-day return percentile vs the stock's own year (0.20)** — how unusual the last week's move is for this name.
- **RSI(14) above 50 (0.20)** — scales from 0 at RSI 50 to 1 at RSI 100.

Bands: **Low** below 25, **Moderate** 25–50, **High** 50–75, **Very high** 75+. Measuring in ATR units (not raw %) makes a quiet stock and a volatile stock comparable.`,
    },
    {
      heading: "How to read it",
      body: `- **"Very high"** means the stock has moved far and fast relative to its own normal range. That is *interesting context* — a stretched name may consolidate, or may keep running.
- Combine with Trend Score: a high Trend Score *with* high Extension is a strong trend that has run hard recently.
- Use it to size expectations about day-to-day noise, not to time exits.`,
    },
    {
      heading: "The honest finding — no mean-reversion claim",
      body: `We validity-tested the "High/Very high" extension cohort as a **risk** hypothesis: do extended names underperform going forward? They did **not**. Over 16 years, extended names actually returned *slightly more* than the baseline at 20–120 days (+0.8pp at 20d), with no reliable underperformance.

So we deliberately keep "Extended" as a **descriptive state label** — "stretched vs its own history" — and make **no claim that extended stocks will mean-revert or fall**. Anyone telling you a stock "must pull back because it's extended" is asserting something our own data doesn't support.`,
    },
  ],
};
