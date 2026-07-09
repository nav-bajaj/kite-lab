import type { LearnExplainer } from "./_types";

export const volumeConfirmation: LearnExplainer = {
  slug: "volume-confirmation",
  title: "Volume Confirmation",
  category: "indicator",
  summary:
    "A 0–100 score of whether volume is backing a move — today's and the week's volume vs average, plus the up/down-day volume balance.",
  related: ["breakout", "rs-rank"],
  lastUpdated: "2026-07-09",
  sections: [
    {
      heading: "What it measures",
      body: `Volume Confirmation asks "is participation behind this move, or is it drifting on thin trade?" Higher scores mean today and the last week traded materially above the stock's normal volume, and up-days have carried more volume than down-days. Bands: **Weak / Neutral / Strong**.`,
    },
    {
      heading: "Exactly how we compute it",
      body: `A weighted checklist, each component scored 0–1 then blended:

- **Today's volume ratio (0.45)** — today's volume ÷ the prior 20-day average. Scales from 1x (0) to 3x (full score).
- **5-day volume ratio (0.30)** — the last week's average vs the 20-day average. Scales from 1x to 2.5x.
- **Up/down-day volume balance over 20 days (0.25)** — volume on up-days vs down-days. Scales from 1x (balanced) to 3x (up-days dominate).

Bands: **Weak** below 33, **Neutral** 33–66, **Strong** 66+. Using ratios (not raw volume) makes small and large names comparable.`,
    },
    {
      heading: "How to read it",
      body: `- **Strong** — a move with participation: heavy, up-day-led volume. More durable than a quiet drift.
- **Weak** — price may be moving, but trade is light or down-days are heavier. Treat the move with more caution.
- Volume confirmation is most useful *alongside* a price event — a breakout on Strong volume is a different animal from the same breakout on Weak volume. See [Breakout](/insights/learn/breakout).`,
    },
    {
      heading: "Common misreadings",
      body: `- **Strong volume is context, not a recommendation.** It describes participation, nothing more.
- **The 2–3x cutoffs are transparent design choices**, chosen as round, interpretable numbers — not thresholds optimized on forward returns.
- **One heavy day can spike the "today" term.** The 5-day and up/down terms are there to temper single-session noise.`,
    },
  ],
};
