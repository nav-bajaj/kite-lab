import { cn } from "@/lib/utils";

/**
 * Fixed-viewport quant grid for the marketing base (homepage_visual_refresh).
 *
 * Graph-paper lines with faint intersection nodes, radially masked so the
 * pattern concentrates in the viewport focus and fades at the edges. Because
 * the layer is fixed, the focus band follows the page as it scrolls — whatever
 * the reader is looking at always has grid behind it. All styling (including a
 * whisper of opacity breath, static under reduced-motion) lives in the
 * `.mw-flow-grid` rule. Sits at z-0 behind the content; opaque panels cover it,
 * so it reads only in the near-white base. Decorative (aria-hidden).
 */
export function FlowGrid({ className }: { className?: string }) {
  return (
    <div
      aria-hidden
      className={cn("mw-flow-grid pointer-events-none fixed inset-0 z-0", className)}
    />
  );
}
