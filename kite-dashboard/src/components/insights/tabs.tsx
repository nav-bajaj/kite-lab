"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

const TABS = [
  { href: "/insights", label: "Pulse" },
  { href: "/insights/screener", label: "Screener" },
  { href: "/insights/sectors", label: "Sectors" },
  { href: "/insights/watchlists", label: "Watchlists" },
  { href: "/insights/learn", label: "Learn" },
];

export function InsightsTabs() {
  const pathname = usePathname();
  return (
    <nav className="flex flex-wrap gap-2">
      {TABS.map((t) => {
        const active =
          t.href === "/insights"
            ? pathname === "/insights"
            : t.href === "/insights/screener"
              ? pathname.startsWith(t.href) || pathname.startsWith("/insights/stocks")
              : pathname.startsWith(t.href);
        return (
          <Link
            key={t.href}
            href={t.href}
            className={cn(
              "rounded-lg px-4 py-2 text-sm font-medium transition-colors",
              active
                ? "bg-primary text-primary-foreground"
                : "border border-border text-muted-foreground hover:text-foreground",
            )}
          >
            {t.label}
          </Link>
        );
      })}
    </nav>
  );
}
