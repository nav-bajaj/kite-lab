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
// Visibility of the Insights entry follows the tri-state access mode:
//   all   → shown to everyone.
//   admin → shown only to admins (the pre-public admin sandbox).
//   off   → hidden entirely (the middleware also redirects the route).
// The Admin entry stays admin-only regardless.
export function getNavigation(isAdmin: boolean): NavItem[] {
  const insightsVisible =
    INSIGHTS_ACCESS === "all" || (INSIGHTS_ACCESS === "admin" && isAdmin);

  const items: NavItem[] = [
    { name: "Overview", href: "/dashboard", icon: LayoutDashboard },
    { name: "Open Positions", href: "/positions", icon: Wallet },
    { name: "Performance", href: "/performance", icon: TrendingUp },
    { name: "Upcoming Trades", href: "/rebalance", icon: RefreshCw },
    { name: "Trade Log", href: "/trades", icon: History },
  ];

  if (insightsVisible) {
    items.push({ name: "Insights", href: "/insights", icon: LineChart });
  }

  if (isAdmin) {
    items.push({ name: "Admin", href: "/admin", icon: Settings });
  }

  return items;
}
