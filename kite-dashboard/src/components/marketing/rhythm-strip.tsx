import { cn } from "@/lib/utils";

/**
 * Textured gutter band between sections — part of the structural grid layer
 * (tasks/design_studies/PREFERENCES.md R1). Texture is confined to these
 * strips; content zones stay clean. Rendered inside the `.mw-rails` frame so
 * the band reads as a rung of the page grid, not a stray divider.
 */
export function RhythmStrip({
  texture = "ticks",
  className,
}: {
  texture?: "ticks" | "hatch" | "grid";
  className?: string;
}) {
  return (
    <div aria-hidden className={cn("mw-strip", `mw-strip-${texture}`, className)} />
  );
}
