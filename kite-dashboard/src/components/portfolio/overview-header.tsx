"use client";

import { usePortfolio } from "@/lib/hooks";
import { useUniverse } from "@/contexts/universe-context";
import { getUniverse } from "@/lib/universes";

/** Plain-language header for the Overview: which portfolio you're looking at,
 *  a one-line description, and the date it's current as of. */
export function OverviewHeader() {
  const { universeId } = useUniverse();
  const universe = getUniverse(universeId);
  const { data } = usePortfolio();

  const asOf = data?.as_of_date
    ? new Date(data.as_of_date).toLocaleDateString("en-IN", {
        day: "numeric",
        month: "short",
        year: "numeric",
      })
    : null;

  return (
    <div className="flex flex-col gap-1">
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <h2 className="text-xl font-semibold text-foreground">{universe.name}</h2>
        <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
          {universe.riskProfile}
        </span>
      </div>
      <p className="max-w-2xl text-sm text-muted-foreground">
        {universe.description}. A model portfolio, rebuilt on a schedule to stay
        with the market&apos;s current leaders.
        {asOf ? ` Values as of ${asOf}.` : ""}
      </p>
    </div>
  );
}
