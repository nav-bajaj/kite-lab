import Link from "next/link";
import { notFound } from "next/navigation";
import {
  getReading,
  getBreadthTimeseries,
  getStressTimeseries,
  getMacroTimeseries,
  getConcentrationTimeseries,
  getRegimeHistory,
  fmtPct,
  fmtNum,
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
  { slug: "vix", label: "India VIX", ready: true },
  { slug: "net-new-highs", label: "Net new highs", ready: true },
  { slug: "mcclellan", label: "McClellan osc", ready: true },
  { slug: "concentration", label: "Concentration", ready: true },
];

const TITLES: Record<string, string> = {
  regime: "Market state",
  stress: "Market stress",
  breadth: "Market breadth",
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
          Learn more →
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
      <LearnPanel slug="vix" title="What this measures">
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

async function NetNewHighsDetail({ reading }: { reading: MarketReading }) {
  const series = await getBreadthTimeseries({
    days: 4000,
    metrics: ["net_new_highs_pct"],
  }).catch((): TimeseriesResponse => ({ index: [], data: {} }));
  const values = series.data["net_new_highs_pct"] ?? [];
  const now = reading.breadth["net_new_highs_pct"] ?? null;

  return (
    <div className="flex flex-col gap-4">
      <ChartCard
        title="Net new 52-week highs, share of NSE 500"
        sub="Stocks at fresh 1-year highs minus fresh 1-year lows. Crashes push the low side much harder than rallies push the high side."
      >
        <TimeseriesChart dates={series.index} values={values} bands={NNH_BANDS} percent />
      </ChartCard>
      <StatStrip
        stats={[
          { label: "Now", value: fmtPct(now, 1), sub: "of NSE 500" },
          { label: "Median since 2010", value: "+2.4%", sub: "the typical day" },
          { label: "Bottom 5% of days", value: "-10%", sub: "washout territory" },
          { label: "Top 5% of days", value: "+13.2%", sub: "expansion territory" },
        ]}
      />
      <LearnPanel title="What this measures">
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

async function McClellanDetail({ reading }: { reading: MarketReading }) {
  const series = await getBreadthTimeseries({
    days: 4000,
    metrics: ["mcclellan_osc"],
  }).catch((): TimeseriesResponse => ({ index: [], data: {} }));
  const values = series.data["mcclellan_osc"] ?? [];
  const now = reading.breadth["mcclellan_osc"] ?? null;

  return (
    <div className="flex flex-col gap-4">
      <ChartCard
        title="McClellan oscillator (NSE 500 advance-decline flow)"
        sub="Fast EMA minus slow EMA of daily advance-decline breadth. A flow gauge — it describes what just happened, not where the cycle is."
      >
        <TimeseriesChart dates={series.index} values={values} bands={MCC_BANDS} defaultRange="1Y" />
      </ChartCard>
      <StatStrip
        stats={[
          { label: "Now", value: fmtNum(now, 3), sub: "oscillator level" },
          { label: "Typical band", value: "±0.041", sub: "76% of days sit inside" },
          { label: "Bottom 5% of days", value: "-0.068", sub: "heavy selling flow" },
          { label: "Top 5% of days", value: "+0.067", sub: "heavy buying flow" },
        ]}
      />
      <LearnPanel slug="mcclellan-oscillator" title="What this measures">
        A zero-centered oscillator over daily advances minus declines. It
        flickers — most readings sit in the middle band, and extremes fade
        within days. Historically its sharpest positive spikes have clustered
        around the bounces off deep lows, which is why it reads as flow, not
        as a level signal.
      </LearnPanel>
    </div>
  );
}

async function ConcentrationDetail({ reading }: { reading: MarketReading }) {
  const series = await getConcentrationTimeseries(4000).catch(
    (): TimeseriesResponse => ({ index: [], data: {} }),
  );
  const values = series.data["spread_20d_avg_pp"] ?? [];
  const c = reading.concentration;

  return (
    <div className="flex flex-col gap-4">
      <ChartCard
        title="Cap-weighted vs equal-weighted Nifty 50, 20-day average spread"
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
            value: `${c.cap_vs_equal_spread_pp >= 0 ? "+" : ""}${c.cap_vs_equal_spread_pp.toFixed(2)}pp`,
            sub: "cap minus equal weighted",
          },
          {
            label: "Top-5 share of move",
            // Share-of-move ratios explode on near-flat days (a 160% share
            // of a 0.1% move is noise) — suppress below a quarter percent.
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
          {
            label: "Names covered",
            value: `${c.n_constituents_covered}/${c.n_constituents_total}`,
            sub: "Nifty 50 constituents",
          },
        ]}
      />
      <LearnPanel slug="concentration" title="What this measures">
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
      {indicator === "vix" && <VixDetail reading={reading} />}
      {indicator === "net-new-highs" && <NetNewHighsDetail reading={reading} />}
      {indicator === "mcclellan" && <McClellanDetail reading={reading} />}
      {indicator === "concentration" && <ConcentrationDetail reading={reading} />}
      <p className="mt-4 text-[11px] leading-[1.6] text-muted-foreground">
        Educational market analytics — descriptions of conditions, not
        recommendations. History charts always run through the most recent
        trading day, while the snapshot date rewinds today&apos;s readings.
      </p>
    </DetailShell>
  );
}
