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
    {
      heading: "Historical context",
      body: `- **2017-2018 banks divergence.** NIFTY BANK looked decent at the index level but private vs PSU breadth split meaningfully. PSU bank constituents weakened well before the IL&FS aftermath hit broader financials.
- **2020 IT broad participation.** Almost every NIFTY IT constituent above 200-DMA simultaneously — one of the cleanest broad-sector setups in the panel.
- **2024 capital goods narrowing.** Index strength was real but constituent breadth started narrowing — the top 3 names accounted for an outsized share of the move. Early caution.

Coverage caveat: sectors with constituents outside our NSE 500 panel show a "partial coverage" badge. Treat those breadth numbers with proportionate caution.`,
    },
    {
      heading: "Common misreadings",
      body: `- **"Sector breadth and sector RS say the same thing."** They don't. RS is the index-level return; breadth is the constituent-level participation. A leading sector with narrow breadth is fragile; a lagging sector with improving breadth is interesting.
- **"% above 200-DMA inside the sector = 60% is OK."** Inside a sector this is often weaker than it sounds — sectors with 12 constituents and 7 above 200-DMA isn't broad; it's 5 holdouts. Use breadth as a relative read between sectors, not an absolute threshold.
- **"Leader / laggard lists are buy / sell calls."** They're observation lists. The RS leaders inside a sector are typically the names other quant systems (including our Quality Momentum portfolio) will already be holding — interesting context, not an entry signal.`,
    },
  ],
};
