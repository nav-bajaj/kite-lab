import Link from "next/link";
import {
  getReading,
  fmtPct,
  fmtNum,
  regimeLabel,
  ConcentrationReading,
  CrossAssetEntry,
} from "@/lib/insights-api";
import { RegimeLegend } from "./_components/regime-legend";

function LearnLink({ slug, label = "What is this?" }: { slug: string; label?: string }) {
  return (
    <Link
      href={`/insights/learn/${slug}`}
      className="text-xs text-neutral-500 underline-offset-2 hover:underline"
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
  const reading = await getReading(date);
  const { regime, stress, sector_leaderboard_60d, concentration, cross_asset } = reading;

  return (
    <main className="space-y-8">
      {/* ──────────────── HEADLINE ──────────────── */}
      <section>
        <h2 className="text-lg font-semibold">Today&apos;s Pulse</h2>
        <p className="text-sm text-neutral-500">
          As of {new Date(reading.date).toLocaleDateString("en-IN", {
            weekday: "long", year: "numeric", month: "long", day: "numeric",
          })}
        </p>

        <div className="mt-4 grid gap-4 sm:grid-cols-3">
          <Stat
            label="Regime"
            value={regimeLabel(regime.regime)}
            sub={`Day ${regime.persistence_days}`}
            help={
              <div className="flex gap-3">
                <a
                  href="#regime-legend"
                  className="text-xs text-neutral-500 underline-offset-2 hover:underline"
                >
                  What do these mean?
                </a>
                <LearnLink slug="regime" label="Deep-dive →" />
              </div>
            }
          />
          <Stat
            label="Stress"
            value={stress.score.toFixed(0)}
            sub={`/100 · pctile ${stress.score_percentile.toFixed(0)}`}
            help={<LearnLink slug="stress-score" />}
          />
          <Stat
            label="NIFTY 100 vs 100-DMA"
            value={regime.nifty100_above_100dma ? "Above" : "Below"}
            sub={`Breadth ${fmtPct(regime.pct_above_200dma, 0)} above 200-DMA`}
            help={<LearnLink slug="pct-above-200dma" label="What is breadth?" />}
          />
        </div>

        {regime.prev_regime && regime.persistence_days <= 10 && (
          <p className="mt-3 text-sm text-neutral-600">
            Just transitioned from{" "}
            <span className="font-medium">{regimeLabel(regime.prev_regime)}</span>
            {" "}(which lasted {regime.prev_regime_lasted_days} trading days).
          </p>
        )}
      </section>

      {/* ──────────────── CONCENTRATION ──────────────── */}
      <ConcentrationSection concentration={concentration} />

      {/* ──────────────── STRESS COMPONENTS ──────────────── */}
      <section>
        <div className="flex items-baseline justify-between">
          <h3 className="text-base font-semibold">Stress breakdown</h3>
          <LearnLink slug="stress-score" label="How is this computed?" />
        </div>
        <table className="mt-3 w-full text-sm">
          <thead className="border-b text-left text-neutral-500">
            <tr>
              <th className="py-2">Component</th>
              <th className="py-2 text-right">Contribution (0–100)</th>
              <th className="py-2 text-right">Raw</th>
            </tr>
          </thead>
          <tbody>
            <Row label="VIX percentile (252d)"
                 component={stress.vix_pctile_component}
                 raw={`VIX = ${fmtNum(stress.vix_close, 1)}`} />
            <Row label="Nifty drawdown depth"
                 component={stress.drawdown_component}
                 raw={fmtPct(stress.nifty_drawdown_pct, 1, true)} />
            <Row label="% NSE 500 below 200-DMA"
                 component={stress.below_200dma_component}
                 raw={fmtPct(stress.pct_above_200dma ? 1 - stress.pct_above_200dma : null, 0)} />
            <Row label="Cross-sectional dispersion"
                 component={stress.dispersion_component}
                 raw={`z = ${fmtNum(stress.dispersion_z, 2)}`} />
          </tbody>
        </table>
      </section>

      {/* ──────────────── SECTOR LEADERBOARD ──────────────── */}
      <section>
        <div className="flex items-baseline justify-between">
          <h3 className="text-base font-semibold">Sector leaderboard (60-day RS)</h3>
          <div className="flex gap-3">
            <LearnLink slug="sector-rs" label="What is RS?" />
            <LearnLink slug="sector-breadth" label="What is breadth?" />
          </div>
        </div>
        <p className="mt-1 text-xs text-neutral-500">
          Relative strength vs Nifty 50. Right column shows breadth — % of
          sector constituents above their 200-DMA.
        </p>
        <table className="mt-3 w-full text-sm">
          <thead className="border-b text-left text-neutral-500">
            <tr>
              <th className="w-10 py-2">#</th>
              <th className="py-2">Sector</th>
              <th className="py-2 text-right">5d</th>
              <th className="py-2 text-right">20d</th>
              <th className="py-2 text-right">60d</th>
              <th className="py-2 text-right">120d</th>
              <th className="py-2 text-right">Δ rank (1w)</th>
              <th className="py-2 text-right">Breadth</th>
            </tr>
          </thead>
          <tbody>
            {sector_leaderboard_60d.map((s) => (
              <tr key={s.sector} className="border-b last:border-0">
                <td className="py-2 text-neutral-500">{s.rank_60d ?? "—"}</td>
                <td className="py-2 font-medium">
                  {s.sector.replace("NIFTY_", "")}
                </td>
                <td className="py-2 text-right">{fmtPct(s.rs_5d, 1, true)}</td>
                <td className="py-2 text-right">{fmtPct(s.rs_20d, 1, true)}</td>
                <td className="py-2 text-right">{fmtPct(s.rs_60d, 1, true)}</td>
                <td className="py-2 text-right">{fmtPct(s.rs_120d, 1, true)}</td>
                <td className="py-2 text-right">
                  {s.rank_change_wow_60d === null ? "—" :
                   s.rank_change_wow_60d > 0 ? `+${s.rank_change_wow_60d}` :
                   s.rank_change_wow_60d}
                </td>
                <td className="py-2 text-right">{fmtPct(s.pct_above_200dma, 0)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      {/* ──────────────── CROSS-ASSET ──────────────── */}
      <CrossAssetSection cross_asset={cross_asset} />

      {/* ──────────────── REGIME GLOSSARY ──────────────── */}
      <RegimeLegend />
    </main>
  );
}

function Stat({
  label,
  value,
  sub,
  help,
}: {
  label: string;
  value: string;
  sub: string;
  help?: React.ReactNode;
}) {
  return (
    <div className="rounded border p-4">
      <div className="text-xs uppercase tracking-wide text-neutral-500">{label}</div>
      <div className="mt-1 text-2xl font-semibold">{value}</div>
      <div className="mt-1 text-xs text-neutral-500">{sub}</div>
      {help && <div className="mt-2">{help}</div>}
    </div>
  );
}

function ConcentrationSection({ concentration: c }: { concentration: ConcentrationReading }) {
  const indexFlat = c.top_3_share_of_move === null;
  const headline = buildConcentrationHeadline(c);

  return (
    <section>
      <div className="flex items-baseline justify-between">
        <h3 className="text-base font-semibold">Who drove today&apos;s Nifty 50 move</h3>
        <Link
          href="/insights/learn/concentration"
          className="text-xs text-neutral-500 underline-offset-2 hover:underline"
        >
          What is this?
        </Link>
      </div>

      <p className="mt-2 text-sm text-neutral-700 dark:text-neutral-300">
        {headline}
      </p>

      <div className="mt-3 grid gap-3 sm:grid-cols-3">
        <Stat
          label="Nifty 50 (cap-wt)"
          value={fmtPct(c.nifty_return_pct / 100, 2, true)}
          sub={`Equal-weighted: ${fmtPct(c.equal_weighted_return_pct / 100, 2, true)}`}
        />
        <Stat
          label="Cap vs equal spread"
          value={fmtPct(c.cap_vs_equal_spread_pp / 100, 2, true)}
          sub={
            Math.abs(c.cap_vs_equal_spread_pp) > 0.3
              ? c.cap_vs_equal_spread_pp > 0
                ? "Mega-caps led"
                : "Broad participation"
              : "Even tape"
          }
        />
        <Stat
          label="Top-3 share of move"
          value={indexFlat ? "—" : fmtPct(c.top_3_share_of_move, 0)}
          sub={indexFlat ? "Index ~flat today" : c.top_3_symbols.join(" · ")}
        />
      </div>

      {/* Per-constituent contribution table — top 10 by absolute contribution */}
      <details className="mt-4">
        <summary className="cursor-pointer text-xs text-neutral-600 underline-offset-2 hover:underline">
          Show top 10 contributors (by absolute impact on the index)
        </summary>
        <table className="mt-2 w-full text-sm">
          <thead className="border-b text-left text-neutral-500">
            <tr>
              <th className="py-2">Symbol</th>
              <th className="py-2 text-right">Weight</th>
              <th className="py-2 text-right">Stock %</th>
              <th className="py-2 text-right">Contribution (bps)</th>
              <th className="py-2 text-right">Share of move</th>
            </tr>
          </thead>
          <tbody>
            {c.constituents.slice(0, 10).map((row) => (
              <tr key={row.symbol} className="border-b last:border-0">
                <td className="py-2 font-medium">{row.symbol}</td>
                <td className="py-2 text-right">{row.weight.toFixed(2)}%</td>
                <td className="py-2 text-right">
                  {fmtPct(row.return_pct / 100, 2, true)}
                </td>
                <td className="py-2 text-right">
                  {row.contribution_bps >= 0 ? "+" : ""}
                  {row.contribution_bps.toFixed(1)}
                </td>
                <td className="py-2 text-right">
                  {row.share_of_move === null
                    ? "—"
                    : fmtPct(row.share_of_move, 0)}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="mt-2 text-xs text-neutral-500">
          Weights from NSE NIFTY 50 monthly factsheet (current snapshot, not
          historical). Coverage: {c.n_constituents_covered}/{c.n_constituents_total} constituents.
        </p>
      </details>
    </section>
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

  // If top-3 explains > 80% of the move, leadership is narrow
  if (Math.abs(top3) > 0.8) {
    return `Nifty ${moveDir} ${absMove} — but ${top3Pct}% of the move came from just ${c.top_3_symbols.join(", ")}. Narrow tape.`;
  }
  if (Math.abs(top3) > 0.5) {
    return `Nifty ${moveDir} ${absMove}. Top 3 (${c.top_3_symbols.join(", ")}) drove ${top3Pct}% of the move — concentrated but not extreme.`;
  }
  return `Nifty ${moveDir} ${absMove} with broad participation — no single name dominated (top-3 share ${top3Pct}%).`;
}

function CrossAssetSection(
  { cross_asset }: { cross_asset: Record<string, CrossAssetEntry> },
) {
  // Display order: most reader-relevant first
  const order = ["usdinr", "gold", "crude", "india_10y", "us_10y"];
  const available = order
    // eslint-disable-next-line security/detect-object-injection
    .map((k) => cross_asset[k])
    .filter((e): e is CrossAssetEntry => Boolean(e));

  const liveEntries = available.filter((e) => e.data_available);
  const deferredEntries = available.filter((e) => !e.data_available);

  // Notable assets — anything in the top or bottom 5% of its trailing year
  // OR z252 above ±2. These are the conditions that fire commentary
  // spotlights, so flagging them here keeps the dashboard and the notes in
  // visual agreement.
  const notable = liveEntries.filter((e) => {
    const f = e.features;
    const pctileExtreme = f.pctile_252d !== null
      && (f.pctile_252d >= 0.95 || f.pctile_252d <= 0.05);
    const zExtreme = (f.z_252d !== null && Math.abs(f.z_252d) >= 2.0);
    return pctileExtreme || zExtreme;
  });

  return (
    <section>
      <div className="flex items-baseline justify-between">
        <h3 className="text-base font-semibold">Cross-asset context</h3>
        <Link
          href="/insights/learn/glossary#flows-structure"
          className="text-xs text-neutral-500 underline-offset-2 hover:underline"
        >
          What is this?
        </Link>
      </div>
      <p className="mt-1 text-xs text-neutral-500">
        Where four assets that influence Indian equities are sitting today,
        each relative to its own trailing-year range. Reading: z-score
        (today vs the past 252 days), distance from 200-day moving average,
        and percentile within the trailing year.
      </p>

      {notable.length > 0 && (
        <div className="mt-3 rounded border border-amber-200 bg-amber-50 p-3 text-sm dark:border-amber-900 dark:bg-amber-900/20">
          <strong>Notable:</strong>{" "}
          {notable.map((e, i) => (
            <span key={e.asset_id}>
              {i > 0 ? " · " : ""}
              <span className="font-medium">{e.label.split(" (")[0]}</span>{" "}
              {describeExtreme(e)}
            </span>
          ))}
        </div>
      )}

      <table className="mt-3 w-full text-sm">
        <thead className="border-b text-left text-neutral-500">
          <tr>
            <th className="py-2">Asset</th>
            <th className="py-2 text-right">Close</th>
            <th className="py-2 text-right">5d</th>
            <th className="py-2 text-right">20d</th>
            <th className="py-2 text-right">60d</th>
            <th className="py-2 text-right">z (1y)</th>
            <th className="py-2 text-right">vs 200-DMA</th>
            <th className="py-2 text-right">Percentile</th>
          </tr>
        </thead>
        <tbody>
          {liveEntries.map((e) => (
            <tr key={e.asset_id} className="border-b last:border-0">
              <td className="py-2 font-medium">{e.label.split(" (")[0]}</td>
              <td className="py-2 text-right">{fmtNum(e.features.close, 2)}</td>
              <td className="py-2 text-right">
                {fmtPct(e.features.roc_5d, 1, true)}
              </td>
              <td className="py-2 text-right">
                {fmtPct(e.features.roc_20d, 1, true)}
              </td>
              <td className="py-2 text-right">
                {fmtPct(e.features.roc_60d, 1, true)}
              </td>
              <td className="py-2 text-right">
                {e.features.z_252d === null
                  ? "—"
                  : `${e.features.z_252d >= 0 ? "+" : ""}${e.features.z_252d.toFixed(2)}`}
              </td>
              <td className="py-2 text-right">
                {fmtPct(e.features.dist_from_200dma, 1, true)}
              </td>
              <td className="py-2 text-right">
                {e.features.pctile_252d === null
                  ? "—"
                  : `${(e.features.pctile_252d * 100).toFixed(0)}%`}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {deferredEntries.length > 0 && (
        <p className="mt-2 text-xs text-neutral-500">
          Data pending for:{" "}
          {deferredEntries.map((e) => e.label.split(" (")[0]).join(", ")}
        </p>
      )}
    </section>
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
    <tr className="border-b last:border-0">
      <td className="py-2">{label}</td>
      <td className="py-2 text-right">{fmtNum(component, 0)}</td>
      <td className="py-2 text-right text-neutral-500">{raw}</td>
    </tr>
  );
}
