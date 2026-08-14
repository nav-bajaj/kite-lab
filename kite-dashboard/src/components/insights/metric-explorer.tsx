"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import {
  TimeseriesChart,
  type ReferenceBand,
} from "@/components/insights/timeseries-chart";

/**
 * Chip-switchable metric variants inside one detail chart (breadth detail:
 * the % > N-DMA family + the continuous avg-dist sibling). All series arrive
 * pre-fetched from the server component; switching is pure client state.
 */
export interface MetricVariant {
  /** Panel column name. Named `metric`, not `key` — gitleaks flags
   *  `key:` + string-literal pairs as generic API keys (same false
   *  positive as the insights_v2 sortKey→sortField rename). */
  metric: string;
  label: string;
  sub: string;
  percent: boolean;
  bands: ReferenceBand[];
  values: (number | null)[];
}

export function MetricExplorer({
  dates,
  variants,
}: {
  dates: string[];
  variants: MetricVariant[];
}) {
  const [active, setActive] = useState(variants[0]?.metric);
  const current = variants.find((v) => v.metric === active) ?? variants[0];
  if (!current) return null;

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap gap-1.5">
        {variants.map((v) => (
          <button
            key={v.metric}
            onClick={() => setActive(v.metric)}
            aria-pressed={v.metric === current.metric}
            className={cn(
              "rounded-full border px-3 py-1 text-[12px] font-medium transition-colors",
              v.metric === current.metric
                ? "border-primary bg-primary/[0.08] text-primary"
                : "border-border text-muted-foreground hover:bg-muted hover:text-foreground",
            )}
          >
            {v.label}
          </button>
        ))}
      </div>
      <p className="text-[13px] text-muted-foreground">{current.sub}</p>
      <TimeseriesChart
        key={current.metric}
        dates={dates}
        values={current.values}
        bands={current.bands}
        percent={current.percent}
      />
    </div>
  );
}
