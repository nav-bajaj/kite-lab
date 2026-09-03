/**
 * Pure display helpers for the insight surfaces.
 *
 * These live apart from `insights-api.ts` because that module is
 * server-only: it forwards the caller's session token, which means it
 * imports `next/headers`, which cannot be pulled into a client bundle.
 * The screener table is a Client Component and needs these formatters,
 * so keeping them here is what lets both sides share them.
 *
 * Nothing in this file may import server-only modules.
 */

/** Strip the NIFTY_ prefix for display; sector baskets are index names. */
export function sectorLabel(s: string): string {
  return s.replace(/^NIFTY_/, "").replace(/_/g, " ");
}

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
