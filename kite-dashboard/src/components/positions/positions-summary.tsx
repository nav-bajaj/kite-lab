"use client";

import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Clock, Activity, CalendarDays } from "lucide-react";
import { formatCurrency, formatPercentValue, getPnLClass } from "@/lib/utils";
import { FlashOnChange } from "@/components/ui/flash-on-change";
import type { PositionsSummary as PositionsSummaryType, MarketStatus } from "@/lib/types";

interface PositionsSummaryProps {
  summary: PositionsSummaryType | null;
  marketStatus: MarketStatus | null;
  holdingsAsOf?: string | null;
  isLoading: boolean;
}

export function PositionsSummary({
  summary,
  marketStatus,
  holdingsAsOf,
  isLoading,
}: PositionsSummaryProps) {
  if (isLoading) {
    return <PositionsSummarySkeleton />;
  }

  if (!summary) {
    return null;
  }

  const holdingsDate = holdingsAsOf ? new Date(holdingsAsOf) : null;

  // One combo card instead of four (UX study pattern): the four headline
  // metrics share a card as labeled cells — a 2×2 grid on mobile (one card
  // of scroll instead of four), a single row on desktop.
  const cells = [
    {
      title: "Invested",
      value: formatCurrency(summary.total_invested),
      flashValue: summary.total_invested,
    },
    {
      title: "Current value",
      value: formatCurrency(summary.total_current_value),
      flashValue: summary.total_current_value,
    },
    {
      title: "Total P&L",
      value: formatCurrency(summary.total_pnl),
      flashValue: summary.total_pnl,
      subValue: formatPercentValue(summary.total_pnl_pct),
      valueColor: getPnLClass(summary.total_pnl),
    },
    {
      title: "Day P&L",
      value: formatCurrency(summary.day_pnl),
      flashValue: summary.day_pnl,
      subValue: formatPercentValue(summary.day_pnl_pct),
      valueColor: getPnLClass(summary.day_pnl),
    },
  ];

  return (
    <div className="space-y-4">
      {/* Market Status Banner */}
      {marketStatus && (
        <div className="flex items-center justify-between rounded-lg bg-muted/50 px-4 py-2">
          <div className="flex items-center gap-2">
            <Activity
              className={`h-4 w-4 ${
                marketStatus.is_open ? "text-green-500 animate-pulse" : "text-gray-400"
              }`}
            />
            <span className="text-sm text-muted-foreground">
              {marketStatus.is_open
                ? "Live market prices"
                : "Showing last closing prices"}
            </span>
          </div>
          <Badge variant={marketStatus.is_open ? "default" : "secondary"}>
            {marketStatus.status === "open"
              ? "Market Open"
              : marketStatus.status === "pre_open"
              ? "Pre-Market"
              : "Market Closed"}
          </Badge>
        </div>
      )}

      {/* Combo summary card */}
      <Card>
        <CardContent className="pt-6">
          <div className="grid grid-cols-2 gap-x-6 gap-y-5 md:grid-cols-4">
            {cells.map((cell) => (
              <div key={cell.title} className="space-y-1">
                <p className="text-[11px] font-semibold uppercase tracking-[0.1em] text-muted-foreground">
                  {cell.title}
                </p>
                <p className={`text-xl font-bold tabular-nums sm:text-2xl ${cell.valueColor || ""}`}>
                  <FlashOnChange value={cell.flashValue}>
                    {cell.value}
                  </FlashOnChange>
                </p>
                {cell.subValue && (
                  <p className={`text-sm tabular-nums ${cell.valueColor || ""}`}>
                    {cell.subValue}
                  </p>
                )}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Stats Row */}
      <div className="flex items-center gap-6 text-sm text-muted-foreground">
        <div className="flex items-center gap-2">
          <span className="font-medium">{summary.position_count}</span>
          <span>Positions</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-green-600 font-medium">{summary.winners}</span>
          <span>Winners</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-red-600 font-medium">{summary.losers}</span>
          <span>Losers</span>
        </div>
        {holdingsDate && (
          <div
            className="flex items-center gap-2 ml-auto"
            title="The holdings shown, from the portfolio's most recent rebalance, priced live"
          >
            <CalendarDays className="h-3 w-3" />
            <span>Holdings as of {holdingsDate.toLocaleDateString()}</span>
          </div>
        )}
        {marketStatus && (
          <div className={`flex items-center gap-2 ${holdingsDate ? "" : "ml-auto"}`}>
            <Clock className="h-3 w-3" />
            <span>
              Updated {new Date(marketStatus.last_updated).toLocaleTimeString()}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}

function PositionsSummarySkeleton() {
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <Skeleton className="h-5 w-40" />
        <Skeleton className="h-6 w-24" />
      </div>
      <div className="grid gap-4">
        {[1].map((i) => (
          <Card key={i}>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div className="space-y-2">
                  <Skeleton className="h-4 w-24" />
                  <Skeleton className="h-8 w-32" />
                  <Skeleton className="h-4 w-16" />
                </div>
                <Skeleton className="h-8 w-8 rounded-full" />
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
