import type { SectionTabItem } from "@/components/insights/mission";

/**
 * The Market Pulse section's tab row — identical on every indicator detail
 * so navigation never changes shape while drilling (founder feedback,
 * 2026-08-14). Regime leads; there is no separate section-root tab —
 * /insights/market redirects to the regime tab (the old "Daily read"
 * duplicated the Overview).
 */
export const MARKET_TABS: SectionTabItem[] = [
  { slug: "regime", label: "Regime" },
  { slug: "stress", label: "Stress" },
  { slug: "breadth", label: "Breadth" },
  { slug: "advance-decline", label: "Advances & declines" },
  { slug: "net-new-highs", label: "Net new highs" },
  { slug: "mcclellan", label: "McClellan" },
  { slug: "vix", label: "India VIX" },
  { slug: "concentration", label: "Concentration" },
];
