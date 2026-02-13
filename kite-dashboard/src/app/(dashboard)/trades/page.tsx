"use client";

import { TradeSummary, TradesTable } from "@/components/trades";

export default function TradesPage() {
  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Trade History</h1>
        <p className="text-muted-foreground">
          All executed trades with filtering and export
        </p>
      </div>

      {/* Summary Stats */}
      <TradeSummary />

      {/* Trades Table */}
      <TradesTable />
    </div>
  );
}
