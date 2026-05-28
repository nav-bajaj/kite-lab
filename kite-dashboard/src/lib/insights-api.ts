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
}

// ---------- fetchers ----------

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
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

// ---------- formatters ----------

export function fmtPct(v: number | null | undefined, decimals = 1, signed = false): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  const formatted = (v * 100).toFixed(decimals);
  return signed && v >= 0 ? `+${formatted}%` : `${formatted}%`;
}

export function fmtNum(v: number | null | undefined, decimals = 2): string {
  if (v === null || v === undefined || Number.isNaN(v)) return "—";
  return v.toFixed(decimals);
}

const REGIME_LABELS: Record<string, string> = Object.freeze({
  TREND_BULL: "Trend Bull",
  DRIFT: "Drift",
  STRETCHED: "Stretched",
  STRESS: "Stress",
});

export function regimeLabel(r: string): string {
  return Object.prototype.hasOwnProperty.call(REGIME_LABELS, r)
    ? REGIME_LABELS[r as keyof typeof REGIME_LABELS]
    : r;
}
