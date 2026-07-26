"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useUser } from "@clerk/nextjs";
import { UserButton } from "@clerk/nextjs";
import { Button } from "@/components/ui/button";
import { Sheet, SheetClose, SheetContent, SheetTrigger, SheetTitle } from "@/components/ui/sheet";
import { BookOpen, Layers, Home as HomeIcon, LineChart, Menu, Settings, User as UserIcon } from "lucide-react";
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
      {/* Mobile menu — the WEBSITE pages (marketing surfaces) plus the
          app extras that have no bottom-nav slot. The dashboard sections
          themselves live in the bottom nav now (UX study D3 revision). */}
      <Sheet>
        <SheetTrigger asChild>
          <Button variant="ghost" size="icon" className="shrink-0 lg:hidden">
            <Menu className="h-5 w-5" />
            <span className="sr-only">Open site menu</span>
          </Button>
        </SheetTrigger>
        <SheetContent side="left" className="w-64 p-4">
          <SheetTitle className="sr-only">Site menu</SheetTitle>
          <div className="mt-6 flex flex-col gap-1">
            <span className="px-3 pb-1 text-[11px] font-semibold uppercase tracking-[0.1em] text-muted-foreground">
              Marketworks
            </span>
            {[
              { name: "Home", href: "/", icon: HomeIcon },
              { name: "Portfolios", href: "/portfolios", icon: Layers },
              { name: "Library", href: "/library", icon: BookOpen },
            ].map((item) => (
              <SheetClose asChild key={item.href}>
                <Link
                  href={item.href}
                  className="flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-foreground transition-colors hover:bg-primary/10"
                >
                  <item.icon className="h-4.5 w-4.5 text-muted-foreground" />
                  {item.name}
                </Link>
              </SheetClose>
            ))}
            <div className="my-2 border-t" />
            <span className="px-3 pb-1 text-[11px] font-semibold uppercase tracking-[0.1em] text-muted-foreground">
              Your account
            </span>
            {[
              ...(insightsItem ? [{ name: "Insights", href: "/insights", icon: LineChart }] : []),
              { name: "Account", href: "/account", icon: UserIcon },
              ...(isAdmin ? [{ name: "Admin", href: "/admin", icon: Settings }] : []),
            ].map((item) => (
              <SheetClose asChild key={item.href}>
                <Link
                  href={item.href}
                  className="flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-foreground transition-colors hover:bg-primary/10"
                >
                  <item.icon className="h-4.5 w-4.5 text-muted-foreground" />
                  {item.name}
                </Link>
              </SheetClose>
            ))}
          </div>
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
              <HomeIcon className="h-5 w-5" />
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
