/**
 * Plain-English legend for the four regime labels. Mirrors the actual
 * classifier rules in `kite-api/app/insights/regime.py` so what readers
 * see here is exactly what the engine is doing — no marketing translation
 * gap.
 *
 * The rules are stated in the open, not behind a disclosure control
 * (founder, 2026-08-15): if the reader has to click to find out what the
 * label means, the label is doing the talking instead of the rule. The
 * rule text is scoped to the selected universe, because the regime is —
 * a Nifty 500 Trend Bull reads the Nifty 500's own trend and the Nifty
 * 500's own breadth.
 */

function regimes(indexLabel: string, universeLabel: string) {
  return [
    {
      label: "Trend Bull",
      accent: "var(--positive)",
      plain:
        "A healthy uptrend with the market behind it — direction is up and most stocks are joining the move.",
      rule: `${indexLabel} is above its 100-day average and more than 55% of ${universeLabel} stocks are above their own 200-day average.`,
    },
    {
      label: "Drift",
      accent: "var(--muted-foreground)",
      plain:
        "The messy middle — neither trending strongly nor under real pressure. This is the most common regime.",
      rule: "Neither the trend-and-participation conditions nor the stress conditions are met.",
    },
    {
      label: "Stretched",
      accent: "var(--warning)",
      plain:
        "Above trend, almost everything participating, and nobody worried. A description of complacency, not a sell signal.",
      rule: `${indexLabel} is above its 100-day average, more than 85% of ${universeLabel} stocks are above their 200-day average, and India VIX sits more than one standard deviation below its own year.`,
    },
    {
      label: "Stress",
      accent: "var(--negative)",
      plain:
        "Conditions are tense — volatility has spiked, or the market is below trend while participation breaks down.",
      rule: `India VIX is more than 1.5 standard deviations above its own year, or ${indexLabel} is below its 100-day average while fewer than 35% of ${universeLabel} stocks hold above their 200-day average.`,
    },
  ];
}

export function RegimeLegend({
  indexLabel = "Nifty 500",
  universeLabel = "Nifty 500",
}: {
  indexLabel?: string;
  universeLabel?: string;
}) {
  return (
    <section id="regime-legend" className="flex flex-col gap-4">
      <div className="flex flex-col gap-1">
        <h3 className="font-serif text-xl font-medium tracking-[-0.01em] text-foreground">
          The four regimes, explained
        </h3>
        <p className="text-[13px] text-muted-foreground">
          Every day the market is sorted into one of four regimes from three
          observable inputs: trend, participation and volatility. Each card
          gives the plain meaning and the exact rule the engine checks — so
          there is no gap between what we say and what the model does.
        </p>
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        {regimes(indexLabel, universeLabel).map((r) => (
          <div
            key={r.label}
            className="flex flex-col gap-2 rounded-xl border border-border bg-card p-4 text-sm"
          >
            <div className="flex items-center gap-2 font-medium text-foreground">
              <span
                className="inline-block h-2.5 w-2.5 rounded-full"
                style={{ backgroundColor: r.accent }}
                aria-hidden
              />
              {r.label}
            </div>
            <p className="text-sm leading-[1.55] text-foreground">{r.plain}</p>
            <p className="text-[13px] leading-[1.5] text-muted-foreground">
              <span className="font-medium text-foreground">The rule: </span>
              {r.rule}
            </p>
          </div>
        ))}
      </div>
      <p className="text-[13px] text-muted-foreground">
        A regime change needs 3 consecutive days in the new regime before the
        label switches, so a single rough session doesn&apos;t flip it.
      </p>
    </section>
  );
}
