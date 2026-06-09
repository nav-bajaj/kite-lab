"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { RefreshCw, Upload } from "lucide-react";
import { PositionsSummary, PositionsTable } from "@/components/positions";
import { usePositions } from "@/lib/hooks";
import { useUniverse } from "@/contexts/universe-context";
import { syncPositionsFromCsv, getPositionsStreamUrl } from "@/lib/api-client";
import { useToast } from "@/hooks/use-toast";
import type { PositionsResponse } from "@/lib/types";

export default function PositionsPage() {
  const { universeId } = useUniverse();
  const { toast } = useToast();
  const [isSyncing, setIsSyncing] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamData, setStreamData] = useState<PositionsResponse | null>(null);
  const [reconnectNonce, setReconnectNonce] = useState(0);

  // Poll only while the SSE stream isn't carrying updates — no double-fetch.
  const { data, isLoading, error, mutate } = usePositions({
    enablePolling: !isStreaming,
  });

  // Prefer live stream data; fall back to polled data.
  const positionsData = streamData || data;
  const marketOpen = positionsData?.market_status?.is_open ?? false;

  // Live price stream. Open it only while the market is open AND the tab is
  // visible — pausing on hidden saves mobile battery/data — and reconnect
  // after transport errors via a nonce that re-runs this effect.
  useEffect(() => {
    if (!marketOpen || typeof window === "undefined") return;

    let eventSource: EventSource | null = null;
    let retryTimer: ReturnType<typeof setTimeout> | null = null;

    const close = () => {
      if (eventSource) {
        eventSource.close();
        eventSource = null;
      }
      setIsStreaming(false);
    };

    const open = () => {
      if (eventSource) return;
      eventSource = new EventSource(getPositionsStreamUrl(universeId, 3));

      eventSource.onopen = () => setIsStreaming(true);

      eventSource.addEventListener("price_update", (event) => {
        try {
          setStreamData(
            JSON.parse((event as MessageEvent).data) as PositionsResponse
          );
        } catch (e) {
          console.error("Failed to parse price update:", e);
        }
      });

      eventSource.addEventListener("market_status", (event) => {
        try {
          const status = JSON.parse((event as MessageEvent).data);
          setStreamData((prev) => (prev ? { ...prev, market_status: status } : prev));
        } catch (e) {
          console.error("Failed to parse market status:", e);
        }
      });

      eventSource.addEventListener("error", (event) => {
        try {
          const errorData = JSON.parse((event as MessageEvent).data);
          if (errorData.error === "token_expired") {
            toast({
              title: "Token Expired",
              description: "Please login to Zerodha again.",
              variant: "destructive",
            });
          }
        } catch {
          // transport-level error — handled by onerror below
        }
      });

      eventSource.onerror = () => {
        close();
        retryTimer = setTimeout(() => setReconnectNonce((n) => n + 1), 5000);
      };
    };

    const syncToVisibility = () => {
      if (document.visibilityState === "visible") open();
      else close();
    };

    syncToVisibility();
    document.addEventListener("visibilitychange", syncToVisibility);

    return () => {
      document.removeEventListener("visibilitychange", syncToVisibility);
      if (retryTimer) clearTimeout(retryTimer);
      close();
    };
  }, [marketOpen, universeId, reconnectNonce, toast]);

  // Handle sync from CSV
  const handleSync = async () => {
    setIsSyncing(true);
    try {
      const result = await syncPositionsFromCsv(universeId);
      if (result.success) {
        toast({
          title: "Sync Complete",
          description: `Synced ${result.synced_count} positions for ${universeId}`,
        });
        mutate(); // Refresh data
      } else {
        toast({
          title: "Sync Failed",
          description: result.message,
          variant: "destructive",
        });
      }
    } catch (e) {
      toast({
        title: "Sync Error",
        description: e instanceof Error ? e.message : "Unknown error",
        variant: "destructive",
      });
    } finally {
      setIsSyncing(false);
    }
  };

  // Handle refresh
  const handleRefresh = () => {
    mutate();
    setStreamData(null);
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Open Positions</h1>
          <p className="text-muted-foreground">
            Live portfolio with real-time prices from Zerodha
          </p>
        </div>
        <div className="flex items-center gap-2">
          {isStreaming && (
            <span className="flex items-center gap-1 text-sm text-[color:var(--positive)]">
              <span className="h-2 w-2 rounded-full bg-[color:var(--positive)] animate-pulse" />
              Live
            </span>
          )}
          <Button
            variant="outline"
            size="sm"
            onClick={handleRefresh}
            disabled={isLoading}
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${isLoading ? "animate-spin" : ""}`} />
            Refresh
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={handleSync}
            disabled={isSyncing}
          >
            <Upload className={`h-4 w-4 mr-2 ${isSyncing ? "animate-spin" : ""}`} />
            Sync from CSV
          </Button>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="rounded-md border border-destructive bg-destructive/10 p-4">
          <p className="text-sm text-destructive">
            Failed to load positions: {error.message}
          </p>
        </div>
      )}

      {/* Empty State - No Positions */}
      {!isLoading && !error && positionsData?.positions?.length === 0 && (
        <div className="rounded-md border border-dashed p-8 text-center">
          <h3 className="text-lg font-medium">No positions found</h3>
          <p className="text-sm text-muted-foreground mt-2 mb-4">
            Sync your portfolio holdings from CSV to see live positions with prices.
          </p>
          <Button onClick={handleSync} disabled={isSyncing}>
            <Upload className={`h-4 w-4 mr-2 ${isSyncing ? "animate-spin" : ""}`} />
            Sync from Portfolio CSV
          </Button>
        </div>
      )}

      {/* Summary Cards */}
      <PositionsSummary
        summary={positionsData?.summary || null}
        marketStatus={positionsData?.market_status || null}
        isLoading={isLoading && !positionsData}
      />

      {/* Positions Table */}
      <PositionsTable
        positions={positionsData?.positions || []}
        isLoading={isLoading && !positionsData}
      />
    </div>
  );
}
