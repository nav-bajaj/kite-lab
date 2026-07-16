import Link from "next/link";
import {
  getReading,
  getMovers,
  fmtPct,
  MoversResponse,
} from "@/lib/insights-api";
import { RegimeLegend } from "./_components/regime-legend";
import {
  Section,
  MetricCard,
  RegimeCard,
  StressGauge,
  SectorBars,
} from "@/components/insights/ui";

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

export const dynamic = "force-dynamic"; // always fetch latest reading
export const revalidate = 900;

export default async function PulsePage({
  searchParams,
}: {
  searchParams: Promise<{ date?: string }>;
}) {
  const { date } = await searchParams;
  const [reading, movers] = await Promise.all([
    getReading(date),
    getMovers(date),
  ]);
  const { regime, stress, sector_leaderboard_60d } = reading;
  const dateQuery = date ? `?date=${encodeURIComponent(date)}` : "";

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
    <main className="flex flex-col gap-12">
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
          <StressGauge stress={stress} help={<LearnLink slug="stress-score" />} />
          <MetricCard
            label="Market breadth"
            value={fmtPct(regime.pct_above_200dma, 0)}
            tone={regime.nifty100_above_100dma ? "positive" : "negative"}
            sub="How many stocks are healthy, not just the index — the share in a long-term uptrend"
            help={<LearnLink slug="pct-above-200dma" label="What is breadth?" />}
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

      {/* ──────────────── STOCK MOVERS ──────────────── */}
      {movers.data_available && (
        <StockMoversSection movers={movers} dateQuery={dateQuery} />
      )}

      {/* ──────────────── REGIME GLOSSARY ──────────────── */}
      <RegimeLegend />
    </main>
  );
}

function StockMoversSection({ movers, dateQuery }: { movers: MoversResponse; dateQuery: string }) {
  const { fresh_highs, fresh_lows, rs_improvers } = movers;
  return (
    <Section
      title="Stock movers"
      help={
        <Link
          href={`/insights/screener${dateQuery}`}
          className="text-[13px] text-muted-foreground underline-offset-2 hover:text-foreground hover:underline"
        >
          Open screener →
        </Link>
      }
    >
      <p className="-mt-2 text-[13px] text-muted-foreground">
        Individual stocks making a move today. On the left, names hitting a new
        1-year high or low — a quick read on who&apos;s breaking out and who&apos;s
        breaking down. On the right, the stocks that climbed the most in our
        strength ranking over the past month.
      </p>
      <div className="grid gap-4 md:grid-cols-2">
        {/* Fresh 52-week highs / lows */}
        <div className="flex flex-col gap-3 rounded-xl border border-border bg-card p-5">
          <div className="flex items-baseline justify-between">
            <span className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
              New 1-year highs / lows
            </span>
            <span className="text-[13px] text-muted-foreground">
              {fresh_highs.count} high{fresh_highs.count === 1 ? "" : "s"} · {fresh_lows.count} low{fresh_lows.count === 1 ? "" : "s"}
            </span>
          </div>
          <MoverRow
            label="New highs"
            names={fresh_highs.names.map((n) => n.symbol)}
            dateQuery={dateQuery}
            preset="near-high"
          />
          <MoverRow
            label="New lows"
            names={fresh_lows.names.map((n) => n.symbol)}
            dateQuery={dateQuery}
          />
        </div>

        {/* Biggest RS-rank improvers — observation only */}
        <div className="flex flex-col gap-3 rounded-xl border border-border bg-card p-5">
          <div className="flex items-baseline justify-between">
            <span className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
              Biggest climbers in our strength ranking (past month)
            </span>
            <Link
              href={`/insights/screener${dateQuery ? dateQuery + "&" : "?"}preset=fresh`}
              className="text-[12px] text-muted-foreground underline-offset-2 hover:text-foreground hover:underline"
            >
              See all →
            </Link>
          </div>
          {rs_improvers.length === 0 ? (
            <p className="text-[13px] text-muted-foreground">No notable rank improvers today.</p>
          ) : (
            <ul className="flex flex-col gap-1.5 text-[13px]">
              {rs_improvers.map((e) => (
                <li key={e.symbol} className="flex items-center justify-between gap-2">
                  <Link href={`/insights/stocks/${e.symbol}${dateQuery}`} className="font-medium text-foreground underline-offset-2 hover:underline">
                    {e.symbol}
                  </Link>
                  <span className="tabular-nums text-muted-foreground">
                    {e.rank_21d_ago ?? "—"} → {e.rank ?? "—"}
                    {e.rank_delta_21d ? <span className="ml-1 text-[color:var(--positive)]">(+{e.rank_delta_21d})</span> : null}
                  </span>
                </li>
              ))}
            </ul>
          )}
          <p className="text-[11px] italic leading-[1.5] text-muted-foreground">
            Rank change is a fact, not a forecast — this cohort did not beat the
            baseline in our forward-return study.
          </p>
        </div>
      </div>
    </Section>
  );
}

function MoverRow({ label, names, dateQuery, preset }: { label: string; names: string[]; dateQuery: string; preset?: string }) {
  const presetHref = preset
    ? `/insights/screener${dateQuery ? dateQuery + "&" : "?"}preset=${preset}`
    : null;
  return (
    <div className="flex flex-col gap-1">
      <span className="text-[11px] uppercase tracking-wide text-muted-foreground">{label}</span>
      {names.length === 0 ? (
        <span className="text-[13px] text-muted-foreground">None today.</span>
      ) : (
        <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-[13px]">
          {names.map((s) => (
            <Link key={s} href={`/insights/stocks/${s}${dateQuery}`} className="font-medium text-foreground underline-offset-2 hover:underline">
              {s}
            </Link>
          ))}
          {presetHref && (
            <Link href={presetHref} className="text-[12px] text-muted-foreground underline-offset-2 hover:text-foreground hover:underline">
              (screener →)
            </Link>
          )}
        </div>
      )}
    </div>
  );
}
