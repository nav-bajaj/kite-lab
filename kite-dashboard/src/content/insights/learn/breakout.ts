import type { LearnExplainer } from "./_types";

export const breakout: LearnExplainer = {
  slug: "breakout",
  title: "Breakout",
  category: "pattern",
  summary:
    "When a stock closes above a recent high — a sign it may be starting a fresh leg up after a pause.",
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
    {
      heading: "How we detect it on the Watchlists page",
      body: `The transparent detection rule is in our codebase (\`watchlists.get_breakouts\`):

- Close today is **above the highest close** of the prior 20 trading days (excluding today)
- Close today is **above the 50-day moving average**
- Sorted by % distance above the 20-day high — names extending further are listed first

That's it. No volume filter, no proprietary scoring. The simplicity is intentional — we want the signal to be reproducible if you wanted to screen on your own data. Multi-year breakout variants (52-week, 5-year) are not yet on the live watchlist (Phase 4.2 — needs validity work before we publish forward-return claims).`,
    },
    {
      heading: "When breakouts fail",
      body: `- **STRESS or STRETCHED regime.** Failure rate is meaningfully higher; many breakouts immediately reverse below the breakout level.
- **Low volume on the breakout day.** Quiet breakouts have historically faded more often than thrust breakouts. The Watchlists page doesn't filter by volume — that's a check you'd do yourself.
- **Index-level breakouts in narrow tapes.** When a sector breakout depends on 1-2 mega-caps (high [concentration](/insights/learn/concentration), narrow [sector breadth](/insights/learn/sector-breadth)), the move is less structurally supported.
- **Late-stage TREND_BULL.** Lots of stocks "break out" in extended uptrends; the signal-to-noise of any individual breakout falls because every name is making new highs.`,
    },
  ],
};
