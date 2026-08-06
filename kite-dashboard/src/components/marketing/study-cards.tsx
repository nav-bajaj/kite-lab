import type { ReactNode } from "react";

import { cn } from "@/lib/utils";

/* Card primitives under study (design_studies loop 15). Three families from
 * the founder's references, all token-derived so they re-theme per palette:
 *
 *  GrainCard   — Google Fonts Knowledge banner: grainy corner-wash gradient,
 *                abstract oversized glyph cropped at the edge, faint
 *                typographic guide lines.
 *  StackCard   — clay.com: pastel card with sibling layers peeking behind,
 *                pill label, content + optional media panel.
 *  CollageCard — clay.com: media field with a color blob and overlapping
 *                floating mini-panels (slots for real product UI later;
 *                the gallery fills them with abstract placeholder rows).
 *
 * These are experiments to be composed into layouts as needed — not yet part
 * of the design system proper.
 */

export function GrainCard({
  glyph = "m",
  className,
  children,
}: {
  glyph?: string;
  className?: string;
  children: ReactNode;
}) {
  return (
    <div
      className={cn(
        "mw-grainy relative overflow-hidden rounded-[28px] border border-border/60",
        className,
      )}
      style={{
        background:
          "radial-gradient(ellipse 70% 110% at 0% 30%, color-mix(in oklab, var(--secondary) 34%, #ffffff) 0%, transparent 62%)," +
          "radial-gradient(ellipse 60% 80% at 100% 100%, color-mix(in oklab, var(--primary) 10%, #ffffff) 0%, transparent 70%)," +
          "linear-gradient(120deg, color-mix(in oklab, var(--primary) 6%, #ffffff), #f6f7f7 70%)",
      }}
    >
      {/* abstract oversized glyph, cropped at the right edge */}
      <span
        aria-hidden
        className="pointer-events-none absolute -right-8 top-1/2 -translate-y-[38%] select-none font-semibold leading-none text-primary/[0.16]"
        style={{ fontSize: "22rem", fontFamily: "var(--font-fraunces), serif" }}
      >
        {glyph}
      </span>
      {/* typographic guide lines around the glyph zone */}
      <div aria-hidden className="pointer-events-none absolute inset-y-0 right-0 w-[46%]">
        <div className="absolute left-0 right-6 top-[18%] border-t border-dashed border-foreground/25" />
        <div className="absolute left-0 right-6 top-[58%] border-t border-foreground/15" />
        <div className="absolute left-0 right-6 top-[82%] border-t border-foreground/15" />
      </div>
      <div className="relative max-w-[58%] p-8 sm:p-10">{children}</div>
    </div>
  );
}

export function StackCard({
  label,
  media,
  className,
  children,
}: {
  label?: string;
  media?: ReactNode;
  className?: string;
  children: ReactNode;
}) {
  return (
    <div className={cn("relative", className)}>
      {/* sibling layers peeking behind the card (clay stack) */}
      <div
        aria-hidden
        className="absolute inset-x-6 -top-3 h-16 rounded-t-[24px] bg-wash3"
      />
      <div
        aria-hidden
        className="absolute inset-x-3 -top-1.5 h-16 rounded-t-[24px] bg-wash2"
      />
      <div className="relative overflow-hidden rounded-[24px] bg-wash1">
        <div className={cn("grid gap-8 p-8 sm:p-10", media && "lg:grid-cols-[1fr_1.05fr]")}>
          <div className="flex flex-col items-start">
            {label ? (
              <span className="rounded-full border border-acc1-line/40 bg-card px-3 py-1 font-mono text-[11px] uppercase tracking-[0.14em] text-acc1-fg">
                {label}
              </span>
            ) : null}
            <div className={cn(label && "mt-5")}>{children}</div>
          </div>
          {media ? (
            <div className="relative min-h-[220px] overflow-hidden rounded-[20px]">
              {media}
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}

export function CollageCard({
  className,
  blobClassName,
  children,
}: {
  className?: string;
  /** color of the backdrop blob; defaults to a primary-tinted field */
  blobClassName?: string;
  children: ReactNode;
}) {
  return (
    <div
      className={cn(
        "relative min-h-[320px] overflow-hidden rounded-[28px] bg-card",
        className,
      )}
    >
      <div
        aria-hidden
        className={cn(
          "absolute inset-x-10 bottom-6 top-16 rounded-[40px]",
          blobClassName ?? "bg-[color-mix(in_oklab,var(--primary)_26%,#ffffff)]",
        )}
      />
      <div className="absolute inset-0">{children}</div>
    </div>
  );
}

/** Floating mini-panel for CollageCard compositions. */
export function FloatPanel({
  className,
  children,
}: {
  className?: string;
  children: ReactNode;
}) {
  return (
    <div
      className={cn(
        "absolute rounded-xl border border-border/70 bg-card p-4 shadow-[0_18px_40px_-18px_rgba(10,20,40,0.35)]",
        className,
      )}
    >
      {children}
    </div>
  );
}

/** Abstract placeholder rows for collage panels — deliberately data-free. */
export function GhostRows({ rows = 4 }: { rows?: number }) {
  const widths = [82, 64, 74, 52, 68, 58];
  return (
    <div className="flex w-full flex-col gap-2.5">
      {Array.from({ length: rows }, (_, i) => (
        <div key={i} className="flex items-center gap-2.5">
          <div className="h-2 w-2 rounded-sm bg-acc1-line/50" />
          <div
            className="h-2 rounded-full bg-muted-foreground/25"
            style={{ width: `${widths[i % widths.length]}%` }}
          />
        </div>
      ))}
    </div>
  );
}
