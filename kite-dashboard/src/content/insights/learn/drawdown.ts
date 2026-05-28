import type { LearnExplainer } from "./_types";

export const drawdown: LearnExplainer = {
  slug: "drawdown",
  title: "Drawdown",
  category: "concept",
  summary:
    "How far an index or stock is below its most recent peak. The most-used measure of pain in markets.",
  related: ["stress-score", "regime"],
  lastUpdated: "2026-05-28",
  sections: [
    {
      heading: "What it is",
      body: `Drawdown is the percentage decline from a series' all-time-high (or rolling peak) to the current value. If Nifty made an all-time high at 25,000 and is now at 22,500, the current drawdown is -10%.

We track drawdowns at two scopes:

- **Index drawdown** — Nifty 50 from its peak. Used as one input to the [stress score](/insights/learn/stress-score) (25% weight).
- **Maximum drawdown** — the worst drawdown experienced over a chosen window. Used to characterise how painful past episodes were.

Drawdowns are **always negative or zero** (a series at its peak has zero drawdown; a series below its peak has negative drawdown).`,
    },
    {
      heading: "Why it matters",
      body: `Average return tells you what to expect long-term. Drawdown tells you what the journey feels like — and what you can survive. Backtested strategies with the same CAGR can have very different drawdown profiles, and the one with the deeper drawdowns is the one investors actually sell at the bottom of.

For the broad Indian market, drawdowns have a relatively stable structure: most years see a 5-12% intra-year drawdown; about every 4-7 years there's a 20-30% drawdown; once-a-decade events go to 40%+. Knowing this lets you size positions for the conditions you can tolerate.`,
    },
    {
      heading: "How to read it",
      body: `- **-5% or less** — Routine. Most years see at least one of these.
- **-5% to -10%** — Notable. Often coincides with regime shifting from TREND_BULL to DRIFT.
- **-10% to -20%** — Painful. Historically the zone where the [stress score](/insights/learn/stress-score) becomes elevated.
- **-20% to -30%** — Crisis-zone. 2008, 2015-16, 2018-19, 2020 all qualified. Forward returns from these levels have historically been strong, but the **path** to get there can take months.
- **> -30%** — Once-a-decade. COVID's flash to -35% in March 2020 is the most recent example.

Drawdown depth itself isn't a tradeable signal — it's a context input. The combination of "deep drawdown + breadth healing + volatility cooling" is what often marks the bottom, not drawdown alone.`,
    },
    {
      heading: "Historical context — major Nifty drawdowns",
      body: `- **2008 GFC** — Nifty drawdown approached -60% intraday at the worst. Took years to fully recover. The deepest event in the modern panel.
- **2015-2016 China / oil cycle.** Multi-quarter drawdown into the -20% range; resolved by mid-2016.
- **2018-2019 NBFC aftermath.** Drawdown depth modest at the index level (~-15%) but mid/small caps had a much worse experience — emphasising that index drawdown understates broader pain.
- **Feb-Mar 2020 COVID.** -35% in about a month — the fastest deep drawdown in the panel. The recovery from those lows was equally fast.
- **2022 rate shock.** Shallow at the Nifty level (~-10%) but persistent — DRIFT regime characteristic.

For per-portfolio drawdown (which is generally different from the index), see the performance pages.`,
    },
    {
      heading: "Common misreadings",
      body: `- **"-20% drawdown = capitulation."** Sometimes. Often it's a midway point and not a low. Capitulation usually requires stress + breadth + dispersion to all confirm together.
- **"My portfolio drawdown should look like the Nifty drawdown."** Nope. Concentrated portfolios and smaller-cap portfolios usually run deeper drawdowns than the headline Nifty in the same episode. Plan for portfolio-specific drawdown expectations.
- **"Drawdown is just a number."** It's a behavioral input. The deepest drawdown you can tolerate without forced selling is the actual limit of your strategy, regardless of how good the backtest looks.`,
    },
  ],
};
