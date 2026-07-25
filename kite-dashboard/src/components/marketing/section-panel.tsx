import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

/**
 * Inset, rounded, floating section panel — the layered marketing surface
 * (DESIGN.md §2.5). Colored sections are NEVER full-bleed bands: the panel
 * floats on the continuous near-white base with side gutters, a large radius,
 * and the panel shadow, so the base flows around it. Variants map to the
 * surface/depth tokens; `deep` and `lichen` carry mist text.
 */
type Variant = "mist" | "tint" | "lichen" | "deep";

function variantClasses(variant: Variant): string {
  switch (variant) {
    case "mist":
      return "bg-surface-panel-mist text-foreground";
    case "tint":
      return "bg-surface-panel-tint text-foreground";
    case "lichen":
      return "bg-primary text-primary-foreground mw-panel-texture";
    case "deep":
      return "bg-surface-panel-deep text-primary-foreground mw-panel-texture";
  }
}

export function SectionPanel({
  variant,
  className,
  children,
}: {
  variant: Variant;
  className?: string;
  children: ReactNode;
}) {
  return (
    <section className="px-6 py-5 sm:px-8">
      <div
        className={cn(
          "relative mx-auto max-w-[1080px] overflow-hidden rounded-panel px-8 py-14 shadow-panel sm:px-14 sm:py-16",
          variantClasses(variant),
          className,
        )}
      >
        {children}
      </div>
    </section>
  );
}
