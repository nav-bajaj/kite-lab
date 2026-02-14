"use client";

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { useRebalancePreview } from "@/lib/hooks";
import { Plus, Minus } from "lucide-react";

export function ChangesPreview() {
  const { data, isLoading, error } = useRebalancePreview();

  if (isLoading) {
    return <ChangesPreviewSkeleton />;
  }

  if (error || !data) {
    return (
      <Card>
        <CardContent className="pt-6">
          <p className="text-sm text-muted-foreground">Failed to load preview</p>
        </CardContent>
      </Card>
    );
  }

  if (data.message) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>Changes Preview</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">{data.message}</p>
        </CardContent>
      </Card>
    );
  }

  const additions = data.additions || [];
  const removals = data.removals || [];
  const hasChanges = additions.length > 0 || removals.length > 0;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Changes Preview</CardTitle>
        <CardDescription>
          {data.signal_date
            ? `Signal date: ${data.signal_date}`
            : "Upcoming portfolio changes"}
        </CardDescription>
      </CardHeader>
      <CardContent>
        {!hasChanges ? (
          <p className="text-sm text-muted-foreground text-center py-4">
            No changes in the upcoming rebalance
          </p>
        ) : (
          <div className="grid md:grid-cols-2 gap-6">
            {/* Additions */}
            <div>
              <div className="flex items-center gap-2 mb-3">
                <div className="p-1 rounded bg-green-100 dark:bg-green-900">
                  <Plus className="h-4 w-4 text-green-600" />
                </div>
                <h3 className="font-medium">Additions ({data.additions_count || 0})</h3>
              </div>
              {additions.length === 0 ? (
                <p className="text-sm text-muted-foreground">No additions</p>
              ) : (
                <div className="space-y-2">
                  {additions.map((item) => (
                    <div
                      key={item.symbol}
                      className="flex items-center justify-between p-2 rounded-lg border bg-green-50 dark:bg-green-950"
                    >
                      <div className="flex items-center gap-2">
                        <span className="font-medium">{item.symbol}</span>
                        <Badge variant="outline" className="text-xs">
                          Rank {item.rank}
                        </Badge>
                      </div>
                      {item.score && (
                        <span className="text-sm text-muted-foreground">
                          {item.score.toFixed(2)}
                        </span>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Removals */}
            <div>
              <div className="flex items-center gap-2 mb-3">
                <div className="p-1 rounded bg-red-100 dark:bg-red-900">
                  <Minus className="h-4 w-4 text-red-600" />
                </div>
                <h3 className="font-medium">Removals ({data.removals_count || 0})</h3>
              </div>
              {removals.length === 0 ? (
                <p className="text-sm text-muted-foreground">No removals</p>
              ) : (
                <div className="space-y-2">
                  {removals.map((item) => (
                    <div
                      key={item.symbol}
                      className="flex items-center justify-between p-2 rounded-lg border bg-red-50 dark:bg-red-950"
                    >
                      <div className="flex items-center gap-2">
                        <span className="font-medium">{item.symbol}</span>
                        {item.prev_rank && (
                          <Badge variant="outline" className="text-xs">
                            Was #{item.prev_rank}
                          </Badge>
                        )}
                      </div>
                      <span className="text-xs text-muted-foreground">
                        {item.reason}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function ChangesPreviewSkeleton() {
  return (
    <Card>
      <CardHeader>
        <Skeleton className="h-5 w-32" />
        <Skeleton className="h-4 w-48" />
      </CardHeader>
      <CardContent>
        <div className="grid md:grid-cols-2 gap-6">
          <div className="space-y-2">
            <Skeleton className="h-6 w-24" />
            {[...Array(3)].map((_, i) => (
              <Skeleton key={i} className="h-12 w-full" />
            ))}
          </div>
          <div className="space-y-2">
            <Skeleton className="h-6 w-24" />
            {[...Array(3)].map((_, i) => (
              <Skeleton key={i} className="h-12 w-full" />
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
