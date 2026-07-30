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
import { AlertCircle, Loader2, RefreshCw } from "lucide-react";
import { useOptionsWorkerStatus } from "@/lib/hooks";
import { cn } from "@/lib/utils";

// Live view of the options data worker (separate Railway service). Answers
// "is the capture alive" from anywhere: phase, feed staleness, tick/packet
// counters, and the raw-tick recorder totals. Data source is the worker's
// 30s Postgres heartbeat — if that goes stale during market hours the dot
// goes red even though this page still loads fine.

function dotClass(status: "ok" | "warn" | "bad" | "off"): string {
  switch (status) {
    case "ok":
      return "bg-green-500";
    case "warn":
      return "bg-yellow-500";
    case "bad":
      return "bg-red-500";
    default:
      return "bg-muted-foreground";
  }
}

function Stat({ label, value, mono = true }: { label: string; value: React.ReactNode; mono?: boolean }) {
  return (
    <div className="space-y-0.5">
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className={cn("text-sm font-medium", mono && "tabular-nums")}>{value}</div>
    </div>
  );
}

export function OptionsWorkerPanel() {
  const { data, error, isLoading, mutate, isValidating } = useOptionsWorkerStatus();

  const snap = data?.snapshot;
  const ws = snap?.ws;
  // Live state outranks a stale error: a connected, fresh capture is
  // green even if last_error still holds a transient from hours ago
  // (the error strip below stays visible either way).
  const status: "ok" | "warn" | "bad" | "off" = !data?.found
    ? "off"
    : data.heartbeat_stale
    ? "bad"
    : data.phase === "capture"
    ? ws?.connected
      ? "ok"
      : "bad"
    : snap?.last_error
    ? "bad"
    : "warn";

  return (
    <Card>
      <CardHeader className="flex-row items-start justify-between space-y-0">
        <div className="space-y-1">
          <CardTitle className="flex items-center gap-2">
            <span className={cn("inline-block h-2.5 w-2.5 rounded-full", dotClass(status))} />
            Options Worker
            {data?.found && (
              <Badge variant={data.phase === "capture" ? "default" : "secondary"} className="uppercase tracking-wide">
                {data.phase}
              </Badge>
            )}
          </CardTitle>
          <CardDescription>
            {data?.found
              ? `Heartbeat ${Math.round(data.age_seconds ?? 0)}s ago${data.heartbeat_stale ? " — STALE" : ""}`
              : "No heartbeat yet — worker has not reported"}
          </CardDescription>
        </div>
        <Button
          variant="ghost"
          size="icon"
          className="h-7 w-7"
          onClick={() => mutate()}
          disabled={isValidating}
          aria-label="Refresh worker status"
        >
          <RefreshCw className={cn("h-3.5 w-3.5", isValidating && "animate-spin")} />
        </Button>
      </CardHeader>
      <CardContent>
        {error ? (
          <div className="flex items-center gap-2 text-sm text-destructive">
            <AlertCircle className="h-4 w-4" />
            Failed to load worker status
          </div>
        ) : isLoading && !data ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-5 w-5 animate-spin" />
          </div>
        ) : !data?.found ? (
          <p className="text-sm text-muted-foreground">
            The worker writes its first heartbeat within ~30s of booting.
          </p>
        ) : (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
              <Stat label="Selection date" value={snap?.selection_date ?? "—"} />
              <Stat label="Contracts" value={snap?.contracts ?? 0} />
              <Stat label="ATM strike" value={snap?.atm_strike ?? "—"} />
              <Stat label="Spot" value={snap?.chain?.spot_price ? snap.chain.spot_price.toFixed(2) : "—"} />
            </div>
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
              <Stat
                label="WebSocket"
                value={
                  ws ? (
                    <span className={ws.connected ? "text-green-600 dark:text-green-500" : "text-destructive"}>
                      {ws.connected ? "connected" : "disconnected"}
                    </span>
                  ) : (
                    "—"
                  )
                }
                mono={false}
              />
              <Stat label="Packets" value={ws?.packets?.toLocaleString() ?? "—"} />
              <Stat label="Reconnects" value={ws?.reconnects ?? "—"} />
              <Stat
                label="Feed staleness"
                value={snap?.staleness_seconds != null ? `${snap.staleness_seconds.toFixed(1)}s` : "—"}
              />
            </div>
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
              <Stat label="Contracts ticked" value={snap?.chain ? `${snap.chain.contracts_ticked}/${snap.chain.contracts}` : "—"} />
              <Stat label="Ticks applied" value={snap?.chain?.total_ticks?.toLocaleString() ?? "—"} />
              <Stat label="Rows recorded" value={snap?.recorder?.rows_written?.toLocaleString() ?? "—"} />
              <Stat label="Widen events" value={snap?.widen_events ?? 0} />
            </div>
            {snap?.last_error && (
              <div className="flex items-start gap-2 rounded-md border border-destructive/30 bg-destructive/5 p-2 text-xs text-destructive">
                <AlertCircle className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                {snap.last_error}
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
