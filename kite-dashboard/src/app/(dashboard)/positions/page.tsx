"use client";

import { useState, useEffect, useCallback } from "react";
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
  const { data, isLoading, error, mutate } = usePositions();
  const { toast } = useToast();
  const [isSyncing, setIsSyncing] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamData, setStreamData] = useState<PositionsResponse | null>(null);

  // Use stream data if available, otherwise fall back to polled data
  const positionsData = streamData || data;

  // Start SSE stream for real-time updates
  const startStream = useCallback(() => {
    if (isStreaming) return;

    const streamUrl = getPositionsStreamUrl(universeId, 3);
    const eventSource = new EventSource(streamUrl);

    eventSource.onopen = () => {
      setIsStreaming(true);
    };

    eventSource.addEventListener("price_update", (event) => {
      try {
        const data = JSON.parse(event.data) as PositionsResponse;
        setStreamData(data);
      } catch (e) {
        console.error("Failed to parse price update:", e);
      }
    });

    eventSource.addEventListener("market_status", (event) => {
      try {
        const status = JSON.parse(event.data);
        // Update just the market status
        setStreamData((prev) =>
          prev ? { ...prev, market_status: status } : null
        );
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
        // Connection error
      }
    });

    eventSource.onerror = () => {
      setIsStreaming(false);
      eventSource.close();
      // Retry after a delay
      setTimeout(() => {
        if (positionsData?.market_status?.is_open) {
          startStream();
        }
      }, 5000);
    };

    // Cleanup on unmount
    return () => {
      eventSource.close();
      setIsStreaming(false);
    };
  }, [universeId, isStreaming, positionsData?.market_status?.is_open, toast]);

  // Auto-start stream when market is open
  useEffect(() => {
    if (data?.market_status?.is_open && !isStreaming) {
      const cleanup = startStream();
      return cleanup;
    }
  }, [data?.market_status?.is_open, isStreaming, startStream]);

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
