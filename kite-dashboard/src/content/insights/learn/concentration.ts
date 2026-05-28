import type { LearnExplainer } from "./_types";

export const concentration: LearnExplainer = {
  slug: "concentration",
  title: "Concentration / index attribution",
  category: "concept",
  summary:
    "What % of today's Nifty 50 move came from the top 3, top 5, and Reliance specifically. Tells you whether a tape is broad or narrow.",
  related: ["sector-breadth", "pct-above-200dma"],
  lastUpdated: "2026-05-28",
  sections: [
    {
      heading: "What it is",
      body: `Nifty 50 is a **cap-weighted** index. HDFCBANK at ~13% weight and Reliance at ~8% weight contribute far more to the daily index move than a 0.5%-weight name moving the same percentage. The concentration widget decomposes today's Nifty move into per-constituent contributions:

  contribution_i = weight_i × return_i
  share_of_move_i = contribution_i / index_return

It then aggregates:

- **Top-3 share of move** — what percentage of today's index change came from the three largest contributors
- **Top-5 share of move** — same, for the top 5
- **Reliance share** — RIL specifically, since it's the single most-watched concentration risk in Indian equities
- **Cap-weighted vs equal-weighted spread** — official Nifty return minus the simple average of constituent returns. Large positive = mega-caps led. Large negative = small-caps in the index led, mega-caps lagged.`,
    },
    {
      heading: "Why it matters",
      body: `A Nifty +0.4% day can mean very different things:

- **+0.4% with broad participation** (top-3 share ~25%, cap-vs-equal close to zero) — money is flowing widely across names; the move has structural support
- **+0.4% driven by RIL alone** (top-3 share 80%+, cap-vs-equal strongly positive) — the move depends on a couple of mega-caps; it's a thin tape that can reverse fast

The same index print masks fundamentally different market conditions. Concentration math forces the truth out: **the index level is the average, but the average can hide who's actually moving**.

This is especially relevant in Indian equities because the top 5 names in Nifty 50 add up to ~40% of the index, and a single RIL earnings day can swing the headline by 1% even if every other stock is flat.`,
    },
    {
      heading: "How to read it",
      body: `- **Top-3 share > 80%** — Very narrow tape. The headline depends on a few names. Treat the broader market signal with caution.
- **Top-3 share 50-80%** — Concentrated, but not extreme. Pretty normal for Nifty on small-move days.
- **Top-3 share < 30%** — Broad participation. Index move is well-distributed; structurally healthier.
- **Cap-vs-equal spread > +0.3pp** — Mega-caps led; small/mid-caps in the index lagged
- **Cap-vs-equal spread < -0.3pp** — Broad-base lifted; mega-caps a drag
- **When Nifty barely moved** — attribution becomes mathematically unstable (division by near-zero). The widget shows "—" in that case, which is honest, not a bug.

Read this alongside [sector breadth](/insights/learn/sector-breadth) — concentration tells you index-level participation; sector breadth tells you participation within each sector. Both can disagree: Nifty broad participation with banks narrowly concentrated, for example.`,
    },
  ],
};
