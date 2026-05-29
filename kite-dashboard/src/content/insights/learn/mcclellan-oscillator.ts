import type { LearnExplainer } from "./_types";

export const mcclellanOscillator: LearnExplainer = {
  slug: "mcclellan-oscillator",
  title: "McClellan oscillator",
  category: "indicator",
  summary:
    "A breadth momentum indicator computed from advancing minus declining stocks across NSE 500.",
  related: ["pct-above-200dma", "dispersion"],
  lastUpdated: "2026-05-28",
  sections: [
    {
      heading: "What it is",
      body: `Each trading day, count the NSE 500 stocks that closed UP versus the stocks that closed DOWN. The difference (advances minus declines) gives daily breadth. The **McClellan oscillator** is the spread between a fast and slow exponential moving average of that daily difference — specifically a 19-day EMA minus a 39-day EMA.

When more stocks are advancing than declining over the recent fast window relative to the slower baseline, the oscillator is positive. When fewer are, it's negative. Extreme readings (typically ±100 or more on NSE 500-scaled values) flag breadth thrusts or breadth washouts.`,
    },
    {
      heading: "Why it matters",
      body: `Index-level price hides what's happening across the broader market. A Nifty +0.5% day driven by RIL + 2 banks while 60% of NSE 500 fell is materially different from a +0.5% day with 75% participation. McClellan captures the participation dimension.

It's a **momentum** measure of breadth, not a level — it's not asking "are most stocks above their 200-DMA right now?" (that's a different indicator). It's asking "are more stocks advancing than declining lately relative to the recent baseline?"`,
    },
    {
      heading: "How to read it",
      body: `- **Positive and rising** — breadth momentum healthy, rallies likely to broaden.
- **Negative and falling** — selling is broadening, often precedes index-level breakdowns.
- **Extreme negative readings** that quickly reverse — historically these have marked durable lows in Indian markets (e.g., late-March 2020).
- **Bearish divergence** (index makes new high while McClellan does not) — late-cycle warning; participation narrowing.
- **Bullish divergence** (index makes new low while McClellan does not) — early bottoming sign.

Always use alongside regime: a slipping McClellan in TREND_BULL is a minor caution; the same in STRETCHED demands more attention.`,
    },
    {
      heading: "Historical context",
      body: `- **Late March 2020.** Extreme negative McClellan readings during the COVID washout, followed by a rapid swing positive — historically a high-confidence reversal pattern, and it played out cleanly in the subsequent recovery.
- **Aug-Sep 2018.** McClellan started fading well before the index broke down — bearish divergence ran for weeks before the NBFC crisis became headline news.
- **Early 2021.** McClellan stayed positive for an unusually long stretch — the post-COVID broad re-rating.

McClellan dovetails with [% above 200-DMA](/insights/learn/pct-above-200dma) (which measures the level of breadth) and the [stress score](/insights/learn/stress-score).`,
    },
    {
      heading: "Common misreadings",
      body: `- **"McClellan crossed zero — buy / sell."** The crossover itself isn't a trade; many small crossings happen in normal conditions. Sustained moves are the signal.
- **"Negative McClellan = bearish."** Not always. Deep negative readings that quickly reverse have historically marked bullish reversals more often than further drops. Direction matters less than extremity and reversal.
- **"McClellan and 200-DMA breadth tell the same story."** They don't. McClellan is *momentum* of breadth; 200-DMA breadth is *level* of breadth. They can disagree — and the disagreement often surfaces transition periods.`,
    },
  ],
};
