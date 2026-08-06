"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useHoldings } from "@/lib/hooks";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from "recharts";

// Sector-pie palette from the accent-rotation tokens so the pie re-themes
// with the six-palette system (SVG presentation attributes resolve CSS
// variables). Slices 7-12 reuse the rotation softened toward the surface,
// keeping adjacent-slice contrast without hardcoding per-palette hexes.
const ACCENTS = [1, 2, 3, 4, 5, 6].map((n) => `var(--acc${n}-line)`);
const COLORS = [
  ...ACCENTS,
  ...ACCENTS.map((c) => `color-mix(in srgb, ${c} 55%, var(--background))`),
];

type SectorSlice = { name: string; value: number; count: number };

export function AllocationChart() {
  const { data, isLoading, error } = useHoldings();

  if (isLoading) {
    return <AllocationChartSkeleton />;
  }

  if (error || !data || data.holdings.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Allocation by sector</CardTitle>
          <CardDescription>How the portfolio is spread across sectors</CardDescription>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">No allocation data available</p>
        </CardContent>
      </Card>
    );
  }

  // Aggregate holding weights into sectors.
  const bySector = new Map<string, SectorSlice>();
  for (const h of data.holdings) {
    const name = h.sector && h.sector.trim() ? h.sector : "Uncategorised";
    const slice = bySector.get(name);
    if (slice) {
      slice.value += h.weight;
      slice.count += 1;
    } else {
      bySector.set(name, { name, value: h.weight, count: 1 });
    }
  }
  const chartData = Array.from(bySector.values()).sort((a, b) => b.value - a.value);

  // Plain-English read of the pie: leading sector + how spread out it is.
  const top = chartData[0];
  const topShare = top?.value ?? 0;
  const concentration =
    chartData.length <= 2
      ? `Concentrated in ${top?.name ?? "one sector"} (${topShare.toFixed(0)}%).`
      : topShare >= 40
        ? `Heavily tilted toward ${top.name} (${topShare.toFixed(0)}% of the portfolio), across ${chartData.length} sectors.`
        : topShare >= 25
          ? `Leaning toward ${top.name} (${topShare.toFixed(0)}%), but spread across ${chartData.length} sectors.`
          : `Well diversified — no single sector above ${topShare.toFixed(0)}%, across ${chartData.length} sectors.`;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Allocation by sector</CardTitle>
        <CardDescription>{concentration}</CardDescription>
      </CardHeader>
      <CardContent>
        <div className="grid gap-6 md:grid-cols-2">
          <div className="h-[240px]">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={chartData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={95}
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
          {/* Legend */}
          <div className="flex flex-col justify-center gap-1.5">
            {chartData.map((item, index) => (
              <div key={item.name} className="flex items-center gap-2 text-sm">
                <div
                  className="h-3 w-3 flex-shrink-0 rounded-sm"
                  style={{ backgroundColor: COLORS[index % COLORS.length] }}
                />
                <span className="truncate text-foreground">{item.name}</span>
                <span className="ml-auto shrink-0 tabular-nums text-muted-foreground">
                  {item.value.toFixed(1)}% · {item.count}
                </span>
              </div>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function CustomTooltip({
  active,
  payload,
}: {
  active?: boolean;
  payload?: Array<{ payload: SectorSlice }>;
}) {
  if (!active || !payload || !payload.length) {
    return null;
  }
  const d = payload[0].payload;
  return (
    <div className="rounded-lg border bg-background p-2 shadow-md">
      <p className="font-medium">{d.name}</p>
      <p className="text-sm text-muted-foreground">
        {d.value.toFixed(1)}% · {d.count} stock{d.count === 1 ? "" : "s"}
      </p>
    </div>
  );
}

function AllocationChartSkeleton() {
  return (
    <Card>
      <CardHeader>
        <Skeleton className="h-6 w-40" />
        <Skeleton className="h-4 w-56" />
      </CardHeader>
      <CardContent>
        <div className="flex h-[240px] items-center justify-center">
          <Skeleton className="h-[200px] w-[200px] rounded-full" />
        </div>
      </CardContent>
    </Card>
  );
}
