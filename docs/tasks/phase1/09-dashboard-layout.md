# Task 9: Create Dashboard Layout with Sidebar Navigation

**Status**: `pending`
**Blocked By**: #7 (shadcn/ui Components)
**Blocks**: #12 (Deploy)

## Objective

Build the dashboard shell with sidebar navigation, sticky header, and responsive mobile support.

## Tasks

- [ ] Create dashboard layout with sidebar
- [ ] Build sidebar component with navigation links
- [ ] Add collapsible sidebar functionality
- [ ] Create sticky navbar with breadcrumbs
- [ ] Add user menu dropdown
- [ ] Implement responsive mobile sidebar (Sheet)

## src/app/(dashboard)/layout.tsx

```tsx
import { Sidebar } from "@/components/shared/sidebar";
import { Navbar } from "@/components/shared/navbar";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="flex min-h-screen">
      {/* Sidebar */}
      <Sidebar />

      {/* Main content */}
      <div className="flex-1 flex flex-col lg:pl-64">
        {/* Navbar */}
        <Navbar />

        {/* Page content */}
        <main className="flex-1 p-6">
          {children}
        </main>
      </div>
    </div>
  );
}
```

## src/components/shared/sidebar.tsx

```tsx
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  LayoutDashboard,
  Briefcase,
  TrendingUp,
  RefreshCw,
  History,
  Settings,
  ChevronLeft,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { useState } from "react";

const navigation = [
  { name: "Dashboard", href: "/", icon: LayoutDashboard },
  { name: "Portfolio", href: "/portfolio", icon: Briefcase },
  { name: "Performance", href: "/performance", icon: TrendingUp },
  { name: "Rebalance", href: "/rebalance", icon: RefreshCw },
  { name: "Trades", href: "/trades", icon: History },
  { name: "Admin", href: "/admin", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();
  const [collapsed, setCollapsed] = useState(false);

  return (
    <>
      {/* Desktop sidebar */}
      <aside
        className={cn(
          "fixed left-0 top-0 z-40 h-screen hidden lg:flex flex-col border-r bg-card transition-all duration-300",
          collapsed ? "w-16" : "w-64"
        )}
      >
        {/* Logo */}
        <div className="flex h-16 items-center justify-between px-4 border-b">
          {!collapsed && (
            <Link href="/" className="flex items-center gap-2">
              <div className="h-8 w-8 rounded-lg bg-primary flex items-center justify-center">
                <span className="text-primary-foreground font-bold">K</span>
              </div>
              <span className="font-semibold">Kite-Lab</span>
            </Link>
          )}
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setCollapsed(!collapsed)}
            className={cn(collapsed && "mx-auto")}
          >
            <ChevronLeft
              className={cn(
                "h-4 w-4 transition-transform",
                collapsed && "rotate-180"
              )}
            />
          </Button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 space-y-1 p-2">
          {navigation.map((item) => {
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.name}
                href={item.href}
                className={cn(
                  "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:bg-muted hover:text-foreground",
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
          <div className="border-t p-4">
            <p className="text-xs text-muted-foreground">
              Kite-Lab Dashboard v1.0
            </p>
          </div>
        )}
      </aside>
    </>
  );
}
```

## src/components/shared/navbar.tsx

