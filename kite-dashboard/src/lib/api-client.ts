import { UniverseId } from "./types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

interface FetchOptions {
  method?: "GET" | "POST" | "PUT" | "DELETE";
  body?: unknown;
  token?: string;
}

async function apiFetch<T>(
  endpoint: string,
  options: FetchOptions = {}
): Promise<T> {
  const { method = "GET", body, token } = options;

  const headers: HeadersInit = {
    "Content-Type": "application/json",
  };

  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    method,
    headers,
    body: body ? JSON.stringify(body) : undefined,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Unknown error" }));
    throw new ApiError(error.detail || "Request failed", response.status);
  }

  return response.json();
}

// Health check (no auth required)
export async function getHealth() {
  return apiFetch<{ status: string; database: string; timestamp: string }>("/api/health");
}

// Auth endpoints
export async function verifyToken(token: string) {
  return apiFetch<{ valid: boolean; email: string }>("/api/auth/verify", { token });
}

export async function getCurrentUser(token: string) {
  return apiFetch<{ email: string; name: string }>("/api/auth/me", { token });
}

// Portfolio endpoints
export async function getPortfolio(universe: UniverseId, token: string) {
  return apiFetch<{
    total_value: number;
    cash: number;
    invested: number;
    daily_pnl: number;
    daily_pnl_pct: number;
    total_return: number;
    total_return_pct: number;
    holdings_count: number;
    as_of_date: string;
  }>(`/api/portfolio?universe=${universe}`, { token });
}

export async function getHoldings(universe: UniverseId, token: string) {
  return apiFetch<{
    holdings: Array<{
      symbol: string;
      shares: number;
      avg_cost: number;
      current_price: number;
      notional: number;
      pnl: number;
      pnl_pct: number;
      weight: number;
      entry_date: string;
      holding_days: number;
      rank: number;
    }>;
    summary: {
      total_pnl: number;
      winners: number;
      losers: number;
    };
  }>(`/api/portfolio/holdings?universe=${universe}`, { token });
}

// Metrics endpoints
export async function getMetrics(universe: UniverseId, token: string) {
  return apiFetch<{
    period: { start: string; end: string; days: number };
    returns: { total_return: number; cagr: number; mtd: number; ytd: number };
    risk: {
      max_drawdown: number;
      max_dd_duration: number;
      volatility: number;
      sharpe_ratio: number;
      sortino_ratio: number;
      calmar_ratio: number;
    };
    activity: {
      total_trades: number;
      avg_turnover: number;
      annualized_turnover: number;
      avg_holding_days: number;
      hit_rate: number;
    };
  }>(`/api/metrics?universe=${universe}`, { token });
}

export async function getEquityCurve(universe: UniverseId, token: string) {
  return apiFetch<{
    data: Array<{
      date: string;
      portfolio_value: number;
      benchmark_value: number;
      drawdown: number;
    }>;
  }>(`/api/metrics/equity-curve?universe=${universe}`, { token });
}

// Trades endpoints
export async function getTrades(
  universe: UniverseId,
  token: string,
  params?: { limit?: number; offset?: number; symbol?: string; side?: string }
) {
  const searchParams = new URLSearchParams({ universe });
  if (params?.limit) searchParams.set("limit", String(params.limit));
  if (params?.offset) searchParams.set("offset", String(params.offset));
  if (params?.symbol) searchParams.set("symbol", params.symbol);
  if (params?.side) searchParams.set("side", params.side);

  return apiFetch<{
    trades: Array<{
      id: number;
      date: string;
      symbol: string;
      side: "BUY" | "SELL";
      shares: number;
      price: number;
      notional: number;
      slippage: number;
    }>;
    total_count: number;
    limit: number;
    offset: number;
  }>(`/api/trades?${searchParams}`, { token });
}

// Rebalance endpoints
export async function getRebalanceStatus(universe: UniverseId, token: string) {
  return apiFetch<{
    status: "pending" | "preview" | "ready" | "executed";
    signal_date: string;
    order_date: string;
    preview_available: boolean;
    orders_available: boolean;
  }>(`/api/rebalance/status?universe=${universe}`, { token });
}

export async function getRebalancePreview(universe: UniverseId, token: string) {
  return apiFetch<{
    additions: Array<{ symbol: string; rank: number; score: number }>;
    removals: Array<{ symbol: string; prev_rank: number; reason: string }>;
    signal_date: string;
  }>(`/api/rebalance/preview?universe=${universe}`, { token });
}

// Jobs endpoints
export async function getJobs(token: string, limit = 20) {
  return apiFetch<{
    jobs: Array<{
      id: string;
      command: string;
      label?: string;
      universe?: string;
      status: "queued" | "running" | "completed" | "failed" | "cancelled";
      started_at?: string;
      ended_at?: string;
      duration_seconds?: number;
      error_message?: string;
      created_at: string;
    }>;
  }>(`/api/jobs?limit=${limit}`, { token });
}

export async function createJob(
  token: string,
  data: { command: string; label?: string; universe?: string }
) {
  return apiFetch<{ id: string; status: string }>("/api/jobs", {
    method: "POST",
    body: data,
    token,
  });
}

export async function cancelJob(token: string, jobId: string) {
  return apiFetch<{ success: boolean }>(`/api/jobs/${jobId}/cancel`, {
    method: "POST",
    token,
  });
}
