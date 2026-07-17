"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useMetrics, useTradeSummary } from "@/lib/hooks";
import { InfoHint } from "@/components/shared/info-hint";

export function AdditionalMetrics() {
  const { data, isLoading, error } = useMetrics();
  const { data: trades } = useTradeSummary();

  if (isLoading) {
    return <AdditionalMetricsSkeleton />;
  }

  if (error || !data) {
    return (
      <Card>
        <CardContent className="pt-6">
          <p className="text-sm text-muted-foreground">Failed to load metrics</p>
        </CardContent>
      </Card>
    );
  }

  const metrics = [
    {
      title: "Sortino Ratio",
      value: data.risk.sortino_ratio?.toFixed(2) ?? "N/A",
      hint: "Like Sharpe, but only penalises downside swings — it ignores 'good' volatility. Higher is better.",
    },
    {
      title: "Calmar Ratio",
      value: data.risk.calmar_ratio?.toFixed(2) ?? "N/A",
      hint: "Yearly return divided by the worst drop. Higher means more return for the pain endured.",
    },
    {
      title: "Win Rate",
      value:
        trades?.win_rate != null ? `${trades.win_rate.toFixed(1)}%` : "N/A",
      hint: "Share of matched trades that were profitable — each sell matched to its buy lots (FIFO). The same figure shown on the Trades page.",
    },
    {
      title: "Avg Holding",
      value: `${data.activity.avg_holding_days.toFixed(0)} days`,
      hint: "How long a position is typically held before it's sold.",
    },
    // Turnover is only shown when the pipeline has populated it (currently 0).
    ...(data.activity.annualized_turnover > 0
      ? [
          {
            title: "Turnover",
            value: `${data.activity.annualized_turnover.toFixed(0)}%`,
            hint: "How much of the portfolio is traded in a year — higher means more frequent rotation.",
          },
        ]
      : []),
    {
      title: "Total Trades",
      value: data.activity.total_trades.toLocaleString(),
      hint: "Total buys and sells over the whole period.",
    },
    {
      title: "MTD Return",
      value: `${data.returns.mtd >= 0 ? "+" : ""}${data.returns.mtd.toFixed(2)}%`,
      hint: "Return so far this month.",
    },
    {
      title: "YTD Return",
      value: `${data.returns.ytd >= 0 ? "+" : ""}${data.returns.ytd.toFixed(2)}%`,
      hint: "Return so far this calendar year.",
    },
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">More metrics</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {metrics.map((metric) => (
            <div
              key={metric.title}
              className="flex flex-col space-y-1 rounded-lg border p-4"
            >
              <span className="flex items-center gap-1.5 text-sm text-muted-foreground">
                {metric.title}
                <InfoHint text={metric.hint} />
              </span>
              <span className="text-xl font-semibold">{metric.value}</span>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

function AdditionalMetricsSkeleton() {
  return (
    <Card>
      <CardHeader>
        <Skeleton className="h-5 w-32" />
      </CardHeader>
      <CardContent>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[...Array(7)].map((_, i) => (
            <div key={i} className="flex flex-col space-y-2 rounded-lg border p-4">
              <Skeleton className="h-4 w-20" />
              <Skeleton className="h-6 w-16" />
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
