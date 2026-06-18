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
                  <th className="py-2 font-medium text-right">Traded</th>
                </tr>
              </thead>
              <tbody>
                {history.map((row) => (
                  <tr key={row.date} className="border-b last:border-0">
                    <td className="py-2 pr-4 font-medium">{row.date}</td>
                    <td className="py-2 pr-4 text-right text-green-600">
                      {row.additions}
                    </td>
                    <td className="py-2 pr-4 text-right text-red-600">
                      {row.removals}
                    </td>
                    <td className="py-2 pr-4 text-right text-muted-foreground">
                      {row.turnover_pct !== null
                        ? `${row.turnover_pct.toFixed(1)}%`
                        : "—"}
                    </td>
                    <td className="py-2 text-right text-muted-foreground">
                      {formatCurrency(row.notional)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
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
