# Task 6: Metrics Grid Component

**Status**: `completed`
**Blocked By**: #2 (Metrics Endpoint)
**Blocks**: None

## Objective

Create the primary metrics grid showing key performance indicators.

## Tasks

- [ ] Create `metrics-grid.tsx` in `kite-dashboard/src/components/performance/`
- [ ] Display CAGR, Sharpe Ratio, Max Drawdown, Volatility
- [ ] Add loading skeleton state
- [ ] Add error state handling
- [ ] Create `useMetrics()` hook

## Implementation

### File: `kite-dashboard/src/components/performance/metrics-grid.tsx`

```tsx
"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useMetrics } from "@/lib/hooks";
import { formatPercent } from "@/lib/utils";
import { TrendingUp, Shield, TrendingDown, Activity } from "lucide-react";

export function MetricsGrid() {
  const { data, isLoading, error } = useMetrics();

  if (isLoading) {
    return <MetricsGridSkeleton />;
  }

  if (error || !data) {
    return (
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">
              Failed to load metrics
            </p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const metrics = [
    {
      title: "CAGR",
      value: formatPercent(data.returns.cagr),
      description: "Compound Annual Growth Rate",
      icon: TrendingUp,
      color: data.returns.cagr >= 0 ? "text-green-600" : "text-red-600",
    },
    {
      title: "Sharpe Ratio",
      value: data.risk.sharpe_ratio?.toFixed(2) || "—",
      description: "Risk-adjusted return",
      icon: Shield,
      color: data.risk.sharpe_ratio >= 1 ? "text-green-600" : "text-yellow-600",
    },
    {
      title: "Max Drawdown",
      value: formatPercent(data.risk.max_drawdown),
      description: `${data.risk.max_dd_duration || 0} days duration`,
      icon: TrendingDown,
      color: "text-red-600",
    },
    {
      title: "Volatility",
      value: formatPercent(data.risk.volatility),
      description: "Annualized std deviation",
      icon: Activity,
      color: "text-muted-foreground",
    },
  ];

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      {metrics.map((metric) => (
        <Card key={metric.title}>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">
              {metric.title}
            </CardTitle>
            <metric.icon className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${metric.color}`}>
              {metric.value}
            </div>
            <p className="text-xs text-muted-foreground">
              {metric.description}
            </p>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

function MetricsGridSkeleton() {
  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      {[1, 2, 3, 4].map((i) => (
        <Card key={i}>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <Skeleton className="h-4 w-20" />
            <Skeleton className="h-4 w-4" />
          </CardHeader>
          <CardContent>
            <Skeleton className="h-8 w-24 mb-1" />
            <Skeleton className="h-3 w-32" />
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
```

### Add Hook: `kite-dashboard/src/lib/hooks.ts`

```tsx
export function useMetrics() {
  const { universeId } = useUniverse();

  return useSWR(
    ["metrics", universeId],
    ([, universe]) => getMetrics(universe),
    {
      refreshInterval: SLOW_REFRESH,
      revalidateOnFocus: false,
    }
  );
}
```

### Add API Client Function: `kite-dashboard/src/lib/api-client.ts`

```tsx
export async function getMetrics(universe: UniverseId) {
  return apiFetch<{
    period: { start: string; end: string; days: number };
    returns: { total_return: number; cagr: number; mtd: number; ytd: number };
    risk: {
      max_drawdown: number;
      max_dd_duration: number;
      volatility: number;
      sharpe_ratio: number;
      sortino_ratio: number;
      calmar_ratio: number;
    };
    activity: {
      total_trades: number;
      avg_turnover: number;
      annualized_turnover: number;
      avg_holding_days: number;
      hit_rate: number;
    };
  }>(`/api/metrics?universe=${universe}`);
}
```

## Color Coding

| Metric | Positive | Negative |
|--------|----------|----------|
| CAGR | Green | Red |
| Sharpe | Green (>=1) | Yellow (<1) |
| Max DD | Always Red | — |
| Volatility | Neutral | — |

---

*Status Key: `pending` | `in_progress` | `completed`*
