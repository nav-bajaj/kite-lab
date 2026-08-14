import { redirect } from "next/navigation";
import { insightsQuery, parseUniverse } from "@/lib/insights-api";

export const dynamic = "force-dynamic";

/**
 * The Market Pulse section has no separate landing page — the old "Daily
 * read" duplicated the Overview (founder, 2026-08-14). The sidebar entry
 * lands on the first tab, Regime, preserving snapshot/universe scope.
 */
export default async function MarketPulseIndex({
  searchParams,
}: {
  searchParams: Promise<{ date?: string; universe?: string }>;
}) {
  const { date, universe } = await searchParams;
  redirect(`/insights/market/regime${insightsQuery({ date, universe: parseUniverse(universe) })}`);
}
