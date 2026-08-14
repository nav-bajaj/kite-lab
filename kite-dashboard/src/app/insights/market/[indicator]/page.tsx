import Link from "next/link";
import { notFound } from "next/navigation";
import {
  getReading,
  getBreadthTimeseries,
  getStressTimeseries,
  getRegimeHistory,
  fmtPct,
  regimeLabel,
  type MarketReading,
  type RegimeEpisode,
  type TimeseriesResponse,
} from "@/lib/insights-api";
import { DetailShell, StatStrip, type SubRailItem } from "@/components/insights/mission";
import { TimeseriesChart, type ReferenceBand } from "@/components/insights/timeseries-chart";

export const dynamic = "force-dynamic";
export const revalidate = 900;

/**
 * Market indicator detail views (mission control: expand a card → land here).
 * Slice 1 ships breadth / stress / regime; the remaining Market indicators
 * appear in the sub-rail as "soon" so the section's full shape is visible.
 */

const RAIL: SubRailItem[] = [
  { slug: "regime", label: "Market state", ready: true },
  { slug: "stress", label: "Market stress", ready: true },
  { slug: "breadth", label: "Breadth", ready: true },
  { slug: "vix", label: "India VIX", ready: false },
  { slug: "net-new-highs", label: "Net new highs", ready: false },
  { slug: "mcclellan", label: "McClellan osc", ready: false },
  { slug: "concentration", label: "Concentration", ready: false },
];

const TITLES: Record<string, string> = {
  regime: "Market state",
  stress: "Market stress",
  breadth: "Market breadth",
};

export async function generateMetadata({
  params,
}: {
  params: Promise<{ indicator: string }>;
}) {
  const { indicator } = await params;
  const title = Object.prototype.hasOwnProperty.call(TITLES, indicator)
    ? TITLES[indicator as keyof typeof TITLES]
    : "Market";
  return { title: `${title} — Marketworks Insights` };
}

function LearnPanel({
  slug,
  title,
  children,
}: {
  slug: string;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-2 rounded-xl border border-border bg-primary/[0.03] p-5">
      <span className="text-[12px] font-semibold text-foreground">{title}</span>
      <p className="text-[13px] leading-[1.6] text-muted-foreground">{children}</p>
      <Link
        href={`/insights/learn/${slug}`}
        className="text-[13px] font-medium text-primary underline-offset-2 hover:underline"
      >
        Learn more →
      </Link>
    </div>
  );
}

function ChartCard({
  title,
  sub,
  children,
}: {
  title: string;
  sub: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-3 rounded-xl border border-border bg-card p-5">
      <div className="flex flex-col gap-0.5">
        <span className="font-serif text-lg font-medium text-foreground">{title}</span>
        <span className="text-[13px] text-muted-foreground">{sub}</span>
      </div>
      {children}
    </div>
  );
}

// Reference levels from the Breadth Atlas empirical profile
// (tasks/breadth_atlas/REPORT.md §1: p5 = 22%, median = 59%, p95 = 94%
// for pct_above_200dma over 2010-2026). Descriptive context lines, not
// thresholds to act on.
const BREADTH_BANDS: ReferenceBand[] = [
  { value: 0.94, label: "rare strength since 2010 (top 5% of days)", tone: "warning" },
  { value: 0.59, label: "median day since 2010", tone: "muted" },
  { value: 0.22, label: "washed-out territory (bottom 5% of days)", tone: "negative" },
];

async function BreadthDetail({ reading }: { reading: MarketReading }) {
  const series = await getBreadthTimeseries({
    days: 4000,
    metrics: ["pct_above_200dma"],
  }).catch((): TimeseriesResponse => ({ index: [], data: {} }));
  const values = series.data["pct_above_200dma"] ?? [];
  const now = reading.regime.pct_above_200dma;

  let streak = 0;
  for (let i = values.length - 1; i >= 0; i--) {
    /* eslint-disable-next-line security/detect-object-injection -- numeric loop index */
    const v = values[i];
    if (v === null || v < 0.59) break;
    streak += 1;
  }

  return (
    <div className="flex flex-col gap-4">
      <ChartCard
        title="Share of NSE 500 above the 200-day average"
        sub="Participation in long-term uptrends, daily since 2010. Dashed lines mark where days like today have historically sat."
      >
        <TimeseriesChart dates={series.index} values={values} bands={BREADTH_BANDS} percent />
      </ChartCard>
      <StatStrip
        stats={[
          { label: "Now", value: fmtPct(now, 0), sub: "of NSE 500" },
          { label: "Median since 2010", value: "59%", sub: "the typical day" },
          { label: "Washed-out line", value: "22%", sub: "bottom 5% of days" },
          {
            label: "Days at or above median",
            value: String(streak),
            sub: streak === 0 ? "currently below the median" : "current run",
          },
        ]}
      />
      <LearnPanel slug="pct-above-200dma" title="What this measures">
        Breadth counts how many stocks are in long-term uptrends, not just
        whether the index is up. Narrow rallies — index rising while breadth
        stalls — have historically been the more fragile kind. This series
        moves over weeks, not days, which is why the chart carries more
        information than any single day&apos;s number.
      </LearnPanel>
    </div>
  );
}

