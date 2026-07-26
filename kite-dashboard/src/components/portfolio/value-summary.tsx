"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { usePortfolio, useHoldings, useEquityCurve } from "@/lib/hooks";
import { formatCurrency, formatPercentValue } from "@/lib/utils";
import { InfoHint } from "@/components/shared/info-hint";

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
    // Two combo cards instead of four (UX study pattern): related metrics
    // share a card as labeled cells, so mobile scrolls two cards, not four.
    <div className="grid gap-4 lg:grid-cols-2">
      {/* What it's worth + what that means in profit */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium">Value &amp; profit</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-x-6">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-[0.1em] text-muted-foreground">
                Portfolio value
              </p>
              <div className="mt-1 text-xl font-bold tabular-nums sm:text-2xl">
                {formatCurrency(data.total_value)}
              </div>
              <p className="mt-1 text-xs text-muted-foreground">
                Cost {formatCurrency(data.invested)} · {data.holdings_count} holding{data.holdings_count === 1 ? "" : "s"}
              </p>
            </div>
            <div>
              <p className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-[0.1em] text-muted-foreground">
                Current profit
                <InfoHint text="Unrealised profit on the stocks held right now — the gain if you sold today. Not the strategy's long-term return." />
              </p>
              <div
                className={
                  profitUp
                    ? "mt-1 text-xl font-bold tabular-nums text-[color:var(--positive)] sm:text-2xl"
                    : "mt-1 text-xl font-bold tabular-nums text-[color:var(--negative)] sm:text-2xl"
                }
              >
                {formatPercentValue(data.total_return_pct)}
              </div>
              <p className="mt-1 text-xs text-muted-foreground">
                {formatCurrency(data.total_return)} open profit
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* How the book is positioned: age of the holdings + distance off peak */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium">Position character</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-x-6">
            <div>
              <p className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-[0.1em] text-muted-foreground">
                Avg. holding age
                <InfoHint text="The average time the current stocks have been held. Momentum portfolios rotate, so this is usually weeks to a few months." />
              </p>
              <div className="mt-1 text-xl font-bold tabular-nums sm:text-2xl">
                {avgAge === null ? "—" : `${avgAge} days`}
              </div>
              <p className="mt-1 text-xs text-muted-foreground">
                Average age of the current holdings
              </p>
            </div>
            <div>
              <p className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-[0.1em] text-muted-foreground">
                Current drawdown
                <InfoHint text="How far below its highest recent value the portfolio is right now. A small dip is normal; a big one means it's well off its peak." />
              </p>
              <div
                className={
                  currentDD !== null && currentDD < -0.05
                    ? "mt-1 text-xl font-bold tabular-nums text-[color:var(--negative)] sm:text-2xl"
                    : "mt-1 text-xl font-bold tabular-nums text-foreground sm:text-2xl"
                }
              >
                {currentDD === null ? "—" : formatPercentValue(currentDD)}
              </div>
              <p className="mt-1 text-xs text-muted-foreground">
                Distance below the recent high
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function ValueSummarySkeleton() {
  return (
    <div className="grid gap-4 lg:grid-cols-2">
      {[1, 2].map((i) => (
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
