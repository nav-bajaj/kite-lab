import { cn } from "@/lib/utils";

/**
 * Editorial base texture for the layered marketing surface (DESIGN.md §2.5).
 * A low-opacity lichen texture that sits in the near-white base and flows down
 * the whole page behind the inset panels (which cover it with their solid fill),
 * so the texture only reads in the white "flow". Two styles:
 *   - grid: fine quant graph-paper lines (Spade reference)
 *   - dots: an editorial dot-grid stipple (printed-page feel)
 * Fades at the top (under the nav) and bottom (into the footer). Decorative,
 * aria-hidden; render inside a `relative` container.
 */
export function MarketingBackground({
  texture = "grid",
  className,
}: {
  texture?: "grid" | "dots";
  className?: string;
}) {
  return (
    <div
      aria-hidden
      className={cn(
        "pointer-events-none absolute inset-0 [mask-image:linear-gradient(to_bottom,transparent,#000_5%,#000_85%,transparent)]",
        texture === "dots" ? "mw-dots" : "mw-grid",
        className,
      )}
    />
  );
}
