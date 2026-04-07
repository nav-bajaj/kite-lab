# Task 8: Drawdown Chart

**Status**: `completed`
**Blocked By**: #3 (Equity Curve Endpoint)
**Blocks**: None

## Objective

Create a dedicated drawdown visualization chart.

## Tasks

- [ ] Create `drawdown-chart.tsx` in `kite-dashboard/src/components/performance/`
- [ ] Display drawdown over time as negative area
- [ ] Highlight maximum drawdown point
- [ ] Add loading state
- [ ] Show drawdown statistics

## Implementation

### File: `kite-dashboard/src/components/performance/drawdown-chart.tsx`

```tsx
"use client";

import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useEquityCurve, useMetrics } from "@/lib/hooks";
import { formatDate, formatPercent } from "@/lib/utils";

export function DrawdownChart() {
  const { data: equityData, isLoading: equityLoading } = useEquityCurve();
  const { data: metricsData } = useMetrics();

  if (equityLoading) {
    return <DrawdownChartSkeleton />;
  }

  if (!equityData?.data) {
    return (
      <Card>
        <CardContent className="pt-6">
          <p className="text-sm text-muted-foreground">
            Failed to load drawdown data
          </p>
        </CardContent>
      </Card>
    );
  }

  const maxDrawdown = metricsData?.risk.max_drawdown || 0;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Drawdown</CardTitle>
        <CardDescription>
          Maximum: {formatPercent(maxDrawdown)}
          {metricsData?.risk.max_dd_duration &&
            ` (${metricsData.risk.max_dd_duration} days)`
          }
        </CardDescription>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={250}>
          <AreaChart data={equityData.data}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
            <XAxis
              dataKey="date"
              tickFormatter={(date) => formatDate(date, "MMM yy")}
              tick={{ fontSize: 11 }}
            />
            <YAxis
              tickFormatter={(value) => `${value.toFixed(0)}%`}
              tick={{ fontSize: 11 }}
              domain={["dataMin", 0]}
            />
            <Tooltip
              labelFormatter={(date) => formatDate(date, "dd MMM yyyy")}
              formatter={(value: number) => [`${value.toFixed(2)}%`, "Drawdown"]}
            />

            {/* Max drawdown reference line */}
            <ReferenceLine
              y={maxDrawdown}
              stroke="#dc2626"
              strokeDasharray="4 4"
              label={{
                value: `Max: ${formatPercent(maxDrawdown)}`,
                position: "insideBottomLeft",
                fill: "#dc2626",
                fontSize: 11,
              }}
            />

            {/* Zero line */}
            <ReferenceLine y={0} stroke="#6b7280" />

            {/* Drawdown area */}
            <Area
              type="monotone"
              dataKey="drawdown"
              name="Drawdown"
              stroke="#dc2626"
              fill="#dc2626"
              fillOpacity={0.3}
            />
          </AreaChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

function DrawdownChartSkeleton() {
  return (
    <Card>
      <CardHeader>
        <Skeleton className="h-5 w-24" />
        <Skeleton className="h-4 w-40" />
      </CardHeader>
      <CardContent>
        <Skeleton className="h-[250px] w-full" />
      </CardContent>
    </Card>
  );
}
```

## Chart Features

- **Negative Y-Axis**: All values are below zero
- **Max Drawdown Line**: Dashed reference line at maximum drawdown
- **Zero Line**: Reference line at 0%
- **Red Fill**: Area chart with red color indicating loss
- **Tooltip**: Shows exact drawdown percentage on hover

## Notes

- Drawdown data comes from the equity curve endpoint
- Maximum drawdown value comes from metrics endpoint
- Chart domain is `[dataMin, 0]` to show only negative values

---

*Status Key: `pending` | `in_progress` | `completed`*
