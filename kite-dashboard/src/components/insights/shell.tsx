"use client";

import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import {
  Activity,
  BookOpen,
  ChevronLeft,
  LayoutGrid,
  ListChecks,
  Radar,
  Search,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useSidebar } from "@/contexts/sidebar-context";
import { Button } from "@/components/ui/button";
import { PalettePicker } from "@/components/shared/palette-picker";
import { UserMenu } from "@/components/shared/user-menu";

/**
 * Insights app shell — full-screen like the portfolios dashboard (founder
 * review, Slice 1): fixed collapsible sidebar + full-width top bar, no
 * marketing chrome. The top bar stays site-level (wordmark, Dashboard link,
 * account); insights sections live ONLY in the sidebar
 * (tasks/insights_dashboard_v2/DASHBOARD_DESIGN.md §1).
 */
const NAV = [
  { href: "/insights", label: "Overview", icon: LayoutGrid, exact: true },
  { href: "/insights/market", label: "Market Pulse", icon: Activity },
  { href: "/insights/sectors", label: "Sectors & Rotation", icon: Radar },
  { href: "/insights/watchlists", label: "Stock Lists", icon: ListChecks },
  { href: "/insights/screener", label: "Screener", icon: Search, alsoActive: "/insights/stocks" },
  { href: "/insights/learn", label: "Learn", icon: BookOpen },
];

function useNavState() {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const date = searchParams.get("date");
  const dateQuery = date ? `?date=${encodeURIComponent(date)}` : "";
  const isActive = (item: (typeof NAV)[number]) =>
    item.exact
      ? pathname === item.href
      : pathname.startsWith(item.href) ||
        (item.alsoActive ? pathname.startsWith(item.alsoActive) : false);
  return { dateQuery, isActive };
}

/** Fixed desktop sidebar, collapse behavior identical to the dashboard's. */
export function InsightsAppSidebar() {
  const { dateQuery, isActive } = useNavState();
  const { collapsed, toggle } = useSidebar();

  return (
    <aside
      className={cn(
        "fixed left-0 top-0 z-40 hidden h-screen flex-col border-r bg-sidebar transition-all duration-300 lg:flex",
        collapsed ? "w-16" : "w-48",
      )}
    >
      <div className="flex h-16 items-center border-b border-sidebar-border px-4">
        <Link
          href="/"
          aria-label="Marketworks home"
          className={cn(
            "text-2xl font-semibold tracking-tight text-primary",
            collapsed && "mx-auto",
          )}
        >
          {collapsed ? "m" : "marketworks"}
        </Link>
      </div>

      <div className="flex items-center px-2 pt-3">
        <Button
          variant="ghost"
          size="sm"
          onClick={toggle}
          className={cn(
            "gap-1.5 text-muted-foreground",
            collapsed ? "mx-auto px-2" : "px-3",
          )}
        >
          <ChevronLeft
            className={cn("h-4 w-4 transition-transform", collapsed && "rotate-180")}
          />
          {!collapsed && "Collapse"}
        </Button>
      </div>

      <nav aria-label="Insights sections" className="flex flex-col gap-1 px-2 py-3">
        {NAV.map((item) => {
          const active = isActive(item);
          const Icon = item.icon;
          return (
            <Link
              key={item.href}
              href={`${item.href}${dateQuery}`}
              aria-current={active ? "page" : undefined}
              title={collapsed ? item.label : undefined}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                active
                  ? "bg-primary text-primary-foreground"
                  : "text-foreground hover:bg-primary/10",
                collapsed && "justify-center px-2",
              )}
            >
              <Icon className="h-4 w-4 shrink-0" aria-hidden />
              {!collapsed && item.label}
            </Link>
          );
        })}
      </nav>

      {!collapsed && (
        <div className="mt-auto border-t border-sidebar-border px-4 py-3 text-[11px] text-muted-foreground">
          Marketworks Insights
        </div>
      )}
    </aside>
  );
}

/**
 * Full-width top bar. `pickerSlot` receives the compact snapshot picker from
 * the layout (it lives under app/insights/_components).
 */
export function InsightsTopbar({ pickerSlot }: { pickerSlot?: React.ReactNode }) {
  return (
    <header className="sticky top-0 z-30 flex h-16 items-center gap-3 border-b bg-background px-3 sm:px-4 lg:px-6">
      <Link
        href="/"
        className="text-xl font-semibold tracking-tight text-primary lg:hidden"
      >
        marketworks
      </Link>
      <span className="hidden text-[15px] font-semibold text-foreground lg:block">
        Insights
      </span>
      <div className="ml-auto flex items-center gap-2 sm:gap-3">
        {pickerSlot}
        <Link
          href="/dashboard"
          className="hidden text-[13px] font-medium text-muted-foreground transition-colors hover:text-foreground sm:block"
        >
          Dashboard
        </Link>
        <PalettePicker />
        <UserMenu />
      </div>
    </header>
  );
}

/** Horizontal scroll section nav for < lg screens (no sidebar there). */
export function InsightsMobileNav() {
  const { dateQuery, isActive } = useNavState();
  return (
    <nav
      aria-label="Insights sections"
      className="flex gap-1.5 overflow-x-auto pb-1"
    >
      {NAV.map((item) => {
        const active = isActive(item);
        return (
          <Link
            key={item.href}
            href={`${item.href}${dateQuery}`}
            aria-current={active ? "page" : undefined}
            className={cn(
              "shrink-0 whitespace-nowrap rounded-full border px-3.5 py-1.5 text-[13px] font-medium transition-colors",
              active
                ? "border-primary bg-primary text-primary-foreground"
                : "border-border bg-card text-foreground",
            )}
          >
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}
