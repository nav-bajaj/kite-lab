import Link from "next/link";
import {
  getReading,
  getMovers,
  getOnThisDay,
  getSeasonality,
  getPreEvent,
  fmtPct,
  fmtNum,
  ConcentrationReading,
  CrossAssetEntry,
  MoversResponse,
  OnThisDayResponse,
  SeasonalityResponse,
  PreEventResponse,
  regimeLabel,
} from "@/lib/insights-api";
import { RegimeLegend } from "./_components/regime-legend";
import {
  Section,
  MetricCard,
  RegimeCard,
  StressGauge,
  SectorBars,
  Pct,
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
  // Calendar-strip fetches are additive context — never let them break the
  // core Pulse render, so each degrades to null on error.
  const nullOnErr = <T,>(p: Promise<T>) => p.catch(() => null);
  const [reading, movers, onThisDay, seasonality, preEvent] = await Promise.all([
    getReading(date),
    getMovers(date),
    nullOnErr(getOnThisDay(date)),
    nullOnErr(getSeasonality(date)),
    nullOnErr(getPreEvent(date)),
  ]);
  const { regime, stress, sector_leaderboard_60d, concentration, cross_asset } = reading;
  const dateQuery = date ? `?date=${encodeURIComponent(date)}` : "";

  return (
    <main className="flex flex-col gap-12">
      {/* ──────────────── HEADLINE ──────────────── */}
      <section className="flex flex-col gap-4">
        <div className="flex flex-col gap-1">
          <h2 className="font-serif text-2xl font-medium tracking-[-0.01em] text-foreground">
            Today&apos;s pulse
          </h2>
          <p className="text-[13px] text-muted-foreground">
            As of{" "}
            {new Date(reading.date).toLocaleDateString("en-IN", {
              weekday: "long",
              year: "numeric",
              month: "long",
              day: "numeric",
            })}
          </p>
        </div>

        <div className="grid gap-4 sm:grid-cols-3">
          <RegimeCard
            regime={regime}
            help={<LearnLink slug="regime" label="Deep-dive →" />}
          />
          <StressGauge stress={stress} help={<LearnLink slug="stress-score" />} />
          <MetricCard
            label="Nifty 100 vs 100-DMA"
            value={regime.nifty100_above_100dma ? "Above" : "Below"}
            tone={regime.nifty100_above_100dma ? "positive" : "negative"}
            sub={`Breadth ${fmtPct(regime.pct_above_200dma, 0)} above 200-DMA`}
            help={<LearnLink slug="pct-above-200dma" label="What is breadth?" />}
          />
        </div>
      </section>

      {/* ──────────────── STOCK MOVERS (C6) ──────────────── */}
      {movers.data_available && (
        <StockMoversSection movers={movers} dateQuery={dateQuery} />
      )}

      {/* ──────────────── MARKET CALENDAR (B3) ──────────────── */}
      <CalendarStrip
        onThisDay={onThisDay}
        seasonality={seasonality}
        preEvent={preEvent}
      />

      {/* ──────────────── CONCENTRATION ──────────────── */}
      <ConcentrationSection concentration={concentration} />

      {/* ──────────────── SECTOR LEADERBOARD ──────────────── */}
      <Section
        title="Sector leaderboard"
        help={
          <>
            <LearnLink slug="sector-rs" label="What is RS?" />
            <LearnLink slug="sector-breadth" label="What is breadth?" />
          </>
        }
      >
        <p className="-mt-2 text-[13px] text-muted-foreground">
          60-day relative strength vs Nifty 50, ranked.
        </p>
        <SectorBars sectors={sector_leaderboard_60d} />

        <details className="mt-2">
          <summary className="cursor-pointer text-[13px] text-muted-foreground underline-offset-2 hover:text-foreground hover:underline">
            Full table — 5d / 20d / 60d / 120d + breadth
          </summary>
          <div className="mt-3 overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="border-b border-border text-left text-muted-foreground">
                <tr>
                  <th className="w-10 py-2 font-medium">#</th>
                  <th className="py-2 font-medium">Sector</th>
                  <th className="py-2 text-right font-medium">5d</th>
                  <th className="py-2 text-right font-medium">20d</th>
                  <th className="py-2 text-right font-medium">60d</th>
                  <th className="py-2 text-right font-medium">120d</th>
                  <th className="py-2 text-right font-medium">Δ rank</th>
                  <th className="py-2 text-right font-medium">Breadth</th>
                </tr>
              </thead>
              <tbody>
                {sector_leaderboard_60d.map((s) => (
                  <tr key={s.sector} className="border-b border-border last:border-0">
                    <td className="py-2 text-muted-foreground">{s.rank_60d ?? "—"}</td>
                    <td className="py-2 font-medium text-foreground">
                      {s.sector.replace("NIFTY_", "")}
                    </td>
                    <td className="py-2 text-right tabular-nums"><Pct v={s.rs_5d} /></td>
                    <td className="py-2 text-right tabular-nums"><Pct v={s.rs_20d} /></td>
                    <td className="py-2 text-right tabular-nums"><Pct v={s.rs_60d} /></td>
                    <td className="py-2 text-right tabular-nums"><Pct v={s.rs_120d} /></td>
                    <td className="py-2 text-right tabular-nums text-muted-foreground">
                      {s.rank_change_wow_60d === null
                        ? "—"
                        : s.rank_change_wow_60d > 0
                          ? `+${s.rank_change_wow_60d}`
                          : s.rank_change_wow_60d}
                    </td>
                    <td className="py-2 text-right tabular-nums text-muted-foreground">
                      {fmtPct(s.pct_above_200dma, 0)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
      </Section>

      {/* ──────────────── STRESS BREAKDOWN ──────────────── */}
      <Section
        title="Stress breakdown"
        help={<LearnLink slug="stress-score" label="How is this computed?" />}
      >
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="border-b border-border text-left text-muted-foreground">
              <tr>
                <th className="py-2 font-medium">Component</th>
                <th className="py-2 text-right font-medium">Contribution (0–100)</th>
                <th className="py-2 text-right font-medium">Raw</th>
              </tr>
            </thead>
            <tbody>
              <Row label="VIX percentile (252d)" component={stress.vix_pctile_component} raw={`VIX = ${fmtNum(stress.vix_close, 1)}`} />
              <Row label="Nifty drawdown depth" component={stress.drawdown_component} raw={fmtPct(stress.nifty_drawdown_pct, 1, true)} />
              <Row label="% NSE 500 below 200-DMA" component={stress.below_200dma_component} raw={fmtPct(stress.pct_above_200dma ? 1 - stress.pct_above_200dma : null, 0)} />
              <Row label="Cross-sectional dispersion" component={stress.dispersion_component} raw={`z = ${fmtNum(stress.dispersion_z, 2)}`} />
            </tbody>
          </table>
        </div>
      </Section>

      {/* ──────────────── CROSS-ASSET ──────────────── */}
      <CrossAssetSection cross_asset={cross_asset} />

      {/* ──────────────── REGIME GLOSSARY ──────────────── */}
      <RegimeLegend />
    </main>
  );
}

function ConcentrationSection({ concentration: c }: { concentration: ConcentrationReading }) {
  const indexFlat = c.top_3_share_of_move === null;
  const headline = buildConcentrationHeadline(c);

  return (
    <Section
      title="Who drove today's Nifty 50 move"
      help={<LearnLink slug="concentration" />}
    >
      <p className="-mt-2 text-[15px] leading-[1.6] text-foreground">{headline}</p>

      <div className="grid gap-4 sm:grid-cols-3">
        <MetricCard
          label="Nifty 50 (cap-wt)"
          value={<Pct v={c.nifty_return_pct / 100} decimals={2} />}
          sub={`Equal-weighted: ${fmtPct(c.equal_weighted_return_pct / 100, 2, true)}`}
        />
        <MetricCard
          label="Cap vs equal spread"
          value={<Pct v={c.cap_vs_equal_spread_pp / 100} decimals={2} />}
          sub={
            Math.abs(c.cap_vs_equal_spread_pp) > 0.3
              ? c.cap_vs_equal_spread_pp > 0
                ? "Mega-caps led"
                : "Broad participation"
              : "Even tape"
          }
        />
        <MetricCard
          label="Top-3 share of move"
          value={indexFlat ? "—" : fmtPct(c.top_3_share_of_move, 0)}
          sub={indexFlat ? "Index ~flat today" : c.top_3_symbols.join(" · ")}
        />
      </div>

      <details className="mt-1">
        <summary className="cursor-pointer text-[13px] text-muted-foreground underline-offset-2 hover:text-foreground hover:underline">
          Show top 10 contributors (by absolute impact on the index)
        </summary>
        <div className="mt-3 overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="border-b border-border text-left text-muted-foreground">
              <tr>
                <th className="py-2 font-medium">Symbol</th>
                <th className="py-2 text-right font-medium">Weight</th>
                <th className="py-2 text-right font-medium">Stock %</th>
                <th className="py-2 text-right font-medium">Contribution (bps)</th>
                <th className="py-2 text-right font-medium">Share of move</th>
              </tr>
            </thead>
            <tbody>
              {c.constituents.slice(0, 10).map((row) => (
                <tr key={row.symbol} className="border-b border-border last:border-0">
                  <td className="py-2 font-medium text-foreground">{row.symbol}</td>
                  <td className="py-2 text-right tabular-nums text-muted-foreground">{row.weight.toFixed(2)}%</td>
                  <td className="py-2 text-right tabular-nums"><Pct v={row.return_pct / 100} decimals={2} /></td>
                  <td className="py-2 text-right tabular-nums text-muted-foreground">
                    {row.contribution_bps >= 0 ? "+" : ""}
                    {row.contribution_bps.toFixed(1)}
                  </td>
                  <td className="py-2 text-right tabular-nums text-muted-foreground">
                    {row.share_of_move === null ? "—" : fmtPct(row.share_of_move, 0)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-2 text-[13px] text-muted-foreground">
          Weights from NSE NIFTY 50 monthly factsheet (current snapshot, not
          historical). Coverage: {c.n_constituents_covered}/{c.n_constituents_total} constituents.
        </p>
      </details>
    </Section>
  );
}

function buildConcentrationHeadline(c: ConcentrationReading): string {
  const niftyMove = c.nifty_return_pct;
  const moveDir = niftyMove > 0 ? "rose" : niftyMove < 0 ? "fell" : "was flat";
  const sign = niftyMove > 0 ? "+" : "";
  const absMove = `${sign}${niftyMove.toFixed(2)}%`;

  if (Math.abs(niftyMove) < 0.05) {
    return `Nifty 50 was essentially flat (${absMove}). Attribution is not meaningful when the index barely moves.`;
  }

  const top3 = c.top_3_share_of_move ?? 0;
  const top3Pct = Math.abs(top3 * 100).toFixed(0);

  if (Math.abs(top3) > 0.8) {
    return `Nifty ${moveDir} ${absMove} — but ${top3Pct}% of the move came from just ${c.top_3_symbols.join(", ")}. Narrow tape.`;
  }
  if (Math.abs(top3) > 0.5) {
    return `Nifty ${moveDir} ${absMove}. Top 3 (${c.top_3_symbols.join(", ")}) drove ${top3Pct}% of the move — concentrated but not extreme.`;
  }
  return `Nifty ${moveDir} ${absMove} with broad participation — no single name dominated (top-3 share ${top3Pct}%).`;
}

function CrossAssetSection({ cross_asset }: { cross_asset: Record<string, CrossAssetEntry> }) {
  const order = ["usdinr", "gold", "crude", "india_10y", "us_10y"];
  const available = order
    // eslint-disable-next-line security/detect-object-injection
    .map((k) => cross_asset[k])
    .filter((e): e is CrossAssetEntry => Boolean(e));

  const liveEntries = available.filter((e) => e.data_available);
  const deferredEntries = available.filter((e) => !e.data_available);

  const notable = liveEntries.filter((e) => {
    const f = e.features;
    const pctileExtreme =
      f.pctile_252d !== null && (f.pctile_252d >= 0.95 || f.pctile_252d <= 0.05);
    const zExtreme = f.z_252d !== null && Math.abs(f.z_252d) >= 2.0;
    return pctileExtreme || zExtreme;
  });

  return (
    <Section
      title="Cross-asset context"
      help={<LearnLink slug="glossary#flows-structure" />}
    >
      <p className="-mt-2 text-[13px] leading-[1.5] text-muted-foreground">
        Where four assets that influence Indian equities are sitting today,
        each relative to its own trailing-year range — z-score, distance from
        the 200-day moving average, and percentile within the trailing year.
      </p>

      {notable.length > 0 && (
        <div className="rounded-xl border border-border bg-card p-4 text-sm text-foreground">
          <span className="font-semibold text-[color:var(--warning)]">Notable:</span>{" "}
          {notable.map((e, i) => (
            <span key={e.asset_id}>
              {i > 0 ? " · " : ""}
              <span className="font-medium">{e.label.split(" (")[0]}</span>{" "}
              {describeExtreme(e)}
            </span>
          ))}
        </div>
      )}

      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="border-b border-border text-left text-muted-foreground">
            <tr>
              <th className="py-2 font-medium">Asset</th>
              <th className="py-2 text-right font-medium">Close</th>
              <th className="py-2 text-right font-medium">5d</th>
              <th className="py-2 text-right font-medium">20d</th>
              <th className="py-2 text-right font-medium">60d</th>
              <th className="py-2 text-right font-medium">z (1y)</th>
              <th className="py-2 text-right font-medium">vs 200-DMA</th>
              <th className="py-2 text-right font-medium">Percentile</th>
            </tr>
          </thead>
          <tbody>
            {liveEntries.map((e) => (
              <tr key={e.asset_id} className="border-b border-border last:border-0">
                <td className="py-2 font-medium text-foreground">{e.label.split(" (")[0]}</td>
                <td className="py-2 text-right tabular-nums text-muted-foreground">{fmtNum(e.features.close, 2)}</td>
                <td className="py-2 text-right tabular-nums"><Pct v={e.features.roc_5d} /></td>
                <td className="py-2 text-right tabular-nums"><Pct v={e.features.roc_20d} /></td>
                <td className="py-2 text-right tabular-nums"><Pct v={e.features.roc_60d} /></td>
                <td className="py-2 text-right tabular-nums text-muted-foreground">
                  {e.features.z_252d === null
                    ? "—"
                    : `${e.features.z_252d >= 0 ? "+" : ""}${e.features.z_252d.toFixed(2)}`}
                </td>
                <td className="py-2 text-right tabular-nums"><Pct v={e.features.dist_from_200dma} /></td>
                <td className="py-2 text-right tabular-nums text-muted-foreground">
                  {e.features.pctile_252d === null
                    ? "—"
                    : `${(e.features.pctile_252d * 100).toFixed(0)}%`}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {deferredEntries.length > 0 && (
        <p className="text-[13px] text-muted-foreground">
          Data pending for:{" "}
          {deferredEntries.map((e) => e.label.split(" (")[0]).join(", ")}
        </p>
      )}
    </Section>
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
      <div className="grid gap-4 md:grid-cols-2">
        {/* Fresh 52-week highs / lows */}
        <div className="flex flex-col gap-3 rounded-xl border border-border bg-card p-5">
          <div className="flex items-baseline justify-between">
            <span className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
              Fresh 52-week highs / lows
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
              Biggest RS-rank improvers (21d)
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

// ──────────────── Market calendar strip (B3) ────────────────

/** Format a percentage-point value (already ×100 by the engine). */
function fmtPP(v: number | null | undefined, decimals = 1): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  const s = v.toFixed(decimals);
  return v >= 0 ? `+${s}%` : `${s}%`;
}

const EVENT_TYPE_LABEL: Record<string, string> = {
  budget: "Union Budget",
  rbi_policy: "RBI policy",
  election: "General election",
};

function CalendarStrip({
  onThisDay,
  seasonality,
  preEvent,
}: {
  onThisDay: OnThisDayResponse | null;
  seasonality: SeasonalityResponse | null;
  preEvent: PreEventResponse | null;
}) {
  // Prefer the longest-horizon anniversary that lands on a curated event.
  const tagged = onThisDay
    ? Object.values(onThisDay.anniversaries)
        .filter((a) => a.event_tag)
        .sort((a, b) => b.horizon_years - a.horizon_years)
    : [];
  const anniversary = tagged[0] ?? null;

  const month = seasonality?.data_available ? seasonality.seasonality.month : null;
  const upcoming = preEvent?.upcoming ?? [];

  // Nothing to show → render nothing (additive strip).
  if (!anniversary && !month && upcoming.length === 0) return null;

  return (
    <Section
      title="Market calendar"
      help={<LearnLink slug="regime" label="What is regime?" />}
    >
      <div className="grid gap-4 md:grid-cols-3">
        {/* On this day */}
        {anniversary && (
          <div className="flex flex-col gap-2 rounded-xl border border-border bg-card p-5">
            <span className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
              On this day
            </span>
            <p className="text-[13px] leading-[1.55] text-foreground">
              <span className="font-medium">
                {anniversary.horizon_years} year
                {anniversary.horizon_years === 1 ? "" : "s"} ago
              </span>{" "}
              ({new Date(anniversary.date).toLocaleDateString("en-IN", {
                day: "numeric",
                month: "short",
                year: "numeric",
              })}
              ): {anniversary.event_tag}
            </p>
            <p className="text-[12px] text-muted-foreground">
              Regime that day: {regimeLabel(anniversary.regime)}
              {anniversary.stress_score !== null
                ? ` · stress ${anniversary.stress_score.toFixed(0)}/100`
                : ""}
            </p>
          </div>
        )}

        {/* Seasonality — descriptive, n disclosed, no forecast */}
        {month && (
          <div className="flex flex-col gap-2 rounded-xl border border-border bg-card p-5">
            <span className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
              {month.label} seasonality
            </span>
            <p className="text-[13px] leading-[1.55] text-foreground">
              Over the last {month.n} years, {month.label} posted a median Nifty
              return of{" "}
              <span className="font-medium tabular-nums">
                {fmtPP(month.median_return_pct)}
              </span>{" "}
              (middle-half {fmtPP(month.q1_return_pct)} to{" "}
              {fmtPP(month.q3_return_pct)}), positive in{" "}
              {month.pct_positive !== null
                ? Math.round(month.pct_positive * month.n)
                : "—"}{" "}
              of {month.n}.
            </p>
            <p className="text-[11px] italic leading-[1.5] text-muted-foreground">
              A historical tendency across a small sample (n={month.n}), not a
              forecast.
            </p>
          </div>
        )}

        {/* Upcoming curated events + same-type history */}
        <div className="flex flex-col gap-2 rounded-xl border border-border bg-card p-5">
          <span className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
            Upcoming events
          </span>
          {upcoming.length === 0 ? (
            <p className="text-[12px] leading-[1.5] text-muted-foreground">
              No curated events in the next 7 days. Known event dates (budgets,
              RBI policy, elections) are added by hand as they are scheduled.
            </p>
          ) : (
            <ul className="flex flex-col gap-2 text-[13px]">
              {upcoming.map((e) => (
                <li key={`${e.date}-${e.tag}`} className="flex flex-col gap-0.5">
                  <span className="text-foreground">
                    <span className="font-medium">
                      {e.days_until === 0
                        ? "Today"
                        : `In ${e.days_until} day${e.days_until === 1 ? "" : "s"}`}
                    </span>
                    : {e.tag}
                  </span>
                  {e.history && (
                    <span className="text-[12px] text-muted-foreground">
                      Past {EVENT_TYPE_LABEL[e.event_type ?? ""] ?? "similar"}{" "}
                      days (n={e.history.n}): median 1-day move{" "}
                      <span className="tabular-nums">
                        {fmtPP(e.history.median_move_1d_pct)}
                      </span>
                      {e.history.median_move_5d_pct !== null ? (
                        <>
                          , 5-day{" "}
                          <span className="tabular-nums">
                            {fmtPP(e.history.median_move_5d_pct)}
                          </span>
                        </>
                      ) : null}
                    </span>
                  )}
                </li>
              ))}
              <li className="text-[11px] italic leading-[1.5] text-muted-foreground">
                Historical context only — past moves are not a forecast.
              </li>
            </ul>
          )}
        </div>
      </div>
    </Section>
  );
}

function describeExtreme(e: CrossAssetEntry): string {
  const f = e.features;
  if (f.pctile_252d !== null && f.pctile_252d >= 0.95) {
    return `at the ${Math.round(f.pctile_252d * 100)}th percentile of its trailing year`;
  }
  if (f.pctile_252d !== null && f.pctile_252d <= 0.05) {
    return `at the ${Math.round(f.pctile_252d * 100)}th percentile of its trailing year (very low)`;
  }
  if (f.z_252d !== null && Math.abs(f.z_252d) >= 2.0) {
    const dir = f.z_252d > 0 ? "elevated" : "depressed";
    return `z = ${f.z_252d >= 0 ? "+" : ""}${f.z_252d.toFixed(2)} (${dir})`;
  }
  return "notable";
}

function Row({ label, component, raw }: { label: string; component: number | null; raw: string }) {
  return (
    <tr className="border-b border-border last:border-0">
      <td className="py-2 text-foreground">{label}</td>
      <td className="py-2 text-right tabular-nums text-foreground">{fmtNum(component, 0)}</td>
      <td className="py-2 text-right tabular-nums text-muted-foreground">{raw}</td>
    </tr>
  );
}