// Stress score bands mirror the gauge's own wording (calm / elevated / high).
const STRESS_BANDS: ReferenceBand[] = [
  { value: 66, label: "high-stress zone", tone: "negative" },
  { value: 33, label: "calm below this line", tone: "muted" },
];

async function StressDetail({ reading }: { reading: MarketReading }) {
  const series = await getStressTimeseries(4000).catch(
    (): TimeseriesResponse => ({ index: [], data: {} }),
  );
  const values = series.data["score"] ?? [];
  const s = reading.stress;
  const components: { label: string; value: number | null }[] = [
    { label: "Volatility (VIX percentile)", value: s.vix_pctile_component },
    { label: "Nifty drawdown", value: s.drawdown_component },
    { label: "Stocks below 200-DMA", value: s.below_200dma_component },
    { label: "Return dispersion", value: s.dispersion_component },
  ];

  return (
    <div className="flex flex-col gap-4">
      <ChartCard
        title="Market stress composite, 0–100"
        sub="Volatility, drawdown, breadth and dispersion folded into one score. Spikes cluster at regime breaks; quiet stretches are the norm."
      >
        <TimeseriesChart dates={series.index} values={values} bands={STRESS_BANDS} />
      </ChartCard>
      <StatStrip
        stats={[
          { label: "Now", value: s.score.toFixed(0), sub: "out of 100" },
          {
            label: "Percentile",
            value: `p${s.score_percentile.toFixed(0)}`,
            sub: "vs all past days",
          },
          { label: "India VIX", value: s.vix_close?.toFixed(1) ?? "—", sub: "close" },
          {
            label: "Nifty drawdown",
            value: fmtPct(s.nifty_drawdown_pct, 1),
            sub: "from recent high",
          },
        ]}
      />
      <div className="flex flex-col gap-2 rounded-xl border border-border bg-card p-5">
        <span className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
          What&apos;s driving the score today
        </span>
        {components.map((c) => (
          <div key={c.label} className="flex items-center gap-3">
            <span className="w-56 shrink-0 text-[13px] text-foreground">{c.label}</span>
            <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
              <div
                className="h-full rounded-full bg-[color:var(--chart-1)]"
                style={{ width: `${Math.max(0, Math.min(100, (c.value ?? 0) * 100))}%` }}
              />
            </div>
            <span className="w-10 shrink-0 text-right font-mono text-[12px] tabular-nums text-muted-foreground">
              {c.value === null ? "—" : (c.value * 100).toFixed(0)}
            </span>
          </div>
        ))}
      </div>
      <LearnPanel slug="stress-score" title="What this measures">
        A single 0–100 read on how tense conditions are, blending four
        observable inputs. It describes the environment — calm markets tend to
        produce smaller swings, stressed ones bigger and faster swings — and
        says nothing about direction.
      </LearnPanel>
    </div>
  );
}

const REGIME_COLOR: Record<RegimeEpisode["regime"], string> = {
  TREND_BULL: "var(--positive)",
  DRIFT: "var(--muted-foreground)",
  STRETCHED: "var(--warning)",
  STRESS: "var(--negative)",
};

function RegimeTimeline({ episodes }: { episodes: RegimeEpisode[] }) {
  if (episodes.length === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        Regime history is not available right now.
      </p>
    );
  }
  const totalDays = episodes.reduce((acc, e) => acc + e.days, 0);
  const W = 1000;
  const H = 34;
  const segments = episodes.reduce<{ x: number; w: number }[]>((arr, e) => {
    const prev = arr.length > 0 ? arr[arr.length - 1] : null;
    arr.push({ x: prev ? prev.x + prev.w : 0, w: (e.days / totalDays) * W });
    return arr;
  }, []);
  return (
    <div className="flex flex-col gap-2">
      <svg viewBox={`0 0 ${W} ${H}`} className="h-9 w-full" preserveAspectRatio="none">
        {episodes.map((e, i) => (
          <rect
            key={`${e.start}-${i}`}
            /* eslint-disable-next-line security/detect-object-injection -- numeric loop index */
            x={segments[i].x}
            y={6}
            /* eslint-disable-next-line security/detect-object-injection -- numeric loop index */
            width={Math.max(segments[i].w - 0.5, 0.5)}
            height={22}
            rx={2}
            fill={REGIME_COLOR[e.regime]}
            opacity={0.85}
          />
        ))}
      </svg>
      <div className="flex justify-between text-[11px] text-muted-foreground">
        <span>
          {new Date(episodes[0].start).toLocaleDateString("en-IN", {
            month: "short",
            year: "numeric",
          })}
        </span>
        <span>
          {new Date(episodes[episodes.length - 1].end).toLocaleDateString("en-IN", {
            month: "short",
            year: "numeric",
          })}
        </span>
      </div>
      <div className="flex flex-wrap gap-4 pt-1">
        {(Object.keys(REGIME_COLOR) as RegimeEpisode["regime"][]).map((r) => (
          <span key={r} className="flex items-center gap-1.5 text-[12px] text-muted-foreground">
            <span
              className="inline-block h-2.5 w-2.5 rounded-[3px]"
              /* eslint-disable-next-line security/detect-object-injection -- r iterates REGIME_COLOR's own keys */
              style={{ backgroundColor: REGIME_COLOR[r] }}
            />
            {regimeLabel(r)}
          </span>
        ))}
      </div>
    </div>
  );
}

