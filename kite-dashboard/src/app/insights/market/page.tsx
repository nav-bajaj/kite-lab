import Link from "next/link";
import {
  getReading,
  fmtPct,
  insightsQuery,
  parseUniverse,
} from "@/lib/insights-api";
import { RegimeLegend } from "../_components/regime-legend";
import {
  Section,
  MetricCard,
  RegimeCard,
  StressGauge,
  SectorBars,
} from "@/components/insights/ui";
import { SectionTabs } from "@/components/insights/mission";
import { MARKET_TABS } from "./_tabs";

function LearnLink({ slug, label = "What is this?" }: { slug: string; label?: string }) {
  return (
    <Link
      href={`/insights/learn/${slug}`}
      className="text-[13px] text-muted-foreground underline-offset-2 hover:text-foreground hover:underline"
    >
      {label}
    </Link>
  );
}

function DetailLink({ slug, dateQuery }: { slug: string; dateQuery: string }) {
  return (
    <Link
      href={`/insights/market/${slug}${dateQuery}`}
      className="text-[13px] font-medium text-primary underline-offset-2 hover:underline"
    >
      History &amp; detail →
    </Link>
  );
}

export const dynamic = "force-dynamic"; // always fetch latest reading
export const revalidate = 900;

// The Market Pulse section page — the full daily read. Headline indicator
// cards here deep-link into their history detail views (./[indicator]).
export default async function MarketPulsePage({
  searchParams,
}: {
  searchParams: Promise<{ date?: string; universe?: string }>;
}) {
  const { date, universe: rawUniverse } = await searchParams;
  const reading = await getReading(date);
  const { regime, stress, sector_leaderboard_60d } = reading;
  const dateQuery = insightsQuery({ date, universe: parseUniverse(rawUniverse) });

  const rankedSectors = [...sector_leaderboard_60d]
    .filter((s) => s.rs_60d !== null)
    .sort((a, b) => (b.rs_60d ?? 0) - (a.rs_60d ?? 0));
  const sectorLeaders = rankedSectors
    .slice(0, 2)
    .map((s) => s.sector.replace("NIFTY_", ""));
  const sectorLaggard =
    rankedSectors.length > 2
      ? rankedSectors[rankedSectors.length - 1].sector.replace("NIFTY_", "")
      : null;
  const sectorTakeaway =
    sectorLeaders.length > 0
      ? `Right now ${sectorLeaders.join(" and ")} are leading the market` +
        (sectorLaggard ? `, while ${sectorLaggard} lags behind` : "") +
        ". Leadership rotates over time — watching it shows which parts of the market are gaining strength and which are losing it."
      : null;

  const breadth = regime.pct_above_200dma;
  const breadthTakeaway =
    breadth === null
      ? undefined
      : breadth >= 0.6
        ? "Most stocks are healthy — the market's strength is broad, not just a few big names."
        : breadth >= 0.4
          ? "About half the market is in good shape — participation is moderate."
          : "Only a minority of stocks are healthy — the market is leaning on a handful of names.";

  return (
    <main className="flex flex-col gap-10">
      <SectionTabs items={MARKET_TABS} activeSlug="" basePath="/insights/market" query={dateQuery} />

      {/* ──────────────── HEADLINE: today's market read ──────────────── */}
      <section className="flex flex-col gap-4">
        <div className="flex flex-col gap-1">
          <h2 className="font-serif text-2xl font-medium tracking-[-0.01em] text-foreground">
            Today&apos;s market
          </h2>
          <p className="text-[13px] text-muted-foreground">
            As of{" "}
            {new Date(reading.date).toLocaleDateString("en-IN", {
              weekday: "long",
              year: "numeric",
              month: "long",
              day: "numeric",
            })}{" "}
            — a quick read on the market&apos;s trend, how calm or stressed it
            is, and how many stocks are healthy.
          </p>
        </div>

        <div className="grid gap-4 sm:grid-cols-3">
          <RegimeCard
            regime={regime}
            help={<LearnLink slug="regime" label="Deep-dive →" />}
          />
          <StressGauge
            stress={stress}
            help={<DetailLink slug="stress" dateQuery={dateQuery} />}
          />
          <MetricCard
            label="Market breadth"
            value={fmtPct(regime.pct_above_200dma, 0)}
            tone={regime.nifty100_above_100dma ? "positive" : "negative"}
            sub="How many stocks are healthy, not just the index — the share in a long-term uptrend"
            help={<DetailLink slug="breadth" dateQuery={dateQuery} />}
            takeaway={breadthTakeaway}
          />
        </div>
      </section>

      {/* ──────────────── SECTOR LEADERS ──────────────── */}
      <Section
        title="Sector leaders"
        help={<LearnLink slug="sector-rs" label="What is relative strength?" />}
      >
        <p className="-mt-2 text-[13px] text-muted-foreground">
          Which parts of the market are leading right now — each sector measured
          against the Nifty 50 over roughly the last three months. Green is
          ahead of the market, red is behind.
        </p>
        <SectorBars sectors={sector_leaderboard_60d} />
        {sectorTakeaway && (
          <p className="border-t border-border pt-3 text-[13px] leading-[1.5] text-foreground">
            {sectorTakeaway}
          </p>
        )}
      </Section>

      {/* ──────────────── REGIME GLOSSARY ──────────────── */}
      <RegimeLegend />
    </main>
  );
}
