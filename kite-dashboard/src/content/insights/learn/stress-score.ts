import type { LearnExplainer } from "./_types";

export const stressScore: LearnExplainer = {
  slug: "stress-score",
  title: "Stress score",
  category: "indicator",
  summary:
    "A 0–100 reading of how tense the market is right now — high means fear and big swings, low means calm. It rolls four warning signs into one number.",
  related: ["vix", "drawdown", "pct-above-200dma", "dispersion"],
  lastUpdated: "2026-05-28",
  sections: [
    {
      heading: "What it is",
      body: `The stress score is a single number from **0 (very calm)** to **100 (panic / capitulation)** that combines four pieces of evidence about market conditions in India:

- **VIX percentile (35%)** — where today's India VIX sits relative to its trailing 252-day distribution
- **Nifty drawdown depth (25%)** — how far Nifty is below its recent peak
- **% NSE 500 below 200-DMA (20%)** — share of broad-market stocks below their long-term trend
- **Cross-sectional dispersion (20%)** — how unevenly stocks are moving versus their own history

Each component is scaled to 0-100 and then weighted as above. The output is a single, comparable reading across regimes.`,
    },
    {
      heading: "Why it matters",
      body: `Markets rarely give one clean signal. Volatility can be high while breadth still holds; drawdowns can deepen while dispersion stays calm. The composite forces those threads into one number that's hard to argue with — when stress reads 85, multiple things are wrong at once.

The score is also useful for **conditional thinking**: how have markets historically behaved when stress was last in this range? Our [conditional distribution engine](/insights/learn/concept/conditional-distribution) uses this exact bucketing — over 17 years of Indian data, the highest-stress quintile has shown materially higher forward returns at the 20-day horizon than calm quintiles. That's the empirical basis for "buy panic" thinking, with the caveat that any individual instance can still feel terrible.`,
    },
    {
      heading: "How to read it",
      body: `Three bands, and they are the only ones we use — the chart lines, the card label and this list all read from the same two numbers in the engine:

- **Below 35 — Calm.** Trend-following conditions; breadth typically healthy. About 45% of days sit here.
- **35-60 — Middle ground.** Mixed signals, no clear edge either way. About 39% of days.
- **Above 60 — Stressed.** Volatility unusually high, breadth weakening, drawdown notable. About 17% of days — the deepest clusters being Aug-Dec 2011 (euro-zone crisis, 140 days), Feb-Apr 2020 (COVID, 90 days), Oct 2018 (NBFC crisis, 72 days) and 2013's taper tantrum (71 days).

Single-day jumps of 15+ points in the score are themselves informative — they usually mark either a crystallising breakdown or the early phase of an event that will need several days to resolve.`,
    },
    {
      heading: "Historical context",
      body: `The panel starts in **March 2009**, so it does not contain 2008. Across it, 180 days have crossed 80 — the largest clusters:

- **Aug-Dec 2011 — euro-zone crisis.** 69 days above 80, the longest stretch in the panel; a grinding, months-long regime rather than a spike.
- **Feb-Mar 2020 — COVID lockdown.** 55 days above 80 and the panel's highest readings; VIX and drawdown both at extremes, breadth collapsed below 10%.
- **Jan-Feb 2016 — global growth scare.** 16 days above 80.
- **Oct 2018 — IL&FS / NBFC crisis.** 13 days above 80; breadth deteriorated more slowly than VIX spiked.
- **Jun 2022 — global rate shock.** 9 days above 80, peaking at 87.6 on 20 June.

For the live chart and the exact daily values, see the [stress timeseries on Pulse](/insights). The breakdown table shows each of the four components' current contributions.`,
    },
    {
      heading: "Common misreadings",
      body: `- **"Stress is rising fast — it must be a crash coming."** Not always. Rising stress is a warning, but most rises into 50-70 mean-revert without becoming a crisis. The full-blown crash regime requires stress to stay elevated for many days, not just spike for one.
- **"Stress is below 35 — it's safe."** Calm conditions can persist for very long stretches AND complacency itself becomes a risk — readings below 20 with VIX at multi-year lows have historically preceded volatility expansions.
- **"Component X is driving stress today, so I should watch X."** The whole point of the composite is that no single component is the signal — it's the convergence. A 70 driven by VIX alone (other components quiet) is different from a 70 driven by all four climbing together; the latter is far more meaningful.`,
    },
  ],
};
