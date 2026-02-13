"use client";

import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useMetrics } from "@/lib/hooks";
import { TrendingUp, TrendingDown, Activity, Target } from "lucide-react";

export function MetricsGrid() {
  const { data, isLoading, error } = useMetrics();

  if (isLoading) {
    return <MetricsGridSkeleton />;
  }

  if (error || !data) {
    return (
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {[...Array(4)].map((_, i) => (
          <Card key={i}>
            <CardContent className="pt-6">
              <p className="text-sm text-muted-foreground">Failed to load metrics</p>
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  const metrics = [
    {
      title: "CAGR",
      value: `${data.returns.cagr.toFixed(1)}%`,
      description: "Compound annual growth rate",
      icon: TrendingUp,
      positive: data.returns.cagr >= 0,
    },
    {
      title: "Sharpe Ratio",
      value: data.risk.sharpe_ratio?.toFixed(2) ?? "N/A",
      description: "Risk-adjusted return",
      icon: Target,
      positive: (data.risk.sharpe_ratio ?? 0) >= 1,
    },
    {
      title: "Max Drawdown",
      value: `${data.risk.max_drawdown.toFixed(1)}%`,
      description: data.risk.max_dd_duration ? `${data.risk.max_dd_duration} days duration` : "Maximum peak-to-trough",
      icon: TrendingDown,
      positive: false,
    },
    {
      title: "Volatility",
      value: `${data.risk.volatility.toFixed(1)}%`,
      description: "Annualized standard deviation",
      icon: Activity,
      positive: true,
    },
  ];

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      {metrics.map((metric) => (
        <Card key={metric.title}>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">
                  {metric.title}
                </p>
                <p
                  className={`text-2xl font-bold ${
                    metric.title === "Max Drawdown"
                      ? "text-red-600"
                      : metric.positive
                      ? "text-green-600"
                      : ""
                  }`}
                >
                  {metric.value}
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  {metric.description}
                </p>
              </div>
              <metric.icon
                className={`h-8 w-8 ${
                  metric.title === "Max Drawdown"
                    ? "text-red-200"
                    : "text-muted-foreground/30"
                }`}
              />
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

function MetricsGridSkeleton() {
  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      {[...Array(4)].map((_, i) => (
        <Card key={i}>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div className="space-y-2">
                <Skeleton className="h-4 w-16" />
                <Skeleton className="h-8 w-24" />
                <Skeleton className="h-3 w-32" />
              </div>
              <Skeleton className="h-8 w-8 rounded" />
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
