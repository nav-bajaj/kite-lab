"use client";

import useSWR, { type SWRConfiguration, type Key, type Fetcher } from "swr";
import { useUniverse } from "@/contexts/universe-context";
import { useApiAuth } from "@/contexts/api-auth-context";
import { useNetworkStatus } from "@/hooks/use-network-status";
import {
  getPortfolio,
  getHoldings,
  getMetrics,
  getEquityCurve,
  getIndexReturns,
  getMonthlyReturns,
  getTrades,
  getTradeSummary,
  getRebalanceSummary,
  getRebalancePreview,
  getRebalanceOrders,
  getRebalanceHistory,
  getRebalanceUpcoming,
  getJobs,
  getJob,
  getJobLogs,
  getSchedule,
  getSystemStatus,
  getFreshnessReport,
  getOptionsWorkerStatus,
  getOptionsLiveAnalytics,
  getHealth,
  getPositions,
  getMarketStatus,
  type Job,
  type JobListResponse,
  type ScheduleListResponse,
  type SystemStatus,
  type FreshnessReport,
  type OptionsWorkerStatus,
  type OptionsLiveAnalytics,
} from "./api-client";
import type { PositionsResponse, MarketStatus } from "./types";

// Refresh intervals. Aligned with the backend Cache-Control windows so we
// don't poll faster than the data can change:
//  - Daily DB data (portfolio, holdings, trades, rebalance) is refreshed
//    once a day by the pipeline → SLOW_REFRESH. Live P&L lives on the
//    Positions page (SSE), not here.
//  - REFRESH_INTERVAL is for genuinely minute-scale signals (market open/
//    closed status).
const REFRESH_INTERVAL = 60_000; // 1 minute
const SLOW_REFRESH = 300_000; // 5 minutes

// SWR wrapper that holds the request until auth is ready. Passing a null
// key makes SWR a no-op (no fetch, no error), so authed endpoints never
// fire before a token can be attached — the root cause of the spurious
// "session expired" toast on login. Callers pass the key they would have
// passed to useSWR; it is nulled out while auth is not ready.
function useAuthedSWR<Data = unknown, SWRKey extends Key = Key>(
  key: SWRKey,
  fetcher: Fetcher<Data, SWRKey>,
  config?: SWRConfiguration<Data>
) {
  const { authReady } = useApiAuth();
  return useSWR<Data>(
    authReady ? key : null,
    fetcher as Fetcher<Data>,
    config
  );
}

// Health check (no auth)
export function useHealth() {
  return useSWR("health", getHealth, {
    refreshInterval: SLOW_REFRESH,
    revalidateOnFocus: false,
  });
}

// Portfolio data (no auth required)
export function usePortfolio() {
  const { universeId } = useUniverse();

  return useAuthedSWR(
    ["portfolio", universeId],
    ([, universe]) => getPortfolio(universe),
    {
      refreshInterval: SLOW_REFRESH,
      revalidateOnFocus: true,
    }
  );
}

// Holdings data (no auth required)
export function useHoldings() {
  const { universeId } = useUniverse();

  return useAuthedSWR(
    ["holdings", universeId],
    ([, universe]) => getHoldings(universe),
    {
      refreshInterval: SLOW_REFRESH,
      revalidateOnFocus: true,
    }
  );
}

// Performance metrics (public, no auth required)
export function useMetrics() {
  const { universeId } = useUniverse();

  return useAuthedSWR(
    ["metrics", universeId],
    ([, universe]) => getMetrics(universe),
    {
      refreshInterval: SLOW_REFRESH,
      revalidateOnFocus: false,
    }
  );
}

// Equity curve data (public, no auth required)
export function useEquityCurve() {
  const { universeId } = useUniverse();

  return useAuthedSWR(
    ["equity-curve", universeId],
    ([, universe]) => getEquityCurve(universe),
    {
      refreshInterval: SLOW_REFRESH,
      revalidateOnFocus: false,
    }
  );
}

// Index rolling returns (public market data — universe-independent, no auth gate)
export function useIndexReturns() {
  return useSWR("index-returns", getIndexReturns, {
    refreshInterval: SLOW_REFRESH,
    revalidateOnFocus: false,
  });
}

// Monthly returns data (public, no auth required)
export function useMonthlyReturns() {
  const { universeId } = useUniverse();

  return useAuthedSWR(
    ["monthly-returns", universeId],
    ([, universe]) => getMonthlyReturns(universe),
    {
      refreshInterval: SLOW_REFRESH,
      revalidateOnFocus: false,
    }
  );
}

// Trades with pagination (public, no auth required)
export function useTrades(params?: {
  limit?: number;
  offset?: number;
  symbol?: string;
  side?: string;
  start_date?: string;
  end_date?: string;
}) {
  const { universeId } = useUniverse();

  return useAuthedSWR(
    ["trades", universeId, params],
    ([, universe, p]) => getTrades(universe, p),
    {
      refreshInterval: SLOW_REFRESH,
      revalidateOnFocus: true,
    }
  );
}

// Trade summary (public, no auth required)
export function useTradeSummary() {
  const { universeId } = useUniverse();

  return useAuthedSWR(
    ["trade-summary", universeId],
    ([, universe]) => getTradeSummary(universe),
    {
      refreshInterval: SLOW_REFRESH,
      revalidateOnFocus: false,
    }
  );
}

// Rebalance summary — cadence-aware previous + next rebalance
export function useRebalanceSummary() {
  const { universeId } = useUniverse();

  return useAuthedSWR(
    ["rebalance-summary", universeId],
    ([, universe]) => getRebalanceSummary(universe),
    {
      refreshInterval: SLOW_REFRESH,
      revalidateOnFocus: true,
    }
  );
}

