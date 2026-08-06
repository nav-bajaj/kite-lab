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
  visual,
  className,
  children,
}: {
  glyph?: string;
  /** replaces the glyph + guide lines in the right zone (e.g. ResearchLens) */
  visual?: ReactNode;
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
          "radial-gradient(ellipse 70% 110% at 0% 30%, color-mix(in oklab, var(--secondary) 34%, var(--card)) 0%, transparent 62%)," +
          "radial-gradient(ellipse 60% 80% at 100% 100%, color-mix(in oklab, var(--primary) 10%, var(--card)) 0%, transparent 70%)," +
          "linear-gradient(120deg, color-mix(in oklab, var(--primary) 6%, var(--card)), color-mix(in oklab, var(--foreground) 3%, var(--card)) 70%)",
      }}
    >
      {visual ? (
        <div
          aria-hidden
          className="pointer-events-none absolute inset-y-0 right-0 w-[46%]"
        >
          {visual}
        </div>
      ) : (
        <>
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
        </>
      )}
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
          blobClassName ?? "bg-[color-mix(in_oklab,var(--primary)_26%,var(--card))]",
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

/* ---- Loop 16 additions (clay.com references, batch 2) ---- */

/** Centered section opener: heading, subcopy, one dark pill CTA. */
export function SectionHeader({
  title,
  sub,
  cta,
}: {
  title: ReactNode;
  sub?: ReactNode;
  cta?: { href: string; label: string };
}) {
  return (
    <div className="mx-auto max-w-[760px] text-center">
      <h2 className="text-[1.9rem] font-semibold leading-[1.1] tracking-[-0.02em] text-foreground sm:text-[2.5rem]">
        {title}
      </h2>
      {sub ? (
        <p className="mx-auto mt-4 max-w-[58ch] text-base leading-[1.65] text-muted-foreground sm:text-lg">
          {sub}
        </p>
      ) : null}
      {cta ? (
        <a
          href={cta.href}
          className="mt-7 inline-flex items-center gap-2 rounded-full bg-foreground px-6 py-3 text-sm font-semibold text-background transition-transform duration-150 hover:-translate-y-px"
        >
          {cta.label} <span aria-hidden>→</span>
        </a>
      ) : null}
    </div>
  );
}

/** Soft feature tile: icon, generous air, heading, body (clay 3-up row). */
export function FeatureTile({
  icon,
  iconClassName,
  title,
  children,
  className,
}: {
  icon?: ReactNode;
  /** color utility for the icon, e.g. "text-acc1-line" (defaults to primary) */
  iconClassName?: string;
  title: string;
  children: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "rounded-[20px] bg-[color-mix(in_oklab,var(--foreground)_3.5%,var(--card))] p-7 sm:p-8",
        className,
      )}
    >
      {icon ? (
        <div className={cn("mb-10", iconClassName ?? "text-primary")}>{icon}</div>
      ) : null}
      <h3 className="text-xl font-semibold leading-[1.25] tracking-[-0.01em] text-foreground">
        {title}
      </h3>
      <p className="mt-3 text-[15px] leading-[1.65] text-muted-foreground">
        {children}
      </p>
    </div>
  );
}

/** Colored frame wrapping a cropped white media panel (clay guide cards). */
export function FrameCard({
  frameClassName,
  className,
  children,
}: {
  /** background utility for the frame, e.g. "bg-acc1-line" */
  frameClassName?: string;
  className?: string;
  children: ReactNode;
}) {
  return (
    <div
      className={cn(
        "overflow-hidden rounded-[22px] pl-4 pt-4",
        frameClassName ?? "bg-acc1-line",
        className,
      )}
    >
      <div className="h-full min-h-[180px] overflow-hidden rounded-tl-[16px] bg-card p-5">
        {children}
      </div>
    </div>
  );
}

/** Guide/library card: framed media, tag pill, title, footer meta. */
export function GuideCard({
  href,
  media,
  frameClassName,
  tag,
  tagClassName,
  title,
  meta,
  children,
}: {
  href: string;
  media: ReactNode;
  frameClassName?: string;
  tag?: string;
  tagClassName?: string;
  title: string;
  meta?: ReactNode;
  children?: ReactNode;
}) {
  return (
    <a href={href} className="group flex h-full flex-col">
      <FrameCard frameClassName={frameClassName}>{media}</FrameCard>
      {tag ? (
        <span
          className={cn(
            "mt-5 w-fit rounded-full px-3 py-1 text-xs font-semibold",
            tagClassName ?? "bg-acc1 text-acc1-fg",
          )}
        >
          {tag}
        </span>
      ) : null}
      <h3 className="mt-3 text-xl font-semibold leading-[1.25] tracking-[-0.01em] text-foreground group-hover:text-primary">
        {title}
      </h3>
      {children ? (
        <p className="mt-2 text-[15px] leading-[1.6] text-muted-foreground">
          {children}
        </p>
      ) : null}
      {meta ? (
        <div className="mt-auto flex items-center justify-between pt-5 text-sm text-muted-foreground">
          {meta}
        </div>
      ) : null}
    </a>
  );
}
