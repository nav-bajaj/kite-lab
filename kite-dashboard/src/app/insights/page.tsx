import {
  getReading,
  getBreadthTimeseries,
  fmtPct,
  regimeLabel,
  sectorLabel,
  type TimeseriesResponse,
  type WatchlistEntry,
} from "@/lib/insights-api";
import { SectionHeader, IndicatorCard } from "@/components/insights/mission";
import { SectorBars } from "@/components/insights/ui";

export const dynamic = "force-dynamic";
export const revalidate = 900;

/**
 * Mission control — the Overview. Every indicator appears as a compact card
 * grouped by section; expanding a card opens its detail view (history +
 * how-to-read). Structure per tasks/insights_dashboard_v2/DASHBOARD_DESIGN.md.
 */
export default async function OverviewPage({
  searchParams,
}: {
  searchParams: Promise<{ date?: string }>;
}) {
  const { date } = await searchParams;
  const dateQuery = date ? `?date=${encodeURIComponent(date)}` : "";

  const [reading, breadthSeries] = await Promise.all([
    getReading(date),
    // 6 months of sparkline context for the market cards; detail views fetch
    // full history themselves. Degrades to no-spark when unavailable.
    getBreadthTimeseries({ days: 126, metrics: ["pct_above_200dma"] }).catch(
      (): TimeseriesResponse => ({ index: [], data: {} }),
    ),
  ]);
  const { regime, stress } = reading;
  const breadthSpark = breadthSeries.data["pct_above_200dma"] ?? [];

  const regimeTone =
    regime.regime === "TREND_BULL"
      ? "text-[color:var(--positive)]"
      : regime.regime === "STRESS"
        ? "text-[color:var(--negative)]"
        : regime.regime === "STRETCHED"
          ? "text-[color:var(--warning)]"
          : "text-foreground";
  const stressLevel =
    stress.score < 33 ? "Calm" : stress.score < 66 ? "Elevated" : "High";

  const asOf = new Date(reading.date).toLocaleDateString("en-IN", {
    weekday: "long",
    day: "numeric",
    month: "long",
    year: "numeric",
  });

  // Curated list slots (Slice 4 formalizes these as products; today they show
  // the existing validity-reviewed watchlists behind the same names).
  const listSlots: { key: string; title: string; foot: string }[] = [
    { key: "breakouts", title: "Breakouts", foot: "New 20-day highs above the 50-DMA" },
    { key: "rs_leaders", title: "Relative strength leaders", foot: "Strongest vs Nifty over 6 months" },
    { key: "coiled_springs", title: "Coiled springs", foot: "Tight ranges near the 50-DMA, low volatility" },
    { key: "sustained_uptrend", title: "Sustained uptrends", foot: "Steadily above a rising 200-DMA" },
  ];

  return (
    <main className="flex flex-col gap-8">
      <div className="flex flex-col gap-1">
        <h1 className="font-serif text-3xl font-medium tracking-[-0.01em] text-foreground">
          Overview
        </h1>
        <p className="text-[13px] text-muted-foreground">
          As of {asOf}. Everything at a glance — open any card for its history
          and how to read it.
        </p>
      </div>

      {/* ──────────────── MARKET ──────────────── */}
      <section className="flex flex-col gap-4">
        <SectionHeader
          label="Market"
          link={{ href: "/insights/market", label: "Open Market Pulse" }}
          dateQuery={dateQuery}
        />
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          <IndicatorCard label="Market state" href={`/insights/market/regime${dateQuery}`}>
            <div className="flex items-baseline gap-2">
              <span className={`text-2xl font-semibold leading-tight ${regimeTone}`}>
                {regimeLabel(regime.regime)}
              </span>
              <span className="font-mono text-[12px] text-muted-foreground">
                day {regime.persistence_days}
              </span>
            </div>
            <span className="text-[12px] leading-[1.5] text-muted-foreground">
              One of four rules-based market states, from trend and stress
              conditions.
            </span>
          </IndicatorCard>

          <IndicatorCard label="Market stress" href={`/insights/market/stress${dateQuery}`}>
            <div className="flex items-baseline gap-2">
              <span className="text-2xl font-semibold leading-tight text-foreground">
                {stressLevel}
              </span>
              <span className="font-mono text-[12px] text-muted-foreground">
                {stress.score.toFixed(0)}/100 · p{stress.score_percentile.toFixed(0)}
              </span>
            </div>
            <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
              <div
                className="h-full rounded-full bg-[color:var(--warning)]"
                style={{ width: `${Math.max(0, Math.min(100, stress.score))}%` }}
              />
            </div>
            <span className="text-[12px] leading-[1.5] text-muted-foreground">
              Composite of volatility, drawdown, breadth and dispersion.
            </span>
          </IndicatorCard>

          <IndicatorCard
            label="Market breadth"
            href={`/insights/market/breadth${dateQuery}`}
            spark={breadthSpark}
            foot="Share of NSE 500 stocks above their 200-day average — participation, not just the index."
          >
            <div className="flex items-baseline gap-2">
              <span className="text-2xl font-semibold leading-tight text-foreground">
                {fmtPct(regime.pct_above_200dma, 0)}
              </span>
              <span className="font-mono text-[12px] text-muted-foreground">
                above 200-DMA
              </span>
            </div>
          </IndicatorCard>
        </div>
      </section>

      {/* ──────────────── SECTORS & ROTATION ──────────────── */}
      <section className="flex flex-col gap-4">
        <SectionHeader
          label="Sectors & rotation"
          link={{ href: "/insights/sectors", label: "Open Sectors" }}
          dateQuery={dateQuery}
        />
        <div className="rounded-xl border border-border bg-card p-5">
          <div className="mb-3 flex items-baseline justify-between gap-3">
            <span className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
              Sector relative strength vs Nifty 50 · 60 days
            </span>
          </div>
          <SectorBars sectors={reading.sector_leaderboard_60d} limit={10} />
        </div>
      </section>

      {/* ──────────────── STOCK LISTS ──────────────── */}
      <section className="flex flex-col gap-4">
        <SectionHeader
          label="Stock lists"
          link={{ href: "/insights/watchlists", label: "Open Stock Lists" }}
          dateQuery={dateQuery}
        />
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {listSlots.map((slot) => {
            const entries: WatchlistEntry[] = reading.watchlists[slot.key] ?? [];
            return (
              <IndicatorCard
                key={slot.key}
                label={slot.title}
                href={`/insights/watchlists${dateQuery}`}
                foot={slot.foot}
              >
                <div className="flex items-baseline gap-2">
                  <span className="text-2xl font-semibold leading-tight text-foreground">
                    {/* The reading payload caps each list at 15 entries. */}
                    {entries.length >= 15 ? "15+" : entries.length}
                  </span>
                  <span className="text-[12px] text-muted-foreground">
                    name{entries.length === 1 ? "" : "s"} today
                  </span>
                </div>
                {entries.length > 0 && (
                  <span className="truncate font-mono text-[11px] text-muted-foreground">
                    {entries.slice(0, 3).map((e) => e.symbol).join(" · ")}
                    {entries.length > 3 ? " …" : ""}
                  </span>
                )}
              </IndicatorCard>
            );
          })}
        </div>
      </section>

      {/* Sector context line, derived from the leaderboard (descriptive only). */}
      {reading.sector_leaderboard_60d.length > 0 && (
        <p className="text-[12px] leading-[1.6] text-muted-foreground">
          Leadership right now:{" "}
          {[...reading.sector_leaderboard_60d]
            .filter((s) => s.rs_60d !== null)
            .sort((a, b) => (b.rs_60d ?? 0) - (a.rs_60d ?? 0))
            .slice(0, 3)
            .map((s) => sectorLabel(s.sector))
            .join(", ")}{" "}
          lead the market over the last three months. Rotation is normal —
          the Sectors view tracks how it shifts.
        </p>
      )}
    </main>
  );
}
