"use client";

import { useState } from "react";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useRebalanceHistory } from "@/lib/hooks";
import { formatCurrency } from "@/lib/utils";
import type { RebalanceHistoryItem } from "@/lib/types";
import { ChevronDown, ChevronRight } from "lucide-react";

const fmtDate = (d: string) => {
  const parsed = new Date(d);
  if (Number.isNaN(parsed.getTime())) return d;
  return parsed.toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
};

const isNoActionRow = (row: RebalanceHistoryItem) =>
  row.no_action === true || (row.additions === 0 && row.removals === 0);

export function RebalanceHistory({ limit = 12 }: { limit?: number }) {
  const { data, isLoading, error } = useRebalanceHistory(limit);

  if (isLoading) return <HistorySkeleton />;

  if (error || !data) {
    return (
      <Card>
        <CardContent className="pt-6">
          <p className="text-sm text-muted-foreground">Failed to load history</p>
        </CardContent>
      </Card>
    );
  }

  const history = data.history || [];

  return (
    <Card>
      <CardHeader>
        <CardTitle>Past rebalances</CardTitle>
        <CardDescription>
          Every recent reshuffle — tap a row to see exactly what changed.
        </CardDescription>
      </CardHeader>
      <CardContent>
        {history.length === 0 ? (
          <p className="py-4 text-center text-sm text-muted-foreground">
            No rebalance history yet.
          </p>
        ) : (
          <div className="divide-y rounded-md border">
            {history.map((row) => (
              <HistoryRow key={row.date} row={row} />
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function HistoryRow({ row }: { row: RebalanceHistoryItem }) {
  const noAction = isNoActionRow(row);
  const [open, setOpen] = useState(false);

  return (
    <div>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center gap-3 px-3 py-3 text-left transition-colors hover:bg-muted/50"
      >
        <span className="text-muted-foreground">
          {open ? (
            <ChevronDown className="h-4 w-4" />
          ) : (
            <ChevronRight className="h-4 w-4" />
          )}
        </span>
        <span className="min-w-0 flex-1">
          <span className="font-medium">{fmtDate(row.date)}</span>
        </span>
        <span className="shrink-0 text-sm text-muted-foreground">
          {noAction ? (
            <Badge variant="outline" className="text-[10px] uppercase tracking-wide">
              No changes
            </Badge>
          ) : (
            <span className="flex items-center gap-2">
              {row.additions > 0 && (
                <span className="text-green-600">+{row.additions}</span>
              )}
              {row.removals > 0 && (
                <span className="text-red-600">−{row.removals}</span>
              )}
            </span>
          )}
        </span>
      </button>

      {open && (
        <div className="space-y-3 bg-muted/30 px-3 pb-4 pl-10 pt-1 text-sm">
          {noAction ? (
            <p className="text-muted-foreground">
              The strategy reviewed the market this day but the leaders barely
              shifted, so it held every name it already owned. No trades were
              placed — a deliberate no-change, not a missed rebalance.
            </p>
          ) : (
            <>
              {row.added && row.added.length > 0 && (
                <div className="space-y-1.5">
                  <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                    Bought in
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {row.added.map((s) => (
                      <Badge
                        key={`add-${s}`}
                        variant="outline"
                        className="border-green-600 text-green-700 dark:text-green-400"
                      >
                        + {s}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
              {row.removed && row.removed.length > 0 && (
                <div className="space-y-1.5">
                  <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                    Sold out
                  </p>
                  <div className="flex flex-wrap gap-1.5">
                    {row.removed.map((s) => (
                      <Badge
                        key={`rem-${s}`}
                        variant="outline"
                        className="border-red-600 text-red-700 dark:text-red-400"
                      >
                        − {s}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
              <div className="flex flex-wrap gap-x-6 gap-y-1 pt-1 text-xs text-muted-foreground">
                {row.turnover_pct !== null && (
                  <span>
                    <span className="font-medium text-foreground">
                      {row.turnover_pct.toFixed(1)}%
                    </span>{" "}
                    of the portfolio changed hands
                  </span>
                )}
                <span>
                  <span className="font-medium text-foreground">
                    {formatCurrency(row.notional)}
                  </span>{" "}
                  traded{" "}
                  <span className="opacity-70">(model book, not your capital)</span>
                </span>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}

function HistorySkeleton() {
  return (
    <Card>
      <CardHeader>
        <Skeleton className="h-5 w-40" />
        <Skeleton className="h-4 w-56" />
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          {[...Array(5)].map((_, i) => (
            <Skeleton key={i} className="h-11 w-full" />
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
