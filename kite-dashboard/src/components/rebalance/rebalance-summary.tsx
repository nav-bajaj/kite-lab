"use client";

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useRebalanceSummary } from "@/lib/hooks";
import { formatCurrency } from "@/lib/utils";
import {
  CalendarClock,
  History,
  ArrowRight,
  RefreshCw,
  Scissors,
} from "lucide-react";

export function RebalanceSummary() {
  const { data, isLoading, error } = useRebalanceSummary();

  if (isLoading) return <SummarySkeleton />;

  if (error || !data) {
    return (
      <Card>
        <CardContent className="pt-6">
          <p className="text-sm text-muted-foreground">
            Failed to load rebalance summary
          </p>
        </CardContent>
      </Card>
    );
  }

  const { previous, next: upcoming } = data;

  return (
    <div className="space-y-4">
      {/* Cadence banner */}
      <div className="flex flex-wrap items-center justify-between gap-2 rounded-lg bg-muted/50 px-4 py-2">
        <div className="flex items-center gap-2 text-sm">
          <RefreshCw className="h-4 w-4 text-muted-foreground" />
          <span className="text-muted-foreground">Rebalance schedule</span>
          <Badge variant="secondary">{data.cadence_label}</Badge>
        </div>
        <span className="text-sm text-muted-foreground">
          {data.holdings_count} holdings
        </span>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        {/* Next rebalance */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <CalendarClock className="h-5 w-5 text-blue-500" />
              <CardTitle>Next rebalance</CardTitle>
            </div>
            <CardDescription>Projected from the strategy&apos;s cadence</CardDescription>
          </CardHeader>
          <CardContent>
            {!upcoming ? (
              <p className="text-sm text-muted-foreground">
                Not enough history yet to project the next rebalance.
              </p>
            ) : (
              <div className="space-y-3">
                <div>
                  {upcoming.has_weekly_exit && (
                    <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                      Next entry
                    </p>
                  )}
                  <p className="text-2xl font-bold">{upcoming.signal_date}</p>
                  <p className="text-sm text-muted-foreground">
                    {upcoming.trading_days_until === 0
                      ? "Entry is today or already underway"
                      : `${upcoming.trading_days_until} trading day${
                          upcoming.trading_days_until === 1 ? "" : "s"
                        } away`}
                  </p>
                </div>
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <span>Signal {upcoming.signal_date}</span>
                  <ArrowRight className="h-3 w-3" />
                  <span>Trades take effect {upcoming.exec_date}</span>
                </div>
                {upcoming.has_weekly_exit && upcoming.exit_check_date && (
                  <div className="flex items-start gap-2 rounded-md bg-amber-50 px-2 py-1.5 text-xs text-amber-700 dark:bg-amber-950/40 dark:text-amber-400">
                    <Scissors className="mt-0.5 h-3 w-3 shrink-0" />
                    <span>
                      Holdings are also reviewed for exits every Friday — next
                      check {upcoming.exit_check_date}
                      {upcoming.exit_check_days_until !== null &&
                        ` (${upcoming.exit_check_days_until} trading day${
                          upcoming.exit_check_days_until === 1 ? "" : "s"
                        } away)`}
                      .
                    </span>
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Previous rebalance */}
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <History className="h-5 w-5 text-purple-500" />
              <CardTitle>Previous rebalance</CardTitle>
            </div>
            <CardDescription>
              {previous ? previous.date : "Most recent trades"}
            </CardDescription>
          </CardHeader>
          <CardContent>
            {!previous ? (
              <p className="text-sm text-muted-foreground">
                No rebalance trades recorded yet.
              </p>
            ) : previous.no_action ||
              (previous.buy_count === 0 && previous.sell_count === 0) ? (
              <div className="space-y-3">
                <Badge variant="outline" className="text-xs">
                  No-action rebalance
                </Badge>
                <p className="text-sm text-muted-foreground">
                  The engine processed the signal day but the momentum
                  rotation stayed inside the exit buffer, so it held the
                  existing names. No trades were placed.
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                <Badge variant="outline" className="text-xs">
                  {previous.buy_count > 0 ? "Entry rebalance" : "Weekly exit"}
                </Badge>
                <div className="flex items-center gap-4 text-sm">
                  <span>
                    <span className="font-medium text-green-600">
                      {previous.buy_count}
                    </span>{" "}
                    added
                  </span>
                  <span>
                    <span className="font-medium text-red-600">
                      {previous.sell_count}
                    </span>{" "}
                    removed
                  </span>
                  {previous.turnover_pct !== null && (
                    <span className="text-muted-foreground">
                      {previous.turnover_pct.toFixed(1)}% turnover
                    </span>
                  )}
                </div>

                {previous.added.length > 0 && (
                  <div className="flex flex-wrap gap-1.5">
                    {previous.added.map((s) => (
                      <Badge
                        key={`add-${s}`}
                        variant="outline"
                        className="border-green-600 text-green-700 dark:text-green-400"
                      >
                        + {s}
                      </Badge>
                    ))}
                  </div>
                )}
                {previous.removed.length > 0 && (
                  <div className="flex flex-wrap gap-1.5">
                    {previous.removed.map((s) => (
                      <Badge
                        key={`rem-${s}`}
                        variant="outline"
                        className="border-red-600 text-red-700 dark:text-red-400"
                      >
                        - {s}
                      </Badge>
                    ))}
                  </div>
                )}
                {previous.added.length === 0 && previous.removed.length === 0 && (
                  <p className="text-sm text-muted-foreground">
                    No holdings changed at this rebalance.
                  </p>
                )}

                <p className="text-xs text-muted-foreground">
                  {formatCurrency(previous.notional_traded)} traded
                  <span className="ml-1 opacity-70">(model book)</span>
                </p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function SummarySkeleton() {
  return (
    <div className="space-y-4">
      <Skeleton className="h-10 w-full" />
      <div className="grid gap-4 md:grid-cols-2">
        {[1, 2].map((i) => (
          <Card key={i}>
            <CardHeader>
              <Skeleton className="h-5 w-40" />
              <Skeleton className="h-4 w-32" />
            </CardHeader>
            <CardContent>
              <Skeleton className="h-20 w-full" />
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
