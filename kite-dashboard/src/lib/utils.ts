import { clsx, type ClassValue } from "clsx"
import { twMerge } from "tailwind-merge"

/**
 * Merge Tailwind CSS classes with clsx
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/**
 * Format number as Indian Rupees
 */
export function formatCurrency(value: number, decimals = 0): string {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: decimals,
  }).format(value);
}

/**
 * Format decimal as percentage with sign (0.55 -> +55.00%)
 * Use this for decimal ratios (e.g., 0.0788 for 7.88%)
 */
export function formatPercent(value: number, decimals = 2): string {
  const sign = value >= 0 ? "+" : "";
  return `${sign}${(value * 100).toFixed(decimals)}%`;
}

/**
 * Format percentage value with sign (55 -> +55.00%)
 * Use this when the value is already a percentage (e.g., 55.42 for 55.42%)
 */
export function formatPercentValue(value: number, decimals = 2): string {
  const sign = value >= 0 ? "+" : "";
  return `${sign}${value.toFixed(decimals)}%`;
}

/**
 * Format large numbers with Indian notation (lakhs, crores)
 */
export function formatNumber(value: number, decimals = 2): string {
  return new Intl.NumberFormat("en-IN", {
    maximumFractionDigits: decimals,
  }).format(value);
}

/**
 * Format number in compact form (1.2M, 3.4Cr, etc.)
 */
export function formatCompact(value: number): string {
  if (value >= 10000000) {
    return `₹${(value / 10000000).toFixed(2)}Cr`;
  }
  if (value >= 100000) {
    return `₹${(value / 100000).toFixed(2)}L`;
  }
  return formatCurrency(value);
}

/**
 * Format date as ISO string (YYYY-MM-DD)
 */
export function formatDate(date: string | Date): string {
  const d = typeof date === "string" ? new Date(date) : date;
  return d.toISOString().split("T")[0];
}

/**
 * Format date as human readable (Jan 15, 2026)
 */
export function formatDateLong(date: string | Date): string {
  const d = typeof date === "string" ? new Date(date) : date;
  return d.toLocaleDateString("en-IN", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

/**
 * Get CSS class for P&L coloring
 */
export function getPnLClass(value: number): string {
  if (value > 0) return "text-positive";
  if (value < 0) return "text-negative";
  return "text-muted-foreground";
}
