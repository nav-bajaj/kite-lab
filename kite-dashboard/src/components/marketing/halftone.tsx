import { cn } from "@/lib/utils";

/**
 * Editorial halftone dot-screen texture (DESIGN.md §2.5, Corgi reference).
 * Decorative overlay — monochrome dots in the current text color (default
 * lichen). Pass a mask/opacity via className. Meaning lives in adjacent text,
 * so it is aria-hidden. For a true tonal halftone over an illustration, bake it
 * into the self-hosted asset; this is the flat dot-field accent.
 */
export function Halftone({ className }: { className?: string }) {
  return (
    <div
      aria-hidden
      className={cn("mw-halftone pointer-events-none text-primary", className)}
    />
  );
}
