import Link from "next/link";
import { getWatchlists, WatchlistEntry } from "@/lib/insights-api";
import { Pct } from "@/components/insights/ui";

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
  "multi_year_breakouts",
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
    <main className="flex flex-col gap-12">
      <section className="flex flex-col gap-1">
        <h2 className="font-serif text-2xl font-medium tracking-[-0.01em] text-foreground">
          Watchlists
        </h2>
        <p className="max-w-2xl text-[13px] leading-[1.55] text-muted-foreground">
          {date && `As of ${new Date(date).toLocaleDateString("en-IN")}. `}
          Quant-driven daily lists from the NSE 500 panel. Educational context
          only — these are not buy or sell recommendations.
        </p>
      </section>

      {LIST_ORDER.map((listName) => {
        // eslint-disable-next-line security/detect-object-injection
        const entries = lists[listName] ?? [];
        // eslint-disable-next-line security/detect-object-injection
        const meta = LIST_LABELS[listName];
        if (!meta) return null;

        return (
          <section key={listName} className="flex flex-col gap-3">
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <div className="flex flex-wrap items-baseline gap-3">
                <h3 className="font-serif text-lg font-medium tracking-[-0.01em] text-foreground">
                  {meta.title}
                </h3>
                {meta.validityBadge === "validated" && (
                  <span
                    className="rounded-full border border-[color:var(--positive)] px-2 py-0.5 text-[10px] font-medium text-[color:var(--positive)]"
                    title={meta.validityNote}
                  >
                    validity-tested ✓
                  </span>
                )}
                {meta.validityBadge === "names-only" && (
                  <span
                    className="rounded-full border border-[color:var(--warning)] px-2 py-0.5 text-[10px] font-medium text-[color:var(--warning)]"
                    title={meta.validityNote}
                  >
                    names-only · no fwd-return claims
                  </span>
                )}
              </div>
              {meta.learn && (
                <Link
                  href={`/insights/learn/${meta.learn}`}
                  className="text-[13px] text-muted-foreground underline-offset-2 hover:text-foreground hover:underline"
                >
                  What is this?
                </Link>
              )}
            </div>
            <p className="text-[13px] leading-[1.5] text-muted-foreground">{meta.blurb}</p>
            {meta.validityNote && (
              <p className="text-[13px] italic leading-[1.5] text-muted-foreground">
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
      <p className="text-sm text-muted-foreground">No names fit this setup today.</p>
    );
  }

  return (
    <>
    {/* Mobile: stacked rows — symbol + day move, then the note (the point
        of a watchlist) at full width. No horizontal scroll. */}
    <div className="flex flex-col md:hidden">
      {entries.map((e) => (
        <div key={e.symbol} className="border-b border-border py-3 last:border-0">
          <div className="flex items-baseline justify-between gap-3">
            <span className="text-sm font-semibold text-foreground">{e.symbol}</span>
            <span className="tabular-nums text-sm"><Pct v={e.chg_today_pct} decimals={2} /></span>
          </div>
          <div className="mt-0.5 text-xs text-muted-foreground tabular-nums">
            {e.close.toFixed(2)}
            {e.sectors.length > 0 &&
              ` · ${e.sectors.map((x) => x.replace("NIFTY_", "")).join(", ")}`}
          </div>
          <p className="mt-1.5 text-sm leading-[1.5] text-foreground">{e.note}</p>
        </div>
      ))}
    </div>

    <div className="hidden overflow-x-auto md:block">
      <table className="w-full text-sm">
        <thead className="border-b border-border text-left text-muted-foreground">
          <tr>
            <th className="py-2 font-medium">Symbol</th>
            <th className="py-2 text-right font-medium">Close</th>
            <th className="py-2 text-right font-medium">Day %</th>
            <th className="py-2 font-medium">Note</th>
            <th className="py-2 font-medium">Sectors</th>
          </tr>
        </thead>
        <tbody>
          {entries.map((e) => (
            <tr key={e.symbol} className="border-b border-border last:border-0">
              <td className="py-2 font-medium text-foreground">{e.symbol}</td>
              <td className="py-2 text-right tabular-nums text-muted-foreground">{e.close.toFixed(2)}</td>
              <td className="py-2 text-right tabular-nums"><Pct v={e.chg_today_pct} decimals={2} /></td>
              <td className="py-2 text-foreground">{e.note}</td>
              <td className="py-2 text-xs text-muted-foreground">
                {e.sectors.length === 0
                  ? "—"
                  : e.sectors.map((s) => s.replace("NIFTY_", "")).join(", ")}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
    </>
  );
}
