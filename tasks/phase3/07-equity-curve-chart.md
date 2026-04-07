# Task 7: Equity Curve Chart

**Status**: `completed`
**Blocked By**: #3 (Equity Curve Endpoint)
**Blocks**: #9

## Objective

Create an interactive equity curve chart with Recharts.

## Tasks

- [ ] Create `equity-curve.tsx` in `kite-dashboard/src/components/performance/`
- [ ] Display portfolio value over time
- [ ] Add benchmark comparison overlay
- [ ] Add toggle controls (Portfolio/Benchmark/Drawdown)
- [ ] Add loading state
- [ ] Create `useEquityCurve()` hook
- [ ] Add tooltip with formatted values
- [ ] Responsive chart sizing

## Implementation

### File: `kite-dashboard/src/components/performance/equity-curve.tsx`

```tsx
"use client";

import { useState } from "react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { Skeleton } from "@/components/ui/skeleton";
import { useEquityCurve } from "@/lib/hooks";
import { formatCurrency, formatDate } from "@/lib/utils";

export function EquityCurve() {
  const { data, isLoading, error } = useEquityCurve();
  const [showBenchmark, setShowBenchmark] = useState(true);
  const [showDrawdown, setShowDrawdown] = useState(false);

  if (isLoading) {
    return <EquityCurveSkeleton />;
  }

  if (error || !data?.data) {
    return (
      <Card>
        <CardContent className="pt-6">
          <p className="text-sm text-muted-foreground">
            Failed to load equity curve
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>Equity Curve</CardTitle>
        <ToggleGroup type="multiple" size="sm">
          <ToggleGroupItem
            value="benchmark"
            aria-label="Toggle benchmark"
            pressed={showBenchmark}
            onPressedChange={setShowBenchmark}
          >
            Benchmark
          </ToggleGroupItem>
          <ToggleGroupItem
            value="drawdown"
            aria-label="Toggle drawdown"
            pressed={showDrawdown}
            onPressedChange={setShowDrawdown}
          >
            Drawdown
          </ToggleGroupItem>
        </ToggleGroup>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={400}>
          <AreaChart data={data.data}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
            <XAxis
              dataKey="date"
              tickFormatter={(date) => formatDate(date, "MMM yy")}
              tick={{ fontSize: 12 }}
            />
            <YAxis
              tickFormatter={(value) => `₹${(value / 1000000).toFixed(1)}M`}
              tick={{ fontSize: 12 }}
            />
            <Tooltip
              content={<CustomTooltip />}
              labelFormatter={(date) => formatDate(date, "dd MMM yyyy")}
            />
            <Legend />

            {/* Portfolio Value */}
            <Area
              type="monotone"
              dataKey="portfolio_value"
              name="Portfolio"
              stroke="#3b82f6"
              fill="#3b82f6"
              fillOpacity={0.1}
              strokeWidth={2}
            />

            {/* Benchmark (optional) */}
            {showBenchmark && (
              <Area
                type="monotone"
                dataKey="benchmark_value"
                name="Benchmark"
                stroke="#6b7280"
                fill="transparent"
                strokeWidth={1}
                strokeDasharray="4 4"
              />
            )}
          </AreaChart>
        </ResponsiveContainer>

        {/* Drawdown Chart (conditional) */}
        {showDrawdown && (
          <ResponsiveContainer width="100%" height={150}>
            <AreaChart data={data.data}>
              <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
              <XAxis dataKey="date" hide />
              <YAxis
                tickFormatter={(value) => `${value.toFixed(0)}%`}
                tick={{ fontSize: 12 }}
                domain={["dataMin", 0]}
              />
              <Tooltip />
              <Area
                type="monotone"
                dataKey="drawdown"
                name="Drawdown"
                stroke="#dc2626"
                fill="#dc2626"
                fillOpacity={0.2}
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  );
}

function CustomTooltip({ active, payload, label }: any) {
  if (!active || !payload) return null;

  return (
    <div className="rounded-lg border bg-background p-3 shadow-md">
      <p className="font-medium">{label}</p>
      {payload.map((entry: any) => (
        <p key={entry.name} style={{ color: entry.color }}>
          {entry.name}: {formatCurrency(entry.value)}
        </p>
      ))}
    </div>
  );
}

function EquityCurveSkeleton() {
  return (
    <Card>
      <CardHeader>
        <Skeleton className="h-6 w-32" />
      </CardHeader>
      <CardContent>
        <Skeleton className="h-[400px] w-full" />
      </CardContent>
    </Card>
  );
}
```

### Add Hook: `kite-dashboard/src/lib/hooks.ts`

```tsx
export function useEquityCurve() {
  const { universeId } = useUniverse();

  return useSWR(
    ["equity-curve", universeId],
    ([, universe]) => getEquityCurve(universe),
    {
      refreshInterval: SLOW_REFRESH,
      revalidateOnFocus: false,
    }
  );
}
```

## Chart Features

- **Portfolio Line**: Blue solid line with light fill
- **Benchmark Line**: Gray dashed line (toggleable)
- **Drawdown**: Red area chart below main chart (toggleable)
- **Tooltip**: Shows formatted currency values
- **X-Axis**: Dates formatted as "MMM yy"
- **Y-Axis**: Values in millions (₹1.5M format)

## Color Scheme

| Element | Color |
|---------|-------|
| Portfolio | #3b82f6 (blue-500) |
| Benchmark | #6b7280 (gray-500) |
| Drawdown | #dc2626 (red-600) |
| Grid | muted border color |

---

*Status Key: `pending` | `in_progress` | `completed`*
