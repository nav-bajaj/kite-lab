"use client";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { AlertCircle, Loader2, RefreshCw } from "lucide-react";
import { useFreshnessReport } from "@/lib/hooks";
import { cn } from "@/lib/utils";
import type { FreshnessStatus, SourceFreshness } from "@/lib/api-client";

// Read-only ops view of the per-source data-freshness monitor. It exists so a
// silently frozen input (the INDIA_VIX incident) surfaces at a glance instead
// of hiding behind a current-looking reading date.

const STATUS_ORDER: Record<FreshnessStatus, number> = {
  critical: 0,
  missing: 1,
  stale: 2,
  fresh: 3,
};

function statusDotClass(status: FreshnessStatus): string {
  switch (status) {
    case "fresh":
      return "bg-green-500";
    case "stale":
      return "bg-yellow-500";
    case "critical":
      return "bg-red-500";
    default:
      return "bg-muted-foreground";
  }
}

function StatusBadge({ status }: { status: FreshnessStatus }) {
  const variant =
    status === "critical"
      ? "destructive"
      : status === "fresh"
      ? "default"
      : "secondary";
  return (
    <Badge variant={variant} className="uppercase tracking-wide">
      {status}
    </Badge>
  );
}

function SourceRow({ s }: { s: SourceFreshness }) {
  return (
    <TableRow>
      <TableCell>
        <span
          className={cn("inline-block h-2 w-2 rounded-full", statusDotClass(s.status))}
        />
      </TableCell>
      <TableCell className="font-medium">{s.name}</TableCell>
      <TableCell className="text-muted-foreground">{s.kind}</TableCell>
      <TableCell className="tabular-nums">{s.last_date ?? "—"}</TableCell>
      <TableCell className="tabular-nums text-right">
        {s.lag_trading_days ?? "—"}
      </TableCell>
      <TableCell>
        <StatusBadge status={s.status} />
      </TableCell>
      <TableCell className="max-w-[28rem] text-xs text-muted-foreground">
        {s.detail}
      </TableCell>
    </TableRow>
  );
}

export function FreshnessPanel() {
  const { data, error, isLoading, mutate, isValidating } = useFreshnessReport();

  const sources = data?.sources
    ? [...data.sources].sort(
        (a, b) => STATUS_ORDER[a.status] - STATUS_ORDER[b.status]
      )
    : [];

  return (
    <Card>
      <CardHeader className="flex-row items-start justify-between space-y-0">
        <div className="space-y-1">
          <CardTitle className="flex items-center gap-2">
            {data && (
              <span
                className={cn(
                  "inline-block h-2.5 w-2.5 rounded-full",
                  statusDotClass(data.overall_status)
                )}
              />
            )}
            Data Freshness
          </CardTitle>
          <CardDescription>
            {data?.generated_for_reference_date
              ? `Reference trading day: ${data.generated_for_reference_date}`
              : "Per-source staleness monitor"}
          </CardDescription>
        </div>
        <Button
          variant="ghost"
          size="icon"
          className="h-7 w-7"
          onClick={() => mutate()}
          disabled={isValidating}
          aria-label="Refresh freshness report"
        >
          <RefreshCw className={cn("h-3.5 w-3.5", isValidating && "animate-spin")} />
        </Button>
      </CardHeader>
      <CardContent>
        {error ? (
          <div className="flex items-center gap-2 text-sm text-destructive">
            <AlertCircle className="h-4 w-4" />
            Failed to load freshness report
          </div>
        ) : isLoading && !data ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-5 w-5 animate-spin" />
          </div>
        ) : (
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-8" />
                  <TableHead>Source</TableHead>
                  <TableHead>Kind</TableHead>
                  <TableHead>Last date</TableHead>
                  <TableHead className="text-right">Lag (td)</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Detail</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {sources.map((s) => (
                  <SourceRow key={`${s.kind}:${s.name}`} s={s} />
                ))}
              </TableBody>
            </Table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
