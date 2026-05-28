import type { LearnExplainer } from "./_types";

export const sectorBreadth: LearnExplainer = {
  slug: "sector-breadth",
  title: "Sector breadth (constituent-level)",
  category: "indicator",
  summary:
    "How many stocks WITHIN a sector are actually participating. Tells you whether sector strength is broad or just a few mega-caps.",
  related: ["sector-rs", "pct-above-200dma"],
  lastUpdated: "2026-05-28",
  sections: [
    {
      heading: "What it is",
      body: `Sector indices like NIFTY BANK are cap-weighted, so HDFCBANK and ICICIBANK dominate the headline. The sector index can rise even when most of its constituents are flat or weak. **Constituent-level breadth** fixes that.

For every NIFTY sector, we compute:

- **% above 50-DMA / 200-DMA** across the sector's constituent stocks (not the index)
- **Top / bottom 3 RS** stocks within the sector vs Nifty over the last 6 months
- **Internal dispersion** — standard deviation of constituent daily returns
- **Thrust days** — sessions when 80%+ of sector constituents moved in the same direction

You'll see breadth alongside RS on the sector leaderboard. The two together give an honest read.`,
    },
    {
      heading: "Why it matters",
      body: `A sector leading with **broad breadth** (10 of 12 constituents above 200-DMA) is structurally bullish — the rally has legs because money is flowing across many names. A sector leading with **narrow breadth** (only 3 of 12 above) is fragile — the headline depends on a couple of mega-caps and reverses quickly if those falter.

Historical example: NIFTY IT in 2020-2021 had both leadership AND wide breadth — most constituents participated. By contrast, NIFTY BANK in 2018 had decent index strength masking serious weakness in PSU bank constituents (which later cracked broadly).

Breadth divergence is one of the cleanest leading signals we track.`,
    },
    {
      heading: "How to read it",
      body: `- Sectors with **breadth > 70%** (most constituents above 200-DMA) tend to sustain leadership.
- Sectors with **breadth < 30%** are vulnerable even if the index hasn't broken yet — the internals say something is wrong.
- A **thrust day** (>80% of constituents up together) is often an early-stage signal that institutional money has stepped in.
- Compare **breadth changes** week-over-week — improving breadth in a lagging sector is one of the earlier rotation signals.`,
    },
  ],
};
