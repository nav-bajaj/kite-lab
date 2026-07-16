import type { LearnExplainer } from "./_types";

export const vix: LearnExplainer = {
  slug: "vix",
  title: "India VIX",
  category: "indicator",
  summary:
    "The market's own forecast of how bumpy the next month will be — often called the 'fear gauge'.",
  related: ["stress-score", "regime"],
  lastUpdated: "2026-05-28",
  sections: [
    {
      heading: "What it is",
      body: `India VIX is a real-time index computed by NSE from the implied volatilities of Nifty 50 index options. Loosely: it tells you what annualised volatility option traders are willing to pay for / receive over the next 30 days.

A reading of **15** means option markets imply roughly 15% annualised volatility — about 4% per month or 0.94% per trading day. A reading of **30** implies double that.

The series goes back to 2008 in India, so we have ~17 years of context — including 2008, 2013 taper tantrum, demonetization, 2018 NBFC, COVID, and 2022 rate shock episodes.`,
    },
    {
      heading: "Why it matters",
      body: `VIX is often called the "fear index" but a better mental model is **uncertainty index**. High VIX means option markets see a wide range of possible outcomes over the next month — either direction. Low VIX means a narrow range is being priced.

VIX has a structural tendency to **mean-revert** — extreme highs come down, extreme lows eventually move up. This makes percentile rank (where VIX sits relative to its trailing 252-day history) more informative than the absolute level. A VIX of 18 in a year of 12-15 readings is unusual; the same 18 in a year of 20-25 readings is unremarkable.

It contributes 35% to the [stress score](/insights/learn/stress-score) — the largest single weight, because VIX captures forward-looking uncertainty better than any backward-looking measure.`,
    },
    {
      heading: "How to read it",
      body: `- **VIX < 12** — Unusual complacency. Markets pricing very narrow ranges. Often precedes volatility expansion.
- **VIX 12-18** — Calm / normal. Most TREND_BULL conditions live here.
- **VIX 18-25** — Elevated. Something is bothering markets. Pay attention.
- **VIX 25-35** — Stress. Drawdown likely in progress; option premia rich.
- **VIX > 35** — Panic. Historically the zone forward returns have been highest over 20-60 days, but the *day-of* is the most uncomfortable to act in.

Don't read VIX in absolute terms only — always compare to its **trailing 252-day percentile**. We display both numbers on the stress breakdown table.`,
    },
    {
      heading: "Historical context",
      body: `Notable VIX episodes in the India series:

- **Oct 2008 — Lehman / GFC.** Highest VIX readings in the panel; multi-week sustained crisis-level uncertainty.
- **Aug 2013 — Taper tantrum / rupee crisis.** VIX spiked into elevated range; resolved within months.
- **Nov 2016 — Demonetization.** Sharp single-event spike; back to baseline within weeks.
- **Mar 2020 — COVID.** Second-highest peak after 2008; the fastest VIX expansion in the panel.
- **2022 rate shock.** VIX stayed in the 18-25 zone for months — elevated, but never crisis-level.

In contrast, the calmest VIX environments in the panel were the 2017 melt-up and stretches of 2024.`,
    },
    {
      heading: "Common misreadings",
      body: `- **"VIX is high — markets are about to crash."** VIX measures perceived uncertainty, not direction. High VIX has historically coincided with bottoms more often than with further drops in our panel — but the timing is uncomfortable.
- **"VIX is low — it's safe to take more risk."** Low VIX often persists for months before any expansion, but very low readings (below 12) have historically marked complacent peaks. Use it alongside the regime label.
- **"This single VIX number is meaningful by itself."** Always read VIX as a **percentile vs trailing history**. A reading of 18 in a 12-15 environment is informative; the same 18 in a 22-25 environment is unremarkable.`,
    },
  ],
};