async function RegimeDetail({ reading }: { reading: MarketReading }) {
  const { episodes } = await getRegimeHistory().catch(() => ({ episodes: [] as RegimeEpisode[] }));
  const r = reading.regime;
  const sameRegime = episodes.filter((e) => e.regime === r.regime);
  const sorted = [...sameRegime].sort((a, b) => a.days - b.days);
  const medianDays =
    sorted.length > 0 ? sorted[Math.floor(sorted.length / 2)].days : null;
  const recent = [...episodes].slice(-10).reverse();

  return (
    <div className="flex flex-col gap-4">
      <ChartCard
        title="Market state over time"
        sub="One of four rules-based states each day, smoothed with a 3-day confirmation so the label doesn't flip on noise."
      >
        <RegimeTimeline episodes={episodes} />
      </ChartCard>
      <StatStrip
        stats={[
          { label: "Now", value: regimeLabel(r.regime), sub: `day ${r.persistence_days}` },
          {
            label: "Previous state",
            value: r.prev_regime ? regimeLabel(r.prev_regime) : "—",
            sub: r.prev_regime_lasted_days ? `lasted ${r.prev_regime_lasted_days} days` : undefined,
          },
          {
            label: `Median ${regimeLabel(r.regime)} spell`,
            value: medianDays !== null ? `${medianDays} days` : "—",
            sub: `across ${sameRegime.length} historical spells`,
          },
          { label: "Spells on record", value: String(episodes.length), sub: "all states" },
        ]}
      />
      <div className="flex flex-col gap-2 rounded-xl border border-border bg-card p-5">
        <span className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
          Recent spells
        </span>
        <div className="flex flex-col">
          {recent.map((e, i) => (
            <div
              key={`${e.start}-${i}`}
              className="flex items-center justify-between gap-3 border-b border-border/60 py-2 text-[13px] last:border-0"
            >
              <span className="flex items-center gap-2 font-medium text-foreground">
                <span
                  className="inline-block h-2.5 w-2.5 rounded-[3px]"
                  style={{ backgroundColor: REGIME_COLOR[e.regime] }}
                />
                {regimeLabel(e.regime)}
              </span>
              <span className="font-mono text-[12px] tabular-nums text-muted-foreground">
                {new Date(e.start).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "2-digit" })}
                {" — "}
                {new Date(e.end).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "2-digit" })}
                {" · "}
                {e.days}d
              </span>
            </div>
          ))}
        </div>
      </div>
      <LearnPanel slug="regime" title="What this measures">
        The market state is a rules-based label built from trend (Nifty 100 vs
        its 100-day average), participation (breadth) and volatility. States
        describe conditions; they are not signals. Spells vary widely in
        length — the median above is context, not a countdown.
      </LearnPanel>
    </div>
  );
}

export default async function MarketIndicatorPage({
  params,
  searchParams,
}: {
  params: Promise<{ indicator: string }>;
  searchParams: Promise<{ date?: string }>;
}) {
  const [{ indicator }, { date }] = await Promise.all([params, searchParams]);
  if (!Object.prototype.hasOwnProperty.call(TITLES, indicator)) notFound();
  const title = TITLES[indicator as keyof typeof TITLES];
  const dateQuery = date ? `?date=${encodeURIComponent(date)}` : "";
  const reading = await getReading(date);

  return (
    <DetailShell
      section="Market Pulse"
      title={title}
      items={RAIL}
      activeSlug={indicator}
      basePath="/insights/market"
      dateQuery={dateQuery}
    >
      {indicator === "breadth" && <BreadthDetail reading={reading} />}
      {indicator === "stress" && <StressDetail reading={reading} />}
      {indicator === "regime" && <RegimeDetail reading={reading} />}
      <p className="mt-4 text-[11px] leading-[1.6] text-muted-foreground">
        Educational market analytics — descriptions of conditions, not
        recommendations. History charts always run through the most recent
        trading day, while the snapshot date rewinds today&apos;s readings.
      </p>
    </DetailShell>
  );
}
