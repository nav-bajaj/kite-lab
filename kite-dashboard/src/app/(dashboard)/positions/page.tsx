"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { RefreshCw } from "lucide-react";
import { PositionsSummary, PositionsTable } from "@/components/positions";
import { usePositions } from "@/lib/hooks";
import { useUniverse } from "@/contexts/universe-context";
import { getPositionsStreamUrl } from "@/lib/api-client";
import type { PositionsResponse } from "@/lib/types";

export default function PositionsPage() {
  const { universeId } = useUniverse();
  const [isStreaming, setIsStreaming] = useState(false);
  const [reconnectNonce, setReconnectNonce] = useState(0);

  // Poll only while the SSE stream isn't carrying updates — no double-fetch.
  // Stream updates are written into this SWR cache entry (not local state) so
  // every subscriber of the key — including the bottom-nav Day P&L notch —
  // sees the same live data.
  const { data: positionsData, isLoading, error, mutate } = usePositions({
    enablePolling: !isStreaming,
  });

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
          const update = JSON.parse(
            (event as MessageEvent).data
          ) as PositionsResponse;
          mutate(update, { revalidate: false });
        } catch (e) {
          console.error("Failed to parse price update:", e);
        }
      });

      eventSource.addEventListener("market_status", (event) => {
        try {
          const status = JSON.parse((event as MessageEvent).data);
          mutate((prev) => (prev ? { ...prev, market_status: status } : prev), {
            revalidate: false,
          });
        } catch (e) {
          console.error("Failed to parse market status:", e);
        }
      });

      // Transport errors (incl. an expired upstream data feed) — close and let
      // the nonce retry. No user-facing broker/token messaging: for a client
      // this just quietly falls back to the last prices.
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
  }, [marketOpen, universeId, reconnectNonce, mutate]);

  const handleRefresh = () => {
    mutate();
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-start justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Open Positions</h1>
          <p className="text-muted-foreground">
            The model portfolio, priced live during market hours — watch it
            update tick by tick.
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

      {/* Empty State */}
      {!isLoading && !error && positionsData?.positions?.length === 0 && (
        <div className="rounded-md border border-dashed p-8 text-center">
          <h3 className="text-lg font-medium">No live positions right now</h3>
          <p className="mt-2 text-sm text-muted-foreground">
            Check back during market hours to see the portfolio update in real
            time.
          </p>
        </div>
      )}

      {/* Summary Cards */}
      <PositionsSummary
        summary={positionsData?.summary || null}
        marketStatus={positionsData?.market_status || null}
        holdingsAsOf={positionsData?.holdings_as_of || null}
        isLoading={isLoading && !positionsData}
      />

      {/* Positions Table */}
      <PositionsTable
        positions={positionsData?.positions || []}
        isLoading={isLoading && !positionsData}
      />

      <p className="text-xs leading-relaxed text-muted-foreground">
        These are the model portfolio&apos;s positions, shown for education.
        Values are notional — this is not your own brokerage account.
      </p>
    </div>
  );
}
