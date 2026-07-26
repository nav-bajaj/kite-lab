"use client";

import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { usePortfolio, useHoldings, useEquityCurve } from "@/lib/hooks";
import { formatCurrency, formatPercentValue } from "@/lib/utils";
import { InfoHint } from "@/components/shared/info-hint";
import { PiggyBank, TrendingUp, TrendingDown, CalendarClock, Waves } from "lucide-react";

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
    // Two combo cards, no title rows (UX study "D2" primitive): the mini
    // accent chips carry each cell's identity; a single hairline splits the
    // pair. Mobile scrolls two compact cards instead of four.
    <div className="grid gap-4 lg:grid-cols-2">
      {/* What it's worth + what that means in profit */}
      <Card className="py-0">
        <CardContent className="p-0">
          <div className="grid grid-cols-2">
            <div className="min-h-[96px] px-4 py-4 sm:px-5">
              <p className="flex items-center gap-1.5">
                <span className="flex h-5 w-5 items-center justify-center rounded-md bg-acc1 text-acc1-fg">
                  <PiggyBank className="h-3 w-3" aria-hidden />
                </span>
                <span className="text-[11px] font-semibold uppercase tracking-[0.09em] text-muted-foreground">
                  Portfolio value
                </span>
              </p>
              <div className="mt-1 text-xl font-bold tabular-nums sm:text-2xl">
                {formatCurrency(data.total_value)}
              </div>
              <p className="mt-1 text-xs text-muted-foreground">
                Cost {formatCurrency(data.invested)} · {data.holdings_count} holding{data.holdings_count === 1 ? "" : "s"}
              </p>
            </div>
            <div className="min-h-[96px] border-l border-border px-4 py-4 sm:px-5">
              <p className="flex items-center gap-1.5">
                <span className="flex h-5 w-5 items-center justify-center rounded-md bg-acc2 text-acc2-fg">
                  {profitUp ? <TrendingUp className="h-3 w-3" aria-hidden /> : <TrendingDown className="h-3 w-3" aria-hidden />}
                </span>
                <span className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-[0.09em] text-muted-foreground">
                  Current profit
                  <InfoHint text="Unrealised profit on the stocks held right now — the gain if you sold today. Not the strategy's long-term return." />
                </span>
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
      <Card className="py-0">
        <CardContent className="p-0">
          <div className="grid grid-cols-2">
            <div className="min-h-[96px] px-4 py-4 sm:px-5">
              <p className="flex items-center gap-1.5">
                <span className="flex h-5 w-5 items-center justify-center rounded-md bg-acc3 text-acc3-fg">
                  <CalendarClock className="h-3 w-3" aria-hidden />
                </span>
                <span className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-[0.09em] text-muted-foreground">
                  Avg. holding age
                  <InfoHint text="The average time the current stocks have been held. Momentum portfolios rotate, so this is usually weeks to a few months." />
                </span>
              </p>
              <div className="mt-1 text-xl font-bold tabular-nums sm:text-2xl">
                {avgAge === null ? "—" : `${avgAge} days`}
              </div>
              <p className="mt-1 text-xs text-muted-foreground">
                Average age of the current holdings
              </p>
            </div>
            <div className="min-h-[96px] border-l border-border px-4 py-4 sm:px-5">
              <p className="flex items-center gap-1.5">
                <span className="flex h-5 w-5 items-center justify-center rounded-md bg-acc4 text-acc4-fg">
                  <Waves className="h-3 w-3" aria-hidden />
                </span>
                <span className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-[0.09em] text-muted-foreground">
                  Current drawdown
                  <InfoHint text="How far below its highest recent value the portfolio is right now. A small dip is normal; a big one means it's well off its peak." />
                </span>
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
        <Card key={i} className="py-0">
          <CardContent className="p-0">
            <div className="grid grid-cols-2">
              {[1, 2].map((j) => (
                <div key={j} className={`min-h-[96px] px-4 py-4 sm:px-5 ${j === 2 ? "border-l border-border" : ""}`}>
                  <Skeleton className="h-4 w-28" />
                  <Skeleton className="mt-2 h-7 w-32" />
                  <Skeleton className="mt-2 h-3 w-36" />
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
