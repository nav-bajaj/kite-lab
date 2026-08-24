import Link from "next/link";
import { notFound } from "next/navigation";
import {
  getReading,
  getBreadthTimeseries,
  getStressTimeseries,
  getMacroTimeseries,
  getConcentrationTimeseries,
  getRegimeHistory,
  getRegimeTimeseries,
  getIndexTimeseries,
  fmtPct,
  fmtNum,
  insightsQuery,
  parseUniverse,
  regimeLabel,
  universeLabel,
  type BreadthUniverse,
  type MarketReading,
  type RegimeEpisode,
  type RegimeTimeseriesResponse,
  type StressSnapshot,
  type TimeseriesResponse,
} from "@/lib/insights-api";
import { DetailShell, StatStrip } from "@/components/insights/mission";
import { MARKET_TABS } from "../_tabs";
import { RegimeLegend } from "../../_components/regime-legend";
import {
  TimeseriesChart,
  type IndexOverlay,
  type ReferenceBand,
} from "@/components/insights/timeseries-chart";
import { MetricExplorer, type MetricVariant } from "@/components/insights/metric-explorer";
import { RegimeChart } from "@/components/insights/regime-chart";
import { cn } from "@/lib/utils";
import { REGIME_CSS_VAR, RegimeChip, regimeColor } from "@/components/insights/ui";
import { ArrowDown, ArrowDownRight, ArrowUp, ArrowUpRight, Equal, Split } from "lucide-react";

export const dynamic = "force-dynamic";
export const revalidate = 900;

/**
 * Market indicator detail views (mission control: expand a card → land
 * here). The tab row is shared across the whole Market section so
 * navigation never changes shape while drilling. Regime leads the tabs;
 * its detail is descriptive only — the forward-return base-rates table
 * was removed as suggestive (founder, 2026-08-14).
 */

const TITLES: Record<string, string> = {
  regime: "Regime",
  stress: "Market stress",
  breadth: "Market breadth",
  "advance-decline": "Advances & declines",
  vix: "India VIX",
  "52-week-highs": "52-week highs",
  concentration: "Concentration",
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
  slug?: string;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-2 rounded-xl border border-border bg-primary/[0.03] p-3 lg:p-4">
      <span className="text-[12px] font-semibold text-foreground">{title}</span>
      <p className="text-[13px] leading-[1.6] text-muted-foreground">{children}</p>
      {slug && (
        <Link
          href={`/insights/learn/${slug}`}
          className="text-[13px] font-medium text-primary underline-offset-2 hover:underline"
        >
          Read the full explainer →
        </Link>
      )}
    </div>
  );
}

/** The scope index, ready to hand to a chart as an overlay. Indicators
 *  mean little without the price they are describing, so most detail
 *  charts offer it behind a toggle. */
async function indexOverlay(
  universe: BreadthUniverse,
  asOf: string,
): Promise<IndexOverlay | undefined> {
  const series = await getIndexTimeseries({ universe }).catch(() => null);
  if (!series || series.index.length === 0) return undefined;
  const end = cutoff(series.index, asOf);
  return {
    label: series.index_label,
    dates: series.index.slice(0, end),
    closes: (series.data.close ?? []).slice(0, end),
  };
}

/** One past the last row dated on or before `day` — everything on a tab
 *  stops at the snapshot date, charts included, so a rewound view never
 *  shows days that hadn't happened yet. */
function cutoff(dates: string[], day: string): number {
  const i = dates.findIndex((d) => d.slice(0, 10) > day);
  return i === -1 ? dates.length : i;
}

/** The timeseries endpoints take no `date` — they always return the most
 *  recent rows — so every detail view truncates what it fetched. Without
 *  this, a rewound non-default universe read its "now" value off today's
 *  last point while the header said otherwise. */
function truncateSeries(series: TimeseriesResponse, day: string): TimeseriesResponse {
  const end = cutoff(series.index, day);
  if (end === series.index.length) return series;
  return {
    index: series.index.slice(0, end),
    data: Object.fromEntries(
      Object.entries(series.data).map(([k, v]) => [k, v.slice(0, end)]),
    ),
  };
}

/** p-th percentile of the non-null values (nearest-rank). */
function percentile(values: (number | null)[], p: number): number | null {
  const clean = values
    .filter((v): v is number => v !== null && !Number.isNaN(v))
    .sort((a, b) => a - b);
  if (clean.length === 0) return null;
  const idx = Math.min(clean.length - 1, Math.max(0, Math.round((p / 100) * (clean.length - 1))));
  return clean.at(idx) ?? null;
}

/** Two readings of the same thing in one card — the level and where that
 *  level sits (founder, 2026-08-15: "current score and its percentile can
 *  become one dual card"). */
