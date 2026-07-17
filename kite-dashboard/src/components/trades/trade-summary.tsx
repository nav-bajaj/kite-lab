"use client";

import { useState } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useTradeSummary } from "@/lib/hooks";
import type { TradeDetail } from "@/lib/api-client";
import { InfoHint } from "@/components/shared/info-hint";
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

const fmtDate = (d: string) =>
  new Date(d).toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });

export function TradeSummary() {
  const { data, isLoading, error } = useTradeSummary();
  const [detail, setDetail] = useState<{ trade: TradeDetail; label: string } | null>(null);

  if (isLoading) {
    return <TradeSummarySkeleton />;
  }

  if (error || !data) {
    return null;
  }

  const fmtPct = (v: number | null | undefined) =>
    v != null ? `${v >= 0 ? "+" : ""}${v.toFixed(2)}%` : "—";

  const performance = [
    {
      title: "Realized P&L",
      value: data.realized_pnl_total != null ? inrCompact(data.realized_pnl_total) : "—",
      icon: Trophy,
      hint: "Total profit or loss actually banked from closed trades, net of costs. Open positions aren't counted here.",
      color:
        data.realized_pnl_total != null
          ? data.realized_pnl_total >= 0
            ? "text-green-600"
            : "text-red-600"
          : "",
    },
    {
      title: "Win Rate",
      value: data.win_rate != null ? `${data.win_rate.toFixed(1)}%` : "—",
      icon: Target,
      hint: "Share of matched trades (each sell matched to its buy lots, FIFO) that were profitable.",
    },
    {
      title: "Avg Hold Days",
      value: data.avg_holding_days != null ? data.avg_holding_days.toFixed(1) : "—",
      icon: Clock,
      hint: "How long a position is typically held, from buy to sell.",
    },
  ];

  const distribution = [
    {
      title: "Best Trade",
      value: fmtPct(data.best_trade_pct),
      icon: ArrowUpRight,
      hint: "The single most profitable matched trade. Click to see it.",
      color: data.best_trade_pct != null && data.best_trade_pct > 0 ? "text-green-600" : "",
      trade: data.best_trade ?? null,
    },
    {
      title: "Worst Trade",
      value: fmtPct(data.worst_trade_pct),
      icon: ArrowDownRight,
      hint: "The single biggest loss on a matched trade. Click to see it.",
      color: data.worst_trade_pct != null && data.worst_trade_pct < 0 ? "text-red-600" : "",
      trade: data.worst_trade ?? null,
    },
    {
      title: "Avg Winner",
      value: fmtPct(data.avg_winner_pct),
      icon: TrendingUp,
      hint: "Average gain across the trades that made money.",
      color: data.avg_winner_pct != null ? "text-green-600" : "",
    },
    {
      title: "Avg Loser",
      value: fmtPct(data.avg_loser_pct),
      icon: TrendingDown,
      hint: "Average loss across the trades that lost money.",
      color: data.avg_loser_pct != null ? "text-red-600" : "",
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
          <StatCard
            key={stat.title}
            {...stat}
            onClick={
              stat.trade
                ? () => setDetail({ trade: stat.trade!, label: stat.title })
                : undefined
            }
          />
        ))}
      </div>

      <Dialog open={!!detail} onOpenChange={(o) => !o && setDetail(null)}>
        <DialogContent>
          {detail && <TradeDetailView trade={detail.trade} label={detail.label} />}
        </DialogContent>
      </Dialog>
    </div>
  );
}

function StatCard({
  title,
  value,
  icon: Icon,
  color,
  hint,
  onClick,
}: {
  title: string;
  value: string;
  icon: React.ComponentType<{ className?: string }>;
  color?: string;
  hint?: string;
  onClick?: () => void;
}) {
  const clickable = !!onClick;
  return (
    <Card
      onClick={onClick}
      className={cn(clickable && "cursor-pointer transition-colors hover:border-primary/40")}
    >
      <CardContent className="pt-6">
        <div className="flex items-center justify-between">
          <div>
            <p className="flex items-center gap-1.5 text-sm font-medium text-muted-foreground">
              {title}
              {hint && <InfoHint text={hint} />}
            </p>
            <p className={cn("text-2xl font-bold", color)}>{value}</p>
            {clickable && (
              <p className="mt-0.5 text-xs text-primary">View trade →</p>
            )}
          </div>
          <Icon className="h-8 w-8 text-muted-foreground/30" />
        </div>
      </CardContent>
    </Card>
  );
}

function TradeDetailView({ trade, label }: { trade: TradeDetail; label: string }) {
  const up = trade.realized_pnl >= 0;
  return (
    <>
      <DialogHeader>
        <DialogTitle className="flex items-center gap-2">
          <span>{trade.symbol}</span>
          <span className="text-xs font-normal uppercase tracking-wide text-muted-foreground">
            {label}
          </span>
        </DialogTitle>
      </DialogHeader>
      <div className="space-y-4">
        <div
          className={cn(
            "text-3xl font-bold",
            up ? "text-[color:var(--positive)]" : "text-[color:var(--negative)]",
          )}
        >
          {trade.realized_pnl_pct >= 0 ? "+" : ""}
          {trade.realized_pnl_pct.toFixed(2)}%
          <span className="ml-2 text-base font-medium text-muted-foreground">
            {inrCompact(trade.realized_pnl)}
          </span>
        </div>

        <div className="grid grid-cols-2 gap-4 rounded-lg border border-border p-4 text-sm">
          <Field label="Bought" value={`${fmtDate(trade.entry_date)} @ ${trade.entry_price.toFixed(2)}`} />
          <Field label="Sold" value={`${fmtDate(trade.exit_date)} @ ${trade.exit_price.toFixed(2)}`} />
          <Field label="Shares" value={trade.shares.toLocaleString("en-IN")} />
          <Field label="Held for" value={`${trade.holding_days} days`} />
        </div>

        <p className="text-xs leading-relaxed text-muted-foreground">
          One matched trade (a sell matched to its buy lots, FIFO). Model
          portfolio, for education — not your own account.
        </p>
      </div>
    </>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex flex-col gap-0.5">
      <span className="text-xs text-muted-foreground">{label}</span>
      <span className="font-mono text-foreground">{value}</span>
    </div>
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
