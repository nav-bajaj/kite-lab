"use client";

import {
  OverviewHeader,
  ValueSummary,
  ReturnsCompare,
  TopContributors,
  HoldingsTable,
  AllocationChart,
} from "@/components/portfolio";

export default function OverviewPage() {
  return (
    <div className="space-y-6">
      {/* Which portfolio, in plain language */}
      <OverviewHeader />

      {/* Value + cost, Current Profit, avg age, current drawdown */}
      <ValueSummary />

      {/* Rolling returns vs the four headline indices */}
      <ReturnsCompare />

      {/* What's driving it — top gainers / laggards */}
      <TopContributors />

      {/* The stocks */}
      <HoldingsTable />

      {/* Allocation by sector — full-width at the bottom */}
      <AllocationChart />
    </div>
  );
}