// Rebalance preview (public, no auth required)
export function useRebalancePreview() {
  const { universeId } = useUniverse();

  return useAuthedSWR(
    ["rebalance-preview", universeId],
    ([, universe]) => getRebalancePreview(universe),
    {
      refreshInterval: SLOW_REFRESH,
      revalidateOnFocus: false,
    }
  );
}

// Rebalance orders (public, no auth required)
export function useRebalanceOrders() {
  const { universeId } = useUniverse();

  return useAuthedSWR(
    ["rebalance-orders", universeId],
    ([, universe]) => getRebalanceOrders(universe),
    {
      refreshInterval: SLOW_REFRESH,
      revalidateOnFocus: false,
    }
  );
}

// Upcoming rebalance — EOD-produced "Actionable trades" payload
// (PLAN.md Phase 2 §3-§4).
export function useRebalanceUpcoming() {
  const { universeId } = useUniverse();

  return useAuthedSWR(
    ["rebalance-upcoming", universeId],
    ([, universe]) => getRebalanceUpcoming(universe),
    {
      refreshInterval: SLOW_REFRESH,
      revalidateOnFocus: true,
    }
  );
}

// Rebalance history (public, no auth required)
export function useRebalanceHistory(limit: number = 20) {
  const { universeId } = useUniverse();

  return useAuthedSWR(
    ["rebalance-history", universeId, limit],
    ([, universe, l]) => getRebalanceHistory(universe, l),
    {
      refreshInterval: SLOW_REFRESH,
      revalidateOnFocus: false,
    }
  );
}

// Jobs list (no auth required for admin panel)
export function useJobs(params?: {
  limit?: number;
  universe?: string;
  status?: string;
}) {
  return useAuthedSWR<JobListResponse>(
    ["jobs", params?.limit, params?.universe, params?.status],
    () => getJobs(params),
    {
      refreshInterval: 5000, // Fast refresh for job status
      revalidateOnFocus: true,
    }
  );
}

// Single job details
export function useJob(jobId: string | null) {
  return useAuthedSWR<Job>(
    jobId ? ["job", jobId] : null,
    () => getJob(jobId!),
    {
      refreshInterval: 2000, // Fast refresh for running jobs
      revalidateOnFocus: true,
    }
  );
}

// Job logs
export function useJobLogs(jobId: string | null, tail?: number) {
  return useAuthedSWR<{ job_id: string; logs: string; status: string }>(
    jobId ? ["job-logs", jobId, tail] : null,
    () => getJobLogs(jobId!, tail),
    {
      refreshInterval: 2000,
      revalidateOnFocus: false,
    }
  );
}

// Schedule list
export function useSchedule() {
  return useAuthedSWR<ScheduleListResponse>(
    "schedule",
    getSchedule,
    {
      refreshInterval: 30000, // Slower refresh for schedule
      revalidateOnFocus: true,
    }
  );
}

// System status
export function useSystemStatus() {
  return useAuthedSWR<SystemStatus>(
    "system-status",
    getSystemStatus,
    {
      refreshInterval: 30000,
      revalidateOnFocus: true,
    }
  );
}

export function useFreshnessReport() {
  return useAuthedSWR<FreshnessReport>("freshness", getFreshnessReport, {
    refreshInterval: 60000,
    revalidateOnFocus: true,
  });
}

export function useOptionsLiveAnalytics() {
  return useAuthedSWR<OptionsLiveAnalytics>("options-live", getOptionsLiveAnalytics, {
    refreshInterval: 15000,
    revalidateOnFocus: true,
  });
}

export function useOptionsWorkerStatus() {
  // Live ops view — the worker heartbeats every 30s, poll a bit faster so
  // a stalled capture surfaces within a minute.
  return useAuthedSWR<OptionsWorkerStatus>("options-worker", getOptionsWorkerStatus, {
    refreshInterval: 15000,
    revalidateOnFocus: true,
  });
}

// Open Positions (live portfolio tracking)
const POSITIONS_REFRESH = 10_000; // 10s when market open and not streaming
const POSITIONS_CLOSED_REFRESH = 60_000; // 1min when closed (just to catch the open)

// `enablePolling` lets the Positions page turn polling off while its SSE
// stream is healthy, so we don't double-fetch. Polling is also gated on
// market hours via the refreshInterval function — no point hammering the
// backend for prices that aren't moving. (SWR already pauses polling while
// the tab is hidden, so battery/data on mobile are covered too.)
export function usePositions(opts?: { enablePolling?: boolean }) {
  const { universeId } = useUniverse();
  const { isSlow } = useNetworkStatus();
  const enablePolling = opts?.enablePolling ?? true;

  return useAuthedSWR<PositionsResponse>(
    ["positions", universeId],
    () => getPositions(universeId),
    {
      refreshInterval: (latest?: PositionsResponse) => {
        if (!enablePolling) return 0;
        const base = latest?.market_status?.is_open
          ? POSITIONS_REFRESH
          : POSITIONS_CLOSED_REFRESH;
        // Back off on metered / slow mobile connections.
        return isSlow ? base * 3 : base;
      },
      revalidateOnFocus: true,
    }
  );
}

export function useMarketStatus() {
  return useAuthedSWR<MarketStatus>(
    "market-status",
    getMarketStatus,
    {
      refreshInterval: REFRESH_INTERVAL,
      revalidateOnFocus: true,
    }
  );
}
