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

function formatDate(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleDateString("en-IN", { month: "short", year: "2-digit" });
}

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
          <p className="text-sm text-muted-foreground">Failed to load drawdown data</p>
        </CardContent>
      </Card>
    );
  }

  const maxDrawdown = metricsData?.risk.max_drawdown ?? 0;
  const maxDdDuration = metricsData?.risk.max_dd_duration;

  // Convert drawdown to negative values for display
  const chartData = equityData.data.map((item) => ({
    ...item,
    drawdown: -Math.abs(item.drawdown),
  }));

  return (
    <Card>
      <CardHeader>
        <CardTitle>Drawdown</CardTitle>
        <CardDescription>
          Maximum: {maxDrawdown.toFixed(1)}%
          {maxDdDuration ? ` (${maxDdDuration} days)` : ""}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={250}>
          <AreaChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
            <XAxis
              dataKey="date"
              tickFormatter={formatDate}
              tick={{ fontSize: 11 }}
              interval="preserveStartEnd"
              minTickGap={50}
            />
            <YAxis
              tickFormatter={(value) => `${value.toFixed(0)}%`}
              tick={{ fontSize: 11 }}
              domain={["dataMin", 0]}
              width={50}
            />
            <Tooltip
              labelFormatter={(date) =>
                new Date(date).toLocaleDateString("en-IN", {
                  day: "numeric",
                  month: "short",
                  year: "numeric",
                })
              }
              formatter={(value) => [`${Number(value).toFixed(2)}%`, "Drawdown"]}
              contentStyle={{
                backgroundColor: "var(--popover)",
                color: "var(--popover-foreground)",
                border: "1px solid var(--border)",
                borderRadius: "8px",
              }}
            />

            {/* Max drawdown reference line */}
            <ReferenceLine
              y={maxDrawdown}
              stroke="var(--negative)"
              strokeDasharray="4 4"
              label={{
                value: `Max: ${maxDrawdown.toFixed(1)}%`,
                position: "insideBottomLeft",
                fill: "var(--negative)",
                fontSize: 11,
              }}
            />

            {/* Zero line */}
            <ReferenceLine y={0} stroke="var(--border)" />

            {/* Drawdown area */}
            <Area
              type="monotone"
              dataKey="drawdown"
              name="Drawdown"
              stroke="var(--negative)"
              fill="var(--negative)"
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
