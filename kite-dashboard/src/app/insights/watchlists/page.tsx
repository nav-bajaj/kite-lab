import { getWatchlists, fmtPct, WatchlistEntry } from "@/lib/insights-api";

export const dynamic = "force-dynamic";
export const revalidate = 900;

const LIST_LABELS: Record<string, { title: string; blurb: string }> = {
  breakouts: {
    title: "Breakouts",
    blurb: "Stocks closing above their trailing 20-day high AND above their 50-DMA.",
  },
  rs_leaders: {
    title: "RS Leaders",
    blurb: "Top NSE 500 names by 126-day return vs Nifty 50.",
  },
  coiled_springs: {
    title: "Coiled Springs",
    blurb: "Tight consolidations: above 50+200 DMA with 20-day volatility in the stock's own bottom quartile.",
  },
  stretched: {
    title: "Stretched",
    blurb: "Names trading > 20% above their 200-DMA — historically a mean-reversion zone.",
  },
  recent_breakdowns: {
    title: "Recent Breakdowns",
    blurb: "Stocks that just crossed below their 50-DMA in the last 5 sessions.",
  },
};

const LIST_ORDER = [
  "breakouts", "rs_leaders", "coiled_springs", "stretched", "recent_breakdowns",
];

export default async function WatchlistsPage() {
  const { date, lists } = await getWatchlists({ limit: 25 });

  return (
    <main className="space-y-8">
      <section>
        <h2 className="text-lg font-semibold">Watchlists</h2>
        <p className="text-sm text-neutral-500">
          {date && `As of ${new Date(date).toLocaleDateString("en-IN")}.`}{" "}
          Quant-driven daily lists from the NSE 500 panel. Educational
          context only — these are not buy or sell recommendations.
        </p>
      </section>

      {LIST_ORDER.map((listName) => {
        // eslint-disable-next-line security/detect-object-injection
        const entries = lists[listName] ?? [];
        // eslint-disable-next-line security/detect-object-injection
        const meta = LIST_LABELS[listName];
        if (!meta) return null;

        return (
          <section key={listName}>
            <h3 className="text-base font-semibold">{meta.title}</h3>
            <p className="mt-1 text-xs text-neutral-500">{meta.blurb}</p>
            <WatchlistTable entries={entries} />
          </section>
        );
      })}
    </main>
  );
}

function WatchlistTable({ entries }: { entries: WatchlistEntry[] }) {
  if (entries.length === 0) {
    return (
      <p className="mt-3 text-sm text-neutral-500">
        No names fit this setup today.
      </p>
    );
  }

  return (
    <table className="mt-3 w-full text-sm">
      <thead className="border-b text-left text-neutral-500">
        <tr>
          <th className="py-2">Symbol</th>
          <th className="py-2 text-right">Close</th>
          <th className="py-2 text-right">Day %</th>
          <th className="py-2">Note</th>
          <th className="py-2">Sectors</th>
        </tr>
      </thead>
      <tbody>
        {entries.map((e) => (
          <tr key={e.symbol} className="border-b last:border-0">
            <td className="py-2 font-medium">{e.symbol}</td>
            <td className="py-2 text-right">{e.close.toFixed(2)}</td>
            <td className="py-2 text-right">{fmtPct(e.chg_today_pct, 2, true)}</td>
            <td className="py-2 text-neutral-600">{e.note}</td>
            <td className="py-2 text-xs text-neutral-500">
              {e.sectors.length === 0
                ? "—"
                : e.sectors.map((s) => s.replace("NIFTY_", "")).join(", ")}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
