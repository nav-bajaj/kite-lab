"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useHoldings } from "@/lib/hooks";
import { formatCurrency, formatPercentValue } from "@/lib/utils";

type Holding = {
  symbol: string;
  pnl: number;
  pnl_pct: number;
  sector?: string | null;
};

function Row({ h }: { h: Holding }) {
  const up = h.pnl_pct >= 0;
  return (
    <div className="flex items-center justify-between gap-3 py-1.5">
      <div className="min-w-0">
        <div className="truncate text-sm font-medium text-foreground">{h.symbol}</div>
        {h.sector ? (
          <div className="truncate text-xs text-muted-foreground">{h.sector}</div>
        ) : null}
      </div>
      <div className="shrink-0 text-right">
        <div
          className={
            up
              ? "text-sm font-semibold tabular-nums text-[color:var(--positive)]"
              : "text-sm font-semibold tabular-nums text-[color:var(--negative)]"
          }
        >
          {formatPercentValue(h.pnl_pct)}
        </div>
        <div className="text-xs tabular-nums text-muted-foreground">
          {formatCurrency(h.pnl)}
        </div>
      </div>
    </div>
  );
}

/** "What's driving it" — the current holdings up and down the most, so the
 *  open profit has a face. Sorted by each stock's return since entry. */
export function TopContributors() {
  const { data, isLoading, error } = useHoldings();

  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base">What&apos;s driving it</CardTitle>
        </CardHeader>
        <CardContent>
          <Skeleton className="h-32 w-full" />
        </CardContent>
      </Card>
    );
  }

  if (error || !data || data.holdings.length === 0) return null;

  const sorted = [...data.holdings].sort((a, b) => b.pnl_pct - a.pnl_pct);
  const n = Math.min(3, Math.floor(sorted.length / 2) || 1);
  const gainers = sorted.slice(0, n);
  const laggards = sorted.slice(-n).reverse();

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">What&apos;s driving it</CardTitle>
        <p className="text-sm text-muted-foreground">
          The current holdings up and down the most since they entered.
        </p>
      </CardHeader>
      <CardContent>
        <div className="grid gap-x-8 gap-y-2 sm:grid-cols-2">
          <div>
            <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Leading
            </div>
            <div className="divide-y divide-border">
              {gainers.map((h) => (
                <Row key={h.symbol} h={h} />
              ))}
            </div>
          </div>
          <div>
            <div className="mb-1 text-xs font-semibold uppercase tracking-wide text-muted-foreground">
              Lagging
            </div>
            <div className="divide-y divide-border">
              {laggards.map((h) => (
                <Row key={h.symbol} h={h} />
              ))}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
