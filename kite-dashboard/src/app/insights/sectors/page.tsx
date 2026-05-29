import Link from "next/link";
import {
  getSectors,
  getSubgroups,
  fmtPct,
  type SubgroupSnapshot,
  type SubgroupSpread,
} from "@/lib/insights-api";

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

export const dynamic = "force-dynamic";
export const revalidate = 900;

export default async function SectorsPage({
  searchParams,
}: {
  searchParams: Promise<{ date?: string }>;
}) {
  const params = await searchParams;
  const [{ date, leaderboard_60d, sector_breadth }, subgroupData] = await Promise.all([
    getSectors(params.date),
    getSubgroups(params.date),
  ]);

  return (
    <main className="space-y-8">
      <section>
        <h2 className="text-lg font-semibold">Sectors</h2>
        <p className="text-sm text-neutral-500">
          {date && `As of ${new Date(date).toLocaleDateString("en-IN")}.`}{" "}
          Sector-index RS (relative strength vs Nifty 50) plus
          constituent-level breadth so you can see whether a sector&apos;s
          rally is broad or narrow.
        </p>
      </section>

      {/* ──────────────── RS LEADERBOARD ──────────────── */}
      <section>
        <div className="flex items-baseline justify-between">
          <h3 className="text-base font-semibold">RS leaderboard</h3>
          <LearnLink slug="sector-rs" label="What is RS?" />
        </div>
        <table className="mt-3 w-full text-sm">
          <thead className="border-b text-left text-neutral-500">
            <tr>
              <th className="w-10 py-2">#</th>
              <th className="py-2">Sector</th>
              <th className="py-2 text-right">Close</th>
              <th className="py-2 text-right">Day %</th>
              <th className="py-2 text-right">5d RS</th>
              <th className="py-2 text-right">20d RS</th>
              <th className="py-2 text-right">60d RS</th>
              <th className="py-2 text-right">120d RS</th>
              <th className="py-2 text-right">252d RS</th>
              <th className="py-2 text-right">Δ wow (60d)</th>
            </tr>
          </thead>
          <tbody>
            {leaderboard_60d.map((s) => (
              <tr key={s.sector} className="border-b last:border-0">
                <td className="py-2 text-neutral-500">{s.rank_60d ?? "—"}</td>
                <td className="py-2 font-medium">{s.sector.replace("NIFTY_", "")}</td>
                <td className="py-2 text-right">
                  {s.sector_close ? s.sector_close.toFixed(0) : "—"}
                </td>
                <td className="py-2 text-right">{fmtPct(s.sector_chg_today_pct, 2, true)}</td>
                <td className="py-2 text-right">{fmtPct(s.rs_5d, 1, true)}</td>
                <td className="py-2 text-right">{fmtPct(s.rs_20d, 1, true)}</td>
                <td className="py-2 text-right">{fmtPct(s.rs_60d, 1, true)}</td>
                <td className="py-2 text-right">{fmtPct(s.rs_120d, 1, true)}</td>
                <td className="py-2 text-right">{fmtPct(s.rs_252d, 1, true)}</td>
                <td className="py-2 text-right">
                  {s.rank_change_wow_60d === null ? "—" :
                   s.rank_change_wow_60d > 0 ? `+${s.rank_change_wow_60d}` :
                   s.rank_change_wow_60d}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      {/* ──────────────── CONSTITUENT-LEVEL BREADTH ──────────────── */}
      <section>
        <div className="flex items-baseline justify-between">
          <h3 className="text-base font-semibold">Constituent-level breadth</h3>
          <LearnLink slug="sector-breadth" label="Why constituent-level?" />
        </div>
        <p className="mt-1 text-xs text-neutral-500">
          How broad is each sector&apos;s rally? % of the sector&apos;s
          constituent stocks above key moving averages, plus the top and
          bottom 3 names by 6-month relative strength.
        </p>

        <div className="mt-4 space-y-6">
          {Object.values(sector_breadth)
            .sort((a, b) =>
              (b.pct_above_200dma ?? 0) - (a.pct_above_200dma ?? 0))
            .map((sb) => (
              <div key={sb.sector} className="rounded border p-4">
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <h4 className="text-sm font-semibold">
                    {sb.sector.replace("NIFTY_", "")}
                    {sb.is_partial_coverage && (
                      <span className="ml-2 rounded bg-amber-100 px-1 py-0.5 text-xs text-amber-800">
                        partial coverage
                      </span>
                    )}
                  </h4>
                  <div className="text-xs text-neutral-500">
                    {sb.n_covered}/{sb.n_constituents} constituents tracked
                    {" · "}{sb.n_advancing} up / {sb.n_declining} down today
                  </div>
                </div>

                <dl className="mt-3 grid grid-cols-2 gap-x-6 gap-y-1 text-sm sm:grid-cols-4">
                  <div>
                    <dt className="text-xs text-neutral-500">% above 50-DMA</dt>
                    <dd>{fmtPct(sb.pct_above_50dma, 0)}</dd>
                  </div>
                  <div>
                    <dt className="text-xs text-neutral-500">% above 100-DMA</dt>
                    <dd>{fmtPct(sb.pct_above_100dma, 0)}</dd>
                  </div>
                  <div>
                    <dt className="text-xs text-neutral-500">% above 200-DMA</dt>
                    <dd className="font-medium">{fmtPct(sb.pct_above_200dma, 0)}</dd>
                  </div>
                  <div>
                    <dt className="text-xs text-neutral-500">Median 20d return</dt>
                    <dd>{fmtPct(sb.median_ret_20d, 1, true)}</dd>
                  </div>
                </dl>

                <div className="mt-3 grid grid-cols-1 gap-2 text-xs sm:grid-cols-2">
                  <div>
                    <div className="text-neutral-500">Leaders (6m RS vs Nifty)</div>
                    <div className="mt-1">
                      {sb.rs_leaders.length === 0 ? "—" :
                        sb.rs_leaders.map(([sym, rs]) => (
                          <span key={sym} className="mr-3">
                            <span className="font-medium">{sym}</span>{" "}
                            <span className="text-emerald-700">{fmtPct(rs, 0, true)}</span>
                          </span>
                        ))}
                    </div>
                  </div>
                  <div>
                    <div className="text-neutral-500">Laggards (6m RS vs Nifty)</div>
                    <div className="mt-1">
                      {sb.rs_laggards.length === 0 ? "—" :
                        sb.rs_laggards.map(([sym, rs]) => (
                          <span key={sym} className="mr-3">
                            <span className="font-medium">{sym}</span>{" "}
                            <span className="text-red-700">{fmtPct(rs, 0, true)}</span>
                          </span>
                        ))}
                    </div>
                  </div>
                </div>
              </div>
            ))}
        </div>
      </section>

      {/* ──────────────── SUBGROUP TRACKER ──────────────── */}
      <SubgroupSection
        subgroups={subgroupData.subgroups}
        spreads={subgroupData.sibling_spreads}
      />
    </main>
  );
}

function SubgroupSection({
  subgroups,
  spreads,
}: {
  subgroups: Record<string, SubgroupSnapshot>;
  spreads: SubgroupSpread[];
}) {
  // Group subgroups by parent sector for the table render
  const byParent = Object.values(subgroups).reduce<
    Record<string, SubgroupSnapshot[]>
  >((acc, s) => {
    (acc[s.parent_sector] ||= []).push(s);
    return acc;
  }, {});

  // Sort spreads by absolute magnitude — biggest divergences first
  const sortedSpreads = [...spreads].sort(
    (a, b) => Math.abs(b.spread_60d_pp ?? 0) - Math.abs(a.spread_60d_pp ?? 0),
  );

  return (
    <section>
      <div className="flex items-baseline justify-between">
        <h3 className="text-base font-semibold">
          Subgroup tracker — within-sector splits
        </h3>
      </div>
      <p className="mt-1 text-xs text-neutral-500">
        Hand-curated subgroups inside the parent sector indices: PSU vs private
        banks, large- vs mid-cap pharma, auto OEMs vs ancillaries, etc.
        Captures divergences that the sector headlines hide.
      </p>

      {/* Sibling spread leaderboard */}
      <div className="mt-4">
        <h4 className="text-sm font-semibold">
          Sibling spreads (60-day RS)
        </h4>
        <table className="mt-2 w-full text-sm">
          <thead className="border-b text-left text-neutral-500">
            <tr>
              <th className="py-2">Pair</th>
              <th className="py-2 text-right">Spread (pp)</th>
            </tr>
          </thead>
          <tbody>
            {sortedSpreads.map((sp) => {
              const v = sp.spread_60d_pp;
              const cls =
                v === null ? "" : v > 0 ? "text-emerald-700" : "text-red-700";
              return (
                <tr key={sp.label} className="border-b last:border-0">
                  <td className="py-2">{sp.label}</td>
                  <td className={`py-2 text-right ${cls}`}>
                    {v === null ? "—" : `${v >= 0 ? "+" : ""}${v.toFixed(1)}pp`}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Per-subgroup detail, grouped by parent sector */}
      <div className="mt-6 space-y-4">
        {Object.entries(byParent).map(([parent, groups]) => (
          <div key={parent}>
            <h4 className="text-sm font-semibold">
              {parent.replace("NIFTY_", "")}
            </h4>
            <table className="mt-2 w-full text-sm">
              <thead className="border-b text-left text-neutral-500">
                <tr>
                  <th className="py-2">Subgroup</th>
                  <th className="py-2 text-right">N</th>
                  <th className="py-2 text-right">Today</th>
                  <th className="py-2 text-right">5d RS</th>
                  <th className="py-2 text-right">20d RS</th>
                  <th className="py-2 text-right">60d RS</th>
                  <th className="py-2 text-right">Δ WoW</th>
                  <th className="py-2 text-right">% above 200-DMA</th>
                </tr>
              </thead>
              <tbody>
                {groups.map((g) => (
                  <tr key={g.subgroup} className="border-b last:border-0">
                    <td className="py-2">{g.label}</td>
                    <td className="py-2 text-right text-neutral-500">
                      {g.n_covered}/{g.n_total}
                    </td>
                    <td className="py-2 text-right">
                      {fmtPct(g.today_chg_pct, 2, true)}
                    </td>
                    <td className="py-2 text-right">{fmtPct(g.rs_5d, 1, true)}</td>
                    <td className="py-2 text-right">{fmtPct(g.rs_20d, 1, true)}</td>
                    <td className="py-2 text-right">{fmtPct(g.rs_60d, 1, true)}</td>
                    <td className="py-2 text-right">
                      {fmtPct(g.rs_60d_wow_delta, 1, true)}
                    </td>
                    <td className="py-2 text-right">
                      {fmtPct(g.pct_above_200dma, 0)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ))}
      </div>
    </section>
  );
}
