"use client";

import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useTradeSummary } from "@/lib/hooks";
import { TrendingUp, TrendingDown, Calendar, DollarSign } from "lucide-react";

export function TradeSummary() {
  const { data, isLoading, error } = useTradeSummary();

  if (isLoading) {
    return <TradeSummarySkeleton />;
  }

  if (error || !data) {
    return null;
  }

  const stats = [
    {
      title: "Total Trades",
      value: data.total_trades.toLocaleString(),
      icon: Calendar,
    },
    {
      title: "Buys",
      value: data.buys.toLocaleString(),
      icon: TrendingUp,
      color: "text-green-600",
    },
    {
      title: "Sells",
      value: data.sells.toLocaleString(),
      icon: TrendingDown,
      color: "text-red-600",
    },
    {
      title: "Total Notional",
      value: (data.total_notional / 10000000).toFixed(1) + " Cr",
      icon: DollarSign,
    },
  ];

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      {stats.map((stat) => (
        <Card key={stat.title}>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-muted-foreground">
                  {stat.title}
                </p>
                <p className={`text-2xl font-bold ${stat.color || ""}`}>
                  {stat.value}
                </p>
              </div>
              <stat.icon className="h-8 w-8 text-muted-foreground/30" />
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

function TradeSummarySkeleton() {
  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      {[...Array(4)].map((_, i) => (
        <Card key={i}>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div className="space-y-2">
                <Skeleton className="h-4 w-20" />
                <Skeleton className="h-8 w-16" />
              </div>
              <Skeleton className="h-8 w-8" />
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