function DualStat({
  label,
  primary,
  secondary,
  emphasis = false,
}: {
  label: string;
  primary: { value: string; sub?: string };
  secondary: { value: string; sub?: string };
  /** Size up the primary reading — used where it is a verdict (the stress
   *  band) rather than a raw figure. */
  emphasis?: boolean;
}) {
  return (
    <div className="flex flex-col gap-2 rounded-xl border border-border bg-card px-4 py-3">
      <span className="text-[10px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">
        {label}
      </span>
      <div className="flex items-end justify-between gap-3">
        {[primary, secondary].map((part, i) => (
          <div
            key={i}
            className={cn(
              "flex min-w-0 flex-col gap-0.5",
              i === 1 && "items-end border-l border-border/70 pl-3 text-right",
            )}
          >
            <span
              className={cn(
                "font-semibold text-foreground",
                i === 0 ? (emphasis ? "text-2xl" : "text-xl") : "text-base",
              )}
            >
              {part.value}
            </span>
            {part.sub && (
              <span className="text-[11px] leading-[1.35] text-muted-foreground">
                {part.sub}
              </span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

/** 1st / 2nd / 3rd / 4th, with the teens handled — the stock page shipped
 *  "42th percentile" before this existed. */
function ordinal(n: number): string {
  const v = Math.round(n);
  const tens = v % 100;
  if (tens >= 11 && tens <= 13) return `${v}th`;
  return `${v}${["th", "st", "nd", "rd"][v % 10] ?? "th"}`;
}

/** A percentile is shown as the stat AND a sentence: "p42" alone reads as
 *  a code, but the plain sentence alone loses the figure people compare on
 *  (founder, 2026-08-20 then 2026-08-21). */
function percentileStat(p: number | null | undefined): string {
  if (p === null || p === undefined || Number.isNaN(p)) return "—";
  return `${ordinal(p)} percentile`;
}

function percentileSentence(
  p: number | null | undefined,
  window: string,
): string | undefined {
  if (p === null || p === undefined || Number.isNaN(p)) return undefined;
  return `higher than ${p.toFixed(0)}% of ${window}`;
}

/** The divergence read, promoted out of the faint `sub` slot. Deliberately
 *  on --chart-3 (the palette-stable "notable, no valence" token) rather than
 *  warning-ochre: a narrowing tape is worth noticing, not an alarm. */
function DivergenceNote({
  note,
}: {
  note?: { text: string; agreeing: boolean };
}) {
  if (!note) return null;
  const { text, agreeing } = note;
  const Icon = agreeing ? Equal : Split;
  return (
    <p
      className="flex items-start gap-1.5 text-[12px] leading-[1.45]"
      style={{ color: agreeing ? "var(--muted-foreground)" : "var(--chart-3)" }}
    >
      <Icon className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden />
      {text}
    </p>
  );
}

/** A signed percentage that carries its direction in colour and an arrow,
 *  not in a minus sign alone. Descriptive of the move — this is not a
 *  buy/sell tone (see the Tag component's note in ui.tsx). */
function SignedPct({ value, decimals = 1 }: { value: number | null; decimals?: number }) {
  if (value === null || Number.isNaN(value)) {
    return <span className="text-muted-foreground">—</span>;
  }
  const up = value >= 0;
  const Icon = up ? ArrowUpRight : ArrowDownRight;
  return (
    <span
      className="flex items-center gap-1"
      style={{ color: up ? "var(--positive)" : "var(--negative)" }}
    >
      <Icon className="h-4 w-4 shrink-0" aria-hidden />
      {fmtPct(value, decimals, true)}
    </span>
  );
}

/** A signed point/pp value with direction colour. The sign character is
 *  already in the string, so the colour is redundant reinforcement — the
 *  safe kind. */
function SignedPp({
  value,
  unit = "pp",
  decimals = 0,
}: {
  value: number | null;
  unit?: string;
  decimals?: number;
}) {
  if (value === null || Number.isNaN(value)) {
    return <span className="text-muted-foreground">—</span>;
  }
  const up = value >= 0;
  return (
    <span style={{ color: up ? "var(--positive)" : "var(--negative)" }}>
      {up ? "+" : ""}
      {value.toFixed(decimals)}
      {unit}
    </span>
  );
}

/** Advancers and decliners side by side, each with its own direction —
 *  the split is easier to read as two coloured counts than as one string
 *  (founder, 2026-08-21). */
function AdvanceDeclineSplit({ up, down }: { up: number | null; down: number | null }) {
  if (up === null || down === null) {
    return <span className="text-muted-foreground">—</span>;
  }
  return (
    <span className="flex items-center gap-3">
      <span
        className="flex items-center gap-1"
        style={{ color: "var(--positive)" }}
      >
        <ArrowUp className="h-4 w-4 shrink-0" aria-hidden />
        {up.toFixed(0)}
        <span className="sr-only">advancing</span>
      </span>
      <span
        className="flex items-center gap-1"
        style={{ color: "var(--negative)" }}
      >
        <ArrowDown className="h-4 w-4 shrink-0" aria-hidden />
        {down.toFixed(0)}
        <span className="sr-only">declining</span>
      </span>
    </span>
  );
}

/** "the past year" / "the last 5 years" from a trading-day window. */
function describeWindow(days: number | null | undefined): string {
  if (!days) return "its own history";
  const years = Math.round(days / 252);
  if (years <= 1) return "the past year";
  return `the last ${years} years`;
}

function ChartCard({
  title,
  sub,
  children,
}: {
  title: string;
  sub?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-2 rounded-xl border border-border bg-card p-3 lg:gap-3 lg:p-4">
      <div className="flex flex-col gap-0.5">
        <span className="text-[15px] font-semibold text-foreground lg:text-lg">{title}</span>
        {sub && <span className="text-[13px] text-muted-foreground">{sub}</span>}
      </div>
      {children}
    </div>
  );
}

const ATLAS_FROM_YEAR = 2010;

// Reference levels for the whole DMA family from the Breadth Atlas
// empirical profile (tasks/breadth_atlas/REPORT.md §1, 2010-2026 p5 /
// median / p95 per metric). Descriptive context lines, not thresholds
// to act on.
function atlasBands(p5: number, median: number, p95: number): ReferenceBand[] {
  return [
    { value: p95, label: `top 5% of days since ${ATLAS_FROM_YEAR}`, tone: "warning" },
    { value: median, label: `median day since ${ATLAS_FROM_YEAR}`, tone: "muted" },
    { value: p5, label: `bottom 5% of days since ${ATLAS_FROM_YEAR}`, tone: "negative" },
  ];
}

const BREADTH_VARIANTS: Omit<MetricVariant, "values">[] = [
  {
    metric: "pct_above_200dma",
    label: "% > 200-DMA",
    sub: "Percentage share of stocks trading above their 200 day average.",
    percent: true,
    bands: atlasBands(0.222, 0.588, 0.937),
  },
  {
    metric: "avg_dist_from_200dma",
    label: "Avg dist from 200-DMA",
    sub: "How far the average stock sits above or below its own 200-day average, in percent.",
    percent: true,
    bands: atlasBands(-0.11, 0.051, 0.292),
  },
  {
    metric: "pct_above_100dma",
    label: "% > 100-DMA",
    sub: "The share of stocks above their own 100-day average — participation over about five months.",
    percent: true,
    bands: atlasBands(0.169, 0.593, 0.895),
  },
  {
    metric: "pct_above_50dma",
    label: "% > 50-DMA",
    sub: "The share of stocks above their own 50-day average — participation over roughly a quarter.",
    percent: true,
    bands: atlasBands(0.157, 0.578, 0.882),
  },
];

function lastNonNull(values: (number | null)[]): number | null {
  for (let i = values.length - 1; i >= 0; i--) {
    const v = values.at(i);
    if (v !== null && v !== undefined && !Number.isNaN(v)) return v;
  }
  return null;
}

/** Bands computed from the fetched series itself — used for non-default
 *  universes, where the NSE-500 Breadth Atlas reference values don't apply. */
function computedBands(values: (number | null)[], fromYear?: number): ReferenceBand[] {
  const p95 = percentile(values, 95);
  const med = percentile(values, 50);
  const p5 = percentile(values, 5);
  // Name the year the window actually starts from, exactly as the atlas
  // bands do — "for this universe" left the reader guessing which span the
  // percentile was taken over (founder, 2026-08-15).
  const since = fromYear ? `since ${fromYear}` : "on record";
  return [
    ...(p95 !== null ? [{ value: p95, label: `top 5% of days ${since}`, tone: "warning" as const }] : []),
    ...(med !== null ? [{ value: med, label: `median day ${since}`, tone: "muted" as const }] : []),
    ...(p5 !== null ? [{ value: p5, label: `bottom 5% of days ${since}`, tone: "negative" as const }] : []),
  ];
}

/** Calendar year the fetched window opens on, for band labels. */
function firstYear(dates: string[]): number | undefined {
  const first = dates.at(0);
  return first ? Number(first.slice(0, 4)) : undefined;
}

/** Where `value` sits within the series' own distribution, 0-100. */
function pctRank(values: (number | null)[], value: number | null): number | null {
  if (value === null) return null;
  const clean = values.filter((v): v is number => v !== null && !Number.isNaN(v));
  if (clean.length === 0) return null;
  const below = clean.filter((v) => v <= value).length;
  return (below / clean.length) * 100;
}

/** Change in the series over the last `n` observations, in raw units. */
function changeOver(values: (number | null)[], n: number): number | null {
  const last = lastNonNull(values);
  const prior = values.at(values.length - 1 - n) ?? null;
  if (last === null || prior === null || Number.isNaN(prior)) return null;
  return last - prior;
}

async function BreadthDetail({
  reading,
  universe,
}: {
  reading: MarketReading;
  universe: BreadthUniverse;
}) {
  const asOf = reading.date.slice(0, 10);
  const [raw, overlay] = await Promise.all([
    getBreadthTimeseries({
      days: 4000,
      metrics: BREADTH_VARIANTS.map((v) => v.metric),
      universe,
    }).catch((): TimeseriesResponse => ({ index: [], data: {} })),
    indexOverlay(universe, asOf),
  ]);
  const end = cutoff(raw.index, asOf);
  const series = {
    index: raw.index.slice(0, end),
    data: Object.fromEntries(
      Object.entries(raw.data).map(([k, v]) => [k, v.slice(0, end)]),
    ),
  };
  const isDefault = universe === "nse500";
  const byKey = new Map(Object.entries(series.data));
  const values = byKey.get("pct_above_200dma") ?? [];
  const now = isDefault ? reading.regime.pct_above_200dma : lastNonNull(values);
  const from = firstYear(series.index);

  // The tiles used to be three static reference levels and a streak, which
  // told you nothing you could act on (founder, 2026-08-15). They now
  // describe state: where participation sits in its own history, which way
  // it is going, and whether the index is being carried by fewer names.
  const rank = pctRank(values, now);
  const changed20 = changeOver(values, 20);
  const overlayCloses = overlay?.closes ?? [];
  const indexChange20 =
    overlayCloses.length > 20
      ? (() => {
          const last = lastNonNull(overlayCloses);
          const prior = overlayCloses.at(overlayCloses.length - 21) ?? null;
          return last !== null && prior !== null && prior > 0 ? last / prior - 1 : null;
        })()
      : null;
  const divergence =
    changed20 !== null && indexChange20 !== null
      ? indexChange20 >= 0 && changed20 < 0
        ? { text: "Index up, participation down — the move is narrowing", agreeing: false }
        : indexChange20 < 0 && changed20 >= 0
          ? { text: "Index down, participation up — the decline is narrowing", agreeing: false }
          : { text: "Index and participation are moving together", agreeing: true }
      : undefined;

  const variants: MetricVariant[] = BREADTH_VARIANTS.map((v) => {
    const vals = byKey.get(v.metric) ?? [];
    return {
      ...v,
      values: vals,
      bands: isDefault ? v.bands : computedBands(vals, from),
    };
  });

  return (
    <div className="flex flex-col gap-2 lg:gap-3">
      <StatStrip
        stats={[
          {
            label: "Above 200-DMA",
            value: fmtPct(now, 0),
            sub: `of ${universeLabel(universe)}`,
          },
          {
            label: "Vs its own history",
            value: percentileStat(rank),
            sub: percentileSentence(rank, from ? `days since ${from}` : "days on record"),
          },
          {
            label: "Change, 20 sessions",
            value: changed20 !== null ? `${changed20 >= 0 ? "+" : ""}${(changed20 * 100).toFixed(0)}pp` : "—",
            sub: "participation widening or narrowing",
          },
          {
            label: `${overlay?.label ?? "Index"}, 20 sessions`,
            value: <SignedPct value={indexChange20} />,
            sub: "against participation",
          },
        ]}
      />
      <DivergenceNote note={divergence} />
      <ChartCard title={`Market Breadth ${universeLabel(universe)}`}>
        <MetricExplorer
          dates={series.index}
          variants={variants}
          overlay={overlay}
        />
      </ChartCard>
      <LearnPanel slug="pct-above-200dma" title="Learn more">
        Breadth counts how many stocks are in long-term uptrends, not just
        whether the index is up. Narrow rallies — index rising while breadth
        stalls — have historically been the more fragile kind. This series
        moves over weeks, not days, which is why the chart carries more
        information than any single day&apos;s number.
      </LearnPanel>
    </div>
  );
}

// Net advances reference levels (NSE 500, Breadth Atlas §1: ad_net_pct
// p5 = -67%, median ≈ 0, p95 = +58%). A flow metric — the atlas's
// mean-reversion profile says it carries information about what happened
// today, not where the cycle is.
const AD_VARIANTS: Omit<MetricVariant, "values">[] = [
  {
    metric: "cumulative_ad_count",
    label: "A-D line (stocks)",
    sub: "A running total of advancers minus decliners, counted in stocks. The direction it travels is the signal; the level is just where the running total happens to be — the dashed line marks where this window starts.",
    percent: false,
    bands: [],
    anchor: true,
  },
  {
    metric: "cumulative_ad",
    label: "A-D line (%)",
    sub: "The same running total, with each day counted as a share of the stocks that moved. A heavy day in a thin market counts for less here than in the stock version.",
    percent: false,
    bands: [],
    anchor: true,
  },
  {
    metric: "ad_diff_pct",
    label: "Net advances (daily)",
    sub: "Advancers minus decliners on the day, as a share of the stocks that moved. It swings between extremes most weeks, so read it a day at a time rather than as a trend.",
    percent: true,
    bands: atlasBands(-0.672, 0.004, 0.582),
  },
];

async function AdvanceDeclineDetail({
  reading,
  universe,
}: {
  reading: MarketReading;
  universe: BreadthUniverse;
}) {
  const asOf = reading.date.slice(0, 10);
  const [raw, overlay] = await Promise.all([
    getBreadthTimeseries({
      days: 4000,
      metrics: [...AD_VARIANTS.map((v) => v.metric), "n_advancing", "n_declining"],
      universe,
    }).catch((): TimeseriesResponse => ({ index: [], data: {} })),
    indexOverlay(universe, asOf),
  ]);
  const series = truncateSeries(raw, asOf);
  const isDefault = universe === "nse500";
  const byKey = new Map(Object.entries(series.data));
  const daily = byKey.get("ad_diff_pct") ?? [];
  const now = isDefault ? (reading.breadth["ad_diff_pct"] ?? null) : lastNonNull(daily);
  const advancing = lastNonNull(byKey.get("n_advancing") ?? []);
  const declining = lastNonNull(byKey.get("n_declining") ?? []);

  // The A-D line earns its keep as a slope read against price, so the tiles
  // carry the 20-session move of both and say plainly whether they agree.
  const lineChange = changeOver(byKey.get("cumulative_ad_count") ?? [], 20);
  const overlayCloses = overlay?.closes ?? [];
  const indexChange20 =
    overlayCloses.length > 20
      ? (() => {
          const last = lastNonNull(overlayCloses);
          const prior = overlayCloses.at(overlayCloses.length - 21) ?? null;
          return last !== null && prior !== null && prior > 0 ? last / prior - 1 : null;
        })()
      : null;
  const divergence =
    lineChange !== null && indexChange20 !== null
      ? indexChange20 >= 0 && lineChange < 0
        ? { text: "Index up while the A-D line falls — fewer names carrying it", agreeing: false }
        : indexChange20 < 0 && lineChange >= 0
          ? { text: "Index down while the A-D line rises — selling is narrowing", agreeing: false }
          : { text: "Index and the A-D line are moving together", agreeing: true }
      : undefined;

  const variants: MetricVariant[] = AD_VARIANTS.map((v) => {
    const vals = byKey.get(v.metric) ?? [];
    const bands =
      v.metric === "ad_diff_pct"
        ? isDefault
          ? v.bands
          : computedBands(vals, firstYear(series.index))
        : [];
    return { ...v, values: vals, bands };
  });

  return (
    <div className="flex flex-col gap-2 lg:gap-3">
      <StatStrip
        stats={[
          {
            label: "Today",
            value: <AdvanceDeclineSplit up={advancing} down={declining} />,
            sub: `of ${universeLabel(universe)}`,
          },
          {
            label: "Net advances",
            value: fmtPct(now, 0, true),
            sub: "of the stocks that moved",
          },
          {
            label: "A-D line, 20 sessions",
            value: <SignedPp value={lineChange} unit="" decimals={0} />,
            sub: "net stocks added to the line",
          },
          {
            label: `${overlay?.label ?? "Index"}, 20 sessions`,
            value: <SignedPct value={indexChange20} />,
            sub: "against the A-D line",
          },
        ]}
      />
      <DivergenceNote note={divergence} />
      <ChartCard
        title={`Advances & declines · ${universeLabel(universe)}`}
        sub="How many stocks moved with the market. The A-D line is the running total — switch between counting stocks and counting each day as a share of the stocks that moved."
      >
        <MetricExplorer
          dates={series.index}
          variants={variants}
          overlay={overlay}
          interactive
          overlayAxis="left"
        />
      </ChartCard>
      <LearnPanel title="Learn more">
        This counts how many stocks rose versus fell, which the index alone
        cannot tell you — a handful of large names can carry it while most
        stocks fall. A single day says little. The running total is where it
        gets useful: when it turns down while the index keeps climbing, the
        move is resting on fewer and fewer stocks.
      </LearnPanel>
    </div>
  );
}

/** Reference lines drawn from the engine's own band boundaries, so the
 *  chart, the card and the explainer can never disagree about where calm
 *  ends and stressed begins (founder, 2026-08-20). */
function stressBands(bands: StressSnapshot["bands"]): ReferenceBand[] {
  return [
    { value: bands.stressed_above, label: "stressed above this line", tone: "negative" },
    { value: bands.calm_below, label: "calm below this line", tone: "muted" },
  ];
}

async function StressDetail({
  reading,
  universe,
}: {
  reading: MarketReading;
  universe: BreadthUniverse;
}) {
  const asOf = reading.date.slice(0, 10);
  const [raw, overlay] = await Promise.all([
    getStressTimeseries(4000).catch(
      (): TimeseriesResponse => ({ index: [], data: {} }),
    ),
    indexOverlay(universe, asOf),
  ]);
  const end = cutoff(raw.index, asOf);
  const series = { index: raw.index.slice(0, end) };
  const values = (raw.data["score"] ?? []).slice(0, end);
  const s = reading.stress;
  const w = s.weights ?? {};
  const components: { label: string; value: number | null; weight: number }[] = [
    {
      label: "Volatility (VIX percentile)",
      value: s.vix_pctile_component,
      weight: w["vix_pctile"] ?? 0,
    },
    { label: "Nifty drawdown", value: s.drawdown_component, weight: w["drawdown"] ?? 0 },
    {
      label: "Stocks below 200-DMA",
      value: s.below_200dma_component,
      weight: w["below_200dma"] ?? 0,
    },
    {
      label: "Return dispersion",
      value: s.dispersion_component,
      weight: w["dispersion"] ?? 0,
    },
  ];
  // Windows come from the engine; describe them rather than restating a
  // hardcoded number that can drift from it.
  const windowLabel = describeWindow(s.percentile_window_days);
  const componentWindowLabel = describeWindow(s.component_window_days);
  // Below a full window the comparison is shallower than the label claims,
  // so say so rather than implying a depth we don't have (audit).
  const shallow =
    s.score_percentile_obs !== null &&
    s.percentile_window_days !== null &&
    s.score_percentile_obs < s.percentile_window_days;

  return (
    <div className="flex flex-col gap-2 lg:gap-3">
      {/* State first, chart second — same order as the Regime tab. */}
      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
        <DualStat
          label="Stress"
          emphasis
          primary={{
            value: s.band ?? "—",
            sub: s.score !== null ? `${s.score.toFixed(0)}/100` : undefined,
          }}
          secondary={{
            value: percentileStat(s.score_percentile),
            sub:
              s.score_percentile === null
                ? "not enough history yet"
                : percentileSentence(
                    s.score_percentile,
                    shallow ? `${s.score_percentile_obs} sessions so far` : windowLabel,
                  ),
          }}
        />
        <DualStat
          label="India VIX"
          primary={{ value: s.vix_close?.toFixed(1) ?? "—", sub: "index level" }}
          secondary={{
            value: percentileStat(s.vix_pctile_component),
            sub: percentileSentence(s.vix_pctile_component, componentWindowLabel),
          }}
        />
        <DualStat
          label="Nifty drawdown"
          primary={{
            value: fmtPct(s.nifty_drawdown_pct, 1),
            sub: "from the past year's high",
          }}
          secondary={{
            value:
              s.below_200dma_component !== null
                ? fmtPct(1 - s.below_200dma_component / 100, 0)
                : "—",
            sub: "of NSE 500 stocks above 200-DMA",
          }}
        />
      </div>
      <ChartCard
        title="Market Stress Composite"
        sub="A blended score using Volatility, Drawdown, Breadth, and Dispersion. Quiet stretches are the norm but spike clusters can occur at regime breaks."
      >
        <TimeseriesChart
          dates={series.index}
          values={values}
          bands={stressBands(s.bands)}
          overlay={overlay}
          overlayValueLabel="Stress"
        />
      </ChartCard>
      <div className="flex flex-col gap-2 rounded-xl border border-border bg-card p-3 lg:p-4">
        <span className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
          What&apos;s driving the score today
        </span>
        <p className="text-[12px] text-muted-foreground">
          Each input is scored 0–100 on its own, then weighted into the
          composite. The weight is what it contributes; the bar is how hot
          that input is running.
        </p>
        {components.map((c) => (
          <div key={c.label} className="flex items-center gap-3">
            <span className="w-56 shrink-0 text-[13px] text-foreground">
              {c.label}
              <span className="ml-1.5 text-[11px] text-muted-foreground">
                {(c.weight * 100).toFixed(0)}%
              </span>
            </span>
            <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
              <div
                className="h-full rounded-full bg-[color:var(--chart-1)]"
                style={{ width: `${Math.max(0, Math.min(100, c.value ?? 0))}%` }}
              />
            </div>
            <span className="w-10 shrink-0 text-right font-mono text-[12px] tabular-nums text-muted-foreground">
              {c.value === null ? "—" : c.value.toFixed(0)}
            </span>
          </div>
        ))}
      </div>
      <div className="flex flex-col gap-2 rounded-xl border border-border bg-card p-3 lg:p-4">
        <span className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
          How the score is computed
        </span>
        <ul className="flex list-disc flex-col gap-1.5 pl-4 text-[13px] leading-[1.55] text-muted-foreground">
          <li>
            <span className="text-foreground">
              Volatility ({fmtPct(w["vix_pctile"], 0)})
            </span>{" "}
            — where India VIX sits within its own past year, as a percentile.
          </li>
          <li>
            <span className="text-foreground">
              Drawdown ({fmtPct(w["drawdown"], 0)})
            </span>{" "}
            — how far the Nifty is below its highest close of the past year.
            At the high scores 0; down 20% or more scores 100.
          </li>
          <li>
            <span className="text-foreground">
              Breadth ({fmtPct(w["below_200dma"], 0)})
            </span>{" "}
            — the share of NSE 500 stocks trading <em>below</em> their 200-day
            average.
          </li>
          <li>
            <span className="text-foreground">
              Dispersion ({fmtPct(w["dispersion"], 0)})
            </span>{" "}
            — how spread out daily returns are versus their own past year, as
            a z-score. Stocks scattering in different directions scores high.
          </li>
          <li>
            Each input is capped to 0–100, multiplied by its weight and summed.
            The percentile above compares today&apos;s score with {windowLabel}.
          </li>
        </ul>
      </div>
      <LearnPanel slug="stress-score" title="Learn more">
        A single 0–100 read on how tense conditions are, blending four
        observable inputs. It describes the environment — calm markets tend to
        produce smaller swings, stressed ones bigger and faster swings — and
        says nothing about direction.
      </LearnPanel>
    </div>
  );
}

async function VixDetail({
  reading,
  universe,
}: {
  reading: MarketReading;
  universe: BreadthUniverse;
}) {
  const asOf = reading.date.slice(0, 10);
  const [rawMacro, overlay] = await Promise.all([
    getMacroTimeseries({ days: 4000, metrics: ["vix_close"] }).catch(
      (): TimeseriesResponse => ({ index: [], data: {} }),
    ),
    indexOverlay(universe, asOf),
  ]);
  const series = truncateSeries(rawMacro, asOf);
  const values = series.data["vix_close"] ?? [];
  // Reference lines from the fetched history itself — descriptive context,
  // recomputed as the series grows rather than hardcoded.
  // Both extremes, not just the high one — a VIX sitting near its own
  // floor is as much of a condition as one near its ceiling (founder,
  // 2026-08-20).
  const from = firstYear(series.index);
  const bands: ReferenceBand[] = computedBands(values, from);
  const m = reading.macro;
  const closes = overlay?.closes ?? [];
  const indexChange5 = (() => {
    const last = lastNonNull(closes);
    const prior = closes.at(closes.length - 6) ?? null;
    return last !== null && prior !== null && prior > 0 ? last / prior - 1 : null;
  })();

  return (
    <div className="flex flex-col gap-2 lg:gap-3">
      <StatStrip
        stats={[
          { label: "India VIX", value: fmtNum(m["vix_close"], 1), sub: "index level" },
          {
            label: "Vs its own history",
            value: percentileStat(pctRank(values, lastNonNull(values))),
            sub: percentileSentence(
              pctRank(values, lastNonNull(values)),
              from ? `days since ${from}` : "days on record",
            ),
          },
          {
            label: "5-day change",
            value: fmtPct(m["vix_roc_5d"], 1),
            sub: "expansion or contraction",
          },
          {
            // Paired with the VIX 5-day change beside it: volatility rising
            // while the index falls is the ordinary case, both rising is the
            // one worth noticing (founder, 2026-08-21).
            label: `${overlay?.label ?? "Index"}, 5 sessions`,
            value: <SignedPct value={indexChange5} />,
            sub: "over the same window",
          },
        ]}
      />
      <ChartCard
        title="India VIX"
        sub="The market's expected 30-day volatility, from option prices. Quiet regimes sit low for months; spikes are sharp and short."
      >
        <TimeseriesChart
          dates={series.index}
          values={values}
          bands={bands}
          overlay={overlay}
          overlayValueLabel="VIX"
        />
      </ChartCard>
      <LearnPanel slug="vix" title="Learn more">
        VIX reads the price of near-term protection: how much movement option
        buyers are paying for over the next month. Low readings describe calm;
        high readings describe fear already being priced. It says nothing
        about direction — crashes and rip-your-face-off rallies both come
        with high VIX.
      </LearnPanel>
    </div>
  );
}

// Reference levels from the Breadth Atlas empirical profile
// (tasks/breadth_atlas/REPORT.md §1): net_new_highs_pct p5 = -10.0%,
// median = +2.4%, p95 = +13.2% over 2010-2026. The asymmetry (deep lows
// cluster harder than highs) is a documented finding, not a display choice.
// Reference levels from the Breadth Atlas empirical profile
// (tasks/breadth_atlas/REPORT.md §1): net_new_highs_pct p5 = -10.0%,
// median = +2.4%, p95 = +13.2% over 2010-2026.
const NNH_BANDS: ReferenceBand[] = [
  { value: 0.132, label: `top 5% of days since ${ATLAS_FROM_YEAR}`, tone: "warning" },
  { value: 0.024, label: `median day since ${ATLAS_FROM_YEAR}`, tone: "muted" },
  { value: -0.1, label: `bottom 5% of days since ${ATLAS_FROM_YEAR}`, tone: "negative" },
];

/** The 52-week-high complex. The headline is the continuous measure —
 *  how far the average stock sits below its own high — because the count
 *  of names printing a literal new high is sparse and spiky, the same
 *  finding the Breadth Atlas reached for the 200-DMA family (founder,
 *  2026-08-20). Bands are computed from each series' own history. */
const HIGHS_VARIANTS: { metric: string; label: string; sub: string; percent: boolean }[] = [
  {
    metric: "avg_dist_from_52w_high",
    label: "Avg distance from 52w high",
    sub: "How far the average stock sits below its own 52-week high. Zero would mean every stock is at its high; it falls as stocks drop away from theirs.",
    percent: true,
  },
  {
    metric: "pct_within_5pct_of_high",
    label: "% within 5% of high",
    sub: "The share of stocks trading within 5% of their own 52-week high — how broad the leadership actually is.",
    percent: true,
  },
  {
    metric: "pct_off_20pct_from_high",
    label: "% more than 20% below",
    sub: "The share of stocks more than 20% below their own 52-week high — how much of the market is already in its own bear market.",
    percent: true,
  },
  {
    metric: "net_new_highs_pct",
    label: "Net new highs",
    sub: "Stocks printing a fresh 52-week high minus those printing a fresh low, as a share of the universe.",
    percent: true,
  },
];

async function FiftyTwoWeekHighsDetail({
  reading,
  universe,
}: {
  reading: MarketReading;
  universe: BreadthUniverse;
}) {
  const asOf = reading.date.slice(0, 10);
  const [raw, overlay] = await Promise.all([
    getBreadthTimeseries({
      days: 4000,
      metrics: HIGHS_VARIANTS.map((v) => v.metric),
      universe,
    }).catch((): TimeseriesResponse => ({ index: [], data: {} })),
    indexOverlay(universe, asOf),
  ]);
  const series = truncateSeries(raw, asOf);
  const isDefault = universe === "nse500";
  const byKey = new Map(Object.entries(series.data));
  const from = firstYear(series.index);

  const dist = byKey.get("avg_dist_from_52w_high") ?? [];
  const within5 = byKey.get("pct_within_5pct_of_high") ?? [];
  const off20 = byKey.get("pct_off_20pct_from_high") ?? [];
  const distNow = lastNonNull(dist);

  const variants: MetricVariant[] = HIGHS_VARIANTS.map((v) => {
    const vals = byKey.get(v.metric) ?? [];
    return {
      ...v,
      values: vals,
      bands:
        v.metric === "net_new_highs_pct" && isDefault
          ? NNH_BANDS
          : computedBands(vals, from),
    };
  });

  return (
    <div className="flex flex-col gap-2 lg:gap-3">
      <StatStrip
        stats={[
          {
            label: "Avg distance from high",
            value: fmtPct(distNow, 1),
            sub: `of ${universeLabel(universe)}`,
          },
          {
            label: "Vs its own history",
            value: percentileStat(pctRank(dist, distNow)),
            sub: percentileSentence(
              pctRank(dist, distNow),
              from ? `days since ${from}` : "days on record",
            ),
          },
          {
            label: "Within 5% of high",
            value: fmtPct(lastNonNull(within5), 0),
            sub: "leadership, however broad",
          },
          {
            label: "More than 20% below",
            value: fmtPct(lastNonNull(off20), 0),
            sub: "already in their own bear market",
          },
        ]}
      />
      <ChartCard
        title={`52-week highs · ${universeLabel(universe)}`}
        sub="Where stocks sit against their own one-year highs. The dashed lines mark the highest and lowest 5% of days in this series' own history."
      >
        <MetricExplorer dates={series.index} variants={variants} overlay={overlay} />
      </ChartCard>
      <LearnPanel title="Learn more">
        A count of stocks printing a literal new high is sparse — on most
        days almost none do, so the measure spends its time near zero and
        then spikes. Distance from the high is defined for every stock every
        day, which is why it leads here. The two shares either side of it
        say the same thing in plainer terms: how many names are near their
        highs, and how many have already fallen a long way from them.
      </LearnPanel>
    </div>
  );
}

async function ConcentrationDetail({
  reading,
  universe,
}: {
  reading: MarketReading;
  universe: BreadthUniverse;
}) {
  const asOf = reading.date.slice(0, 10);
  const series = truncateSeries(
    await getConcentrationTimeseries({ days: 4000, universe }).catch(
      (): TimeseriesResponse => ({ index: [], data: {} }),
    ),
    asOf,
  );
  const values = series.data["spread_20d_avg_pp"] ?? [];
  const daily = series.data["cap_vs_equal_spread_pp"] ?? [];
  const spreadNow = lastNonNull(daily);
  // Per-name attribution needs factsheet weights, which exist only for the
  // Nifty 50 — the heavyweight tiles switch off on other universes.
  const hasAttribution = universe === "nifty50";
  const c = reading.concentration;

  return (
    <div className="flex flex-col gap-2 lg:gap-3">
      <ChartCard
        title={`Cap-weighted vs equal-weighted ${universeLabel(universe)}, 20-day average spread`}
        sub="Above zero: the heavyweights are outrunning the average stock (a narrow tape). Below zero: the average stock leads (broad participation)."
      >
        <TimeseriesChart
          dates={series.index}
          values={values}
          bands={[{ value: 0, label: "even tape", tone: "muted" }]}
         
        />
      </ChartCard>
      <StatStrip
        stats={[
          {
            label: "Today's spread",
            value:
              spreadNow !== null
                ? `${spreadNow >= 0 ? "+" : ""}${spreadNow.toFixed(2)}pp`
                : "—",
            sub: "cap minus equal weighted",
          },
          {
            label: "20-day average",
            value: (() => {
              const v = lastNonNull(values);
              return v !== null ? `${v >= 0 ? "+" : ""}${v.toFixed(2)}pp` : "—";
            })(),
            sub: lastNonNull(values) !== null && (lastNonNull(values) as number) >= 0 ? "narrow tape" : "broad tape",
          },
          ...(hasAttribution
            ? [
                {
                  label: "Top-5 share of move",
                  value:
                    c.top_5_share_of_move !== null && Math.abs(c.nifty_return_pct) >= 0.25
                      ? `${(c.top_5_share_of_move * 100).toFixed(0)}%`
                      : "—",
                  sub:
                    Math.abs(c.nifty_return_pct) < 0.25
                      ? "index barely moved today"
                      : "of today's index move",
                },
                {
                  label: "Heavyweights today",
                  value: c.top_3_symbols.slice(0, 2).join(", ") || "—",
                  sub: "largest contributors",
                },
              ]
            : [
                {
                  label: "Narrowest 5% of stretches",
                  value: (() => {
                    const v = percentile(values, 95);
                    return v !== null ? `+${v.toFixed(2)}pp` : "—";
                  })(),
                  sub: "20-day spread, this index's history",
                },
                {
                  label: "Broadest 5% of stretches",
                  value: (() => {
                    const v = percentile(values, 5);
                    return v !== null ? `${v.toFixed(2)}pp` : "—";
                  })(),
                  sub: "20-day spread, this index's history",
                },
              ]),
        ]}
      />
      {!hasAttribution && (
        <p className="text-[12px] text-muted-foreground">
          Per-name attribution (who drove the move) is available on the
          Nifty 50 scope, where official index weights exist.
        </p>
      )}
      <LearnPanel slug="concentration" title="Learn more">
        Whether the index&apos;s move is the market&apos;s move. A persistently
        positive spread means a handful of heavyweights are carrying the
        tape while the average stock lags — the kind of rally that looks
        stronger in the headline number than underneath.
      </LearnPanel>
    </div>
  );
}

const REGIME_ORDER = Object.keys(REGIME_CSS_VAR) as RegimeEpisode["regime"][];

/** Close-to-close return between two days of a fetched close series.
 *  Used so a rewound snapshot reports the move *so far* in its regime
 *  rather than the whole episode, which would include days that hadn't
 *  happened yet on the snapshot date. */
function returnBetween(
  dates: string[],
  closes: (number | null)[],
  startDay: string,
  endDay: string,
): number | null {
  let first: number | null = null;
  let last: number | null = null;
  for (let i = 0; i < dates.length; i++) {
    /* eslint-disable-next-line security/detect-object-injection -- parallel arrays, numeric loop index */
    const day = dates[i].slice(0, 10);
    if (day < startDay || day > endDay) continue;
    const value = closes.at(i);
    if (value === null || value === undefined || Number.isNaN(value)) continue;
    if (first === null) first = value;
    last = value;
  }
  if (first === null || last === null || first <= 0) return null;
  return last / first - 1;
}

/** Median run length per regime, in days — the typical duration of each
 *  regime rather than how many of them there have been. */
function medianRegimeDays(episodes: RegimeEpisode[], regime: string): number | null {
  const lengths = episodes
    .filter((e) => e.regime === regime)
    .map((e) => e.days)
    .sort((a, b) => a - b);
  if (lengths.length === 0) return null;
  return lengths.at(Math.floor(lengths.length / 2)) ?? null;
}

async function RegimeDetail({
  reading,
  universe,
}: {
  reading: MarketReading;
  universe: BreadthUniverse;
}) {
  const [history, series] = await Promise.all([
    getRegimeHistory(universe).catch(() => ({
      index_label: null,
      episodes: [] as RegimeEpisode[],
    })),
    getRegimeTimeseries({ universe }).catch(
      (): RegimeTimeseriesResponse => ({ index_label: null, index: [], data: {} }),
    ),
  ]);
  const episodes = history.episodes;
  const r = reading.regime;
  const indexLabel = series.index_label ?? history.index_label ?? r.index_label;
  // The episode the reading itself sits in — not simply the newest one, or
  // a rewound snapshot would pair its own regime with today's index move.
  const readingDay = r.date.slice(0, 10);
  const current =
    episodes.find(
      (e) => e.start.slice(0, 10) <= readingDay && readingDay <= e.end.slice(0, 10),
    ) ?? episodes.at(-1);
  // Truncate the chart at the reading date too. Everything else on this tab
  // rewinds with the snapshot, so a chart running on to today was the one
  // element still showing days that hadn't happened yet.
  const future = series.index.findIndex((d) => d.slice(0, 10) > readingDay);
  const end = future === -1 ? series.index.length : future;
  const chart = {
    dates: series.index.slice(0, end),
    opens: (series.data.open ?? []).slice(0, end),
    highs: (series.data.high ?? []).slice(0, end),
    lows: (series.data.low ?? []).slice(0, end),
    closes: (series.data.close ?? []).slice(0, end),
    regimes: (series.data.regime ?? []).slice(0, end),
  };
  const currentReturn = current
    ? (returnBetween(
        chart.dates,
        chart.closes,
        current.start.slice(0, 10),
        readingDay,
      ) ?? current.index_return_pct)
    : null;
  const upToReading = episodes.filter((e) => e.start.slice(0, 10) <= readingDay);
  const recent = [...(upToReading.length > 0 ? upToReading : episodes)]
    .slice(-10)
    .reverse();

  return (
    <div className="flex flex-col gap-2 lg:gap-3">
      {/* Tiles lead: the state of affairs reads faster than the chart, so it
          comes first and the chart backs it up (founder, 2026-08-15). */}
      <StatStrip
        stats={[
          {
            label: "Current regime",
            value: <RegimeChip regime={r.regime} />,
            sub: `day ${r.persistence_days}`,
          },
          {
            label: "Previous regime",
            value: r.prev_regime ? <RegimeChip regime={r.prev_regime} /> : "—",
            sub: r.prev_regime_lasted_days ? `day ${r.prev_regime_lasted_days}` : undefined,
          },
          {
            label: `${indexLabel} this regime`,
            value: fmtPct(currentReturn, 1, true),
          },
          {
            label: "Participation",
            value: fmtPct(r.participation_pct, 0),
            sub: `of ${universeLabel(universe)} above their ${r.participation_ma_days}-day average`,
          },
        ]}
      />
      <ChartCard
        title={`${indexLabel} through its regimes`}
        sub="The index with an overlay tint by regime in force. One of four rules-based regimes, smoothed with a 3-day confirmation."
      >
        <RegimeChart
          dates={chart.dates}
          opens={chart.opens}
          highs={chart.highs}
          lows={chart.lows}
          closes={chart.closes}
          regimes={chart.regimes}
          indexLabel={indexLabel}
        />
      </ChartCard>
      <div className="flex flex-col gap-3 rounded-xl border border-border bg-card p-3 lg:p-4">
        <span className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
          Median regime length
        </span>
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          {REGIME_ORDER.map((reg) => {
            const days = medianRegimeDays(episodes, reg);
            return (
              <div key={reg} className="flex flex-col gap-0.5">
                <span className="flex items-center gap-1.5 text-[12px] text-muted-foreground">
                  <span
                    className="inline-block h-2.5 w-2.5 rounded-[3px]"
                    style={{ backgroundColor: regimeColor(reg) }}
                  />
                  {regimeLabel(reg)}
                </span>
                <span className="text-xl font-semibold text-foreground">
                  {days !== null ? `${days} days` : "—"}
                </span>
              </div>
            );
          })}
        </div>
      </div>
      <div className="flex flex-col gap-2 rounded-xl border border-border bg-card p-3 lg:p-4">
        <span className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
          Recent regimes
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
                  style={{ backgroundColor: regimeColor(e.regime) }}
                />
                {regimeLabel(e.regime)}
              </span>
              <span className="flex items-center gap-3 font-mono text-[12px] tabular-nums">
                <span className="text-muted-foreground">
                  {new Date(e.start).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "2-digit" })}
                  {" — "}
                  {new Date(e.end).toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "2-digit" })}
                  {" · "}
                  {e.days}d
                </span>
                <span
                  className="w-16 text-right font-medium"
                  style={{
                    color:
                      e.index_return_pct === null
                        ? "var(--muted-foreground)"
                        : e.index_return_pct >= 0
                          ? "var(--positive)"
                          : "var(--negative)",
                  }}
                >
                  {fmtPct(e.index_return_pct, 1, true)}
                </span>
              </span>
            </div>
          ))}
        </div>
      </div>
      <RegimeLegend
        indexLabel={indexLabel}
        universeLabel={universeLabel(universe)}
        trendMaDays={r.trend_ma_days}
        participationMaDays={r.participation_ma_days}
      />
      <LearnPanel slug="regime" title="Learn more">
        The regime is a rules-based label built from trend ({indexLabel}{" "}
        versus its {r.trend_ma_days}-day average), participation (how many{" "}
        {universeLabel(universe)} stocks are above their{" "}
        {r.participation_ma_days}-day average) and volatility (India VIX). It
        describes conditions; it is not a signal.
      </LearnPanel>
    </div>
  );
}

