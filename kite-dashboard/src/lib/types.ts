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
export type RebalanceKind = "entry" | "weekly_exit" | "no_action";

export interface RebalancePreviousInfo {
  date: string;
  added: string[];
  removed: string[];
  buy_count: number;
  sell_count: number;
  notional_traded: number;
  turnover_pct: number | null;
  // True when the engine processed the cadence cycle but fired zero trades
  // (top-25 rotation stayed inside the exit buffer). Surfaces "the engine
  // reviewed and held" instead of looking like a missing rebalance.
  no_action?: boolean;
  kind?: RebalanceKind;
}

export interface RebalanceNextInfo {
  signal_date: string;
  exec_date: string;
  trading_days_until: number;
  // Biweekly strategies also run a weekly rank/drawdown exit check on the
  // off-week Fridays; these describe the next such check (null when the
  // strategy's entry and exit cadence are the same).
  has_weekly_exit: boolean;
  exit_check_date: string | null;
  exit_check_days_until: number | null;
}

export interface RebalanceSummary {
  universe: string;
  cadence: string;
  cadence_label: string;
  today: string;
  holdings_count: number;
  previous: RebalancePreviousInfo | null;
  next: RebalanceNextInfo | null;
}

// Upcoming-rebalance "Actionable trades" types — see
// tasks/rebalance_page/PLAN.md Phase 2.
export interface ProposedBuy {
  symbol: string;
  target_weight: number;
  // Producer-sized notional + share count on its `initial_capital` base —
  // ballpark only. The client re-derives ₹ from the subscriber's own
  // portfolio value entered in the BUY card (stored client-side, never
  // sent to the server).
  est_notional: number | null;
  est_shares: number | null;
}

export interface RebalanceUpcoming {
  universe: string;
  available: boolean;
  // True once exec_date has passed (a missed/failed producer run left the
  // previous proposal as the latest row). The UI warns instead of presenting
  // an already-executed rebalance as upcoming.
  stale: boolean;
  exec_date: string | null;
  signal_date: string | null;
  data_as_of: string | null;
  sells: string[];
  buys: ProposedBuy[];
  holds: string[];
  sell_count: number;
  buy_count: number;
  hold_count: number;
  // Regime + drawdown strip — null for strategies without a regime panel
  // (e.g. tl25_v3) or when the proposal is empty.
  regime: "bull" | "bear" | null;
  drawdown_from_peak: number | null;
  final_pv: number | null;
  initial_capital: number | null;
}

export interface RebalanceHistoryItem {
  date: string;
  additions: number;
  removals: number;
  // The actual names traded at this rebalance — powers the expandable detail
  // row. Optional because legacy summary payloads may omit them.
  added?: string[];
  removed?: string[];
  notional: number;
  turnover_pct: number | null;
  // See RebalancePreviousInfo above for the no_action semantics. Optional
  // because legacy strategies' summaries don't carry it yet.
  no_action?: boolean;
  kind?: RebalanceKind;
  off_cadence?: boolean;
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
