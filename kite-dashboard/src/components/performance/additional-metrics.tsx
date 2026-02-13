"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useMetrics } from "@/lib/hooks";

export function AdditionalMetrics() {
  const { data, isLoading, error } = useMetrics();

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
      description: "Downside risk-adjusted",
    },
    {
      title: "Calmar Ratio",
      value: data.risk.calmar_ratio?.toFixed(2) ?? "N/A",
      description: "CAGR / Max DD",
    },
    {
      title: "Hit Rate",
      value: `${data.activity.hit_rate.toFixed(1)}%`,
      description: "Winning trades",
    },
    {
      title: "Avg Holding",
      value: `${data.activity.avg_holding_days.toFixed(0)} days`,
      description: "Position duration",
    },
    {
      title: "Turnover",
      value: `${data.activity.annualized_turnover.toFixed(0)}%`,
      description: "Annualized",
    },
    {
      title: "Total Trades",
      value: data.activity.total_trades.toLocaleString(),
      description: "All time",
    },
    {
      title: "MTD Return",
      value: `${data.returns.mtd >= 0 ? "+" : ""}${data.returns.mtd.toFixed(2)}%`,
      description: "Month to date",
    },
    {
      title: "YTD Return",
      value: `${data.returns.ytd >= 0 ? "+" : ""}${data.returns.ytd.toFixed(2)}%`,
      description: "Year to date",
    },
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle>Additional Metrics</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {metrics.map((metric) => (
            <div
              key={metric.title}
              className="flex flex-col space-y-1 rounded-lg border p-4"
            >
              <span className="text-sm text-muted-foreground">{metric.title}</span>
              <span className="text-xl font-semibold">{metric.value}</span>
              <span className="text-xs text-muted-foreground">{metric.description}</span>
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
        <Skeleton className="h-5 w-40" />
      </CardHeader>
      <CardContent>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[...Array(8)].map((_, i) => (
            <div key={i} className="flex flex-col space-y-2 rounded-lg border p-4">
              <Skeleton className="h-4 w-20" />
              <Skeleton className="h-6 w-16" />
              <Skeleton className="h-3 w-24" />
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
