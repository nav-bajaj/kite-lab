import Link from "next/link";
import {
  getSectors,
  getSubgroups,
  fmtPct,
  type SubgroupSnapshot,
  type SubgroupSpread,
} from "@/lib/insights-api";
import { Section, Pct, SectorBars } from "@/components/insights/ui";

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

/** Colored percentage-point value (e.g. sibling spreads), green up / red down. */
function Pp({ v }: { v: number | null }) {
  if (v === null) return <span className="text-muted-foreground">—</span>;
  const tone =
    v > 0
      ? "text-[color:var(--positive)]"
      : v < 0
        ? "text-[color:var(--negative)]"
        : "text-muted-foreground";
  return <span className={tone}>{`${v >= 0 ? "+" : ""}${v.toFixed(1)}pp`}</span>;
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
    <main className="flex flex-col gap-12">
      <section className="flex flex-col gap-1">
        <h2 className="text-2xl font-semibold tracking-[-0.01em] text-foreground">
          Sectors
        </h2>
        <p className="max-w-2xl text-[13px] leading-[1.55] text-muted-foreground">
          {date && `As of ${new Date(date).toLocaleDateString("en-IN")}. `}
          Sector-index relative strength vs Nifty 50, plus constituent-level
          breadth so you can see whether a sector&apos;s rally is broad or narrow.
        </p>
      </section>

      {/* ──────────────── RS LEADERBOARD ──────────────── */}
      <Section title="RS leaderboard" help={<LearnLink slug="sector-rs" label="What is RS?" />}>
        <SectorBars sectors={leaderboard_60d} limit={leaderboard_60d.length} />
        <details className="mt-2">
          <summary className="cursor-pointer text-[13px] text-muted-foreground underline-offset-2 hover:text-foreground hover:underline">
            Full table — close, day %, and every RS horizon
          </summary>
          {/* Mobile: one stacked row per sector — rank + day move on top,
              every RS horizon in a labeled mini-grid (no horizontal scroll). */}
          <div className="mt-3 flex flex-col md:hidden">
            {leaderboard_60d.map((s) => (
              <div key={s.sector} className="border-b border-border py-3 last:border-0">
                <div className="flex items-baseline justify-between gap-3">
                  <span className="text-sm font-semibold text-foreground">
                    <span className="mr-1.5 text-muted-foreground">
                      {s.rank_60d ? `#${s.rank_60d}` : "—"}
                    </span>
                    {s.sector.replace("NIFTY_", "")}
                  </span>
                  <span className="tabular-nums text-sm">
                    <Pct v={s.sector_chg_today_pct} decimals={2} />
                  </span>
                </div>
                <dl className="mt-2 grid grid-cols-3 gap-x-4 gap-y-1.5 text-[13px] tabular-nums">
                  {(
                    [
                      ["5d", s.rs_5d],
                      ["20d", s.rs_20d],
                      ["60d", s.rs_60d],
                      ["120d", s.rs_120d],
                      ["252d", s.rs_252d],
                    ] as const
                  ).map(([label, v]) => (
                    <div key={label}>
                      <dt className="text-[10.5px] uppercase tracking-[0.08em] text-muted-foreground">
                        {label}
                      </dt>
                      <dd><Pct v={v} /></dd>
                    </div>
                  ))}
                  <div>
                    <dt className="text-[10.5px] uppercase tracking-[0.08em] text-muted-foreground">
                      Δ wow
                    </dt>
                    <dd className="text-muted-foreground">
                      {s.rank_change_wow_60d === null
                        ? "—"
                        : s.rank_change_wow_60d > 0
                          ? `+${s.rank_change_wow_60d}`
                          : s.rank_change_wow_60d}
                    </dd>
                  </div>
                </dl>
              </div>
            ))}
          </div>

          <div className="mt-3 hidden overflow-x-auto md:block">
            <table className="w-full text-sm">
              <thead className="border-b border-border text-left text-muted-foreground">
                <tr>
                  <th className="w-10 py-2 font-medium">#</th>
                  <th className="py-2 font-medium">Sector</th>
                  <th className="py-2 text-right font-medium">Close</th>
                  <th className="py-2 text-right font-medium">Day %</th>
                  <th className="py-2 text-right font-medium">5d</th>
                  <th className="py-2 text-right font-medium">20d</th>
                  <th className="py-2 text-right font-medium">60d</th>
                  <th className="py-2 text-right font-medium">120d</th>
                  <th className="py-2 text-right font-medium">252d</th>
                  <th className="py-2 text-right font-medium">Δ wow</th>
                </tr>
              </thead>
              <tbody>
                {leaderboard_60d.map((s) => (
                  <tr key={s.sector} className="border-b border-border last:border-0">
                    <td className="py-2 text-muted-foreground">{s.rank_60d ?? "—"}</td>
                    <td className="py-2 font-medium text-foreground">{s.sector.replace("NIFTY_", "")}</td>
                    <td className="py-2 text-right tabular-nums text-muted-foreground">
                      {s.sector_close ? s.sector_close.toFixed(0) : "—"}
                    </td>
                    <td className="py-2 text-right tabular-nums"><Pct v={s.sector_chg_today_pct} decimals={2} /></td>
                    <td className="py-2 text-right tabular-nums"><Pct v={s.rs_5d} /></td>
                    <td className="py-2 text-right tabular-nums"><Pct v={s.rs_20d} /></td>
                    <td className="py-2 text-right tabular-nums"><Pct v={s.rs_60d} /></td>
                    <td className="py-2 text-right tabular-nums"><Pct v={s.rs_120d} /></td>
                    <td className="py-2 text-right tabular-nums"><Pct v={s.rs_252d} /></td>
                    <td className="py-2 text-right tabular-nums text-muted-foreground">
                      {s.rank_change_wow_60d === null
                        ? "—"
                        : s.rank_change_wow_60d > 0
                          ? `+${s.rank_change_wow_60d}`
                          : s.rank_change_wow_60d}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </details>
      </Section>

      {/* ──────────────── CONSTITUENT-LEVEL BREADTH ──────────────── */}
      <Section
        title="Constituent-level breadth"
        help={<LearnLink slug="sector-breadth" label="Why constituent-level?" />}
      >
        <p className="-mt-2 text-[13px] leading-[1.5] text-muted-foreground">
          How broad is each sector&apos;s rally? % of the sector&apos;s
          constituent stocks above key moving averages, plus the top and bottom
          3 names by 6-month relative strength.
        </p>
        <div className="flex flex-col gap-4">
          {Object.values(sector_breadth)
            .sort((a, b) => (b.pct_above_200dma ?? 0) - (a.pct_above_200dma ?? 0))
            .map((sb) => (
              <div key={sb.sector} className="rounded-xl border border-border bg-card p-5">
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <h4 className="text-sm font-semibold text-foreground">
                    {sb.sector.replace("NIFTY_", "")}
                    {sb.is_partial_coverage && (
                      <span className="ml-2 rounded-full border border-[color:var(--warning)] px-2 py-0.5 text-[11px] font-medium text-[color:var(--warning)]">
                        partial coverage
                      </span>
                    )}
                  </h4>
                  <div className="text-xs text-muted-foreground">
                    {sb.n_covered}/{sb.n_constituents} tracked
                    {" · "}
                    {sb.n_advancing} up / {sb.n_declining} down today
                  </div>
                </div>

                <dl className="mt-4 grid grid-cols-2 gap-x-6 gap-y-2 text-sm sm:grid-cols-4">
                  {[
                    ["% above 50-DMA", fmtPct(sb.pct_above_50dma, 0), false],
                    ["% above 100-DMA", fmtPct(sb.pct_above_100dma, 0), false],
                    ["% above 200-DMA", fmtPct(sb.pct_above_200dma, 0), true],
                  ].map(([label, val, strong]) => (
                    <div key={label as string}>
                      <dt className="text-xs text-muted-foreground">{label}</dt>
                      <dd className={strong ? "font-medium text-foreground" : "text-foreground"}>{val}</dd>
                    </div>
                  ))}
                  <div>
                    <dt className="text-xs text-muted-foreground">Median 20d return</dt>
                    <dd className="tabular-nums"><Pct v={sb.median_ret_20d} /></dd>
                  </div>
                </dl>

                <div className="mt-4 grid grid-cols-1 gap-3 text-xs sm:grid-cols-2">
                  <div>
                    <div className="text-muted-foreground">Leaders (6m RS vs Nifty)</div>
                    <div className="mt-1 text-foreground">
                      {sb.rs_leaders.length === 0
                        ? "—"
                        : sb.rs_leaders.map(([sym, rs]) => (
                            <span key={sym} className="mr-3">
                              <span className="font-medium">{sym}</span>{" "}
                              <Pct v={rs} decimals={0} />
                            </span>
                          ))}
                    </div>
                  </div>
                  <div>
                    <div className="text-muted-foreground">Laggards (6m RS vs Nifty)</div>
                    <div className="mt-1 text-foreground">
                      {sb.rs_laggards.length === 0
                        ? "—"
                        : sb.rs_laggards.map(([sym, rs]) => (
                            <span key={sym} className="mr-3">
                              <span className="font-medium">{sym}</span>{" "}
                              <Pct v={rs} decimals={0} />
                            </span>
                          ))}
                    </div>
                  </div>
                </div>
              </div>
            ))}
        </div>
      </Section>

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
  const byParent = new Map<string, SubgroupSnapshot[]>();
  for (const s of Object.values(subgroups)) {
    const arr = byParent.get(s.parent_sector) ?? [];
    arr.push(s);
    byParent.set(s.parent_sector, arr);
  }

  const sortedSpreads = [...spreads].sort(
    (a, b) => Math.abs(b.spread_60d_pp ?? 0) - Math.abs(a.spread_60d_pp ?? 0),
  );

  return (
    <Section title="Subgroup tracker — within-sector splits">
      <p className="-mt-2 text-[13px] leading-[1.5] text-muted-foreground">
        Hand-curated subgroups inside the parent sector indices: PSU vs private
        banks, large- vs mid-cap pharma, auto OEMs vs ancillaries, etc. Captures
        divergences the sector headlines hide.
      </p>

      <div className="flex flex-col gap-2">
        <h4 className="text-sm font-semibold text-foreground">Sibling spreads (60-day RS)</h4>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="border-b border-border text-left text-muted-foreground">
              <tr>
                <th className="py-2 font-medium">Pair</th>
                <th className="py-2 text-right font-medium">Spread (pp)</th>
              </tr>
            </thead>
            <tbody>
              {sortedSpreads.map((sp) => (
                <tr key={sp.label} className="border-b border-border last:border-0">
                  <td className="py-2 text-foreground">{sp.label}</td>
                  <td className="py-2 text-right tabular-nums"><Pp v={sp.spread_60d_pp} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="flex flex-col gap-6">
        {[...byParent.entries()].map(([parent, groups]) => (
          <div key={parent} className="flex flex-col gap-2">
            <h4 className="text-sm font-semibold text-foreground">{parent.replace("NIFTY_", "")}</h4>
            {/* Mobile: stacked subgroup rows with labeled mini-grid */}
            <div className="flex flex-col md:hidden">
              {groups.map((g) => (
                <div key={g.subgroup} className="border-b border-border py-3 last:border-0">
                  <div className="flex items-baseline justify-between gap-3">
                    <span className="text-sm font-medium text-foreground">{g.label}</span>
                    <span className="tabular-nums text-sm">
                      <Pct v={g.today_chg_pct} decimals={2} />
                    </span>
                  </div>
                  <dl className="mt-2 grid grid-cols-3 gap-x-4 gap-y-1.5 text-[13px] tabular-nums">
                    {(
                      [
                        ["5d", g.rs_5d],
                        ["20d", g.rs_20d],
                        ["60d", g.rs_60d],
                        ["Δ wow", g.rs_60d_wow_delta],
                      ] as const
                    ).map(([label, v]) => (
                      <div key={label}>
                        <dt className="text-[10.5px] uppercase tracking-[0.08em] text-muted-foreground">
                          {label}
                        </dt>
                        <dd><Pct v={v} /></dd>
                      </div>
                    ))}
                    <div>
                      <dt className="text-[10.5px] uppercase tracking-[0.08em] text-muted-foreground">
                        &gt; 200-DMA
                      </dt>
                      <dd className="text-muted-foreground">{fmtPct(g.pct_above_200dma, 0)}</dd>
                    </div>
                    <div>
                      <dt className="text-[10.5px] uppercase tracking-[0.08em] text-muted-foreground">
                        Tracked
                      </dt>
                      <dd className="text-muted-foreground">{g.n_covered}/{g.n_total}</dd>
                    </div>
                  </dl>
                </div>
              ))}
            </div>

            <div className="hidden overflow-x-auto md:block">
              <table className="w-full text-sm">
                <thead className="border-b border-border text-left text-muted-foreground">
                  <tr>
                    <th className="py-2 font-medium">Subgroup</th>
                    <th className="py-2 text-right font-medium">N</th>
                    <th className="py-2 text-right font-medium">Today</th>
                    <th className="py-2 text-right font-medium">5d</th>
                    <th className="py-2 text-right font-medium">20d</th>
                    <th className="py-2 text-right font-medium">60d</th>
                    <th className="py-2 text-right font-medium">Δ WoW</th>
                    <th className="py-2 text-right font-medium">% &gt; 200-DMA</th>
                  </tr>
                </thead>
                <tbody>
                  {groups.map((g) => (
                    <tr key={g.subgroup} className="border-b border-border last:border-0">
                      <td className="py-2 text-foreground">{g.label}</td>
                      <td className="py-2 text-right tabular-nums text-muted-foreground">{g.n_covered}/{g.n_total}</td>
                      <td className="py-2 text-right tabular-nums"><Pct v={g.today_chg_pct} decimals={2} /></td>
                      <td className="py-2 text-right tabular-nums"><Pct v={g.rs_5d} /></td>
                      <td className="py-2 text-right tabular-nums"><Pct v={g.rs_20d} /></td>
                      <td className="py-2 text-right tabular-nums"><Pct v={g.rs_60d} /></td>
                      <td className="py-2 text-right tabular-nums"><Pct v={g.rs_60d_wow_delta} /></td>
                      <td className="py-2 text-right tabular-nums text-muted-foreground">{fmtPct(g.pct_above_200dma, 0)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ))}
      </div>
    </Section>
  );
}
