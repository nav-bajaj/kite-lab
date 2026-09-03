/**
 * Insight Engine API client — thin server-side wrappers around the
 * /api/insights/* endpoints on kite-api.
 *
 * All functions are async server-side fetchers suitable for use in
 * Next.js Server Components. They include `next.revalidate` so the
 * data refreshes at most every 15 minutes (matches the Cache-Control
 * on the backend).
 *
 * NOTE: Visual treatment of the insights pages is intentionally minimal
 * right now — a separate design engine + content OS will integrate the
 * full styling later. Types/shapes here lock the API contract.
 */

import { getSupabaseServerClient } from "@/lib/supabase/server";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const REVALIDATE_SECONDS = 900; // 15 minutes — same as backend Cache-Control

// ---------- shared lightweight types ----------

export interface RegimeSnapshot {
  date: string;
  regime: "TREND_BULL" | "DRIFT" | "STRETCHED" | "STRESS";
  persistence_days: number;
  days_since_last_change: number;
  nifty100_above_100dma: boolean;
  pct_above_200dma: number | null;
  vix_zscore_252d: number | null;
  prev_regime: string | null;
  prev_regime_lasted_days: number | null;
}

export interface StressSnapshot {
  date: string;
  score: number;
  score_percentile: number;
  vix_pctile_component: number | null;
  drawdown_component: number | null;
  below_200dma_component: number | null;
  dispersion_component: number | null;
  vix_close: number | null;
  nifty_drawdown_pct: number | null;
  pct_above_200dma: number | null;
  dispersion_z: number | null;
}

export interface SectorBreadthSnapshot {
  sector: string;
  date: string;
  n_constituents: number;
  n_covered: number;
  coverage: number;
  pct_above_50dma: number | null;
  pct_above_100dma: number | null;
  pct_above_200dma: number | null;
  pct_advancing_today: number | null;
  n_advancing: number;
  n_declining: number;
  dispersion_20d: number | null;
  median_ret_20d: number | null;
  rs_leaders: [string, number][];
  rs_laggards: [string, number][];
  thrust_day: boolean;
  is_partial_coverage: boolean;
}

export interface SectorRSSnapshot {
  sector: string;
  date: string;
  sector_close: number | null;
  sector_chg_today_pct: number | null;
  rs_5d: number | null;
  rs_20d: number | null;
  rs_60d: number | null;
  rs_120d: number | null;
  rs_252d: number | null;
  rank_5d: number | null;
  rank_20d: number | null;
  rank_60d: number | null;
  rank_120d: number | null;
  rank_252d: number | null;
  rank_change_wow_20d: number | null;
  rank_change_wow_60d: number | null;
  rank_change_wow_120d: number | null;
  rank_change_wow_252d: number | null;
  pct_above_200dma: number | null;
  is_partial_coverage: boolean;
}

export interface AnalogMatch {
  match_date: string;
  distance: number;
  fwd_return_5d: number | null;
  fwd_return_20d: number | null;
  fwd_return_60d: number | null;
  fwd_return_120d: number | null;
  pct_above_200dma: number | null;
  vix_close: number | null;
  nifty_drawdown_pct: number | null;
  stress_score: number | null;
}

export interface AnalogDistribution {
  target_date: string;
  k: number;
  horizon_days: number;
  median: number | null;
  mean: number | null;
  p5: number | null;
  p25: number | null;
  p75: number | null;
  p95: number | null;
  n_with_forward_return: number;
}

export interface WatchlistEntry {
  symbol: string;
  close: number;
  chg_today_pct: number | null;
  score: number;
  note: string;
  sectors: string[];
}

export interface ConstituentContribution {
  symbol: string;
  weight: number;
  return_pct: number;
  contribution_bps: number;
  share_of_move: number | null;
}

export interface ConcentrationReading {
  date: string;
  nifty_return_pct: number;
  equal_weighted_return_pct: number;
  cap_vs_equal_spread_pp: number;
  top_3_share_of_move: number | null;
  top_5_share_of_move: number | null;
  reliance_share_of_move: number | null;
  top_3_symbols: string[];
  top_5_symbols: string[];
  n_constituents_covered: number;
  n_constituents_total: number;
  constituents: ConstituentContribution[];
}

