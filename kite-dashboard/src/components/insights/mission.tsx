import Link from "next/link";
import {
  Activity,
  ArrowLeft,
  ArrowUpDown,
  AudioWaveform,
  Flag,
  Focus,
  Gauge,
  ListChecks,
  Maximize2,
  Radar,
  Users,
  Waypoints,
  type LucideIcon,
} from "lucide-react";

/** Tab and section glyphs. Deliberately NOT one per regime state — the
 *  regime lexicon is compliance-controlled and a glyph per state would be
 *  editorial commentary on it; those keep the colour swatch instead. */
const TAB_ICONS: Record<string, LucideIcon> = {
  regime: Waypoints,
  stress: Gauge,
  breadth: Users,
  advanceDecline: ArrowUpDown,
  highs: Flag,
  vix: AudioWaveform,
  concentration: Focus,
};

/** Written out rather than interpolated — Tailwind only ships classes it can
 *  find as literal strings in the source. */
const ACCENT_CHIP = {
  acc1: "bg-acc1 text-acc1-fg",
  acc3: "bg-acc3 text-acc3-fg",
  acc5: "bg-acc5 text-acc5-fg",
} as const;

const SECTION_ICONS: Record<string, LucideIcon> = {
  market: Activity,
  sectors: Radar,
  lists: ListChecks,
};
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
  icon,
  accent = "acc1",
}: {
  label: string;
  link?: { href: string; label: string };
  dateQuery?: string;
  /** Key into SECTION_ICONS — the same glyph the sidebar uses for this
   *  destination, so header and nav read as the same object. */
  icon?: string;
  /** Categorical accent chip: non-valenced by design, and the only token
   *  family with a matching -fg guaranteed to pass contrast in all six
   *  palettes. Keys are static so Tailwind can extract the classes. */
  accent?: keyof typeof ACCENT_CHIP;
}) {
  /* eslint-disable-next-line security/detect-object-injection -- key comes from our own SECTION_ICONS registry */
  const Icon = icon ? SECTION_ICONS[icon] : undefined;
  return (
    <div className="flex items-center gap-2 lg:gap-3">
      {Icon && (
        <span
          className={cn(
            "flex h-5 w-5 shrink-0 items-center justify-center rounded-md",
            /* eslint-disable-next-line security/detect-object-injection -- accent is a keyof typeof ACCENT_CHIP */
            ACCENT_CHIP[accent],
          )}
        >
          <Icon className="h-3 w-3" aria-hidden />
        </span>
      )}
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

/** A grid whose cells are separated by a 1px rule instead of a gap, so a
 *  dense instrument panel still reads as separate readings. `gap-px` over a
 *  `bg-border` parent is wrap-safe in a way `divide-*` is not. The dashboard
 *  runs tighter than the marketing surface on purpose (founder, 2026-08-21).
 *  `overflow-hidden` clips the rounded corners, so cells opt their focus ring
 *  back on top with `focus-visible:relative focus-visible:z-10`. */
export function CardGrid({
  cols,
  className,
  children,
}: {
  cols?: string;
  className?: string;
  children: React.ReactNode;
}) {
  return (
    <div
      className={cn(
        "grid gap-px overflow-hidden rounded-xl border border-border bg-border",
        cols,
        className,
      )}
    >
      {children}
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
      className={cn("h-6 w-full lg:h-7", className)}
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
            className="h-3 w-3 text-muted-foreground transition-colors group-hover:text-primary"
            aria-hidden
          />
        )}
      </div>
      {children}
      {spark && <Sparkline values={spark} />}
      {foot && (
        <span className="line-clamp-2 text-[11px] leading-[1.4] text-muted-foreground lg:line-clamp-1">
          {foot}
        </span>
      )}
    </>
  );
  const cardClass =
    "flex min-w-0 flex-col gap-1.5 bg-card p-3 transition-colors lg:gap-2 lg:px-3.5 lg:py-2.5";
  if (href) {
    return (
      <Link
        href={href}
        className={cn(
          cardClass,
          // The whole cell is the link; without a border to tint, the hover
          // affordance moves to the surface. z-10 keeps the focus ring above
          // the grid's overflow clip.
          "group hover:bg-muted/50 focus-visible:relative focus-visible:z-10",
        )}
      >
        {body}
      </Link>
    );
  }
  return <div className={cardClass}>{body}</div>;
}

