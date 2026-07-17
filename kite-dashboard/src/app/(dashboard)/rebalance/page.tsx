"use client";

import { ActionableTrades, RebalanceHistory } from "@/components/rebalance";

export default function RebalancePage() {
  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Upcoming Trades</h1>
        <p className="text-muted-foreground">
          The next moves this portfolio plans to make — and a record of every
          past one.
        </p>
      </div>

      {/* The hero — what's about to change, or a countdown to it */}
      <ActionableTrades />

      {/* Expandable log of past rebalances */}
      <RebalanceHistory />
    </div>
  );
}
