"use client";

import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useRebalanceHistory } from "@/lib/hooks";
import { formatCurrency } from "@/lib/utils";

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
  const hasNoAction = history.some(
    (r) => r.no_action === true || (r.additions === 0 && r.removals === 0),
  );

  return (
    <Card>
      <CardHeader>
        <CardTitle>Rebalance history</CardTitle>
        <CardDescription>Recent rebalance activity</CardDescription>
      </CardHeader>
      <CardContent>
        {history.length === 0 ? (
          <p className="py-4 text-center text-sm text-muted-foreground">
            No rebalance history yet.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left text-muted-foreground">
                  <th className="py-2 pr-4 font-medium">Date</th>
                  <th className="py-2 pr-4 font-medium text-right">Added</th>
                  <th className="py-2 pr-4 font-medium text-right">Removed</th>
                  <th className="py-2 pr-4 font-medium text-right">Turnover</th>
                  <th className="py-2 font-medium text-right">
                    Traded
                    <span className="ml-1 font-normal opacity-70">(model)</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {history.map((row) => {
                  // A cycle with zero adds AND zero removes is a no-action
                  // hold even if the backend didn't flag it (audit U9).
                  const isNoAction =
                    row.no_action === true ||
                    (row.additions === 0 && row.removals === 0);
                  return (
                    <tr
                      key={row.date}
                      className={
                        "border-b last:border-0" +
                        (isNoAction ? " text-muted-foreground italic" : "")
                      }
                    >
                      <td className="py-2 pr-4 font-medium">
                        {row.date}
                        {isNoAction && (
                          <span className="ml-2 rounded-sm bg-muted px-1.5 py-0.5 text-[10px] font-normal not-italic uppercase tracking-wide text-muted-foreground">
                            no-action
                          </span>
                        )}
                      </td>
                      <td className={
                        "py-2 pr-4 text-right " +
                        (isNoAction ? "" : "text-green-600")
                      }>
                        {isNoAction ? "—" : row.additions}
                      </td>
                      <td className={
                        "py-2 pr-4 text-right " +
                        (isNoAction ? "" : "text-red-600")
                      }>
                        {isNoAction ? "—" : row.removals}
                      </td>
                      <td className="py-2 pr-4 text-right text-muted-foreground">
                        {isNoAction
                          ? "—"
                          : row.turnover_pct !== null
                            ? `${row.turnover_pct.toFixed(1)}%`
                            : "—"}
                      </td>
                      <td className="py-2 text-right text-muted-foreground">
                        {isNoAction ? "—" : formatCurrency(row.notional)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            {hasNoAction && (
              <p className="mt-3 text-xs text-muted-foreground">
                <span className="font-medium">No-action</span> cycles are
                signal days where the engine reviewed the book but the
                rotation stayed inside the exit buffer, so it held the
                existing names. Not a missed rebalance.
              </p>
            )}
            <p className="mt-1 text-xs text-muted-foreground">
              <span className="font-medium">Traded (model)</span> is the model
              portfolio&apos;s notional — not scaled to your own capital.
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function HistorySkeleton() {
  return (
    <Card>
      <CardHeader>
        <Skeleton className="h-5 w-40" />
        <Skeleton className="h-4 w-32" />
      </CardHeader>
      <CardContent>
        <div className="space-y-2">
          {[...Array(5)].map((_, i) => (
            <Skeleton key={i} className="h-8 w-full" />
          ))}
        </div>
      </CardContent>
    </Card>
  );
}
