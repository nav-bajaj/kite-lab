"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { usePortfolio } from "@/lib/hooks";
import { formatCurrency, formatPercentValue } from "@/lib/utils";
import { TrendingUp, TrendingDown, Wallet, BarChart3, PieChart } from "lucide-react";

export function ValueCards() {
  const { data, isLoading, error } = usePortfolio();

  if (isLoading) {
    return <ValueCardsSkeleton />;
  }

  if (error || !data) {
    return (
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">Failed to load portfolio data</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const stats = [
    {
      title: "Portfolio Value",
      value: formatCurrency(data.total_value),
      subtitle: `${data.holdings_count} holdings`,
      icon: Wallet,
      trend: null,
    },
    {
      title: "Total Return",
      value: formatPercentValue(data.total_return_pct),
      subtitle: formatCurrency(data.total_return),
      icon: data.total_return >= 0 ? TrendingUp : TrendingDown,
      trend: data.total_return >= 0 ? "up" : "down",
    },
    {
      title: "CAGR",
      value: data.cagr ? formatPercentValue(data.cagr) : "—",
      subtitle: "Annualized return",
      icon: BarChart3,
      trend: data.cagr && data.cagr > 0 ? "up" : null,
    },
    {
      title: "Max Drawdown",
      value: data.max_drawdown ? formatPercentValue(data.max_drawdown) : "—",
      subtitle: "Historical worst",
      icon: TrendingDown,
      trend: "down",
    },
  ];

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      {stats.map((stat) => (
        <Card key={stat.title}>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">{stat.title}</CardTitle>
            <stat.icon className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stat.value}</div>
            <p
              className={`text-xs ${
                stat.trend === "up"
                  ? "text-green-600 dark:text-green-400"
                  : stat.trend === "down"
                  ? "text-red-600 dark:text-red-400"
                  : "text-muted-foreground"
              }`}
            >
              {stat.subtitle}
            </p>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

function ValueCardsSkeleton() {
  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      {[1, 2, 3, 4].map((i) => (
        <Card key={i}>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <Skeleton className="h-4 w-24" />
            <Skeleton className="h-4 w-4" />
          </CardHeader>
          <CardContent>
            <Skeleton className="h-8 w-32 mb-1" />
            <Skeleton className="h-3 w-20" />
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
