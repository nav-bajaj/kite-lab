"use client";

import {
  MetricsGrid,
  EquityCurve,
  DrawdownChart,
  MonthlyHeatmap,
  AdditionalMetrics,
} from "@/components/performance";

export default function PerformancePage() {
  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Performance</h1>
        <p className="text-muted-foreground">
          Historical performance metrics and analysis
        </p>
      </div>

      {/* Primary Metrics Grid */}
      <MetricsGrid />

      {/* Equity Curve Chart */}
      <EquityCurve />

      {/* Secondary Charts Row */}
      <div className="grid gap-6 lg:grid-cols-2">
        <DrawdownChart />
        <MonthlyHeatmap />
      </div>

      {/* Additional Metrics */}
      <AdditionalMetrics />
    </div>
  );
}
