"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useUser } from "@clerk/nextjs";
import { UserButton } from "@clerk/nextjs";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTrigger, SheetTitle } from "@/components/ui/sheet";
import { Home, Menu } from "lucide-react";
import { MobileSidebar } from "./mobile-sidebar";
import { UniverseSelector } from "./universe-selector";
import { PalettePicker } from "./palette-picker";
import { getInsightsNavItem } from "@/lib/nav";
import { cn } from "@/lib/utils";

const pathNames: Record<string, string> = {
  "/dashboard": "Overview",
  "/positions": "Open Positions",
  "/performance": "Performance",
  "/rebalance": "Upcoming Trades",
  "/trades": "Trade Log",
  "/insights": "Insights",
  "/admin": "Admin",
  "/account": "Account",
};

export function Navbar() {
  const pathname = usePathname();
  const { user } = useUser();
  const role = (user?.publicMetadata as { role?: string } | undefined)?.role;
  const isAdmin = role === "admin";
  const insightsItem = getInsightsNavItem(isAdmin);
  const insightsActive = pathname.startsWith("/insights");

  // eslint-disable-next-line security/detect-object-injection -- pathname is from Next's router (closed set of known route strings); pathNames is a module-level constant Record
  const pageName = pathNames[pathname] || "Overview";

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center gap-2 border-b bg-background px-3 sm:gap-4 sm:px-4 lg:px-6">
      {/* Mobile menu button */}
      <Sheet>
        <SheetTrigger asChild>
          <Button variant="ghost" size="icon" className="shrink-0 lg:hidden">
            <Menu className="h-5 w-5" />
            <span className="sr-only">Toggle menu</span>
          </Button>
        </SheetTrigger>
        <SheetContent side="left" className="p-0 w-64">
          <SheetTitle className="sr-only">Navigation Menu</SheetTitle>
          <MobileSidebar />
        </SheetContent>
      </Sheet>

      {/* Page title — doubles as the flex spacer. Hidden on mobile (each page
          carries its own in-content heading, and the narrow bar squeezed it to
          a lone truncated letter). */}
      <div className="min-w-0 flex-1">
        <h1 className="hidden truncate text-lg font-semibold sm:block">{pageName}</h1>
      </div>

      {/* Insights — a market-wide view, promoted out of the portfolio sidebar
          into the top bar. Icon-only on the smallest screens. */}
      {insightsItem && (
        <Link
          href={insightsItem.href}
          className={cn(
            "flex shrink-0 items-center gap-1.5 rounded-md px-2.5 py-1.5 text-sm font-medium transition-colors",
            insightsActive
              ? "bg-primary/10 text-primary"
              : "text-muted-foreground hover:bg-muted hover:text-foreground",
          )}
        >
          <insightsItem.icon className="h-4 w-4" />
          <span className="hidden sm:inline">{insightsItem.name}</span>
        </Link>
      )}

      {/* Right cluster — strategy selector + actions. The icon buttons each
          carry ~10px of transparent padding around their glyph, while the
          selector box and avatar are solid-edged. Kept at gap-2, that made the
          icon-to-icon gap (two paddings) read wider than the gaps next to the
          solid elements. Grouping the icon buttons with no gap between them
          collapses that double padding, so every visible glyph/edge sits an
          even ~18px apart. */}
      <div className="flex shrink-0 items-center gap-2">
        {/* Strategy selector — carries its own "Strategy" eyebrow label so it's
            clear what it picks. Visible on mobile portrait too (previously
            hidden under sm). */}
        <UniverseSelector />

        <div className="flex items-center">
          {/* Palette picker — Mint/Ocean/Amber/Coral/Charcoal/Midnight
              (Midnight is the dark theme; replaces the old sun/moon toggle) */}
          <PalettePicker />

          {/* Home — escape hatch back to the public marketing site. The
              dashboard is a separate app shell (sidebar nav), so signed-in
              users otherwise have no link out to the landing page. Hidden on
              mobile (space is tight there) — the hamburger's marketworks
              wordmark links home too. */}
          <Button variant="ghost" size="icon" asChild className="hidden sm:inline-flex">
            <Link href="/" aria-label="Marketworks home">
              <Home className="h-5 w-5" />
            </Link>
          </Button>
        </div>

        {/* User menu — Clerk-managed avatar, profile, sign-out. On sign-out
            the middleware redirects unauthed users to /sign-in automatically. */}
        <UserButton appearance={{ elements: { avatarBox: "h-9 w-9" } }} />
      </div>
    </header>
  );
}
