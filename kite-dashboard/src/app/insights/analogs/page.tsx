import { getAnalogs, fmtPct, fmtNum } from "@/lib/insights-api";

export const dynamic = "force-dynamic";
export const revalidate = 900;

const HORIZONS = ["5", "20", "60", "120"];

export default async function AnalogsPage() {
  const { matches, distribution } = await getAnalogs({ k: 20 });

  return (
    <main className="space-y-8">
      <section>
        <h2 className="text-lg font-semibold">Historical Analogs</h2>
        <p className="text-sm text-neutral-500">
          Today&apos;s market reading vs the closest historical days,
          based on a small feature vector (breadth, VIX, drawdown,
          dispersion). For each match, what happened in the days after.
        </p>
      </section>

      {/* ──────────────── DISTRIBUTION SUMMARY ──────────────── */}
      <section>
        <h3 className="text-base font-semibold">
          Forward-return distribution across {matches.length} closest matches
        </h3>
        <table className="mt-3 w-full text-sm">
          <thead className="border-b text-left text-neutral-500">
            <tr>
              <th className="py-2">Horizon</th>
              <th className="py-2 text-right">n</th>
              <th className="py-2 text-right">Median</th>
              <th className="py-2 text-right">Mean</th>
              <th className="py-2 text-right">25–75% range</th>
              <th className="py-2 text-right">5–95% range</th>
            </tr>
          </thead>
          <tbody>
            {HORIZONS.map((h) => {
              // eslint-disable-next-line security/detect-object-injection
              const d = distribution[h];
              if (!d) return null;
              return (
                <tr key={h} className="border-b last:border-0">
                  <td className="py-2">{h}-day forward</td>
                  <td className="py-2 text-right">{d.n_with_forward_return}</td>
                  <td className="py-2 text-right font-medium">{fmtPct(d.median, 2, true)}</td>
                  <td className="py-2 text-right">{fmtPct(d.mean, 2, true)}</td>
                  <td className="py-2 text-right">
                    {fmtPct(d.p25, 1, true)} → {fmtPct(d.p75, 1, true)}
                  </td>
                  <td className="py-2 text-right text-neutral-500">
                    {fmtPct(d.p5, 1, true)} → {fmtPct(d.p95, 1, true)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </section>

      {/* ──────────────── TOP MATCHES ──────────────── */}
      <section>
        <h3 className="text-base font-semibold">Top {matches.length} matches (closest first)</h3>
        <table className="mt-3 w-full text-sm">
          <thead className="border-b text-left text-neutral-500">
            <tr>
              <th className="py-2">Match date</th>
              <th className="py-2 text-right">Distance</th>
              <th className="py-2 text-right">VIX</th>
              <th className="py-2 text-right">Pct ≥ 200-DMA</th>
              <th className="py-2 text-right">Nifty DD</th>
              <th className="py-2 text-right">Fwd 5d</th>
              <th className="py-2 text-right">Fwd 20d</th>
              <th className="py-2 text-right">Fwd 60d</th>
              <th className="py-2 text-right">Fwd 120d</th>
            </tr>
          </thead>
          <tbody>
            {matches.map((m) => (
              <tr key={m.match_date} className="border-b last:border-0">
                <td className="py-2">
                  {new Date(m.match_date).toLocaleDateString("en-IN", {
                    year: "numeric", month: "short", day: "numeric",
                  })}
                </td>
                <td className="py-2 text-right">{fmtNum(m.distance, 2)}</td>
                <td className="py-2 text-right">{fmtNum(m.vix_close, 1)}</td>
                <td className="py-2 text-right">{fmtPct(m.pct_above_200dma, 0)}</td>
                <td className="py-2 text-right">{fmtPct(m.nifty_drawdown_pct, 1, true)}</td>
                <td className="py-2 text-right">{fmtPct(m.fwd_return_5d, 1, true)}</td>
                <td className="py-2 text-right">{fmtPct(m.fwd_return_20d, 1, true)}</td>
                <td className="py-2 text-right">{fmtPct(m.fwd_return_60d, 1, true)}</td>
                <td className="py-2 text-right">{fmtPct(m.fwd_return_120d, 1, true)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </main>
  );
}
