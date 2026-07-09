"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useUser } from "@clerk/nextjs";
import { cn } from "@/lib/utils";
import { ChevronLeft } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useSidebar } from "@/contexts/sidebar-context";
import { useUniverse } from "@/contexts/universe-context";
import { useApiAuth } from "@/contexts/api-auth-context";
import { preloadRoute } from "@/lib/preload";
import { getNavigation } from "@/lib/nav";

export function Sidebar() {
  const pathname = usePathname();
  const { user } = useUser();
  const role = (user?.publicMetadata as { role?: string } | undefined)?.role;
  const isAdmin = role === "admin";
  const visibleNav = getNavigation(isAdmin);
  const { collapsed, toggle } = useSidebar();
  const { universeId } = useUniverse();
  const { authReady } = useApiAuth();

  // Warm the destination's data on hover/focus so the page renders from
  // cache on click. Gated on authReady so a hover never fires an
  // unauthenticated request (which would 401).
  const warm = (href: string) => {
    if (authReady) preloadRoute(href, universeId);
  };

  return (
    <aside
      className={cn(
        "fixed left-0 top-0 z-40 h-screen hidden lg:flex flex-col border-r bg-sidebar transition-all duration-300",
        collapsed ? "w-16" : "w-48"
      )}
    >
      {/* Logo — matches the marketing wordmark (MarketingNav): lowercase,
          primary green, no icon mark. Collapsed shows just the "m". */}
      <div className="flex h-16 items-center justify-between px-4 border-b border-sidebar-border">
        {!collapsed && (
          <Link
            href="/"
            className="text-2xl font-semibold tracking-tight text-primary"
          >
            marketworks
          </Link>
        )}
        {collapsed && (
          <Link
            href="/"
            aria-label="Marketworks home"
            className="mx-auto text-2xl font-semibold tracking-tight text-primary"
          >
            m
          </Link>
        )}
      </div>

      {/* Collapse button */}
      <div className="px-2 py-2">
        <Button
          variant="ghost"
          size="sm"
          onClick={toggle}
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
              onMouseEnter={() => warm(item.href)}
              onFocus={() => warm(item.href)}
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