export default async function MarketIndicatorPage({
  params,
  searchParams,
}: {
  params: Promise<{ indicator: string }>;
  searchParams: Promise<{ date?: string; universe?: string }>;
}) {
  const [{ indicator }, { date, universe: rawUniverse }] = await Promise.all([
    params,
    searchParams,
  ]);
  if (!Object.prototype.hasOwnProperty.call(TITLES, indicator)) notFound();
  const title = TITLES[indicator as keyof typeof TITLES];
  const universe = parseUniverse(rawUniverse);
  const dateQuery = insightsQuery({ date, universe });
  // The regime is universe-scoped, so the reading is fetched per scope.
  const reading = await getReading(date, universe);

  return (
    <DetailShell
      section="Market Pulse"
      title={title}
      items={MARKET_TABS}
      activeSlug={indicator}
      basePath="/insights/market"
      dateQuery={dateQuery}
    >
      {indicator === "regime" && <RegimeDetail reading={reading} universe={universe} />}
      {indicator === "breadth" && <BreadthDetail reading={reading} universe={universe} />}
      {indicator === "stress" && <StressDetail reading={reading} universe={universe} />}
      {indicator === "advance-decline" && (
        <AdvanceDeclineDetail reading={reading} universe={universe} />
      )}
      {indicator === "vix" && <VixDetail reading={reading} universe={universe} />}
      {indicator === "52-week-highs" && (
        <FiftyTwoWeekHighsDetail reading={reading} universe={universe} />
      )}
      {indicator === "concentration" && (
        <ConcentrationDetail reading={reading} universe={universe} />
      )}
      <p className="mt-3 text-[11px] leading-[1.6] text-muted-foreground">
        Educational market analytics — descriptions of conditions, not
        recommendations.{" "}
        {["regime", "stress", "breadth"].includes(indicator)
          ? "The snapshot date rewinds this page in full — readings and chart both stop on that day."
          : "History charts always run through the most recent trading day, while the snapshot date rewinds today's readings."}
      </p>
    </DetailShell>
  );
}
