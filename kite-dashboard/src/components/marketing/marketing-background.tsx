import { cn } from "@/lib/utils";

/**
 * Editorial base texture for the layered marketing surface (DESIGN.md §2.5).
 * A low-opacity lichen texture for the near-white base. Two styles:
 *   - grid: fine quant graph-paper lines (Spade reference)
 *   - dots: an editorial dot-grid stipple (printed-page feel)
 *
 * The caller positions and masks it (e.g. absolute, a fixed height, a fade),
 * so the texture can be an accent behind one zone rather than a flat wash over
 * the whole page — a page-wide uniform texture removes the depth contrast that
 * the layering is meant to create. Decorative, aria-hidden; render inside a
 * `relative` container.
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
        "pointer-events-none",
        texture === "dots" ? "mw-dots" : "mw-grid",
        className,
      )}
    />
  );
}
