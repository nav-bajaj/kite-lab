import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

/**
 * Elevated marketing card — the Corgi-derived depth recipe (DESIGN.md §2.5):
 * white surface, 24px radius, soft ink-tinted shadow (never black), lifting to
 * the hover shadow on interaction. Floats on the base or inside a mist/tint
 * SectionPanel to build layered depth. Not for nesting inside another card.
 */
export function MarketingCard({
  className,
  children,
  interactive = true,
}: {
  className?: string;
  children: ReactNode;
  interactive?: boolean;
}) {
  return (
    <div
      className={cn(
        "rounded-card bg-card p-7 shadow-card",
        interactive &&
          "transition-[box-shadow,transform] duration-200 ease-expo hover:-translate-y-0.5 hover:shadow-card-hover",
        className,
      )}
    >
      {children}
    </div>
  );
}
