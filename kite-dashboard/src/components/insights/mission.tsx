import Link from "next/link";
import { ArrowLeft, Maximize2 } from "lucide-react";
import { cn } from "@/lib/utils";

/**
 * Mission-control building blocks (server-safe, no client JS):
 * SectionHeader groups the Overview into MARKET / SECTORS / STOCK LISTS;
 * IndicatorCard is the compact "value + spark + one-liner" card whose expand
 * affordance opens the indicator's detail view; DetailShell wraps a detail
 * view with the back-to-Overview button and a sub-rail of sibling indicators.
 */

export function SectionHeader({
  label,
  link,
  dateQuery = "",
}: {
  label: string;
  link?: { href: string; label: string };
  dateQuery?: string;
}) {
  return (
    <div className="flex items-center gap-3">
      <span className="shrink-0 text-[11px] font-semibold uppercase tracking-[0.15em] text-muted-foreground">
        {label}
      </span>
      <div className="h-px flex-1 bg-border" />
      {link && (
        <Link
          href={`${link.href}${dateQuery}`}
          className="shrink-0 text-[12px] font-medium text-primary underline-offset-2 hover:underline"
        >
          {link.label} ›
        </Link>
      )}
    </div>
  );
}

/** Inline SVG sparkline — server-renderable, tokens resolve via CSS vars. */
export function Sparkline({
  values,
  className,
}: {
  values: (number | null)[];
  className?: string;
}) {
  const pts = values.filter((v): v is number => v !== null && !Number.isNaN(v));
  if (pts.length < 2) return null;
  const W = 300;
  const H = 36;
  const pad = 3;
  const min = Math.min(...pts);
  const max = Math.max(...pts);
  const span = Math.max(1e-9, max - min);
  const n = pts.length;
  const x = (i: number) => pad + (i * (W - 2 * pad)) / (n - 1);
  const y = (v: number) => H - pad - ((v - min) / span) * (H - 2 * pad);
  const points = pts.map((v, i) => `${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(" ");
  const last = pts[n - 1];

  return (
    <svg
      viewBox={`0 0 ${W} ${H}`}
      className={cn("h-9 w-full", className)}
      preserveAspectRatio="none"
      aria-hidden
    >
      <polyline
        points={points}
        fill="none"
        stroke="var(--chart-1)"
        strokeWidth={1.5}
        vectorEffect="non-scaling-stroke"
      />
      <circle cx={x(n - 1)} cy={y(last)} r={2.5} fill="var(--chart-1)" />
    </svg>
  );
}

/**
 * Compact overview card. The whole card is the expand affordance when `href`
 * is given (mission control: click to open the indicator's detail view).
 */
export function IndicatorCard({
  label,
  href,
  children,
  spark,
  foot,
}: {
  label: string;
  href?: string;
  children: React.ReactNode;
  spark?: (number | null)[];
  foot?: React.ReactNode;
}) {
  const body = (
    <>
      <div className="flex items-center justify-between gap-2">
        <span className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
          {label}
        </span>
        {href && (
          <Maximize2
            className="h-3.5 w-3.5 text-muted-foreground transition-colors group-hover:text-primary"
            aria-hidden
          />
        )}
      </div>
      {children}
      {spark && <Sparkline values={spark} />}
      {foot && (
        <span className="text-[12px] leading-[1.5] text-muted-foreground">{foot}</span>
      )}
    </>
  );
  const cardClass =
    "flex flex-col gap-2 rounded-xl border border-border bg-card p-4 transition-colors";
  if (href) {
    return (
      <Link href={href} className={cn(cardClass, "group hover:border-primary/50")}>
        {body}
      </Link>
    );
  }
  return <div className={cardClass}>{body}</div>;
}

export interface SubRailItem {
  slug: string;
  label: string;
  ready: boolean;
}

/**
 * Detail-view wrapper: back button + breadcrumb up top, a sub-rail of the
 * section's sibling indicators on the left, content on the right. Not-yet-built
 * indicators render as disabled "soon" rows rather than dead links.
 */
export function DetailShell({
  section,
  title,
  items,
  activeSlug,
  basePath,
  overviewPath = "/insights",
  dateQuery = "",
  children,
}: {
  section: string;
  title: string;
  items: SubRailItem[];
  activeSlug: string;
  basePath: string;
  overviewPath?: string;
  dateQuery?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-wrap items-center gap-3">
        <Link
          href={`${overviewPath}${dateQuery}`}
          className="flex items-center gap-1.5 rounded-full border border-border bg-card px-3 py-1.5 text-[13px] font-medium text-foreground transition-colors hover:bg-muted"
        >
          <ArrowLeft className="h-3.5 w-3.5" aria-hidden />
          Overview
        </Link>
        <span className="text-[13px] text-muted-foreground">
          {section} / <span className="text-foreground">{title}</span>
        </span>
      </div>
      <div className="flex flex-col gap-5 md:flex-row md:items-start">
        <nav
          aria-label={`${section} indicators`}
          className="flex shrink-0 gap-1 overflow-x-auto md:sticky md:top-24 md:w-44 md:flex-col md:overflow-visible"
        >
          {items.map((item) =>
            item.ready ? (
              <Link
                key={item.slug}
                href={`${basePath}/${item.slug}${dateQuery}`}
                aria-current={item.slug === activeSlug ? "page" : undefined}
                className={cn(
                  "shrink-0 whitespace-nowrap rounded-lg px-3 py-1.5 text-[13px] transition-colors",
                  item.slug === activeSlug
                    ? "bg-primary/[0.08] font-semibold text-primary"
                    : "font-medium text-foreground hover:bg-muted",
                )}
              >
                {item.label}
              </Link>
            ) : (
              <span
                key={item.slug}
                className="flex shrink-0 items-center gap-1.5 whitespace-nowrap rounded-lg px-3 py-1.5 text-[13px] text-muted-foreground"
              >
                {item.label}
                <span className="rounded-full bg-muted px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wide">
                  soon
                </span>
              </span>
            ),
          )}
        </nav>
        <div className="min-w-0 flex-1">{children}</div>
      </div>
    </div>
  );
}

/** Descriptive stat tile row under a detail chart. */
export function StatStrip({
  stats,
}: {
  stats: { label: string; value: string; sub?: string }[];
}) {
  return (
    <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
      {stats.map((s) => (
        <div
          key={s.label}
          className="flex flex-col gap-0.5 rounded-xl border border-border bg-card px-4 py-3"
        >
          <span className="text-[10px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">
            {s.label}
          </span>
          <span className="font-serif text-xl font-medium text-foreground">{s.value}</span>
          {s.sub && <span className="text-[11px] text-muted-foreground">{s.sub}</span>}
        </div>
      ))}
    </div>
  );
}
