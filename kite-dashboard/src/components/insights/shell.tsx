"use client";

import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import {
  Activity,
  BookOpen,
  LayoutGrid,
  ListChecks,
  Radar,
  Search,
} from "lucide-react";
import { cn } from "@/lib/utils";

/**
 * Insights sidebar — the surface's own navigation. The floating site nav
 * above it stays site-level (Portfolios / Library / Insights); these entries
 * never move up there. Mission-control IA: Overview is home, every other
 * entry is a section (see tasks/insights_dashboard_v2/DASHBOARD_DESIGN.md).
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

export function InsightsSidebar() {
  const { dateQuery, isActive } = useNavState();
  return (
    <nav
      aria-label="Insights sections"
      className="sticky top-24 hidden w-52 shrink-0 flex-col gap-1 self-start lg:flex"
    >
      {NAV.map((item) => {
        const active = isActive(item);
        const Icon = item.icon;
        return (
          <Link
            key={item.href}
            href={`${item.href}${dateQuery}`}
            aria-current={active ? "page" : undefined}
            className={cn(
              "flex items-center gap-2.5 rounded-lg px-3 py-2 text-[13px] font-medium transition-colors",
              active
                ? "bg-primary text-primary-foreground"
                : "text-foreground hover:bg-primary/[0.06]",
            )}
          >
            <Icon className="h-4 w-4 shrink-0" aria-hidden />
            {item.label}
          </Link>
        );
      })}
    </nav>
  );
}

/** Horizontal scroll variant for < lg screens. */
export function InsightsMobileNav() {
  const { dateQuery, isActive } = useNavState();
  return (
    <nav
      aria-label="Insights sections"
      className="-mx-4 flex gap-1.5 overflow-x-auto px-4 pb-1 lg:hidden"
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
