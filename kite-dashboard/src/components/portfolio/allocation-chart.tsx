"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useHoldings } from "@/lib/hooks";
import { formatCurrency } from "@/lib/utils";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from "recharts";

// Allocation-pie palette derived from the brand chart hues (DESIGN.md §
// chart-1..5: lichen, signal-green, slate-blue, violet, ochre) plus
// tints/shades, ordered for adjacent-slice contrast. Mid-tones only, so
// every slice reads against both the light (#FFFFFF) and dark (#171717)
// card. Static hex (not var()) because a 25-slice categorical scale needs
// more steps than the five themeable --chart-* tokens provide.
const COLORS = [
  "#14715F", // lichen
  "#9750F8", // violet
  "#C39B5A", // ochre (light)
  "#42608E", // slate-blue
  "#55C374", // signal-green
  "#2E9B7E", // teal (lichen tint)
  "#B08CF0", // violet (light)
  "#9E6A35", // ochre
  "#6B8FC9", // slate-blue (light)
  "#86D89E", // signal-green (light)
  "#7A3FC9", // violet (deep)
  "#3E8E78", // lichen (mid)
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
        <div className="h-[200px] mb-4">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={chartData}
                cx="50%"
                cy="50%"
                innerRadius={50}
                outerRadius={80}
                paddingAngle={1}
                dataKey="value"
              >
                {chartData.map((_, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                ))}
              </Pie>
              <Tooltip content={<CustomTooltip />} />
            </PieChart>
          </ResponsiveContainer>
        </div>
        {/* Scrollable legend */}
        <div className="max-h-[150px] overflow-y-auto">
          <div className="grid grid-cols-2 gap-1">
            {chartData.map((item, index) => (
              <div key={item.name} className="flex items-center gap-2 text-xs">
                <div
                  className="w-3 h-3 rounded-sm flex-shrink-0"
                  style={{ backgroundColor: COLORS[index % COLORS.length] }}
                />
                <span className="truncate">{item.name}</span>
                <span className="text-muted-foreground ml-auto">{item.value.toFixed(1)}%</span>
              </div>
            ))}
          </div>
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
        Weight: {data.value.toFixed(2)}%
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
