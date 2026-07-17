"use client";

import dynamic from "next/dynamic";
import { AllocationChartFallback } from "@/components/charts/chart-fallbacks";

export { ValueCards } from "./value-cards";
export { ValueSummary } from "./value-summary";
export { OverviewHeader } from "./overview-header";
export { ReturnsCompare } from "./returns-compare";
export { TopContributors } from "./top-contributors";
export { HoldingsTable } from "./holdings-table";

// AllocationChart is the only recharts-backed component here; load it
// lazily so recharts stays out of the dashboard's initial bundle.
export const AllocationChart = dynamic(
  () => import("./allocation-chart").then((m) => m.AllocationChart),
  { loading: AllocationChartFallback, ssr: false }
);
