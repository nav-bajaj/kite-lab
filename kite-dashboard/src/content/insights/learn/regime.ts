import type { LearnExplainer } from "./_types";

export const regime: LearnExplainer = {
  slug: "regime",
  title: "Market regime",
  category: "indicator",
  summary:
    "The market's current state, sorted into one of four plain labels — Trend Bull, Drift, Stretched, or Stress — so you can tell at a glance what kind of market you're in.",
  related: ["stress-score", "pct-above-200dma", "vix"],
  lastUpdated: "2026-05-28",
  sections: [
    {
      heading: "What it is",
      body: `Every trading day, the engine classifies the Indian market into one of four regimes based on Nifty 100's position vs its 100-DMA, broad NSE 500 breadth, India VIX percentile, and Nifty drawdown depth:

- **TREND_BULL** — Nifty 100 above 100-DMA, breadth healthy, volatility moderate. Trend-following conditions.
- **DRIFT** — Mixed signals. Index near trend but breadth or volatility lukewarm. Choppy, range-bound conditions.
- **STRETCHED** — Index well above trend with deteriorating internals (narrow leadership or stretched extension). Reversion risk elevated.
- **STRESS** — Index below trend, broad breakdown, volatility elevated. Panic / capitulation conditions.

A 3-day confirmation smoothing prevents whipsaws — single-day border crossings don't flip the regime; the underlying conditions must persist.`,
    },
    {
      heading: "Why it matters",
      body: `The same indicator means different things in different regimes. A breakout signal that fires in TREND_BULL has very different follow-through statistics than the same signal in STRESS. Volatility "running hot" in DRIFT is unremarkable; the same VIX level in STRETCHED is a serious warning.

Conditioning on regime is the single biggest improvement you can make to interpreting any other indicator we publish. **Regime first, indicator second.**`,
    },
    {
      heading: "How to read it",
      body: `Watch the regime label AND its **persistence days**. A 60-day-old TREND_BULL is fundamentally different from a 5-day-old one — late-cycle bulls often show fading breadth even while the headline holds up, while early bulls usually have full breadth participation.

Regime **transitions** are often more informative than the steady state. STRETCHED → STRESS transitions in past data: Sep 2018, Feb-Mar 2020, May-Jun 2022. STRESS → DRIFT or DRIFT → TREND_BULL transitions, by contrast, tend to mark the early phase of new uptrends.

Validated on historical episodes: COVID crash (Mar 2020) reads STRESS; calm 2017 melt-up reads TREND_BULL with high persistence; 2018 NBFC crisis reads STRETCHED → STRESS sequence.`,
    },
    {
      heading: "Historical context",
      body: `Notable regime sequences in our panel:

- **Late 2016 — Demonetization shock.** Brief STRESS regime; recovered quickly (DRIFT → TREND_BULL) by Q1 2017.
- **All of 2017 — sustained TREND_BULL.** One of the longest single-regime runs in the panel; breadth wide, VIX low, drawdowns minimal.
- **Sep-Oct 2018 — IL&FS / NBFC.** TREND_BULL → STRETCHED → STRESS in ~4 weeks. Classic late-cycle deterioration sequence.
- **Feb-Mar 2020 — COVID.** Clean STRESS regime; the fastest TREND_BULL-to-STRESS transition in the panel (compressed by the global lockdown news flow).
- **2022 rate shock — DRIFT/STRETCHED chop.** Index moved sideways while internals slowly weakened; regime classifier stayed in DRIFT/STRETCHED for most of the year.

The exact regime transitions and persistence days are visible on the regime-history endpoint and the regime card on Pulse.`,
    },
    {
      heading: "Common misreadings",
      body: `- **"The regime label doesn't change every day — is it broken?"** That's by design. The 3-day confirmation smoothing prevents whipsaws. A single rough trading day in TREND_BULL doesn't flip the label; consistent weakness across the underlying components does.
- **"We're in TREND_BULL so everything is fine."** Regime tells you the overall state, not what individual sectors are doing. Late-stage TREND_BULL often has narrowing leadership — check breadth and sector RS alongside the regime label.
- **"STRESS = sell everything."** STRESS is the regime where forward returns have historically been highest in our data (see [stress score](/insights/learn/stress-score)). It's an uncomfortable regime, not a directional sell signal.`,
    },
  ],
};
