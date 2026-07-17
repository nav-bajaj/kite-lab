"use client";

import { TradeSummary, TradesTable } from "@/components/trades";

export default function TradesPage() {
  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="space-y-3">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Trade Log</h1>
          <p className="text-muted-foreground">
            Every trade the model portfolio has ever made.
          </p>
        </div>
        <div className="rounded-lg border border-border bg-muted/40 px-4 py-3">
          <p className="text-sm leading-relaxed text-muted-foreground">
            A <span className="font-medium text-foreground">complete, traceable</span>{" "}
            record — every buy and sell, methodically kept and reconciled against
            our backtests. The log you see is the same history the strategy was{" "}
            <span className="font-medium text-foreground">validated on</span>, not
            a curated highlight reel.
          </p>
        </div>
      </div>

      {/* Summary Stats */}
      <TradeSummary />

      {/* Trades Table */}
      <TradesTable />
    </div>
  );
}
