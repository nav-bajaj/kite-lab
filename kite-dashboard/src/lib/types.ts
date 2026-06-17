// Universe types
//
// Internal IDs are stable references for the backend, DB rows, and CSV
// columns. The display names rendered in the UI live in
// kite-dashboard/src/lib/universes.ts. Don't change the IDs; do change
// the labels there if a portfolio gets renamed for users.
export type UniverseId =
  | "om25_v3"
  | "tl25_v3"
  | "l6_v2"
  | "combo_defensive"
  | "nse500"
  | "nifty250"
  | "nifty100";

export interface Universe {
  id: UniverseId;
  name: string;
  shortName: string;
  description: string;
  stocks: number;
  riskProfile: string;
  /** Whether non-admin clients can see and select this universe. Legacy
   *  research universes (nse500/nifty100/nifty250) are admin-only. */
  clientVisible: boolean;
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
export interface MatchedBuy {
  buy_trade_id: number;
  entry_date: string;
  entry_price: number;        // effective (net of slippage) per-share buy price
  shares_matched: number;
  holding_days: number;
  realized_pnl: number;       // net of slippage on both legs
  realized_pnl_pct: number;
}

export interface Trade {
  id: number;
  date: string;
  symbol: string;
  side: "BUY" | "SELL";
  shares: number;
  price: number;
  notional: number;
  slippage: number;
  matches?: MatchedBuy[];     // populated only for SELL trades
}

export interface TradesResponse {
  trades: Trade[];
  total_count: number;
  limit: number;
  offset: number;
}

export interface TradeSummaryData {
  total_trades: number;
  buys: number;
  sells: number;
  total_notional: number;
  realized_pnl_total?: number | null;
  win_rate?: number | null;
  avg_holding_days?: number | null;
  best_trade_pct?: number | null;
  worst_trade_pct?: number | null;
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
  // When the holdings were last written by the daily sync (vs. last_updated,
  // which is the live-price refresh time). Null when there are no holdings.
  holdings_as_of?: string | null;
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
