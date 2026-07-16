import type { LearnExplainer } from "./_types";

export const sectorRs: LearnExplainer = {
  slug: "sector-rs",
  title: "Sector relative strength (RS)",
  category: "indicator",
  summary:
    "How a sector is doing versus the wider market (the Nifty 50). Positive means it's beating the market; negative means it's lagging.",
  related: ["sector-breadth", "rs-leader"],
  lastUpdated: "2026-05-28",
  sections: [
    {
      heading: "What it is",
      body: `Relative strength compares one sector's return to Nifty 50's return over the same window. We compute it at five horizons — **5d / 20d / 60d / 120d / 252d** — for each of the 12 NIFTY sector indices.

A 60-day RS of +5% for NIFTY BANK means: BANK returned 5 percentage points more than Nifty over the last 60 trading days. RS is always a difference, not a ratio — easy to read, easy to compare.

The sector leaderboard on Pulse and Sectors pages ranks sectors by 60-day RS by default. You can hover any cell to see the underlying calculation.`,
    },
    {
      heading: "Why it matters",
      body: `In any market, money rotates. Even in a TREND_BULL regime where every sector is up in absolute terms, RS reveals which sectors are leading and which are funding the rotation. Persistent RS leadership tends to **continue** for weeks-to-months — Indian equity sectors show meaningful momentum at 60-120 day horizons.

The week-over-week **delta in RS rank** is sometimes more informative than the absolute level. A sector jumping from rank 7 to rank 3 in a week often precedes broader recognition that something has changed structurally (earnings inflection, regulation, flows). Falling rank does the opposite.`,
    },
    {
      heading: "How to read it",
      body: `- **Top-3 sectors** at 60d typically lead the next 1-2 months unless regime flips.
- Check **breadth within the leading sector** — if NIFTY BANK leads but only 2 of 12 constituents are positive vs Nifty, the leadership is narrow and fragile.
- Look at **dispersion across sectors** — when the top sector is +8% and the bottom is -8% over 60d, sector rotation is the dominant theme. When the spread compresses, it's an index-driven tape.
- A simultaneous **RS leadership flip** (top → bottom or vice versa in 4-8 weeks) is rare and usually signals a meaningful regime change.`,
    },
    {
      heading: "Historical context",
      body: `- **2020-2021 — IT leadership.** NIFTY IT held top-3 RS for most of the COVID recovery period, then faded sharply in 2022 as global tech sold off.
- **2023-2024 — capital goods / defence run.** Capital Goods (and BEL within it) was a sustained RS leader; the kind of multi-quarter leadership that defines durable themes.
- **Banks rotation, 2018 → 2019.** Private banks led, then PSU banks took over as the IL&FS aftermath shifted attention. RS rank changes preceded the absolute price differentiation.
- **Auto, 2024.** Strong RS leadership as the post-EV inflection played through; M&M and TVSMOTOR were notable component winners.

The 60-day window is our default surface; the longer windows (120d, 252d) capture more durable themes.`,
    },
    {
      heading: "Common misreadings",
      body: `- **"Top RS sector — buy it."** RS is observation, not recommendation. A leading sector might be late-cycle stretched; check the [sector breadth](/insights/learn/sector-breadth) reading inside the sector to see if leadership is broad or narrow.
- **"Bottom RS sector — short it."** Lagging sectors often persist in lagging — but when they turn, the early move can be sharp. RS doesn't tell you when (or if) a turn comes.
- **"Same RS rank for 6 months — nothing happening."** Persistence at the top is itself meaningful — it's compounding. Persistent leadership generally compounds; persistent lagging generally drains.`,
    },
  ],
};
