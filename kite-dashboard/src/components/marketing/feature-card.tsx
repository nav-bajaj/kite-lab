import type { ReactNode } from "react";

import { cn } from "@/lib/utils";
import { MarketingCard } from "./marketing-card";
import { Halftone } from "./halftone";

/**
 * A card with a graphic panel — the second card primitive (DESIGN.md §2.5,
 * Corgi reference). Elevated `MarketingCard` with a tinted inner panel carrying
 * an illustration/line-motif + halftone, then eyebrow / title / body / optional
 * link. Used for how-it-works steps, learn cards, and any card that leads with a
 * graphic. Plain content cards keep `MarketingCard`.
 */
export function FeatureCard({
  graphic,
  eyebrow,
  title,
  body,
  footer,
  className,
}: {
  graphic?: ReactNode;
  eyebrow?: string;
  title: string;
  body: string;
  footer?: ReactNode;
  className?: string;
}) {
  return (
    <MarketingCard className={cn("flex h-full flex-col", className)}>
      <div className="relative mb-5 flex h-28 items-center justify-center overflow-hidden rounded-[14px] bg-surface-panel-tint">
        <Halftone className="absolute inset-0 opacity-[0.12] [mask-image:radial-gradient(circle_at_60%_50%,#000,transparent_72%)]" />
        <div className="relative">{graphic}</div>
      </div>
      {eyebrow ? (
        <span className="font-mono text-sm text-primary">{eyebrow}</span>
      ) : null}
      <h3 className="mt-2 font-serif text-xl font-medium leading-[1.2] text-foreground">
        {title}
      </h3>
      <p className="mt-2 text-[15px] leading-[1.55] text-muted-foreground">
        {body}
      </p>
      {footer ? <div className="mt-auto pt-4">{footer}</div> : null}
    </MarketingCard>
  );
}