export interface SectionTabItem {
  /** "" is the section's own root page. */
  slug: string;
  label: string;
  /** Used under `sm`, where the full label would overflow the row. */
  shortLabel?: string;
  /** Key into TAB_ICONS. */
  icon?: string;
}

/**
 * Horizontal browser-tab-style navigation for a section — rendered
 * identically on the section root AND on every indicator detail, so the
 * navigation never changes shape as the user drills in (founder feedback,
 * 2026-08-14). Underline marks the active tab; the row scrolls on narrow
 * screens.
 */
export function SectionTabs({
  items,
  activeSlug,
  basePath,
  query = "",
}: {
  items: SectionTabItem[];
  activeSlug: string;
  basePath: string;
  query?: string;
}) {
  return (
    // Browser-tab styling: the active tab is a raised card fused with the
    // content edge (transparent bottom border over the rule line).
    <nav
      aria-label="Section indicators"
      className="mw-no-scrollbar relative flex gap-1 overflow-x-auto border-b border-border after:pointer-events-none after:sticky after:right-0 after:ml-auto after:h-8 after:w-8 after:shrink-0 after:bg-gradient-to-l after:from-background lg:after:hidden"
    >
      {items.map((item) => {
        const href = item.slug ? `${basePath}/${item.slug}${query}` : `${basePath}${query}`;
        const active = item.slug === activeSlug;
        const Icon = item.icon ? TAB_ICONS[item.icon] : undefined;
        return (
          <Link
            key={item.slug || "__root"}
            href={href}
            aria-current={active ? "page" : undefined}
            className={cn(
              "-mb-px flex shrink-0 items-center gap-1.5 whitespace-nowrap rounded-t-lg border px-3 py-2.5 text-[13px] transition-colors lg:px-3.5 lg:py-2",
              active
                ? "border-border border-b-transparent bg-card font-semibold text-primary"
                : "border-transparent font-medium text-muted-foreground hover:bg-muted/60 hover:text-foreground",
            )}
          >
            {Icon && <Icon className="h-3.5 w-3.5 shrink-0" aria-hidden />}
            <span className="sm:hidden">{item.shortLabel ?? item.label}</span>
            <span className="hidden sm:inline">{item.label}</span>
          </Link>
        );
      })}
    </nav>
  );
}

/**
 * Detail/section wrapper: back-to-Overview button + section tabs up top,
 * content full-width below. The tab row is the SAME component on the
 * section root and on details — consistent navigation while drilling.
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
  items: SectionTabItem[];
  activeSlug: string;
  basePath: string;
  overviewPath?: string;
  dateQuery?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-2 lg:gap-3">
      {/* The back-pill and breadcrumb repeat what InsightsMobileNav and the
          tab row already show; on a 390px screen that is 50px of chrome
          before any data. Desktop keeps them. */}
      <div className="hidden flex-wrap items-center gap-3 lg:flex">
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
      <SectionTabs
        items={items}
        activeSlug={activeSlug}
        basePath={basePath}
        query={dateQuery}
      />
      <div className="min-w-0">{children}</div>
    </div>
  );
}

/** Descriptive stat tile row under a detail chart. */
export function StatStrip({
  stats,
}: {
  stats: { label: string; value: React.ReactNode; sub?: string }[];
}) {
  return (
    <CardGrid cols="grid-cols-2 lg:grid-cols-4">
      {stats.map((s) => (
        <div
          key={s.label}
          className="flex min-w-0 flex-col gap-0.5 bg-card px-3 py-2 lg:px-4 lg:py-2.5"
        >
          <span className="text-[10px] font-semibold uppercase tracking-[0.12em] text-muted-foreground">
            {s.label}
          </span>
          <span className="text-[18px] font-semibold leading-tight text-foreground lg:text-xl">
            {s.value}
          </span>
          {s.sub && (
            <span className="text-[11px] leading-[1.35] text-muted-foreground">{s.sub}</span>
          )}
        </div>
      ))}
    </CardGrid>
  );
}
