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

function regimes(
  indexLabel: string,
  universeLabel: string,
  trend: number,
  participation: number,
) {
  return [
    {
      label: "Trend Bull",
      accent: "var(--positive)",
      plain:
        "A healthy uptrend with the market behind it. The direction is up and a majority of stocks are joining the move.",
      rule: `${indexLabel} is above its ${trend}-day average and more than 55% of ${universeLabel} stocks are above their own ${participation}-day average.`,
    },
    {
      label: "Drift",
      accent: "var(--muted-foreground)",
      plain: "The messy middle. Not trending strongly on either side.",
      rule: "Neither the trend-and-participation conditions nor the stress conditions are met.",
    },
    {
      label: "Stretched",
      accent: "var(--warning)",
      plain:
        "An overstretched trend. Wide participation with low levels of worry. A sign of complacency.",
      rule: `${indexLabel} is above its ${trend}-day average, more than 85% of ${universeLabel} stocks are above their ${participation}-day average, and India VIX sits more than one standard deviation below its average of the past year.`,
    },
    {
      label: "Stress",
      accent: "var(--negative)",
      plain:
        "Conditions are tense and volatility has spiked. The market is below trend while participation breaks down.",
      rule: `India VIX is more than 1.5 standard deviations above its average of the past year, or ${indexLabel} is below its ${trend}-day average while fewer than 35% of ${universeLabel} stocks hold above their ${participation}-day average.`,
    },
  ];
}

export function RegimeLegend({
  indexLabel = "Nifty 500",
  universeLabel = "Nifty 500",
  trendMaDays = 50,
  participationMaDays = 50,
}: {
  indexLabel?: string;
  universeLabel?: string;
  trendMaDays?: number;
  participationMaDays?: number;
}) {
  return (
    <section id="regime-legend" className="flex flex-col gap-4">
      <div className="flex flex-col gap-1">
        <h3 className="text-xl font-semibold tracking-[-0.01em] text-foreground">
          The four regimes explained:
        </h3>
        <p className="text-[13px] text-muted-foreground">
          Every day the market is sorted into one of four regimes from three
          observable inputs: trend, participation and volatility.
        </p>
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        {regimes(indexLabel, universeLabel, trendMaDays, participationMaDays).map((r) => (
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
    </section>
  );
}
