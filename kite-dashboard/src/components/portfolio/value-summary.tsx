"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { usePortfolio, useHoldings, useEquityCurve } from "@/lib/hooks";
import { formatCurrency, formatPercentValue } from "@/lib/utils";
import { InfoHint } from "@/components/shared/info-hint";
import { Wallet, TrendingUp, TrendingDown, CalendarClock, Waves } from "lucide-react";

/** The Overview's headline stats. All four describe the *current* open
 *  positions: what they're worth vs what they cost, the open profit on them,
 *  how long they've been held, and how far below their recent high they sit. */
export function ValueSummary() {
  const { data, isLoading, error } = usePortfolio();
  const { data: holdingsData } = useHoldings();
  const { data: equity } = useEquityCurve();

  if (isLoading) return <ValueSummarySkeleton />;

  if (error || !data) {
    return (
      <Card>
        <CardContent className="pt-6">
          <p className="text-sm text-muted-foreground">Failed to load portfolio data</p>
        </CardContent>
      </Card>
    );
  }

  const holdings = holdingsData?.holdings ?? [];
  const avgAge = holdings.length
    ? Math.round(holdings.reduce((s, h) => s + h.holding_days, 0) / holdings.length)
    : null;

  const points = equity?.data ?? [];
  // Equity-curve `drawdown` is already a percent (e.g. -2.3); last point = now.
  const currentDD = points.length ? points[points.length - 1].drawdown : null;

  const profitUp = data.total_return >= 0;

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      {/* Portfolio Value — current value, with holding cost underneath */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="text-sm font-medium">Portfolio Value</CardTitle>
          <Wallet className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{formatCurrency(data.total_value)}</div>
          <p className="mt-1 text-xs text-muted-foreground">
            Cost {formatCurrency(data.invested)}
          </p>
          <p className="text-xs text-muted-foreground">
            {data.holdings_count} holding{data.holdings_count === 1 ? "" : "s"}
          </p>
        </CardContent>
      </Card>

      {/* Current Profit — open (unrealised) profit on the positions held now */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="flex items-center gap-1.5 text-sm font-medium">
            Current Profit
            <InfoHint text="Unrealised profit on the stocks held right now — the gain if you sold today. Not the strategy's long-term return." />
          </CardTitle>
          {profitUp ? (
            <TrendingUp className="h-4 w-4 text-muted-foreground" />
          ) : (
            <TrendingDown className="h-4 w-4 text-muted-foreground" />
          )}
        </CardHeader>
        <CardContent>
          <div
            className={
              profitUp
                ? "text-2xl font-bold text-[color:var(--positive)]"
                : "text-2xl font-bold text-[color:var(--negative)]"
            }
          >
            {formatPercentValue(data.total_return_pct)}
          </div>
          <p className="mt-1 text-xs text-muted-foreground">
            {formatCurrency(data.total_return)} open profit on current holdings
          </p>
        </CardContent>
      </Card>

      {/* Avg holding age — over roughly what time this profit was earned */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="flex items-center gap-1.5 text-sm font-medium">
            Avg. Holding Age
            <InfoHint text="The average time the current stocks have been held. Momentum portfolios rotate, so this is usually weeks to a few months." />
          </CardTitle>
          <CalendarClock className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">
            {avgAge === null ? "—" : `${avgAge} days`}
          </div>
          <p className="mt-1 text-xs text-muted-foreground">
            Average age of the current holdings
          </p>
        </CardContent>
      </Card>

      {/* Current drawdown */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
          <CardTitle className="flex items-center gap-1.5 text-sm font-medium">
            Current Drawdown
            <InfoHint text="How far below its highest recent value the portfolio is right now. A small dip is normal; a big one means it's well off its peak." />
          </CardTitle>
          <Waves className="h-4 w-4 text-muted-foreground" />
        </CardHeader>
        <CardContent>
          <div
            className={
              currentDD !== null && currentDD < -0.05
                ? "text-2xl font-bold text-[color:var(--negative)]"
                : "text-2xl font-bold text-foreground"
            }
          >
            {currentDD === null ? "—" : formatPercentValue(currentDD)}
          </div>
          <p className="mt-1 text-xs text-muted-foreground">
            How far below its recent high the portfolio is now
          </p>
        </CardContent>
      </Card>
    </div>
  );
}

function ValueSummarySkeleton() {
  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      {[1, 2, 3, 4].map((i) => (
        <Card key={i}>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <Skeleton className="h-4 w-28" />
            <Skeleton className="h-4 w-4" />
          </CardHeader>
          <CardContent>
            <Skeleton className="mb-2 h-8 w-32" />
            <Skeleton className="h-3 w-40" />
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
