"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useUser } from "@clerk/nextjs";
import { cn } from "@/lib/utils";
import { SheetClose } from "@/components/ui/sheet";
import { getNavigation } from "@/lib/nav";

export function MobileSidebar() {
  const pathname = usePathname();
  const { user } = useUser();
  const role = (user?.publicMetadata as { role?: string } | undefined)?.role;
  const isAdmin = role === "admin";
  const visibleNav = getNavigation(isAdmin);

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
