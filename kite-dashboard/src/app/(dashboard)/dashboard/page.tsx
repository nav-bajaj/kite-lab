"use client";

import { ValueCards, HoldingsTable, AllocationChart } from "@/components/portfolio";

export default function DashboardPage() {
  return (
    <div className="space-y-6">
      {/* Portfolio Value Cards */}
      <ValueCards />

      {/* Holdings Table and Allocation Chart */}
      <div className="grid gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <HoldingsTable />
        </div>
        <div>
          <AllocationChart />
        </div>
      </div>
    </div>
  );
}
