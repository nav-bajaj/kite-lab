"use client";

import { StatusCard, ChangesPreview, OrdersTable } from "@/components/rebalance";

export default function RebalancePage() {
  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Rebalance</h1>
        <p className="text-muted-foreground">
          Weekly portfolio rebalancing workflow
        </p>
      </div>

      {/* Status Card */}
      <StatusCard />

      {/* Changes Preview (Thursday) */}
      <ChangesPreview />

      {/* Orders Table (Friday) */}
      <OrdersTable />
    </div>
  );
}
