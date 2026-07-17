"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useEquityCurve, useIndexReturns } from "@/lib/hooks";
import { useUniverse } from "@/contexts/universe-context";
import { getUniverse } from "@/lib/universes";
import { formatPercent, cn } from "@/lib/utils";
import { InfoHint } from "@/components/shared/info-hint";

const FALLBACK_HORIZONS = ["1M", "6M", "1Y", "3Y", "5Y"];

type EquityPoint = { date: string; portfolio_value: number };

/** Shift an ISO date (YYYY-MM-DD) back by a horizon key like "6M" / "3Y",
 *  in UTC so month/year math never drifts across a day boundary. */
function shiftBack(iso: string, key: string): string {
  const d = new Date(`${iso}T00:00:00Z`);
  const n = parseInt(key, 10);
  if (key.endsWith("M")) d.setUTCMonth(d.getUTCMonth() - n);
  else if (key.endsWith("Y")) d.setUTCFullYear(d.getUTCFullYear() - n);
  return d.toISOString().slice(0, 10);
}

/** Portfolio rolling returns from the equity curve: latest value / value on or
 *  before (latest − horizon) − 1. Null when history doesn't reach back. */
function portfolioReturns(
  points: EquityPoint[],
  horizons: string[],
): Map<string, number | null> {
  const out = new Map<string, number | null>();
  const sorted = [...points].sort((a, b) => a.date.localeCompare(b.date));
  const last = sorted.at(-1);
  for (const key of horizons) {
    if (!last) {
      out.set(key, null);
      continue;
    }
    const target = shiftBack(last.date, key);
    // Latest point on or before the target date (walk from the end).
    const base = [...sorted].reverse().find((p) => p.date <= target);
    out.set(
      key,
      base && base.portfolio_value > 0
        ? last.portfolio_value / base.portfolio_value - 1
        : null,
    );
  }
  return out;
}

function Ret({ v }: { v: number | null | undefined }) {
  if (v === null || v === undefined || Number.isNaN(v)) {
    return <span className="text-muted-foreground">—</span>;
  }
  return (
    <span
      className={cn(
        "tabular-nums",
        v > 0
          ? "text-[color:var(--positive)]"
          : v < 0
            ? "text-[color:var(--negative)]"
            : "text-muted-foreground",
      )}
    >
      {formatPercent(v, 1)}
    </span>
  );
}

export function ReturnsCompare() {
  const { universeId } = useUniverse();
  const universe = getUniverse(universeId);
  const { data: equity, isLoading: eqLoading } = useEquityCurve();
  const { data: indexData, isLoading: idxLoading } = useIndexReturns();

  if (eqLoading || idxLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Returns vs the market</CardTitle>
        </CardHeader>
        <CardContent>
          <Skeleton className="h-40 w-full" />
        </CardContent>
      </Card>
    );
  }

  const horizons = indexData?.horizons?.length ? indexData.horizons : FALLBACK_HORIZONS;
  const pf = portfolioReturns(equity?.data ?? [], horizons);
  const indices = indexData?.indices ?? [];

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Returns vs the market</CardTitle>
        <p className="text-sm text-muted-foreground">
          How this portfolio has performed over each period, next to the main
          Indian market indices.
        </p>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border text-left text-muted-foreground">
                <th className="py-2 pr-4 font-medium">&nbsp;</th>
                {horizons.map((h) => (
                  <th key={h} className="py-2 px-3 text-right font-medium">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {/* Portfolio row — highlighted, labelled model */}
              <tr className="border-b border-border bg-primary/[0.05]">
                <td className="py-2.5 pr-4">
                  <span className="font-semibold text-foreground">{universe.name}</span>
                  <span className="ml-2 inline-flex items-center gap-1 rounded border border-border px-1.5 py-0.5 text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
                    model
                    <InfoHint text="Results from historical backtests of the strategy, not live trading — especially over longer periods." />
                  </span>
                </td>
                {horizons.map((h) => (
                  <td key={h} className="py-2.5 px-3 text-right font-semibold">
                    <Ret v={pf.get(h)} />
                  </td>
                ))}
              </tr>
              {/* Index rows */}
              {indices.map((idx) => (
                <tr key={idx.key} className="border-b border-border last:border-0">
                  <td className="py-2.5 pr-4 text-muted-foreground">{idx.label}</td>
                  {horizons.map((h) => (
                    <td key={h} className="py-2.5 px-3 text-right">
                      {/* eslint-disable-next-line security/detect-object-injection -- h is from our own horizons list; idx.returns is a plain API record */}
                      <Ret v={idx.returns?.[h]} />
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="mt-3 text-xs leading-relaxed text-muted-foreground">
          Educational only. Portfolio figures come from robust historical
          backtests, not live trading, and past performance doesn&apos;t
          guarantee future results.
        </p>
      </CardContent>
    </Card>
  );
}
