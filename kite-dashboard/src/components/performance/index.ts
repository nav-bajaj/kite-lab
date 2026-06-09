"use client";

import dynamic from "next/dynamic";
import {
  EquityCurveFallback,
  DrawdownChartFallback,
} from "@/components/charts/chart-fallbacks";

export { MetricsGrid } from "./metrics-grid";
export { MonthlyHeatmap } from "./monthly-heatmap";
export { AdditionalMetrics } from "./additional-metrics";

// Recharts-backed charts load lazily so recharts stays out of the initial
// route bundle. ssr:false: ResponsiveContainer needs the DOM and the data
// is client-fetched anyway, so the static prerender shows the skeleton.
export const EquityCurve = dynamic(
  () => import("./equity-curve").then((m) => m.EquityCurve),
  { loading: EquityCurveFallback, ssr: false }
);

export const DrawdownChart = dynamic(
  () => import("./drawdown-chart").then((m) => m.DrawdownChart),
  { loading: DrawdownChartFallback, ssr: false }
);
