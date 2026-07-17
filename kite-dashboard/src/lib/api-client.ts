import { UniverseId } from "./types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Global token storage for authenticated requests
let globalAuthToken: string | null = null;

// Optional async resolver registered by ApiAuthContext. When present it
// returns a guaranteed-fresh token (Clerk's getToken() caches internally
// and only hits the network near expiry), so requests never ride on a
// stale or not-yet-populated globalAuthToken. The global slot stays as a
// synchronous fallback for any non-React caller.
let tokenProvider: (() => Promise<string | null>) | null = null;

/**
 * Set the global authentication token.
 * Called by ApiAuthContext when token changes.
 */
export function setGlobalAuthToken(token: string | null) {
  globalAuthToken = token;
}

/**
 * Get the current global authentication token.
 */
export function getGlobalAuthToken(): string | null {
  return globalAuthToken;
}

/**
 * Register (or clear) the async token resolver. Called by ApiAuthContext
 * once Clerk is loaded and signed in.
 */
export function setTokenProvider(
  provider: (() => Promise<string | null>) | null
) {
  tokenProvider = provider;
}

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
  skipAuth?: boolean;
}

async function apiFetch<T>(
  endpoint: string,
  options: FetchOptions = {}
): Promise<T> {
  const { method = "GET", body, token, skipAuth = false } = options;

  const headers: HeadersInit = {
    "Content-Type": "application/json",
  };

  // Resolve the token at fetch time: explicit token wins, then the async
  // provider (always fresh), then the synchronous global as a fallback.
  let authToken: string | null = token ?? null;
  if (!authToken && !skipAuth) {
    authToken = tokenProvider ? await tokenProvider() : globalAuthToken;
  }
  if (authToken) {
    headers["Authorization"] = `Bearer ${authToken}`;
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
  return apiFetch<{ status: string; database: string; timestamp: string }>("/api/health", { skipAuth: true });
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
      sector?: string | null;
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
    benchmark_label?: string;
    data: Array<{
      date: string;
      portfolio_value: number;
      benchmark_value: number | null;
      drawdown: number;
    }>;
    count: number;
  }>(`/api/metrics/equity-curve?universe=${universe}`);
}

// Index returns (public market data, no auth) — for the Overview comparison.
export interface IndexReturns {
  as_of: string | null;
  horizons: string[];
  indices: Array<{
    key: string;
    label: string;
    as_of: string | null;
    data_available: boolean;
    returns: Record<string, number | null>;
  }>;
}

export async function getIndexReturns() {
  return apiFetch<IndexReturns>("/api/indices/returns", { skipAuth: true });
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
      matches?: Array<{
        buy_trade_id: number;
        entry_date: string;
        entry_price: number;
        shares_matched: number;
        holding_days: number;
        realized_pnl: number;
        realized_pnl_pct: number;
      }>;
    }>;
    total_count: number;
    limit: number;
    offset: number;
    has_more: boolean;
  }>(`/api/trades?${searchParams}`);
}

export interface TradeDetail {
  symbol: string;
  entry_date: string;
  exit_date: string;
  entry_price: number;
  exit_price: number;
  shares: number;
  holding_days: number;
  realized_pnl: number;
  realized_pnl_pct: number;
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
    realized_pnl_total?: number | null;
    win_rate?: number | null;
    avg_holding_days?: number | null;
    best_trade_pct?: number | null;
    worst_trade_pct?: number | null;
    avg_winner_pct?: number | null;
    avg_loser_pct?: number | null;
    best_trade?: TradeDetail | null;
    worst_trade?: TradeDetail | null;
  }>(`/api/trades/summary?universe=${universe}`);
}

// Rebalance endpoints (public, no auth required)
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

export async function getRebalanceSummary(universe: UniverseId) {
  return apiFetch<import("./types").RebalanceSummary>(
    `/api/rebalance/summary?universe=${universe}`
  );
}

export async function getRebalanceHistory(universe: UniverseId, limit: number = 20) {
  return apiFetch<{
    universe: string;
    history: import("./types").RebalanceHistoryItem[];
    count: number;
  }>(`/api/rebalance/history?universe=${universe}&limit=${limit}`);
}

export async function getRebalanceUpcoming(universe: UniverseId) {
  return apiFetch<import("./types").RebalanceUpcoming>(
    `/api/rebalance/upcoming?universe=${universe}`
  );
}

// Jobs endpoints
export interface Job {
  id: string;
  command: string;
  label: string | null;
  universe: string | null;
  args: Record<string, unknown> | null;
  status: "queued" | "running" | "completed" | "failed" | "cancelled";
  started_at: string | null;
  ended_at: string | null;
  duration_seconds: number | null;
  error_message: string | null;
  created_at: string;
}

export interface JobListResponse {
  jobs: Job[];
}

export interface CreateJobRequest {
  command: string;
  universe?: string;
  args?: Record<string, unknown>;
  label?: string;
}

export async function getJobs(params?: {
  limit?: number;
  universe?: string;
  status?: string;
}) {
  const searchParams = new URLSearchParams();
  if (params?.limit) searchParams.set("limit", String(params.limit));
  if (params?.universe) searchParams.set("universe", params.universe);
  if (params?.status) searchParams.set("status", params.status);

  return apiFetch<JobListResponse>(`/api/jobs?${searchParams}`);
}

