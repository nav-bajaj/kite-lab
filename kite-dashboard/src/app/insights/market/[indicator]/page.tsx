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
  fmtPct,
  fmtNum,
  insightsQuery,
  parseUniverse,
  regimeLabel,
  universeLabel,
  type BreadthUniverse,
  type MarketReading,
  type RegimeEpisode,
  type TimeseriesResponse,
} from "@/lib/insights-api";
import { DetailShell, StatStrip } from "@/components/insights/mission";
import { MARKET_TABS } from "../_tabs";
import { RegimeLegend } from "../../_components/regime-legend";
import { TimeseriesChart, type ReferenceBand } from "@/components/insights/timeseries-chart";
import { MetricExplorer, type MetricVariant } from "@/components/insights/metric-explorer";
import { RegimeChart } from "@/components/insights/regime-chart";

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
  "net-new-highs": "Net new highs",
  mcclellan: "McClellan oscillator",
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
    <div className="flex flex-col gap-2 rounded-xl border border-border bg-primary/[0.03] p-5">
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

/** p-th percentile of the non-null values (nearest-rank). */
function percentile(values: (number | null)[], p: number): number | null {
  const clean = values
    .filter((v): v is number => v !== null && !Number.isNaN(v))
    .sort((a, b) => a - b);
  if (clean.length === 0) return null;
  const idx = Math.min(clean.length - 1, Math.max(0, Math.round((p / 100) * (clean.length - 1))));
  return clean.at(idx) ?? null;
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

// Reference levels for the whole DMA family from the Breadth Atlas
// empirical profile (tasks/breadth_atlas/REPORT.md §1, 2010-2026 p5 /
// median / p95 per metric). Descriptive context lines, not thresholds
// to act on.
function atlasBands(p5: number, median: number, p95: number): ReferenceBand[] {
  return [
    { value: p95, label: "top 5% of days since 2010", tone: "warning" },
    { value: median, label: "median day since 2010", tone: "muted" },
    { value: p5, label: "bottom 5% of days since 2010", tone: "negative" },
  ];
}

const BREADTH_VARIANTS: Omit<MetricVariant, "values">[] = [
  {
    metric: "pct_above_200dma",
    label: "% > 200-DMA",
    sub: "Participation in long-term uptrends — the headline breadth read.",
    percent: true,
    bands: atlasBands(0.22, 0.59, 0.94),
  },
  {
    metric: "avg_dist_from_200dma",
    label: "Avg dist from 200-DMA",
    sub: "The continuous sibling: average distance of every stock from its 200-day line. Same signal, finer extremes — the atlas's most robust deep-panic gauge.",
    percent: true,
    bands: atlasBands(-0.11, 0.051, 0.292),
  },
  {
    metric: "pct_above_100dma",
    label: "% > 100-DMA",
    sub: "Medium-horizon participation (about five months of trend).",
    percent: true,
    bands: atlasBands(0.169, 0.593, 0.895),
  },
  {
    metric: "pct_above_50dma",
    label: "% > 50-DMA",
    sub: "Faster participation — reacts in weeks rather than months.",
    percent: true,
    bands: atlasBands(0.157, 0.578, 0.882),
  },
  {
    metric: "pct_above_21dma",
    label: "% > 21-DMA",
    sub: "The fastest of the family — one-month trend participation, flickers the most.",
    percent: true,
    bands: atlasBands(0.148, 0.549, 0.851),
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
function computedBands(values: (number | null)[]): ReferenceBand[] {
  const p95 = percentile(values, 95);
  const med = percentile(values, 50);
  const p5 = percentile(values, 5);
  return [
    ...(p95 !== null ? [{ value: p95, label: "top 5% of this universe's days", tone: "warning" as const }] : []),
    ...(med !== null ? [{ value: med, label: "median day for this universe", tone: "muted" as const }] : []),
    ...(p5 !== null ? [{ value: p5, label: "bottom 5% of this universe's days", tone: "negative" as const }] : []),
  ];
}

async function BreadthDetail({
  reading,
  universe,
}: {
  reading: MarketReading;
  universe: BreadthUniverse;
}) {
  const series = await getBreadthTimeseries({
    days: 4000,
    metrics: BREADTH_VARIANTS.map((v) => v.metric),
    universe,
  }).catch((): TimeseriesResponse => ({ index: [], data: {} }));
  const isDefault = universe === "nse500";
  const byKey = new Map(Object.entries(series.data));
  const values = byKey.get("pct_above_200dma") ?? [];
  const now = isDefault ? reading.regime.pct_above_200dma : lastNonNull(values);
  const median = isDefault ? 0.59 : percentile(values, 50);
  const p5 = isDefault ? 0.22 : percentile(values, 5);

  let streak = 0;
  for (let i = values.length - 1; i >= 0; i--) {
    const v = values.at(i);
    if (v === null || v === undefined || median === null || v < median) break;
    streak += 1;
  }

  const variants: MetricVariant[] = BREADTH_VARIANTS.map((v) => {
    const vals = byKey.get(v.metric) ?? [];
    return { ...v, values: vals, bands: isDefault ? v.bands : computedBands(vals) };
  });

  return (
    <div className="flex flex-col gap-4">
      <ChartCard
        title={`Market breadth — the trend-participation family · ${universeLabel(universe)}`}
        sub="Dashed lines mark where days like today have historically sat for the selected metric and universe."
      >
        <MetricExplorer dates={series.index} variants={variants} />
      </ChartCard>
      <StatStrip
        stats={[
          { label: "Now", value: fmtPct(now, 0), sub: `of ${universeLabel(universe)}` },
          {
            label: "Median day",
            value: fmtPct(median, 0),
            sub: isDefault ? "since 2010" : "this universe's history",
          },
          {
            label: "Washed-out line",
            value: fmtPct(p5, 0),
            sub: "bottom 5% of days",
          },
          {
            label: "Days at or above median",
            value: String(streak),
            sub: streak === 0 ? "currently below the median" : "current run",
          },
        ]}
      />
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
    metric: "ad_diff_pct",
    label: "Net advances (daily)",
    sub: "Advancers minus decliners as a share of names traded — the rawest daily flow read. Spiky by nature.",
    percent: true,
    bands: atlasBands(-0.672, 0.004, 0.582),
  },
  {
    metric: "cumulative_ad",
    label: "A-D line (cumulative)",
    sub: "Running total of daily net advances. Read its slope and its divergences from the index — the level itself carries no meaning.",
    percent: false,
    bands: [],
  },
];

async function AdvanceDeclineDetail({
  reading,
  universe,
}: {
  reading: MarketReading;
  universe: BreadthUniverse;
}) {
  const series = await getBreadthTimeseries({
    days: 4000,
    metrics: AD_VARIANTS.map((v) => v.metric),
    universe,
  }).catch((): TimeseriesResponse => ({ index: [], data: {} }));
  const isDefault = universe === "nse500";
  const byKey = new Map(Object.entries(series.data));
  const daily = byKey.get("ad_diff_pct") ?? [];
  const now = isDefault ? (reading.breadth["ad_diff_pct"] ?? null) : lastNonNull(daily);

  const variants: MetricVariant[] = AD_VARIANTS.map((v) => {
    const vals = byKey.get(v.metric) ?? [];
    const bands =
      v.metric === "cumulative_ad" ? [] : isDefault ? v.bands : computedBands(vals);
    return { ...v, values: vals, bands };
  });

  return (
    <div className="flex flex-col gap-4">
      <ChartCard
        title={`Advances & declines · ${universeLabel(universe)}`}
        sub="How many stocks participated in today's move — daily net advances, plus the cumulative A-D line."
      >
        <MetricExplorer dates={series.index} variants={variants} />
      </ChartCard>
      <StatStrip
        stats={[
          { label: "Net advances today", value: fmtPct(now, 0, true), sub: "of names traded" },
          {
            label: "Typical day",
            value: isDefault ? "±0%" : fmtPct(percentile(daily, 50), 0),
            sub: "median is near zero by nature",
          },
          {
            label: "Heavy-selling day",
            value: isDefault ? "-67%" : fmtPct(percentile(daily, 5), 0),
            sub: "bottom 5% of days",
          },
          {
            label: "Broad-buying day",
            value: isDefault ? "+58%" : fmtPct(percentile(daily, 95), 0),
            sub: "top 5% of days",
          },
        ]}
      />
      <LearnPanel title="Learn more">
        The most direct participation gauge there is: how many stocks rose
        versus fell today. Single days are noise — the daily series mean-
        reverts almost immediately — which is why the cumulative A-D line
        exists: when it flattens while the index keeps rising, fewer and
        fewer stocks are carrying the move.
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
      <LearnPanel slug="stress-score" title="Learn more">
        A single 0–100 read on how tense conditions are, blending four
        observable inputs. It describes the environment — calm markets tend to
        produce smaller swings, stressed ones bigger and faster swings — and
        says nothing about direction.
      </LearnPanel>
    </div>
  );
}

async function VixDetail({ reading }: { reading: MarketReading }) {
  const series = await getMacroTimeseries({ days: 4000, metrics: ["vix_close"] }).catch(
    (): TimeseriesResponse => ({ index: [], data: {} }),
  );
  const values = series.data["vix_close"] ?? [];
  // Reference lines from the fetched history itself — descriptive context,
  // recomputed as the series grows rather than hardcoded.
  const med = percentile(values, 50);
  const p90 = percentile(values, 90);
  const bands: ReferenceBand[] = [
    ...(p90 !== null ? [{ value: p90, label: "top 10% of days on record", tone: "warning" as const }] : []),
    ...(med !== null ? [{ value: med, label: "median day on record", tone: "muted" as const }] : []),
  ];
  const m = reading.macro;

  return (
    <div className="flex flex-col gap-4">
      <ChartCard
        title="India VIX"
        sub="The market's expected 30-day volatility, from option prices. Quiet regimes sit low for months; spikes are sharp and short."
      >
        <TimeseriesChart dates={series.index} values={values} bands={bands} />
      </ChartCard>
      <StatStrip
        stats={[
          { label: "Now", value: fmtNum(m["vix_close"], 1), sub: "close" },
          { label: "Median on record", value: med !== null ? med.toFixed(1) : "—", sub: "the typical day" },
          {
            label: "5-day change",
            value: fmtPct(m["vix_roc_5d"], 1),
            sub: "expansion / contraction",
          },
          {
            label: "Above 20",
            value: m["vix_above_20"] ? "Yes" : "No",
            sub: "elevated-volatility line",
          },
        ]}
      />
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
const NNH_BANDS: ReferenceBand[] = [
  { value: 0.132, label: "top 5% of days since 2010", tone: "warning" },
  { value: 0.024, label: "median day since 2010", tone: "muted" },
  { value: -0.1, label: "bottom 5% of days since 2010", tone: "negative" },
];

async function NetNewHighsDetail({
  reading,
  universe,
}: {
  reading: MarketReading;
  universe: BreadthUniverse;
}) {
  const series = await getBreadthTimeseries({
    days: 4000,
    metrics: ["net_new_highs_pct"],
    universe,
  }).catch((): TimeseriesResponse => ({ index: [], data: {} }));
  const isDefault = universe === "nse500";
  const values = series.data["net_new_highs_pct"] ?? [];
  const now = isDefault
    ? (reading.breadth["net_new_highs_pct"] ?? null)
    : lastNonNull(values);
  const bands = isDefault ? NNH_BANDS : computedBands(values);

  return (
    <div className="flex flex-col gap-4">
      <ChartCard
        title={`Net new 52-week highs · ${universeLabel(universe)}`}
        sub="Stocks at fresh 1-year highs minus fresh 1-year lows. Crashes push the low side much harder than rallies push the high side."
      >
        <TimeseriesChart dates={series.index} values={values} bands={bands} percent />
      </ChartCard>
      <StatStrip
        stats={[
          { label: "Now", value: fmtPct(now, 1), sub: `of ${universeLabel(universe)}` },
          {
            label: "Median day",
            value: isDefault ? "+2.4%" : fmtPct(percentile(values, 50), 1),
            sub: isDefault ? "since 2010" : "this universe's history",
          },
          {
            label: "Bottom 5% of days",
            value: isDefault ? "-10%" : fmtPct(percentile(values, 5), 1),
            sub: "washout territory",
          },
          {
            label: "Top 5% of days",
            value: isDefault ? "+13.2%" : fmtPct(percentile(values, 95), 1),
            sub: "expansion territory",
          },
        ]}
      />
      <LearnPanel title="Learn more">
        New-high/new-low counts catch leadership turning before averages do —
        a rally where fewer and fewer names make new highs is thinning out
        even while the index holds up. The measure is asymmetric by nature:
        panics synchronize new lows far more than booms synchronize new
        highs.
      </LearnPanel>
    </div>
  );
}

// McClellan oscillator reference levels from the same atlas profile:
// p5 = -0.068, p95 = +0.067 (76% of days inside ±1σ = ±0.041).
const MCC_BANDS: ReferenceBand[] = [
  { value: 0.067, label: "top 5% of days since 2010", tone: "warning" },
  { value: 0, label: "zero line", tone: "muted" },
  { value: -0.068, label: "bottom 5% of days since 2010", tone: "negative" },
];

async function McClellanDetail({
  reading,
  universe,
}: {
  reading: MarketReading;
  universe: BreadthUniverse;
}) {
  const series = await getBreadthTimeseries({
    days: 4000,
    metrics: ["mcclellan_osc"],
    universe,
  }).catch((): TimeseriesResponse => ({ index: [], data: {} }));
  const isDefault = universe === "nse500";
  const values = series.data["mcclellan_osc"] ?? [];
  const now = isDefault ? (reading.breadth["mcclellan_osc"] ?? null) : lastNonNull(values);
  const bands = isDefault ? MCC_BANDS : computedBands(values);

  return (
    <div className="flex flex-col gap-4">
      <ChartCard
        title={`McClellan oscillator · ${universeLabel(universe)} advance-decline flow`}
        sub="Fast EMA minus slow EMA of daily advance-decline breadth. A flow gauge — it describes what just happened, not where the cycle is."
      >
        <TimeseriesChart dates={series.index} values={values} bands={bands} defaultRange="1Y" />
      </ChartCard>
      <StatStrip
        stats={[
          { label: "Now", value: fmtNum(now, 3), sub: "oscillator level" },
          { label: "Typical band", value: "±0.041", sub: "76% of days sit inside" },
          { label: "Bottom 5% of days", value: "-0.068", sub: "heavy selling flow" },
          { label: "Top 5% of days", value: "+0.067", sub: "heavy buying flow" },
        ]}
      />
      <LearnPanel slug="mcclellan-oscillator" title="Learn more">
        A zero-centered oscillator over daily advances minus declines. It
        flickers — most readings sit in the middle band, and extremes fade
        within days. Historically its sharpest positive spikes have clustered
        around the bounces off deep lows, which is why it reads as flow, not
        as a level signal.
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
  const series = await getConcentrationTimeseries({ days: 4000, universe }).catch(
    (): TimeseriesResponse => ({ index: [], data: {} }),
  );
  const values = series.data["spread_20d_avg_pp"] ?? [];
  const daily = series.data["cap_vs_equal_spread_pp"] ?? [];
  const spreadNow = lastNonNull(daily);
  // Per-name attribution needs factsheet weights, which exist only for the
  // Nifty 50 — the heavyweight tiles switch off on other universes.
  const hasAttribution = universe === "nifty50";
  const c = reading.concentration;

  return (
    <div className="flex flex-col gap-4">
      <ChartCard
        title={`Cap-weighted vs equal-weighted ${universeLabel(universe)}, 20-day average spread`}
        sub="Above zero: the heavyweights are outrunning the average stock (a narrow tape). Below zero: the average stock leads (broad participation)."
      >
        <TimeseriesChart
          dates={series.index}
          values={values}
          bands={[{ value: 0, label: "even tape", tone: "muted" }]}
          defaultRange="1Y"
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

const REGIME_COLOR: Record<RegimeEpisode["regime"], string> = {
  TREND_BULL: "var(--positive)",
  DRIFT: "var(--muted-foreground)",
  STRETCHED: "var(--warning)",
  STRESS: "var(--negative)",
};

const REGIME_ORDER = Object.keys(REGIME_COLOR) as RegimeEpisode["regime"][];

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
    getRegimeTimeseries({ universe }).catch(() => ({
      index_label: null,
      index: [] as string[],
      data: {} as { close?: (number | null)[]; regime?: string[] },
    })),
  ]);
  const episodes = history.episodes;
  const r = reading.regime;
  const indexLabel = series.index_label ?? history.index_label ?? r.index_label;
  const recent = [...episodes].slice(-10).reverse();
  const current = episodes.at(-1);

  return (
    <div className="flex flex-col gap-4">
      <ChartCard
        title={`${indexLabel} through its regimes`}
        sub="The index with an overlay tint by regime in force. One of four rules-based regimes, smoothed with a 3-day confirmation."
      >
        <RegimeChart
          dates={series.index}
          closes={series.data.close ?? []}
          regimes={series.data.regime ?? []}
          indexLabel={indexLabel}
        />
      </ChartCard>
      <StatStrip
        stats={[
          { label: "Now", value: regimeLabel(r.regime), sub: `day ${r.persistence_days}` },
          {
            label: "Previous regime",
            value: r.prev_regime ? regimeLabel(r.prev_regime) : "—",
            sub: r.prev_regime_lasted_days ? `lasted ${r.prev_regime_lasted_days} days` : undefined,
          },
          {
            label: `${indexLabel} this regime`,
            value: fmtPct(current?.index_return_pct ?? null, 1, true),
            sub: "since the regime began",
          },
          {
            label: "Participation",
            value: fmtPct(r.participation_pct, 0),
            sub: `of ${universeLabel(universe)} above their ${r.participation_ma_days}-day average`,
          },
        ]}
      />
      <div className="flex flex-col gap-3 rounded-xl border border-border bg-card p-5">
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
                    /* eslint-disable-next-line security/detect-object-injection -- reg iterates a literal tuple */
                    style={{ backgroundColor: REGIME_COLOR[reg] }}
                  />
                  {regimeLabel(reg)}
                </span>
                <span className="font-serif text-xl font-medium text-foreground">
                  {days !== null ? `${days} days` : "—"}
                </span>
              </div>
            );
          })}
        </div>
        <p className="text-[12px] leading-[1.5] text-muted-foreground">
          Regimes vary widely in length — the medians are context, not a
          countdown.
        </p>
      </div>
      <div className="flex flex-col gap-2 rounded-xl border border-border bg-card p-5">
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
                  style={{ backgroundColor: REGIME_COLOR[e.regime] }}
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
      {indicator === "stress" && <StressDetail reading={reading} />}
      {indicator === "advance-decline" && (
        <AdvanceDeclineDetail reading={reading} universe={universe} />
      )}
      {indicator === "vix" && <VixDetail reading={reading} />}
      {indicator === "net-new-highs" && (
        <NetNewHighsDetail reading={reading} universe={universe} />
      )}
      {indicator === "mcclellan" && <McClellanDetail reading={reading} universe={universe} />}
      {indicator === "concentration" && (
        <ConcentrationDetail reading={reading} universe={universe} />
      )}
      <p className="mt-4 text-[11px] leading-[1.6] text-muted-foreground">
        Educational market analytics — descriptions of conditions, not
        recommendations. History charts always run through the most recent
        trading day, while the snapshot date rewinds today&apos;s readings.
      </p>
    </DetailShell>
  );
}
