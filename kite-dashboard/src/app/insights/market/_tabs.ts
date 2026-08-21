import type { SectionTabItem } from "@/components/insights/mission";

/**
 * The Market Pulse section's tab row — identical on every indicator detail
 * so navigation never changes shape while drilling (founder feedback,
 * 2026-08-14). Regime leads; there is no separate section-root tab —
 * /insights/market redirects to the regime tab (the old "Daily read"
 * duplicated the Overview).
 */
export const MARKET_TABS: SectionTabItem[] = [
  { slug: "regime", label: "Regime", icon: "regime" },
  { slug: "stress", label: "Stress", icon: "stress" },
  { slug: "breadth", label: "Breadth", icon: "breadth" },
  // Short labels keep the row from running 322px off a 390px screen.
  { slug: "advance-decline", label: "Advances & declines", shortLabel: "A/D", icon: "advanceDecline" },
  { slug: "52-week-highs", label: "52-week highs", shortLabel: "52w highs", icon: "highs" },
  { slug: "vix", label: "India VIX", shortLabel: "VIX", icon: "vix" },
  { slug: "concentration", label: "Concentration", shortLabel: "Conc.", icon: "concentration" },
];
