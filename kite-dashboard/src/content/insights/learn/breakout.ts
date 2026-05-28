import type { LearnExplainer } from "./_types";

export const breakout: LearnExplainer = {
  slug: "breakout",
  title: "Breakout",
  category: "pattern",
  summary:
    "A stock closing above a recent significant high — most commonly a 20-day high but can extend to multi-year bases.",
  related: ["coiled-spring", "rs-leader"],
  lastUpdated: "2026-05-28",
  sections: [
    {
      heading: "What it is",
      body: `A **breakout** is a session where a stock closes above a recent meaningful price ceiling. The most common definitions:

- **20-day breakout** — close above the highest close of the prior 20 trading days
- **52-week breakout** — close above the highest close of the prior 252 trading days
- **Multi-year breakout** — close above the highest close of the prior 5+ years (the strongest variant)

The longer the base, the more meaningful the breakout. A multi-year breakout means a stock has cleared every overhead supply level for years — there are no trapped sellers above current price.`,
    },
    {
      heading: "Why it matters",
      body: `Breakouts are the simplest expression of trend continuation. They work because price levels matter via reflexivity — traders watch them, place orders around them, and react when they're crossed.

But breakouts have an honest weakness: **regime-dependence**. In TREND_BULL conditions on Nifty 100, breakouts have meaningfully higher 20-day follow-through. In STRESS or DRIFT regimes, they fail more often. The breakout itself isn't bullish — the breakout in the right regime is.

The Watchlists page surfaces a daily breakout list. We're working on validity-checking multi-year breakouts as a separate, more selective signal (see Phase 4 in our roadmap).`,
    },
    {
      heading: "How to read it",
      body: `- **Volume on the breakout day** should be above average — quiet breakouts have higher fade rates
- **Closing price** matters more than intraday — many "breakouts" reverse below the level by close
- **Follow-through** — the next 1-3 sessions tell you whether the move is real or a fakeout
- **Position vs 200-DMA** — breakouts above 200-DMA in an uptrending market are higher-quality than breakouts in stocks still below their long-term trend
- **Regime** — see [market regime](/insights/learn/regime) for the single biggest filter

Avoid chasing extended breakouts. The best risk-reward is on the day-of or first pullback to the breakout level.`,
    },
  ],
};
