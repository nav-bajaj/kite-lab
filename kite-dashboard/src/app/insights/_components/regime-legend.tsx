/**
 * Plain-English glossary for the four regime labels. Mirrors the actual
 * classifier rules in `kite-api/app/insights/regime.py` so what readers
 * see here is exactly what the engine is doing — no marketing translation
 * gap.
 *
 * Lives on the Pulse page (where the regime is the headline). Also linked
 * to from any regime label via the anchor id "regime-legend" so we can
 * deep-link "What do these mean?" from anywhere on the page.
 */

const REGIMES = [
  {
    label: "Trend Bull",
    accent: "var(--positive)",
    rule: "NIFTY 100 above its 100-day average AND broad participation (more than 55% of NSE 500 stocks above their 200-day average).",
    plain:
      "Markets in a healthy uptrend — direction is up and most stocks are joining the move.",
  },
  {
    label: "Drift",
    accent: "var(--muted-foreground)",
    rule:
      "Neither the trend/breadth nor the stress thresholds are firing. The 'messy middle' — mixed signals.",
    plain:
      "Markets are neutral — neither trending strongly nor under pressure. Most common regime; about 30-35% of historical days.",
  },
  {
    label: "Stretched",
    accent: "var(--warning)",
    rule:
      "Uptrend in place AND very broad (more than 85% above 200-DMA) AND very low vol (VIX z-score below -1).",
    plain:
      "Markets are above trend, almost everything is participating, and nobody is worried — historically a setup that precedes pullbacks. Not a sell signal; just a 'be aware' tag.",
  },
  {
    label: "Stress",
    accent: "var(--negative)",
    rule:
      "VIX z-score above +1.5 (vol spike) OR (Nifty below trend AND less than 35% of stocks above 200-DMA).",
    plain:
      "Markets are under pressure — vol elevated or breadth deteriorating. Historically the BEST forward-return regime in the data: median +3% over the next 20 days from STRESS days, with 72% of observations finishing positive. The 'buy panic' zone, statistically.",
  },
];

export function RegimeLegend() {
  return (
    <section id="regime-legend" className="flex flex-col gap-4">
      <div className="flex flex-col gap-1">
        <h3 className="font-serif text-xl font-medium tracking-[-0.01em] text-foreground">
          The four market states, explained
        </h3>
        <p className="text-[13px] text-muted-foreground">
          Every day we sort the market into one of four states (the technical
          name is &ldquo;regime&rdquo;). It&apos;s a simple rules-based read on
          trend and stress. The plain-English meaning is on top; the exact rule
          we use is underneath, so there&apos;s no gap between what we say and
          what the model does.
        </p>
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        {REGIMES.map((r) => (
          <div
            key={r.label}
            className="rounded-xl border border-border bg-card p-4 text-sm"
          >
            <div className="flex items-center gap-2 font-medium text-foreground">
              <span
                className="inline-block h-2.5 w-2.5 rounded-full"
                style={{ backgroundColor: r.accent }}
                aria-hidden
              />
              {r.label}
            </div>
            <p className="mt-2 text-sm leading-[1.55] text-foreground">{r.plain}</p>
            <p className="mt-2 text-[13px] leading-[1.5] text-muted-foreground">
              <span className="font-semibold">Rule:</span> {r.rule}
            </p>
          </div>
        ))}
      </div>
      <p className="text-[13px] text-muted-foreground">
        Regime transitions need 3 consecutive days in the new state before
        the label changes (smoothing avoids day-to-day flip-flopping).
      </p>
    </section>
  );
}
