"use client";

import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useTradeSummary } from "@/lib/hooks";
import {
  ArrowUpRight,
  ArrowDownRight,
  TrendingUp,
  TrendingDown,
  Trophy,
  Target,
  Clock,
} from "lucide-react";
import { cn } from "@/lib/utils";

const inrCompact = (v: number) => {
  const abs = Math.abs(v);
  const sign = v < 0 ? "-" : "";
  if (abs >= 10000000) return `${sign}₹${(abs / 10000000).toFixed(2)} Cr`;
  if (abs >= 100000) return `${sign}₹${(abs / 100000).toFixed(2)} L`;
  return `${sign}₹${abs.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;
};

export function TradeSummary() {
  const { data, isLoading, error } = useTradeSummary();

  if (isLoading) {
    return <TradeSummarySkeleton />;
  }

  if (error || !data) {
    return null;
  }

  const realizedPnl = data.realized_pnl_total;
  const winRate = data.win_rate;
  const avgHold = data.avg_holding_days;
  const bestPct = data.best_trade_pct;
  const worstPct = data.worst_trade_pct;
  const avgWinner = data.avg_winner_pct;
  const avgLoser = data.avg_loser_pct;

  const fmtPct = (v: number | null | undefined) =>
    v != null ? `${v >= 0 ? "+" : ""}${v.toFixed(2)}%` : "—";

  const performance = [
    {
      title: "Realized P&L",
      value: realizedPnl != null ? inrCompact(realizedPnl) : "—",
      icon: Trophy,
      color:
        realizedPnl != null
          ? realizedPnl >= 0
            ? "text-green-600"
            : "text-red-600"
          : "",
    },
    {
      title: "Win Rate",
      value: winRate != null ? `${winRate.toFixed(1)}%` : "—",
      icon: Target,
    },
    {
      title: "Avg Hold Days",
      value: avgHold != null ? avgHold.toFixed(1) : "—",
      icon: Clock,
    },
  ];

  const distribution = [
    {
      title: "Best Trade",
      value: fmtPct(bestPct),
      icon: ArrowUpRight,
      color: bestPct != null && bestPct > 0 ? "text-green-600" : "",
    },
    {
      title: "Worst Trade",
      value: fmtPct(worstPct),
      icon: ArrowDownRight,
      color: worstPct != null && worstPct < 0 ? "text-red-600" : "",
    },
    {
      title: "Avg Winner",
      value: fmtPct(avgWinner),
      icon: TrendingUp,
      color: avgWinner != null ? "text-green-600" : "",
    },
    {
      title: "Avg Loser",
      value: fmtPct(avgLoser),
      icon: TrendingDown,
      color: avgLoser != null ? "text-red-600" : "",
    },
  ];

  return (
    <div className="space-y-4">
      <div className="grid gap-4 md:grid-cols-3">
        {performance.map((stat) => (
          <StatCard key={stat.title} {...stat} />
        ))}
      </div>
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {distribution.map((stat) => (
          <StatCard key={stat.title} {...stat} />
        ))}
      </div>
    </div>
  );
}

function StatCard({
  title,
  value,
  icon: Icon,
  color,
}: {
  title: string;
  value: string;
  icon: React.ComponentType<{ className?: string }>;
  color?: string;
}) {
  return (
    <Card>
      <CardContent className="pt-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-muted-foreground">
              {title}
            </p>
            <p className={cn("text-2xl font-bold", color)}>{value}</p>
          </div>
          <Icon className="h-8 w-8 text-muted-foreground/30" />
        </div>
      </CardContent>
    </Card>
  );
}

function TradeSummarySkeleton() {
  return (
    <div className="space-y-4">
      <div className="grid gap-4 md:grid-cols-3">
        {[...Array(3)].map((_, i) => (
          <SkeletonCard key={i} />
        ))}
      </div>
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {[...Array(4)].map((_, i) => (
          <SkeletonCard key={i} />
        ))}
      </div>
    </div>
  );
}

function SkeletonCard() {
  return (
    <Card>
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
  );
}
