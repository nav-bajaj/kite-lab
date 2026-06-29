"use client";

import {
  ActionableTrades,
  RebalanceHistory,
  RebalanceSummary,
} from "@/components/rebalance";

export default function RebalancePage() {
  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Rebalance</h1>
        <p className="text-muted-foreground">
          When this portfolio last rebalanced and when it&apos;s due next
        </p>
      </div>

      {/* Actionable trades — what to do at the upcoming rebalance */}
      <ActionableTrades />

      {/* Previous + next rebalance, cadence */}
      <RebalanceSummary />

      {/* History timeline */}
      <RebalanceHistory />
    </div>
  );
}
