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
  Wallet,
} from "lucide-react";
import { SheetClose } from "@/components/ui/sheet";

const navigation = [
  { name: "Dashboard", href: "/dashboard", icon: LayoutDashboard, adminOnly: false },
  { name: "Open Positions", href: "/positions", icon: Wallet, adminOnly: false },
  { name: "Performance", href: "/performance", icon: TrendingUp, adminOnly: false },
  { name: "Rebalance", href: "/rebalance", icon: RefreshCw, adminOnly: false },
  { name: "Trades", href: "/trades", icon: History, adminOnly: false },
  { name: "Admin", href: "/admin", icon: Settings, adminOnly: true },
];

export function MobileSidebar() {
  const pathname = usePathname();
  const { user } = useUser();
  const role = (user?.publicMetadata as { role?: string } | undefined)?.role;
  const isAdmin = role === "admin";
  const visibleNav = navigation.filter((item) => !item.adminOnly || isAdmin);

  return (
    <div className="flex flex-col h-full bg-sidebar">
      {/* Logo */}
      <div className="flex h-16 items-center px-4 border-b border-sidebar-border">
        <SheetClose asChild>
          <Link
            href="/"
            className="text-2xl font-semibold tracking-tight text-primary"
          >
            marketworks
          </Link>
        </SheetClose>
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-1 p-2">
        {visibleNav.map((item) => {
          const isActive = pathname === item.href;
          return (
            <SheetClose asChild key={item.name}>
              <Link
                href={item.href}
                className={cn(
                  "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-sidebar-primary text-sidebar-primary-foreground"
                    : "text-sidebar-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground"
                )}
              >
                <item.icon className="h-5 w-5" />
                <span>{item.name}</span>
              </Link>
            </SheetClose>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="border-t border-sidebar-border p-4">
        <p className="text-xs text-sidebar-foreground/60">
          Marketworks v1.0
        </p>
      </div>
    </div>
  );
}
