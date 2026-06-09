"use client";

import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  TrendingUp,
  TrendingDown,
  DollarSign,
  PiggyBank,
  Clock,
  Activity,
} from "lucide-react";
import { formatCurrency, formatPercentValue, getPnLClass } from "@/lib/utils";
import { FlashOnChange } from "@/components/ui/flash-on-change";
import type { PositionsSummary as PositionsSummaryType, MarketStatus } from "@/lib/types";

interface PositionsSummaryProps {
  summary: PositionsSummaryType | null;
  marketStatus: MarketStatus | null;
  isLoading: boolean;
}

export function PositionsSummary({
  summary,
  marketStatus,
  isLoading,
}: PositionsSummaryProps) {
  if (isLoading) {
    return <PositionsSummarySkeleton />;
  }

  if (!summary) {
    return null;
  }

  const cards = [
    {
      title: "Total Invested",
      value: formatCurrency(summary.total_invested),
      flashValue: summary.total_invested,
      icon: PiggyBank,
      iconColor: "text-blue-500",
    },
    {
      title: "Current Value",
      value: formatCurrency(summary.total_current_value),
      flashValue: summary.total_current_value,
      icon: DollarSign,
      iconColor: "text-purple-500",
    },
    {
      title: "Total P&L",
      value: formatCurrency(summary.total_pnl),
      flashValue: summary.total_pnl,
      subValue: formatPercentValue(summary.total_pnl_pct),
      icon: summary.total_pnl >= 0 ? TrendingUp : TrendingDown,
      iconColor: summary.total_pnl >= 0 ? "text-green-500" : "text-red-500",
      valueColor: getPnLClass(summary.total_pnl),
    },
    {
      title: "Day P&L",
      value: formatCurrency(summary.day_pnl),
      flashValue: summary.day_pnl,
      subValue: formatPercentValue(summary.day_pnl_pct),
      icon: summary.day_pnl >= 0 ? TrendingUp : TrendingDown,
      iconColor: summary.day_pnl >= 0 ? "text-green-500" : "text-red-500",
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
                ? "Live prices from Zerodha"
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

      {/* Summary Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {cards.map((card) => (
          <Card key={card.title}>
            <CardContent className="pt-6">
              <div className="flex items-center justify-between">
                <div className="space-y-1">
                  <p className="text-sm text-muted-foreground">{card.title}</p>
                  <p className={`text-2xl font-bold ${card.valueColor || ""}`}>
                    <FlashOnChange value={card.flashValue}>
                      {card.value}
                    </FlashOnChange>
                  </p>
                  {card.subValue && (
                    <p className={`text-sm ${card.valueColor || ""}`}>
                      {card.subValue}
                    </p>
                  )}
                </div>
                <card.icon className={`h-8 w-8 ${card.iconColor}`} />
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

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
        {marketStatus && (
          <div className="flex items-center gap-2 ml-auto">
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
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {[1, 2, 3, 4].map((i) => (
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
