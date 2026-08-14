import type { SectionTabItem } from "@/components/insights/mission";

/**
 * The Market Pulse section's tab row — shared by the section root and every
 * indicator detail so navigation never changes shape while drilling
 * (founder feedback, 2026-08-14). The market-state (regime) detail was
 * retired the same day; the four states stay explained on the Daily read.
 */
export const MARKET_TABS: SectionTabItem[] = [
  { slug: "", label: "Daily read" },
  { slug: "stress", label: "Stress" },
  { slug: "breadth", label: "Breadth" },
  { slug: "advance-decline", label: "Advances & declines" },
  { slug: "net-new-highs", label: "Net new highs" },
  { slug: "mcclellan", label: "McClellan" },
  { slug: "vix", label: "India VIX" },
  { slug: "concentration", label: "Concentration" },
];