export interface SubgroupSnapshot {
  subgroup: string;
  label: string;
  parent_sector: string;
  n_total: number;
  n_covered: number;
  today_chg_pct: number | null;
  rs_5d: number | null;
  rs_20d: number | null;
  rs_60d: number | null;
  rs_60d_prev_week: number | null;
  rs_60d_wow_delta: number | null;
  pct_above_200dma: number | null;
  members_covered: string[];
}

export interface SubgroupSpread {
  pair: [string, string];
  spread_60d_pp: number | null;
  label: string;
}

export interface SubgroupsResponse {
  subgroups: Record<string, SubgroupSnapshot>;
  sibling_spreads: SubgroupSpread[];
}

export async function getSubgroups(date?: string): Promise<SubgroupsResponse> {
  const q = date ? `?date=${encodeURIComponent(date)}` : "";
  return getJson<SubgroupsResponse>(`/api/insights/subgroups${q}`);
}

export interface AssetFeatures {
  close: number | null;
  z_60d: number | null;
  z_252d: number | null;
  roc_5d: number | null;
  roc_20d: number | null;
  roc_60d: number | null;
  dist_from_200dma: number | null;
  pctile_252d: number | null;
}

export interface CrossAssetEntry {
  asset_id: string;
  label: string;
  data_available: boolean;
  as_of_date: string | null;
  features: AssetFeatures;
}

export interface MarketReading {
  date: string;
  regime: RegimeSnapshot;
  stress: StressSnapshot;
  breadth: Record<string, number | null>;
  macro: Record<string, number | null>;
  sector_breadth: Record<string, SectorBreadthSnapshot>;
  sector_rs: Record<string, SectorRSSnapshot>;
  sector_leaderboard_60d: SectorRSSnapshot[];
  analogs: AnalogMatch[];
  analog_distribution: Record<string, AnalogDistribution>;
  conditional: Record<string, unknown>;
  watchlists: Record<string, WatchlistEntry[]>;
  concentration: ConcentrationReading;
  subgroups: Record<string, SubgroupSnapshot>;
  sibling_spreads: SubgroupSpread[];
  cross_asset: Record<string, CrossAssetEntry>;
}

// ---------- fetchers ----------

/**
 * Forward the caller's Supabase access token to the backend.
 *
 * These are Server Component fetches, so there is no browser to attach a
 * header for us. /api/insights/* is public in normal operation but is
 * admin-only under PRIVATE_MODE (R-028), and the backend enforces that
 * independently of the Next.js middleware gate — deliberately, because
 * R-019 (middleware-bypass CVEs) says one layer is not enough. So the
 * page being reachable does NOT mean the API call is authorised; the
 * token has to travel.
 *
 * Returns null for an anonymous caller rather than throwing: with
 * PRIVATE_MODE off this path is genuinely public and must still work.
 */
async function authHeader(): Promise<Record<string, string>> {
  try {
    const supabase = await getSupabaseServerClient();
    const { data } = await supabase.auth.getSession();
    const token = data.session?.access_token;
    return token ? { Authorization: `Bearer ${token}` } : {};
  } catch {
    return {};
  }
}

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: await authHeader(),
    next: { revalidate: REVALIDATE_SECONDS },
  });
  if (!res.ok) {
    throw new Error(`API ${res.status} ${res.statusText} for ${path}`);
  }
  return res.json() as Promise<T>;
}

export async function getReading(date?: string): Promise<MarketReading> {
  const q = date ? `?date=${encodeURIComponent(date)}` : "";
  return getJson<MarketReading>(`/api/insights/reading${q}`);
}

export interface SectorsResponse {
  date: string | null;
  sector_breadth: Record<string, SectorBreadthSnapshot>;
  sector_rs: Record<string, SectorRSSnapshot>;
  leaderboard_60d: SectorRSSnapshot[];
}

