"use client";

import useSWR from "swr";
import { useSession } from "next-auth/react";
import { useUniverse } from "@/contexts/universe-context";
import {
  getPortfolio,
  getHoldings,
  getMetrics,
  getEquityCurve,
  getMonthlyReturns,
  getTrades,
  getTradeSummary,
  getRebalanceStatus,
  getRebalancePreview,
  getRebalanceOrders,
  getRebalanceHistory,
  getJobs,
  getHealth,
} from "./api-client";

// Refresh intervals
const REFRESH_INTERVAL = 60_000; // 1 minute
const SLOW_REFRESH = 300_000; // 5 minutes

// Helper to get token from session
function useAuthToken() {
  const { data: session } = useSession();
  return session?.accessToken;
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

  return useSWR(
    ["portfolio", universeId],
    ([, universe]) => getPortfolio(universe),
    {
      refreshInterval: REFRESH_INTERVAL,
      revalidateOnFocus: true,
    }
  );
}

// Holdings data (no auth required)
export function useHoldings() {
  const { universeId } = useUniverse();

  return useSWR(
    ["holdings", universeId],
    ([, universe]) => getHoldings(universe),
    {
      refreshInterval: REFRESH_INTERVAL,
      revalidateOnFocus: true,
    }
  );
}

// Performance metrics (public, no auth required)
export function useMetrics() {
  const { universeId } = useUniverse();

  return useSWR(
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

  return useSWR(
    ["equity-curve", universeId],
    ([, universe]) => getEquityCurve(universe),
    {
      refreshInterval: SLOW_REFRESH,
      revalidateOnFocus: false,
    }
  );
}

// Monthly returns data (public, no auth required)
export function useMonthlyReturns() {
  const { universeId } = useUniverse();

  return useSWR(
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

  return useSWR(
    ["trades", universeId, params],
    ([, universe, p]) => getTrades(universe, p),
    {
      refreshInterval: REFRESH_INTERVAL,
      revalidateOnFocus: true,
    }
  );
}

// Trade summary (public, no auth required)
export function useTradeSummary() {
  const { universeId } = useUniverse();

  return useSWR(
    ["trade-summary", universeId],
    ([, universe]) => getTradeSummary(universe),
    {
      refreshInterval: SLOW_REFRESH,
      revalidateOnFocus: false,
    }
  );
}

// Rebalance status (public, no auth required)
export function useRebalanceStatus() {
  const { universeId } = useUniverse();

  return useSWR(
    ["rebalance-status", universeId],
    ([, universe]) => getRebalanceStatus(universe),
    {
      refreshInterval: REFRESH_INTERVAL,
      revalidateOnFocus: true,
    }
  );
}

// Rebalance preview (public, no auth required)
export function useRebalancePreview() {
  const { universeId } = useUniverse();

  return useSWR(
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

  return useSWR(
    ["rebalance-orders", universeId],
    ([, universe]) => getRebalanceOrders(universe),
    {
      refreshInterval: SLOW_REFRESH,
      revalidateOnFocus: false,
    }
  );
}

// Rebalance history (public, no auth required)
export function useRebalanceHistory(limit: number = 20) {
  const { universeId } = useUniverse();

  return useSWR(
    ["rebalance-history", universeId, limit],
    ([, universe, l]) => getRebalanceHistory(universe, l),
    {
      refreshInterval: SLOW_REFRESH,
      revalidateOnFocus: false,
    }
  );
}

// Jobs list
export function useJobs(limit = 20) {
  const token = useAuthToken();

  return useSWR(
    token ? ["jobs", token, limit] : null,
    ([, t, l]) => getJobs(t, l),
    {
      refreshInterval: REFRESH_INTERVAL,
      revalidateOnFocus: true,
    }
  );
}
