import { getReading, fmtPct, fmtNum, regimeLabel } from "@/lib/insights-api";

export const dynamic = "force-dynamic"; // always fetch latest reading
export const revalidate = 900;

export default async function PulsePage() {
  const reading = await getReading();
  const { regime, stress, sector_leaderboard_60d } = reading;

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
          <Stat label="Regime" value={regimeLabel(regime.regime)}
                sub={`Day ${regime.persistence_days}`} />
          <Stat label="Stress" value={stress.score.toFixed(0)}
                sub={`/100 · pctile ${stress.score_percentile.toFixed(0)}`} />
          <Stat label="NIFTY 100 vs 100-DMA"
                value={regime.nifty100_above_100dma ? "Above" : "Below"}
                sub={`Breadth ${fmtPct(regime.pct_above_200dma, 0)} above 200-DMA`} />
        </div>

        {regime.prev_regime && regime.persistence_days <= 10 && (
          <p className="mt-3 text-sm text-neutral-600">
            Just transitioned from{" "}
            <span className="font-medium">{regimeLabel(regime.prev_regime)}</span>
            {" "}(which lasted {regime.prev_regime_lasted_days} trading days).
          </p>
        )}
      </section>

      {/* ──────────────── STRESS COMPONENTS ──────────────── */}
      <section>
        <h3 className="text-base font-semibold">Stress breakdown</h3>
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
        <h3 className="text-base font-semibold">Sector leaderboard (60-day RS)</h3>
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
    </main>
  );
}

function Stat({ label, value, sub }: { label: string; value: string; sub: string }) {
  return (
    <div className="rounded border p-4">
      <div className="text-xs uppercase tracking-wide text-neutral-500">{label}</div>
      <div className="mt-1 text-2xl font-semibold">{value}</div>
      <div className="mt-1 text-xs text-neutral-500">{sub}</div>
    </div>
  );
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
