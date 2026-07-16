"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

// Beta surface: keep only what's distinctly Marketworks — the daily Pulse read
// and the Screener (RS / trend / consistency scores) — plus Learn so newcomers
// can look up any term. Sectors and Watchlists routes still exist and work if
// visited directly; they're just unlinked here until we widen the beta.
const TABS = [
  {
    href: "/insights",
    label: "Pulse",
    desc: "Today's market at a glance — its trend, stress, and which sectors are leading.",
  },
  {
    href: "/insights/screener",
    label: "Screener",
    desc: "Every stock in the market, scored on strength, trend, and consistency.",
  },
  {
    href: "/insights/learn",
    label: "Learn",
    desc: "Plain-English explainers for every term — start here if a word is new.",
  },
];

export function InsightsTabs() {
  const pathname = usePathname();
  return (
    <nav className="grid gap-3 sm:grid-cols-3">
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
            aria-current={active ? "page" : undefined}
            className={cn(
              "flex flex-col gap-1 rounded-xl border p-4 transition-colors",
              active
                ? "border-primary bg-primary/[0.06]"
                : "border-border bg-card hover:border-primary/40",
            )}
          >
            <span
              className={cn(
                "font-serif text-lg font-medium tracking-[-0.01em]",
                active ? "text-primary" : "text-foreground",
              )}
            >
              {t.label}
            </span>
            <span className="text-[13px] leading-[1.45] text-muted-foreground">
              {t.desc}
            </span>
          </Link>
        );
      })}
    </nav>
  );
}