```tsx
"use client";

import { useSession, signOut } from "next-auth/react";
import { usePathname } from "next/navigation";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Menu, Moon, Sun } from "lucide-react";
import { Sheet, SheetContent, SheetTrigger } from "@/components/ui/sheet";
import { MobileSidebar } from "./mobile-sidebar";
import { UniverseSelector } from "./universe-selector";
import { useTheme } from "next-themes";

// Breadcrumb mapping
const pathNames: Record<string, string> = {
  "/": "Dashboard",
  "/portfolio": "Portfolio",
  "/performance": "Performance",
  "/rebalance": "Rebalance",
  "/trades": "Trades",
  "/admin": "Admin",
};

export function Navbar() {
  const { data: session } = useSession();
  const pathname = usePathname();
  const { theme, setTheme } = useTheme();

  const pageName = pathNames[pathname] || "Dashboard";

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center gap-4 border-b bg-background px-4 lg:px-6">
      {/* Mobile menu button */}
      <Sheet>
        <SheetTrigger asChild>
          <Button variant="ghost" size="icon" className="lg:hidden">
            <Menu className="h-5 w-5" />
          </Button>
        </SheetTrigger>
        <SheetContent side="left" className="p-0 w-64">
          <MobileSidebar />
        </SheetContent>
      </Sheet>

      {/* Breadcrumb */}
      <div className="flex-1">
        <h1 className="text-lg font-semibold">{pageName}</h1>
      </div>

      {/* Universe Selector */}
      <UniverseSelector />

      {/* Theme toggle */}
      <Button
        variant="ghost"
        size="icon"
        onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
      >
        <Sun className="h-5 w-5 rotate-0 scale-100 transition-all dark:-rotate-90 dark:scale-0" />
        <Moon className="absolute h-5 w-5 rotate-90 scale-0 transition-all dark:rotate-0 dark:scale-100" />
        <span className="sr-only">Toggle theme</span>
      </Button>

      {/* User menu */}
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="ghost" className="relative h-8 w-8 rounded-full">
            <Avatar className="h-8 w-8">
              <AvatarImage src={session?.user?.image || ""} alt="User" />
              <AvatarFallback>
                {session?.user?.name?.charAt(0) || "U"}
              </AvatarFallback>
            </Avatar>
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent className="w-56" align="end">
          <DropdownMenuLabel>
            <div className="flex flex-col space-y-1">
              <p className="text-sm font-medium">{session?.user?.name}</p>
              <p className="text-xs text-muted-foreground">
                {session?.user?.email}
              </p>
            </div>
          </DropdownMenuLabel>
          <DropdownMenuSeparator />
          <DropdownMenuItem onClick={() => signOut()}>
            Sign out
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </header>
  );
}
```

## src/components/shared/mobile-sidebar.tsx

```tsx
"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  LayoutDashboard,
  Briefcase,
  TrendingUp,
  RefreshCw,
  History,
  Settings,
} from "lucide-react";
import { SheetClose } from "@/components/ui/sheet";

const navigation = [
  { name: "Dashboard", href: "/", icon: LayoutDashboard },
  { name: "Portfolio", href: "/portfolio", icon: Briefcase },
  { name: "Performance", href: "/performance", icon: TrendingUp },
  { name: "Rebalance", href: "/rebalance", icon: RefreshCw },
  { name: "Trades", href: "/trades", icon: History },
  { name: "Admin", href: "/admin", icon: Settings },
];

export function MobileSidebar() {
  const pathname = usePathname();

  return (
    <div className="flex flex-col h-full">
      {/* Logo */}
      <div className="flex h-16 items-center px-4 border-b">
        <Link href="/" className="flex items-center gap-2">
          <div className="h-8 w-8 rounded-lg bg-primary flex items-center justify-center">
            <span className="text-primary-foreground font-bold">K</span>
          </div>
          <span className="font-semibold">Kite-Lab</span>
        </Link>
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-1 p-2">
        {navigation.map((item) => {
          const isActive = pathname === item.href;
          return (
            <SheetClose asChild key={item.name}>
              <Link
                href={item.href}
                className={cn(
                  "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                  isActive
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:bg-muted hover:text-foreground"
                )}
              >
                <item.icon className="h-5 w-5" />
                <span>{item.name}</span>
              </Link>
            </SheetClose>
          );
        })}
      </nav>
    </div>
  );
}
```

## Install Avatar Component

```bash
npx shadcn-ui@latest add avatar
```

## src/app/(dashboard)/page.tsx (Placeholder)

```tsx
export default function DashboardPage() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">Dashboard</h2>
        <p className="text-muted-foreground">
          Welcome to Kite-Lab Portfolio Dashboard
        </p>
      </div>

      {/* Placeholder content */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {[1, 2, 3, 4].map((i) => (
          <div
            key={i}
            className="rounded-xl border bg-card p-6 shadow-sm"
          >
            <p className="text-sm text-muted-foreground">Metric {i}</p>
            <p className="text-2xl font-bold">--</p>
          </div>
        ))}
      </div>
    </div>
  );
}
```

## Verification

1. Start dev server: `npm run dev`
2. Sign in and verify:
   - Sidebar displays on desktop (≥1024px)
   - Sidebar collapses when clicking chevron
   - Mobile menu button appears on smaller screens
   - Sheet opens with navigation on mobile
   - User avatar and dropdown work
   - Theme toggle switches between light/dark
   - Breadcrumb shows current page name

## Notes

- Sidebar is fixed position on desktop, overlay sheet on mobile
- Navigation items highlight based on current pathname
- Theme persists via next-themes
- Universe selector placeholder (implemented in Task #10)

---

*Last updated: February 2026*
