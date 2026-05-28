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
    color: "bg-emerald-50 border-emerald-200 text-emerald-900 dark:bg-emerald-950/30",
    dot: "bg-emerald-500",
    rule: "NIFTY 100 above its 100-day average AND broad participation (more than 55% of NSE 500 stocks above their 200-day average).",
    plain:
      "Markets in a healthy uptrend — direction is up and most stocks are joining the move.",
  },
  {
    label: "Drift",
    color: "bg-neutral-50 border-neutral-200 text-neutral-900 dark:bg-neutral-900/40",
    dot: "bg-neutral-400",
    rule:
      "Neither the trend/breadth nor the stress thresholds are firing. The 'messy middle' — mixed signals.",
    plain:
      "Markets are neutral — neither trending strongly nor under pressure. Most common regime; about 30-35% of historical days.",
  },
  {
    label: "Stretched",
    color: "bg-amber-50 border-amber-200 text-amber-900 dark:bg-amber-950/30",
    dot: "bg-amber-500",
    rule:
      "Uptrend in place AND very broad (more than 85% above 200-DMA) AND very low vol (VIX z-score below -1).",
    plain:
      "Markets are above trend, almost everything is participating, and nobody is worried — historically a setup that precedes pullbacks. Not a sell signal; just a 'be aware' tag.",
  },
  {
    label: "Stress",
    color: "bg-red-50 border-red-200 text-red-900 dark:bg-red-950/30",
    dot: "bg-red-500",
    rule:
      "VIX z-score above +1.5 (vol spike) OR (Nifty below trend AND less than 35% of stocks above 200-DMA).",
    plain:
      "Markets are under pressure — vol elevated or breadth deteriorating. Historically the BEST forward-return regime in the data: median +3% over the next 20 days from STRESS days, with 72% of observations finishing positive. The 'buy panic' zone, statistically.",
  },
];

export function RegimeLegend() {
  return (
    <section id="regime-legend" className="mt-6">
      <h3 className="text-base font-semibold">What do the regimes mean?</h3>
      <p className="mt-1 text-xs text-neutral-500">
        Each day is classified into one of four regimes from a simple
        rules-based model using NSE 500 breadth + VIX. Definitions below
        mirror the actual classifier — no marketing gap.
      </p>
      <div className="mt-3 grid gap-3 sm:grid-cols-2">
        {REGIMES.map((r) => (
          <div
            key={r.label}
            className={`rounded border p-3 text-sm ${r.color}`}
          >
            <div className="flex items-center gap-2 font-medium">
              <span
                className={`inline-block h-2.5 w-2.5 rounded-full ${r.dot}`}
                aria-hidden
              />
              {r.label}
            </div>
            <p className="mt-2 text-sm">{r.plain}</p>
            <p className="mt-2 text-xs text-neutral-600 dark:text-neutral-400">
              <span className="font-semibold">Rule:</span> {r.rule}
            </p>
          </div>
        ))}
      </div>
      <p className="mt-3 text-xs text-neutral-500">
        Regime transitions need 3 consecutive days in the new state before
        the label changes (smoothing avoids day-to-day flip-flopping).
      </p>
    </section>
  );
}
