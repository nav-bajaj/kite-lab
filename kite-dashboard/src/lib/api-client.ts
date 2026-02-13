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
export async function getPortfolio(universe: UniverseId, token?: string) {
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
    universe: string;
    cagr: number | null;
    max_drawdown: number | null;
    sharpe_ratio: number | null;
    error?: string;
  }>(`/api/portfolio?universe=${universe}`, { token });
}

export async function getHoldings(universe: UniverseId, token?: string) {
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

// Metrics endpoints (public, no auth required)
export async function getMetrics(universe: UniverseId) {
  return apiFetch<{
    universe: string;
    period: { start: string | null; end: string | null; days: number };
    returns: { total_return: number; cagr: number; mtd: number; ytd: number };
    risk: {
      max_drawdown: number;
      max_dd_duration: number | null;
      volatility: number;
      sharpe_ratio: number | null;
      sortino_ratio: number | null;
      calmar_ratio: number | null;
    };
    activity: {
      total_trades: number;
      avg_turnover: number;
      annualized_turnover: number;
      avg_holding_days: number;
      hit_rate: number;
    };
    error?: string;
  }>(`/api/metrics?universe=${universe}`);
}

export async function getEquityCurve(universe: UniverseId) {
  return apiFetch<{
    universe: string;
    data: Array<{
      date: string;
      portfolio_value: number;
      benchmark_value: number | null;
      drawdown: number;
    }>;
    count: number;
  }>(`/api/metrics/equity-curve?universe=${universe}`);
}

export async function getMonthlyReturns(universe: UniverseId) {
  return apiFetch<{
    universe: string;
    years: number[];
    data: Array<{
      year: number;
      months: (number | null)[];
      ytd: number;
    }>;
  }>(`/api/metrics/monthly-returns?universe=${universe}`);
}

// Trades endpoints (public, no auth required)
export async function getTrades(
  universe: UniverseId,
  params?: { limit?: number; offset?: number; symbol?: string; side?: string; start_date?: string; end_date?: string }
) {
  const searchParams = new URLSearchParams({ universe });
  if (params?.limit) searchParams.set("limit", String(params.limit));
  if (params?.offset) searchParams.set("offset", String(params.offset));
  if (params?.symbol) searchParams.set("symbol", params.symbol);
  if (params?.side) searchParams.set("side", params.side);
  if (params?.start_date) searchParams.set("start_date", params.start_date);
  if (params?.end_date) searchParams.set("end_date", params.end_date);

  return apiFetch<{
    universe: string;
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
    has_more: boolean;
  }>(`/api/trades?${searchParams}`);
}

export async function getTradeSummary(universe: UniverseId) {
  return apiFetch<{
    universe: string;
    total_trades: number;
    buys: number;
    sells: number;
    first_trade_date: string | null;
    last_trade_date: string | null;
    total_notional: number;
  }>(`/api/trades/summary?universe=${universe}`);
}

// Rebalance endpoints (public, no auth required)
export async function getRebalanceStatus(universe: UniverseId) {
  return apiFetch<{
    universe: string;
    status: string;
    signal_date: string | null;
    order_date: string | null;
    current_phase: string;
    is_rebalance_day: boolean;
    preview_available: boolean;
    orders_available: boolean;
    today: string;
    weekday: string;
  }>(`/api/rebalance/status?universe=${universe}`);
}

export async function getRebalancePreview(universe: UniverseId) {
  return apiFetch<{
    universe: string;
    signal_date: string | null;
    additions: Array<{ symbol: string; rank: number; score: number | null }>;
    removals: Array<{ symbol: string; prev_rank: number | null; reason: string }>;
    additions_count: number;
    removals_count: number;
    message?: string;
  }>(`/api/rebalance/preview?universe=${universe}`);
}

export async function getRebalanceOrders(universe: UniverseId) {
  return apiFetch<{
    universe: string;
    order_date: string | null;
    orders: Array<{
      symbol: string;
      action: "BUY" | "SELL";
      shares: number;
      target_price: number | null;
      notional: number | null;
    }>;
    buy_count: number;
    sell_count: number;
    total_orders: number;
    message?: string;
  }>(`/api/rebalance/orders?universe=${universe}`);
}

export async function getRebalanceHistory(universe: UniverseId, limit: number = 20) {
  return apiFetch<{
    universe: string;
    history: Array<{
      signal_date: string;
      order_date: string | null;
      status: string;
      additions: number;
      removals: number;
      turnover_pct: number | null;
    }>;
    count: number;
  }>(`/api/rebalance/history?universe=${universe}&limit=${limit}`);
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
