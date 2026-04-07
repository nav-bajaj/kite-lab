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
  universe: string;
  cagr: number | null;
  max_drawdown: number | null;
  sharpe_ratio: number | null;
  error?: string;
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

// Open Positions types (live portfolio tracking)
export interface LiveQuote {
  symbol: string;
  instrument_token?: number;
  ltp: number;
  open: number;
  high: number;
  low: number;
  close: number;
  change: number;
  change_pct: number;
  volume?: number;
  last_trade_time?: string;
}

export interface Position {
  symbol: string;
  qty: number;
  avg_price: number;
  entry_date?: string;
  ltp: number;
  day_change: number;
  day_change_pct: number;
  invested: number;
  current_value: number;
  total_pnl: number;
  total_pnl_pct: number;
  day_pnl: number;
  day_pnl_pct: number;
}

export interface MarketStatus {
  is_open: boolean;
  status: "pre_open" | "open" | "closed";
  message: string;
  next_open?: string;
  last_updated: string;
}

export interface PositionsSummary {
  total_invested: number;
  total_current_value: number;
  total_pnl: number;
  total_pnl_pct: number;
  day_pnl: number;
  day_pnl_pct: number;
  position_count: number;
  winners: number;
  losers: number;
}

export interface PositionsResponse {
  universe: string;
  positions: Position[];
  summary: PositionsSummary;
  market_status: MarketStatus;
  last_updated: string;
}

export interface QuotesResponse {
  quotes: Record<string, LiveQuote>;
  market_status: MarketStatus;
  last_updated: string;
}

// API response wrapper
export interface ApiError {
  detail: string;
  status: number;
}