export async function getSectors(date?: string): Promise<SectorsResponse> {
  const q = date ? `?date=${encodeURIComponent(date)}` : "";
  return getJson<SectorsResponse>(`/api/insights/sectors${q}`);
}

export interface AnalogsResponse {
  date: string | null;
  k: number;
  matches: AnalogMatch[];
  distribution: Record<string, AnalogDistribution>;
}

export async function getAnalogs(opts?: { date?: string; k?: number }): Promise<AnalogsResponse> {
  const params: string[] = [];
  if (opts?.date) params.push(`date=${encodeURIComponent(opts.date)}`);
  if (opts?.k) params.push(`k=${opts.k}`);
  const q = params.length ? `?${params.join("&")}` : "";
  return getJson<AnalogsResponse>(`/api/insights/analogs${q}`);
}

export interface WatchlistsResponse {
  date: string | null;
  lists: Record<string, WatchlistEntry[]>;
}

export async function getWatchlists(opts?: { date?: string; limit?: number }): Promise<WatchlistsResponse> {
  const params: string[] = [];
  if (opts?.date) params.push(`date=${encodeURIComponent(opts.date)}`);
  if (opts?.limit) params.push(`limit=${opts.limit}`);
  const q = params.length ? `?${params.join("&")}` : "";
  return getJson<WatchlistsResponse>(`/api/insights/watchlists${q}`);
}

// ---------- stock screener + detail (insights_v2 C4/C5) ----------

/**
 * One NSE 500 row. Screener rows carry the trimmed set; the stock-detail
 * `row` additionally carries the fields marked "detail-only" below (the
 * screener drops them for payload size — see kite-api/app/api/insights.py).
 */
export interface StockRow {
  symbol: string;
  close: number | null;
  // Returns
  ret_1d: number | null;
  ret_1w: number | null;
  ret_1m: number | null;
  ret_3m: number | null;
  ret_6m: number | null;
  ret_12m: number | null;
  // Trend structure
  dist_20dma_pct: number | null;
  dist_50dma_pct: number | null;
  dist_100dma_pct: number | null;
  dist_200dma_pct: number | null;
  dma_50_above_200: boolean | null;
  // Levels
  dist_52w_high_pct: number | null;
  dist_52w_low_pct: number | null;
  days_since_52w_high: number | null;
  drawdown_from_peak_pct: number | null;
  fresh_52w_high: boolean | null;
  // Risk
  atr_pct: number | null;
  vol_60d_annualized: number | null;
  vol_percentile_1y: number | null;
  beta_60d: number | null;
  max_drawdown_1y_pct: number | null;
  rsi_14: number | null;
  // Volume
  vol_ratio: number | null;
  vol_ratio_5d: number | null;
  avg_turnover_20d_cr: number | null;
  liquidity_tier: string | null;
  // RS
  rs_score: number | null;
  rank: number | null;
  percentile: number | null;
  sector_rank: number | null;
  sector_size: number | null;
  rank_delta_21d: number | null;
  // Scores + tags
  trend_score: number | null;
  extension_risk: number | null;
  extension_band: string | null;
  volume_confirmation: number | null;
  volume_band: string | null;
  momentum_consistency: number | null;
  tags: string[];
  sectors: string[];
  zerodha_sector?: string | null;
  super_sector?: string | null;
  // detail-only (present on /stocks/{symbol}.row, absent on screener rows)
  date?: string;
  above_20dma?: boolean | null;
  above_50dma?: boolean | null;
  above_100dma?: boolean | null;
  above_200dma?: boolean | null;
  slope_50dma_20d?: number | null;
  slope_200dma_20d?: number | null;
  vol_20d_annualized?: number | null;
  ret_5d_pctile_1y?: number | null;
  pct_positive_weeks_6m?: number | null;
  updown_vol_ratio_20d?: number | null;
  max_drawdown_6m_pct?: number | null;
  rank_21d_ago?: number | null;
}