export async function getJob(jobId: string) {
  return apiFetch<Job>(`/api/jobs/${jobId}`);
}

export async function createJob(data: CreateJobRequest) {
  return apiFetch<Job>("/api/jobs", {
    method: "POST",
    body: data,
  });
}

export async function getJobLogs(jobId: string, tail?: number) {
  const params = tail ? `?tail=${tail}` : "";
  return apiFetch<{ job_id: string; logs: string; status: string }>(
    `/api/jobs/${jobId}/logs${params}`
  );
}

export function getJobLogsStreamUrl(jobId: string) {
  const token = globalAuthToken || "";
  return `${API_BASE_URL}/api/jobs/${jobId}/logs?stream=true&token=${token}`;
}

export async function cancelJob(jobId: string) {
  return apiFetch<{ success: boolean; job_id: string; status: string }>(
    `/api/jobs/${jobId}/cancel`,
    { method: "POST" }
  );
}

// Schedule endpoints
export interface ScheduledJob {
  id: string;
  name: string;
  trigger: string;
  next_run: string | null;
  enabled: boolean;
}

export interface ScheduleListResponse {
  jobs: ScheduledJob[];
}

export interface CreateScheduleRequest {
  id: string;
  name: string;
  command: string;
  universe?: string;
  trigger?: string;
  hour?: number;
  minute?: number;
  day_of_week?: string;
  hours?: number;
  minutes?: number;
}

export async function getSchedule() {
  return apiFetch<ScheduleListResponse>("/api/schedule");
}

export async function createSchedule(data: CreateScheduleRequest) {
  return apiFetch<ScheduledJob>("/api/schedule", {
    method: "POST",
    body: data,
  });
}

export async function deleteSchedule(jobId: string) {
  return apiFetch<{ success: boolean; job_id: string }>(
    `/api/schedule/${jobId}`,
    { method: "DELETE" }
  );
}

export async function runScheduleNow(jobId: string) {
  return apiFetch<{ success: boolean; job_id: string; message: string }>(
    `/api/schedule/${jobId}/run`,
    { method: "POST" }
  );
}

export async function getScheduleDefaults() {
  return apiFetch<{
    tasks: Array<{
      id: string;
      name: string;
      description: string;
      command: string;
      trigger: string;
      trigger_args: Record<string, unknown>;
    }>;
  }>("/api/schedule/defaults");
}

// System endpoints
export interface TokenStatus {
  valid: boolean;
  expires_at: string | null;
  message: string;
}

export interface DatabaseStatus {
  connected: boolean;
  latency_ms: number | null;
  message: string;
}

export interface SyncStatus {
  last_sync: string | null;
  last_data_date: string | null;
  message: string;
}

export interface SystemStatus {
  api_health: boolean;
  database: DatabaseStatus;
  token: TokenStatus;
  sync: SyncStatus;
  version: string;
  environment: string;
}

export async function getSystemStatus() {
  return apiFetch<SystemStatus>("/api/system/status");
}

// Data-freshness monitor (admin-only). Mirrors the FastAPI SourceFreshness
// dataclass + report envelope in kite-api/app/services/freshness_service.py.
export type FreshnessStatus = "fresh" | "stale" | "critical" | "missing";

export interface SourceFreshness {
  name: string;
  kind: string;
  last_date: string | null;
  age_days: number | null;
  lag_trading_days: number | null;
  status: FreshnessStatus;
  detail: string;
  expected_cadence: string;
}

export interface FreshnessReport {
  generated_at: string;
  generated_for_reference_date: string | null;
  overall_status: FreshnessStatus;
  sources: SourceFreshness[];
}

export async function getFreshnessReport() {
  return apiFetch<FreshnessReport>("/api/freshness");
}

export async function getTokenStatus() {
  return apiFetch<TokenStatus>("/api/system/token");
}

export async function getLoginUrl() {
  return apiFetch<{ url: string; instructions: string }>("/api/system/login-url");
}

export async function headlessLogin() {
  return apiFetch<TokenStatus>("/api/system/headless-login", { method: "POST" });
}

// Positions endpoints (live portfolio tracking)
import type {
  PositionsResponse,
  MarketStatus,
  QuotesResponse,
} from "./types";

export async function getPositions(universe: UniverseId) {
  return apiFetch<PositionsResponse>(`/api/positions?universe=${universe}`);
}

export async function getPositionsHoldings(universe: UniverseId) {
  return apiFetch<{
    universe: string;
    holdings: Array<{
      symbol: string;
      qty: number;
      avg_price: number;
      entry_date?: string;
    }>;
    count: number;
  }>(`/api/positions/holdings?universe=${universe}`);
}

export async function getPositionsQuotes(universe: UniverseId) {
  return apiFetch<QuotesResponse>(`/api/positions/quotes?universe=${universe}`);
}

export async function getMarketStatus() {
  return apiFetch<MarketStatus>("/api/positions/market-status", { skipAuth: true });
}

export async function syncPositionsFromCsv(universe: UniverseId) {
  return apiFetch<{
    success: boolean;
    synced_count: number;
    universe: string;
    message: string;
  }>(`/api/positions/sync-from-csv?universe=${universe}`, { method: "POST" });
}

export function getPositionsStreamUrl(universe: UniverseId, interval: number = 3) {
  const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  const token = globalAuthToken || "";
  return `${API_BASE}/api/positions/stream?universe=${universe}&interval=${interval}&token=${token}`;
}
