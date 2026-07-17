import {
  LayoutDashboard,
  TrendingUp,
  RefreshCw,
  History,
  Settings,
  Wallet,
  LineChart,
  type LucideIcon,
} from "lucide-react";
import { INSIGHTS_ACCESS } from "@/lib/flags";

export interface NavItem {
  name: string;
  href: string;
  icon: LucideIcon;
}

// Single source of truth for the signed-in sidebar (desktop + mobile).
// The sidebar holds the portfolio-scoped tabs; Insights (a market-wide view)
// lives in the top header instead — see getInsightsNavItem. The Admin entry
// stays admin-only.
export function getNavigation(isAdmin: boolean): NavItem[] {
  const items: NavItem[] = [
    { name: "Overview", href: "/dashboard", icon: LayoutDashboard },
    { name: "Open Positions", href: "/positions", icon: Wallet },
    { name: "Performance", href: "/performance", icon: TrendingUp },
    { name: "Upcoming Trades", href: "/rebalance", icon: RefreshCw },
    { name: "Trade Log", href: "/trades", icon: History },
  ];

  if (isAdmin) {
    items.push({ name: "Admin", href: "/admin", icon: Settings });
  }

  return items;
}

// The Insights entry, surfaced in the top header rather than the sidebar.
// Visibility follows the tri-state access mode:
//   all   → shown to everyone.
//   admin → shown only to admins (the pre-public admin sandbox).
//   off   → hidden entirely (the middleware also redirects the route).
export function getInsightsNavItem(isAdmin: boolean): NavItem | null {
  const visible =
    INSIGHTS_ACCESS === "all" || (INSIGHTS_ACCESS === "admin" && isAdmin);
  return visible
    ? { name: "Insights", href: "/insights", icon: LineChart }
    : null;
}
