"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Wallet,
  RefreshCw,
  TrendingUp,
  History,
} from "lucide-react";

import { usePositions } from "@/lib/hooks";
import { cn, formatCurrency, formatPercentValue, getPnLClass } from "@/lib/utils";

/**
 * Mobile bottom navigation (UX study D3, revised 2026-07-26) — five direct
 * destinations, thumb-reachable: Overview · Positions · Rebalance ·
 * Performance · Trade Log. No "More" sheet: the top-bar hamburger carries
 * the website pages, and Account/Admin ride the top bar (avatar, admin nav).
 *
 * Mobile only (hidden ≥ md; desktop keeps the sidebar). Styled in the
 * FloatingNav's floating-glass-pill language — rounded, translucent card,
 * hairline border, backdrop blur — and palette-aware through the tokens.
 */
/**
 * Day's P&L notch — rises from the nav pill on the positions page (the
 * always-visible pulse; Kite's sticky strip re-imagined as part of the nav).
 * Mounted only on /positions, so its SWR hook shares the page's cache entry
 * (same key) and never fetches elsewhere. Polling stays off — the page's own
 * hook keeps the cache fresh (polling while the market is closed, SSE stream
 * writes via mutate while it's open).
 */
function DayPnlNotch() {
  const { data } = usePositions({ enablePolling: false });
  const summary = data?.summary;
  if (!summary || summary.position_count === 0) return null;
  return (
    <div className="-mb-px flex items-baseline gap-2 rounded-t-2xl border border-b-0 border-foreground/8 bg-card/85 px-4 pb-1.5 pt-1 backdrop-blur-md">
      <span className="text-[10.5px] font-semibold uppercase tracking-[0.08em] text-muted-foreground">
        Day&apos;s P&L
      </span>
      <span className={cn("text-[13px] font-semibold tabular-nums", getPnLClass(summary.day_pnl))}>
        {summary.day_pnl >= 0 ? "+" : ""}
        {formatCurrency(summary.day_pnl)} ({formatPercentValue(summary.day_pnl_pct)})
      </span>
    </div>
  );
}

const SLOTS = [
  { name: "Overview", href: "/dashboard", icon: LayoutDashboard },
  { name: "Positions", href: "/positions", icon: Wallet },
  { name: "Rebalance", href: "/rebalance", icon: RefreshCw },
  { name: "Performance", href: "/performance", icon: TrendingUp },
  { name: "Trade Log", href: "/trades", icon: History },
];

export function BottomNav() {
  const pathname = usePathname();

  return (
    <div
      className="fixed inset-x-0 bottom-0 z-40 flex justify-center px-4 pb-[max(env(safe-area-inset-bottom),0.75rem)] md:hidden"
    >
      <div className="flex w-full max-w-[440px] flex-col items-center">
        {pathname.startsWith("/positions") && <DayPnlNotch />}
        <nav
          aria-label="Primary"
          className="grid w-full grid-cols-5 rounded-3xl border border-foreground/8 bg-card/85 px-1 py-1.5 shadow-lg backdrop-blur-md"
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
        </nav>
      </div>
    </div>
  );
}
