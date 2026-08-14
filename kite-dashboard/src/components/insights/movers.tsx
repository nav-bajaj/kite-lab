import Link from "next/link";
import { type MoversResponse } from "@/lib/insights-api";
import { Section } from "@/components/insights/ui";

/**
 * Stock movers block — fresh 1-year highs/lows and the biggest RS-rank
 * climbers. Lives on the Stock Lists surface (founder call, 2026-08-14:
 * name-level lists belong with the lists, not on Market Pulse).
 */
export function StockMoversSection({
  movers,
  dateQuery,
}: {
  movers: MoversResponse;
  dateQuery: string;
}) {
  const { fresh_highs, fresh_lows, rs_improvers } = movers;
  return (
    <Section
      title="Movers today"
      help={
        <Link
          href={`/insights/screener${dateQuery}`}
          className="text-[13px] text-muted-foreground underline-offset-2 hover:text-foreground hover:underline"
        >
          Open screener →
        </Link>
      }
    >
      <p className="-mt-2 text-[13px] text-muted-foreground">
        Individual stocks making a move today. On the left, names hitting a new
        1-year high or low — a quick read on who&apos;s breaking out and who&apos;s
        breaking down. On the right, the stocks that climbed the most in our
        strength ranking over the past month.
      </p>
      <div className="grid gap-4 md:grid-cols-2">
        {/* Fresh 52-week highs / lows */}
        <div className="flex flex-col gap-3 rounded-xl border border-border bg-card p-5">
          <div className="flex items-baseline justify-between">
            <span className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
              New 1-year highs / lows
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
              Biggest climbers in our strength ranking (past month)
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
