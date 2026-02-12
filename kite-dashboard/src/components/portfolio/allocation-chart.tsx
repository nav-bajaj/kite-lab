"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useHoldings } from "@/lib/hooks";
import { formatPercent, formatCurrency } from "@/lib/utils";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend } from "recharts";

// Color palette for the pie chart
const COLORS = [
  "#3b82f6", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6",
  "#ec4899", "#06b6d4", "#84cc16", "#f97316", "#6366f1",
  "#14b8a6", "#eab308", "#e11d48", "#7c3aed", "#0ea5e9",
  "#22c55e", "#fbbf24", "#dc2626", "#a855f7", "#0891b2",
  "#65a30d", "#d97706", "#be123c", "#6d28d9",
];

export function AllocationChart() {
  const { data, isLoading, error } = useHoldings();

  if (isLoading) {
    return <AllocationChartSkeleton />;
  }

  if (error || !data || data.holdings.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Allocation</CardTitle>
          <CardDescription>Position weights</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">No allocation data available</p>
        </CardContent>
      </Card>
    );
  }

  // Prepare data for pie chart
  const chartData = data.holdings
    .map((h) => ({
      name: h.symbol,
      value: h.weight,
      notional: h.notional,
    }))
    .sort((a, b) => b.value - a.value);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Allocation</CardTitle>
        <CardDescription>
          Position weights across {chartData.length} holdings
        </CardDescription>
      </CardHeader>
      <CardContent>
        <div className="h-[300px]">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={chartData}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={100}
                paddingAngle={1}
                dataKey="value"
              >
                {chartData.map((_, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip content={<CustomTooltip />} />
              <Legend
                layout="vertical"
                align="right"
                verticalAlign="middle"
                formatter={(value) => <span className="text-xs">{value}</span>}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </CardContent>
    </Card>
  );
}

function CustomTooltip({ active, payload }: { active?: boolean; payload?: Array<{ payload: { name: string; value: number; notional: number } }> }) {
  if (!active || !payload || !payload.length) {
    return null;
  }

  const data = payload[0].payload;

  return (
    <div className="rounded-lg border bg-background p-2 shadow-md">
      <p className="font-medium">{data.name}</p>
      <p className="text-sm text-muted-foreground">
        Weight: {formatPercent(data.value)}
      </p>
      <p className="text-sm text-muted-foreground">
        Value: {formatCurrency(data.notional)}
      </p>
    </div>
  );
}

function AllocationChartSkeleton() {
  return (
    <Card>
      <CardHeader>
        <Skeleton className="h-6 w-24" />
        <Skeleton className="h-4 w-40" />
      </CardHeader>
      <CardContent>
        <div className="flex items-center justify-center h-[300px]">
          <Skeleton className="h-[200px] w-[200px] rounded-full" />
        </div>
      </CardContent>
    </Card>
  );
}
