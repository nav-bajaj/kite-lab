import Link from "next/link";
import { getWatchlists, fmtPct, WatchlistEntry } from "@/lib/insights-api";

export const dynamic = "force-dynamic";
export const revalidate = 900;

interface PageProps {
  searchParams: Promise<{ date?: string }>;
}

const LIST_LABELS: Record<
  string,
  {
    title: string;
    blurb: string;
    learn?: string;
    /** Set when the pattern passed its validity study and we publish
     * forward-return narrative confidently. */
    validityBadge?: "validated" | "names-only";
    validityNote?: string;
  }
> = {
  breakouts: {
    title: "Breakouts",
    blurb: "Stocks closing above their trailing 20-day high AND above their 50-DMA.",
    learn: "breakout",
  },
  rs_leaders: {
    title: "RS Leaders",
    blurb: "Top NSE 500 names by 126-day return vs Nifty 50.",
    learn: "rs-leader",
  },
  coiled_springs: {
    title: "Coiled Springs",
    blurb: "Tight consolidations: above 50+200 DMA with 20-day volatility in the stock's own bottom quartile.",
    learn: "coiled-spring",
  },
  multi_year_breakouts: {
    title: "Multi-year breakouts",
    blurb: "Close today above the highest close of the prior 5 years AND above the 50-DMA. The 'no overhead supply for years' setup.",
    learn: "breakout",
    validityBadge: "validated",
    validityNote: "Validity-tested: top-25 firings historically beat NSE 500 baseline by +1.4pp at 20d and +6.0pp at 120d in our 14-year sample.",
  },
  sustained_uptrend: {
    title: "Sustained uptrend",
    blurb: "Trailing 1-year return ≥ +20% with max drawdown ≤ 8% over the last 60 days. Stocks in clean, persistent uptrends.",
    learn: "sustained-uptrend",
    validityBadge: "names-only",
    validityNote: "Validity-tested: positive direction lift at all horizons (+4.9pp at 20d, +6.3pp at 120d) but baseline-excess is modest. Published as a names list without forward-return claims.",
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
  "breakouts",
  "multi_year_breakouts",  // validated — sits next to its sibling
  "rs_leaders",
  "coiled_springs",
  "sustained_uptrend",
  "stretched",
  "recent_breakdowns",
];

export default async function WatchlistsPage({ searchParams }: PageProps) {
  const { date: dateParam } = await searchParams;
  const { date, lists } = await getWatchlists({ date: dateParam, limit: 25 });

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
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <div className="flex flex-wrap items-baseline gap-2">
                <h3 className="text-base font-semibold">{meta.title}</h3>
                {meta.validityBadge === "validated" && (
                  <span
                    className="rounded bg-emerald-100 px-1.5 py-0.5 text-[10px] font-medium text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-200"
                    title={meta.validityNote}
                  >
                    validity-tested ✓
                  </span>
                )}
                {meta.validityBadge === "names-only" && (
                  <span
                    className="rounded bg-amber-100 px-1.5 py-0.5 text-[10px] font-medium text-amber-800 dark:bg-amber-900/40 dark:text-amber-200"
                    title={meta.validityNote}
                  >
                    names-only · no fwd-return claims
                  </span>
                )}
              </div>
              {meta.learn && (
                <Link
                  href={`/insights/learn/${meta.learn}`}
                  className="text-xs text-neutral-500 underline-offset-2 hover:underline"
                >
                  What is this?
                </Link>
              )}
            </div>
            <p className="mt-1 text-xs text-neutral-500">{meta.blurb}</p>
            {meta.validityNote && (
              <p className="mt-1 text-xs italic text-neutral-500">
                {meta.validityNote}
              </p>
            )}
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