export interface ScreenerResponse {
  asof: string | null;
  data_available: boolean;
  rows: StockRow[];
}

export async function getScreener(date?: string): Promise<ScreenerResponse> {
  const q = date ? `?date=${encodeURIComponent(date)}` : "";
  return getJson<ScreenerResponse>(`/api/insights/screener${q}`);
}

export interface PriceSeries {
  symbol: string;
  dates: string[];
  close: (number | null)[];
  sma_50: (number | null)[];
  sma_200: (number | null)[];
  vol_ratio: (number | null)[];
}

export interface RSHistoryPoint {
  date: string;
  rank: number;
  percentile: number | null;
}

export interface PeerEntry {
  symbol: string;
  rank: number;
  sector: string;
}

export interface StockDetailResponse {
  symbol: string;
  data_available: boolean;
  asof?: string;
  row: StockRow | null;
  series: Partial<PriceSeries>;
  rs_rank_history: RSHistoryPoint[];
  peers: PeerEntry[];
}

export async function getStockDetail(symbol: string, date?: string): Promise<StockDetailResponse> {
  const q = date ? `?date=${encodeURIComponent(date)}` : "";
  return getJson<StockDetailResponse>(`/api/insights/stocks/${encodeURIComponent(symbol)}${q}`);
}

export interface MoverName {
  symbol: string;
  close: number | null;
  ret_1d: number | null;
  rank: number | null;
  sectors: string[];
}

export interface RSImprover {
  symbol: string;
  rank: number | null;
  rank_21d_ago: number | null;
  rank_delta_21d: number | null;
  sectors: string[];
}

export interface MoversResponse {
  asof: string | null;
  data_available: boolean;
  fresh_highs: { count: number; names: MoverName[] };
  fresh_lows: { count: number; names: MoverName[] };
  rs_improvers: RSImprover[];
}

export async function getMovers(date?: string): Promise<MoversResponse> {
  const q = date ? `?date=${encodeURIComponent(date)}` : "";
  return getJson<MoversResponse>(`/api/insights/movers${q}`);
}

// ---------- calendar strip (insights_v2 B1/B2/B3) ----------

export interface AnniversarySnapshot {
  horizon_years: number;
  date: string;
  regime: string;
  stress_score: number | null;
  event_tag: string | null;
  actual_offset_days: number;
}

export interface OnThisDayResponse {
  asof: string;
  anniversaries: Record<string, AnniversarySnapshot>;
}

export async function getOnThisDay(date?: string): Promise<OnThisDayResponse> {
  const q = date ? `?date=${encodeURIComponent(date)}` : "";
  return getJson<OnThisDayResponse>(`/api/insights/calendar/on-this-day${q}`);
}

export interface PeriodSeasonality {
  kind: string;
  period: number;
  label: string;
  n: number;
  median_return_pct: number | null;
  q1_return_pct: number | null;
  q3_return_pct: number | null;
  pct_positive: number | null;
}

export interface SeasonalityResponse {
  asof: string;
  data_available: boolean;
  seasonality: {
    asof: string;
    month: PeriodSeasonality | null;
    week: PeriodSeasonality | null;
  };
}

export async function getSeasonality(date?: string): Promise<SeasonalityResponse> {
  const q = date ? `?date=${encodeURIComponent(date)}` : "";
  return getJson<SeasonalityResponse>(`/api/insights/calendar/seasonality${q}`);
}

export interface EventTypeHistory {
  event_type: string;
  n: number;
  median_move_1d_pct: number | null;
  median_move_5d_pct: number | null;
}

export interface UpcomingEvent {
  date: string;
  tag: string;
  event_type: string | null;
  days_until: number;
  history: EventTypeHistory | null;
}

export interface PreEventResponse {
  asof: string;
  window_days: number;
  upcoming: UpcomingEvent[];
}

export async function getPreEvent(date?: string): Promise<PreEventResponse> {
  const q = date ? `?date=${encodeURIComponent(date)}` : "";
  return getJson<PreEventResponse>(`/api/insights/calendar/pre-event${q}`);
}
