"use client";

import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useUser } from "@clerk/nextjs";
import {
  LayoutDashboard,
  Wallet,
  RefreshCw,
  TrendingUp,
  Ellipsis,
  History,
  LineChart,
  User,
  Settings,
  Home,
} from "lucide-react";

import { Sheet, SheetContent, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import { getInsightsNavItem } from "@/lib/nav";
import { cn } from "@/lib/utils";

/**
 * Mobile bottom navigation (UX study D3, 2026-07-25) — the five highest-
 * frequency destinations, thumb-reachable: Overview · Positions · Rebalance
 * · Performance · More. "More" opens a bottom sheet with the lower-frequency
 * surfaces (Trade Log, Insights, Account, Admin, marketing home).
 *
 * Mobile only (hidden ≥ md; desktop keeps the sidebar). Styled in the
 * FloatingNav's floating-glass-pill language — rounded, translucent card,
 * hairline border, backdrop blur — and palette-aware through the tokens.
 */
const SLOTS = [
  { name: "Overview", href: "/dashboard", icon: LayoutDashboard },
  { name: "Positions", href: "/positions", icon: Wallet },
  { name: "Rebalance", href: "/rebalance", icon: RefreshCw },
  { name: "Performance", href: "/performance", icon: TrendingUp },
];

export function BottomNav() {
  const pathname = usePathname();
  const [moreOpen, setMoreOpen] = useState(false);
  const { user } = useUser();
  const role = (user?.publicMetadata as { role?: string } | undefined)?.role;
  const isAdmin = role === "admin";
  const insightsItem = getInsightsNavItem(isAdmin);

  const moreItems = [
    { name: "Trade Log", href: "/trades", icon: History },
    ...(insightsItem ? [{ name: "Insights", href: "/insights", icon: LineChart }] : []),
    { name: "Account", href: "/account", icon: User },
    ...(isAdmin ? [{ name: "Admin", href: "/admin", icon: Settings }] : []),
    { name: "Marketworks home", href: "/", icon: Home },
  ];
  const moreActive = moreItems.some(
    (i) => i.href !== "/" && pathname.startsWith(i.href),
  );

  return (
    <div
      className="fixed inset-x-0 bottom-0 z-40 flex justify-center px-4 pb-[max(env(safe-area-inset-bottom),0.75rem)] md:hidden"
    >
      <nav
        aria-label="Primary"
        className="grid w-full max-w-[440px] grid-cols-5 rounded-3xl border border-foreground/8 bg-card/85 px-1 py-1.5 shadow-lg backdrop-blur-md"
      >
        {SLOTS.map((item) => {
          const active = pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              aria-current={active ? "page" : undefined}
              className={cn(
                "flex flex-col items-center gap-0.5 rounded-2xl py-1.5 text-[10.5px] font-semibold transition-colors",
                active ? "text-primary" : "text-muted-foreground hover:text-foreground",
              )}
            >
              <item.icon className="h-5 w-5" aria-hidden />
              {item.name}
            </Link>
          );
        })}

        <Sheet open={moreOpen} onOpenChange={setMoreOpen}>
          <SheetTrigger asChild>
            <button
              type="button"
              className={cn(
                "flex flex-col items-center gap-0.5 rounded-2xl py-1.5 text-[10.5px] font-semibold transition-colors",
                moreActive ? "text-primary" : "text-muted-foreground hover:text-foreground",
              )}
            >
              <Ellipsis className="h-5 w-5" aria-hidden />
              More
            </button>
          </SheetTrigger>
          <SheetContent side="bottom" className="rounded-t-3xl pb-[max(env(safe-area-inset-bottom),1rem)]">
            <SheetTitle className="px-2 pb-1 text-sm font-semibold text-muted-foreground">
              More
            </SheetTitle>
            <div className="grid gap-1">
              {moreItems.map((item) => {
                const active = item.href !== "/" && pathname.startsWith(item.href);
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    onClick={() => setMoreOpen(false)}
                    className={cn(
                      "flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors",
                      active
                        ? "bg-primary/10 text-primary"
                        : "text-foreground hover:bg-muted",
                    )}
                  >
                    <item.icon className="h-4.5 w-4.5" aria-hidden />
                    {item.name}
                  </Link>
                );
              })}
            </div>
          </SheetContent>
        </Sheet>
      </nav>
    </div>
  );
}
