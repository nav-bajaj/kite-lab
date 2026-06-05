"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useUser } from "@clerk/nextjs";
import { cn } from "@/lib/utils";
import {
  LayoutDashboard,
  TrendingUp,
  RefreshCw,
  History,
  Settings,
  ChevronLeft,
  Wallet,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { useState } from "react";

// `adminOnly` items are filtered out for non-admin clients in the render.
const navigation = [
  { name: "Dashboard", href: "/dashboard", icon: LayoutDashboard, adminOnly: false },
  { name: "Open Positions", href: "/positions", icon: Wallet, adminOnly: false },
  { name: "Performance", href: "/performance", icon: TrendingUp, adminOnly: false },
  { name: "Rebalance", href: "/rebalance", icon: RefreshCw, adminOnly: false },
  { name: "Trades", href: "/trades", icon: History, adminOnly: false },
  { name: "Admin", href: "/admin", icon: Settings, adminOnly: true },
];

export function Sidebar() {
  const pathname = usePathname();
  const { user } = useUser();
  const role = (user?.publicMetadata as { role?: string } | undefined)?.role;
  const isAdmin = role === "admin";
  const visibleNav = navigation.filter((item) => !item.adminOnly || isAdmin);
  const [collapsed, setCollapsed] = useState(false);

  return (
    <aside
      className={cn(
        "fixed left-0 top-0 z-40 h-screen hidden lg:flex flex-col border-r bg-sidebar transition-all duration-300",
        collapsed ? "w-16" : "w-64"
      )}
    >
      {/* Logo */}
      <div className="flex h-16 items-center justify-between px-4 border-b border-sidebar-border">
        {!collapsed && (
          <Link href="/dashboard" className="flex items-center gap-2">
            <div className="h-8 w-8 rounded-lg bg-primary flex items-center justify-center">
              <span className="text-primary-foreground font-bold">M</span>
            </div>
            <span className="font-semibold text-sidebar-foreground">Marketworks</span>
          </Link>
        )}
        {collapsed && (
          <div className="mx-auto h-8 w-8 rounded-lg bg-primary flex items-center justify-center">
            <span className="text-primary-foreground font-bold">M</span>
          </div>
        )}
      </div>

      {/* Collapse button */}
      <div className="px-2 py-2">
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setCollapsed(!collapsed)}
          className={cn(
            "w-full justify-start text-sidebar-foreground hover:bg-sidebar-accent",
            collapsed && "justify-center px-2"
          )}
        >
          <ChevronLeft
            className={cn(
              "h-4 w-4 transition-transform",
              collapsed && "rotate-180"
            )}
          />
          {!collapsed && <span className="ml-2">Collapse</span>}
        </Button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-1 px-2 py-2">
        {visibleNav.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.name}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                isActive
                  ? "bg-sidebar-primary text-sidebar-primary-foreground"
                  : "text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground",
                collapsed && "justify-center px-2"
              )}
              title={collapsed ? item.name : undefined}
            >
              <item.icon className="h-5 w-5 flex-shrink-0" />
              {!collapsed && <span>{item.name}</span>}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      {!collapsed && (
        <div className="border-t border-sidebar-border p-4">
          <p className="text-xs text-sidebar-foreground/60">
            Marketworks v1.0
          </p>
        </div>
      )}
    </aside>
  );
}
