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
      <div className="space-y-3">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Performance</h1>
          <p className="text-muted-foreground">
            How the model portfolio has performed over its full history.
          </p>
        </div>
        <div className="rounded-lg border border-border bg-muted/40 px-4 py-3">
          <p className="text-sm leading-relaxed text-muted-foreground">
            These are <span className="font-medium text-foreground">backtested</span>{" "}
            results — how the strategy would have performed on historical data,
            net of estimated costs. They&apos;re for education and research, not a
            promise of future returns.
          </p>
        </div>
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
