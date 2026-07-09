import type { LearnExplainer } from "./_types";

export const liquidity: LearnExplainer = {
  slug: "liquidity",
  title: "Liquidity tier",
  category: "concept",
  summary:
    "A simple Good / Moderate / Low bucket based on a stock's average daily traded value — how easily it trades.",
  related: ["volume-confirmation"],
  lastUpdated: "2026-07-09",
  sections: [
    {
      heading: "What it measures",
      body: `Liquidity is about how easily a stock can be traded without moving its own price. We proxy it with **average daily turnover** — the rupee value traded per day (price × volume), averaged over the last 20 sessions — and bucket every name into **Good / Moderate / Low**.`,
    },
    {
      heading: "Exactly how we compute it — transparent cutoffs",
      body: `We average the daily **turnover in ₹ crore** over the trailing 20 trading days, then apply round, disclosed thresholds:

- **Good** — 20-day average turnover **≥ ₹10 crore/day**
- **Moderate** — **≥ ₹1 crore/day**
- **Low** — below ₹1 crore/day

These cutoffs are **design choices** picked for interpretability, not thresholds derived from any return study. They are round numbers that separate names that trade freely from names where getting in or out is harder.`,
    },
    {
      heading: "How to read it",
      body: `- **Good** — trades comfortably; the other metrics on the screener are more reliable.
- **Low** — thin trade. Prices can be jumpy, moving averages noisier, and the stock harder to transact. Treat its signals with extra caution.
- Liquidity is a **data-quality and tradability caveat**, not a quality judgment about the company.`,
    },
    {
      heading: "Common misreadings",
      body: `- **Turnover isn't market cap.** A large company can trade thinly on a given stretch, and a smaller one can trade heavily around a theme.
- **The tier is a moving average** — it can shift as interest in a name rises or fades.`,
    },
  ],
};
