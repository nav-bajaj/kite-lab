"use client";

import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Clock, Activity, CalendarDays, PiggyBank, Wallet, TrendingUp, TrendingDown } from "lucide-react";
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

  // One combo card instead of four (UX study "D2" primitive): labeled cells
  // with mini accent-chip icons, hairline dividers, 2×2 on mobile / one row
  // on desktop. Divider classes are per-position: columns always split;
  // the second mobile row gains a top hairline that disappears at md.
  const cells = [
    {
      title: "Invested",
      value: formatCurrency(summary.total_invested),
      flashValue: summary.total_invested,
      icon: PiggyBank,
      chip: "bg-acc1 text-acc1-fg",
      divider: "",
    },
    {
      title: "Current value",
      value: formatCurrency(summary.total_current_value),
      flashValue: summary.total_current_value,
      icon: Wallet,
      chip: "bg-acc3 text-acc3-fg",
      divider: "border-l",
    },
    {
      title: "Total P&L",
      value: formatCurrency(summary.total_pnl),
      flashValue: summary.total_pnl,
      subValue: formatPercentValue(summary.total_pnl_pct),
      valueColor: getPnLClass(summary.total_pnl),
      icon: summary.total_pnl >= 0 ? TrendingUp : TrendingDown,
      chip: "bg-acc2 text-acc2-fg",
      divider: "border-t md:border-t-0 md:border-l",
    },
    {
      title: "Day P&L",
      value: formatCurrency(summary.day_pnl),
      flashValue: summary.day_pnl,
      subValue: formatPercentValue(summary.day_pnl_pct),
      valueColor: getPnLClass(summary.day_pnl),
      icon: summary.day_pnl >= 0 ? TrendingUp : TrendingDown,
      chip: "bg-acc4 text-acc4-fg",
      divider: "border-l border-t md:border-t-0",
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

      {/* Combo summary card (D2 primitive) */}
      <Card className="py-0">
        <CardContent className="p-0">
          <div className="grid grid-cols-2 md:grid-cols-4">
            {cells.map((cell) => (
              <div
                key={cell.title}
                className={`min-h-[86px] space-y-1 border-border px-4 py-4 sm:px-5 ${cell.divider}`}
              >
                <p className="flex items-center gap-1.5">
                  <span
                    className={`flex h-5 w-5 items-center justify-center rounded-md ${cell.chip}`}
                  >
                    <cell.icon className="h-3 w-3" aria-hidden />
                  </span>
                  <span className="text-[11px] font-semibold uppercase tracking-[0.09em] text-muted-foreground">
                    {cell.title}
                  </span>
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

      {/* Stats Row — wraps on narrow screens (a rigid no-wrap row was wider
          than a phone and dragged the whole page into horizontal scroll);
          the meta pair right-aligns only from sm up. */}
      <div className="flex flex-wrap items-center gap-x-5 gap-y-1.5 text-sm text-muted-foreground">
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
            className="flex items-center gap-1.5 sm:ml-auto"
            title="The holdings shown, from the portfolio's most recent rebalance, priced live"
          >
            <CalendarDays className="h-3 w-3 shrink-0" />
            <span className="whitespace-nowrap">
              Holdings {holdingsDate.toLocaleDateString("en-IN", { day: "numeric", month: "short" })}
            </span>
          </div>
        )}
        {marketStatus && (
          <div className={`flex items-center gap-1.5 ${holdingsDate ? "" : "sm:ml-auto"}`}>
            <Clock className="h-3 w-3 shrink-0" />
            <span className="whitespace-nowrap">
              Updated {new Date(marketStatus.last_updated).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
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
