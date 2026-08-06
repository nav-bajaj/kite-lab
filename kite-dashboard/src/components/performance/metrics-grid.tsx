"use client";

import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useMetrics } from "@/lib/hooks";
import { InfoHint } from "@/components/shared/info-hint";
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
      description: "Average growth per year",
      hint: "Compound annual growth rate — the steady yearly rate that would turn the start value into the end value over the whole period.",
      icon: TrendingUp,
      positive: data.returns.cagr >= 0,
    },
    {
      title: "Sharpe Ratio",
      value: data.risk.sharpe_ratio?.toFixed(2) ?? "N/A",
      description: "Return earned per unit of risk",
      hint: "Return relative to how bumpy the ride was. Rough guide: above 1 is good, above 2 is excellent.",
      icon: Target,
      positive: (data.risk.sharpe_ratio ?? 0) >= 1,
    },
    {
      title: "Max Drawdown",
      value: `${data.risk.max_drawdown.toFixed(1)}%`,
      description: data.risk.max_dd_duration
        ? `Worst fall · ${data.risk.max_dd_duration} days to recover`
        : "Worst peak-to-trough fall",
      hint: "The deepest drop from a high to the following low over the whole period — the worst loss you'd have sat through.",
      icon: TrendingDown,
      positive: false,
    },
    {
      title: "Volatility",
      value: `${data.risk.volatility.toFixed(1)}%`,
      description: "How much returns swing",
      hint: "How bumpy the ride is, year to year. Lower means steadier; higher means bigger ups and downs.",
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
                <p className="flex items-center gap-1.5 text-sm font-medium text-muted-foreground">
                  {metric.title}
                  <InfoHint text={metric.hint} />
                </p>
                <p
                  className={`text-2xl font-bold ${
                    metric.title === "Max Drawdown"
                      ? "text-negative"
                      : metric.positive
                      ? "text-positive"
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
                    ? "text-negative/30"
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
