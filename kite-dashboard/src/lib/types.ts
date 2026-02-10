// Universe types
export type UniverseId = "nse500" | "nifty250" | "nifty100";

export interface Universe {
  id: UniverseId;
  name: string;
  shortName: string;
  description: string;
  stocks: number;
  riskProfile: string;
}

// Portfolio types
export interface Portfolio {
  total_value: number;
  cash: number;
  invested: number;
  daily_pnl: number;
  daily_pnl_pct: number;
  total_return: number;
  total_return_pct: number;
  holdings_count: number;
  as_of_date: string;
}

export interface Holding {
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
  sector?: string;
  industry?: string;
}

export interface HoldingsSummary {
  total_pnl: number;
  winners: number;
  losers: number;
}

export interface HoldingsResponse {
  holdings: Holding[];
  summary: HoldingsSummary;
}

// Metrics types
export interface Metrics {
  period: {
    start: string;
    end: string;
    days: number;
  };
  returns: {
    total_return: number;
    cagr: number;
    mtd: number;
    ytd: number;
  };
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
}

export interface EquityCurvePoint {
  date: string;
  portfolio_value: number;
  benchmark_value: number;
  drawdown: number;
}

// Trade types
export interface Trade {
  id: number;
  date: string;
  symbol: string;
  side: "BUY" | "SELL";
  shares: number;
  price: number;
  notional: number;
  slippage: number;
}

export interface TradesResponse {
  trades: Trade[];
  total_count: number;
  limit: number;
  offset: number;
}

// Job types
export type JobStatus = "queued" | "running" | "completed" | "failed" | "cancelled";

export interface Job {
  id: string;
  command: string;
  label?: string;
  universe?: string;
  status: JobStatus;
  started_at?: string;
  ended_at?: string;
  duration_seconds?: number;
  error_message?: string;
  created_at: string;
}

// Rebalance types
export interface RebalanceStatus {
  status: "pending" | "preview" | "ready" | "executed";
  signal_date: string;
  order_date: string;
  preview_available: boolean;
  orders_available: boolean;
}

export interface RebalanceAddition {
  symbol: string;
  rank: number;
  score: number;
}

export interface RebalanceRemoval {
  symbol: string;
  prev_rank: number;
  reason: string;
}

// API response wrapper
export interface ApiError {
  detail: string;
  status: number;
}
