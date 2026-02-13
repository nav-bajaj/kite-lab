"use client";

import { useState, useMemo } from "react";
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
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { useEquityCurve, useMetrics } from "@/lib/hooks";

function formatCurrency(value: number): string {
  if (value >= 10000000) {
    return `${(value / 10000000).toFixed(2)} Cr`;
  }
  if (value >= 100000) {
    return `${(value / 100000).toFixed(2)} L`;
  }
  return value.toLocaleString("en-IN");
}

function formatDate(dateStr: string): string {
  const date = new Date(dateStr);
  return date.toLocaleDateString("en-IN", { month: "short", year: "2-digit" });
}

export function EquityCurve() {
  const { data: equityData, isLoading, error } = useEquityCurve();
  const { data: metricsData } = useMetrics();
  const [showBenchmark, setShowBenchmark] = useState(false);

  // Normalize benchmark to start at same value as portfolio
  const normalizedData = useMemo(() => {
    if (!equityData?.data || equityData.data.length === 0) return [];

    const firstPortfolioValue = equityData.data[0].portfolio_value;
    const firstBenchmarkValue = equityData.data[0].benchmark_value;

    if (!firstBenchmarkValue) return equityData.data;

    return equityData.data.map((item) => ({
      ...item,
      benchmark_normalized: item.benchmark_value
        ? (item.benchmark_value / firstBenchmarkValue) * firstPortfolioValue
        : null,
    }));
  }, [equityData]);

  if (isLoading) {
    return <EquityCurveSkeleton />;
  }

  if (error || !equityData?.data) {
    return (
      <Card>
        <CardContent className="pt-6">
          <p className="text-sm text-muted-foreground">Failed to load equity curve data</p>
        </CardContent>
      </Card>
    );
  }

  const totalReturn = metricsData?.returns.total_return ?? 0;
  const startDate = metricsData?.period.start ?? "";
  const endDate = metricsData?.period.end ?? "";

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <div>
          <CardTitle>Equity Curve</CardTitle>
          <CardDescription>
            {totalReturn > 0 ? "+" : ""}
            {totalReturn.toFixed(1)}% total return ({startDate} to {endDate})
          </CardDescription>
        </div>
        <ToggleGroup
          type="single"
          size="sm"
          value={showBenchmark ? "benchmark" : ""}
          onValueChange={(value) => setShowBenchmark(value === "benchmark")}
        >
          <ToggleGroupItem value="benchmark" aria-label="Toggle benchmark">
            Benchmark
          </ToggleGroupItem>
        </ToggleGroup>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={400}>
          <AreaChart data={normalizedData}>
            <defs>
              <linearGradient id="portfolioGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
            <XAxis
              dataKey="date"
              tickFormatter={formatDate}
              tick={{ fontSize: 11 }}
              interval="preserveStartEnd"
              minTickGap={50}
            />
            <YAxis
              tickFormatter={(value) => formatCurrency(value)}
              tick={{ fontSize: 11 }}
              width={80}
            />
            <Tooltip
              labelFormatter={(date) =>
                new Date(date).toLocaleDateString("en-IN", {
                  day: "numeric",
                  month: "short",
                  year: "numeric",
                })
              }
              formatter={(value, name) => [
                formatCurrency(Number(value)),
                name === "portfolio_value" ? "Portfolio" : "Benchmark",
              ]}
              contentStyle={{
                backgroundColor: "hsl(var(--background))",
                border: "1px solid hsl(var(--border))",
                borderRadius: "8px",
              }}
            />
            <Legend />
            <Area
              type="monotone"
              dataKey="portfolio_value"
              name="Portfolio"
              stroke="#3b82f6"
              fill="url(#portfolioGradient)"
              strokeWidth={2}
            />
            {showBenchmark && (
              <Area
                type="monotone"
                dataKey="benchmark_normalized"
                name="Nifty 100"
                stroke="#6b7280"
                fill="transparent"
                strokeWidth={1.5}
                strokeDasharray="4 4"
              />
            )}
          </AreaChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}

function EquityCurveSkeleton() {
  return (
    <Card>
      <CardHeader>
        <Skeleton className="h-5 w-32" />
        <Skeleton className="h-4 w-48" />
      </CardHeader>
      <CardContent>
        <Skeleton className="h-[400px] w-full" />
      </CardContent>
    </Card>
  );
}
